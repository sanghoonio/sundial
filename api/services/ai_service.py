import json
import logging
import re

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.settings import UserSettings
from api.services.ai_prompts import (
    SYSTEM_AUTO_TAG,
    SYSTEM_CHAT,
    SYSTEM_DAILY_SUGGESTIONS,
    SYSTEM_EXTRACT_TASKS,
    SYSTEM_LINK_EVENTS,
)

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_CONTENT_CHARS = 8000


async def _get_config(db: AsyncSession) -> dict:
    """Read AI config from user_settings table."""
    keys = ["openrouter_api_key", "openrouter_model", "ai_enabled"]
    result = await db.execute(
        select(UserSettings).where(UserSettings.key.in_(keys))
    )
    rows = {row.key: row.value for row in result.scalars().all()}
    return {
        "api_key": rows.get("openrouter_api_key", ""),
        "model": rows.get("openrouter_model", "anthropic/claude-sonnet-4"),
        "enabled": rows.get("ai_enabled", "false").lower() == "true",
    }


async def _call_openrouter(
    api_key: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> str:
    """Call OpenRouter chat completions API. Returns the assistant message content."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Sundial",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(OPENROUTER_URL, json=payload, headers=headers)

        if resp.status_code == 429:
            raise RuntimeError("Rate limited by OpenRouter. Please try again later.")
        if resp.status_code == 401:
            raise RuntimeError("Invalid OpenRouter API key. Check your settings.")

        resp.raise_for_status()
        data = resp.json()

    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("No response from AI model.")

    return choices[0]["message"]["content"]


def _parse_json_response(text: str) -> any:
    """Parse JSON from LLM response, stripping markdown code block wrappers."""
    text = text.strip()
    # Strip ```json ... ``` or ``` ... ```
    match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?\s*```$", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


def _truncate(content: str) -> str:
    if len(content) > MAX_CONTENT_CHARS:
        return content[:MAX_CONTENT_CHARS] + "\n...(truncated)"
    return content


async def chat(
    message: str,
    note_id: str | None,
    context: str | None,
    db: AsyncSession,
) -> dict:
    """Chat completion with optional note context."""
    config = await _get_config(db)
    if not config["enabled"]:
        return {"error": "AI is disabled. Enable it in Settings."}
    if not config["api_key"]:
        return {"error": "OpenRouter API key not configured. Add it in Settings > AI."}

    messages = [{"role": "system", "content": SYSTEM_CHAT}]

    if context:
        messages.append({"role": "system", "content": f"Note context:\n{_truncate(context)}"})

    messages.append({"role": "user", "content": message})

    try:
        response = await _call_openrouter(
            config["api_key"], config["model"], messages, temperature=0.5, max_tokens=2048,
        )
        return {"response": response}
    except Exception as e:
        logger.exception("Chat call failed")
        return {"error": str(e)}


async def auto_tag(
    content: str,
    existing_tags: list[str],
    db: AsyncSession,
) -> list[str]:
    """Suggest tags for note content. Returns list of tag name strings."""
    config = await _get_config(db)
    if not config["enabled"] or not config["api_key"]:
        return []

    user_content = f"Existing tags in system: {json.dumps(existing_tags)}\n\nNote content:\n{_truncate(content)}"
    messages = [
        {"role": "system", "content": SYSTEM_AUTO_TAG},
        {"role": "user", "content": user_content},
    ]

    try:
        response = await _call_openrouter(
            config["api_key"], config["model"], messages, temperature=0.2, max_tokens=256,
        )
        tags = _parse_json_response(response)
        if isinstance(tags, list):
            return [str(t).strip().lower() for t in tags if t]
    except Exception:
        logger.exception("Auto-tag failed")

    return []


async def extract_tasks(
    content: str,
    note_title: str,
    db: AsyncSession,
) -> list[dict]:
    """Extract actionable tasks from note content. Returns list of {title, description, priority}."""
    config = await _get_config(db)
    if not config["enabled"] or not config["api_key"]:
        return []

    user_content = f"Note title: {note_title}\n\nNote content:\n{_truncate(content)}"
    messages = [
        {"role": "system", "content": SYSTEM_EXTRACT_TASKS},
        {"role": "user", "content": user_content},
    ]

    try:
        response = await _call_openrouter(
            config["api_key"], config["model"], messages, temperature=0.2, max_tokens=512,
        )
        tasks = _parse_json_response(response)
        if isinstance(tasks, list):
            return tasks
    except Exception:
        logger.exception("Extract tasks failed")

    return []


async def link_events(
    content: str,
    events: list[dict],
    db: AsyncSession,
) -> list[str]:
    """Match note content to calendar events. Returns list of event IDs."""
    config = await _get_config(db)
    if not config["enabled"] or not config["api_key"]:
        return []

    if not events:
        return []

    events_desc = json.dumps(events, default=str)
    user_content = f"Calendar events:\n{events_desc}\n\nNote content:\n{_truncate(content)}"
    messages = [
        {"role": "system", "content": SYSTEM_LINK_EVENTS},
        {"role": "user", "content": user_content},
    ]

    try:
        response = await _call_openrouter(
            config["api_key"], config["model"], messages, temperature=0.1, max_tokens=256,
        )
        ids = _parse_json_response(response)
        if isinstance(ids, list):
            return [str(i) for i in ids]
    except Exception:
        logger.exception("Link events failed")

    return []


async def daily_suggestions(
    events: list[dict],
    tasks: list[dict],
    notes: list[dict],
    db: AsyncSession,
) -> dict:
    """Generate daily overview. Returns {summary, priorities, connections}."""
    config = await _get_config(db)
    if not config["enabled"] or not config["api_key"]:
        return {"summary": "", "priorities": [], "connections": []}

    context_parts = []
    if events:
        context_parts.append(f"Today's events:\n{json.dumps(events, default=str)}")
    if tasks:
        context_parts.append(f"Pending tasks:\n{json.dumps(tasks, default=str)}")
    if notes:
        context_parts.append(f"Recent notes:\n{json.dumps(notes, default=str)}")

    if not context_parts:
        return {"summary": "No events, tasks, or notes for today.", "priorities": [], "connections": []}

    messages = [
        {"role": "system", "content": SYSTEM_DAILY_SUGGESTIONS},
        {"role": "user", "content": "\n\n".join(context_parts)},
    ]

    try:
        response = await _call_openrouter(
            config["api_key"], config["model"], messages, temperature=0.4, max_tokens=512,
        )
        result = _parse_json_response(response)
        if isinstance(result, dict):
            return {
                "summary": result.get("summary", ""),
                "priorities": result.get("priorities", []),
                "connections": result.get("connections", []),
            }
    except Exception:
        logger.exception("Daily suggestions failed")

    return {"summary": "", "priorities": [], "connections": []}
