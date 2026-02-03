"""Parse and serialize block-delimited note content.

Block format uses HTML comments that are invisible in standard markdown renderers:

    <!-- block:md -->
    Markdown text here.
    <!-- /block:md -->

    <!-- block:chat -->
    <!-- chat:user -->
    User message
    <!-- chat:assistant -->
    Assistant reply
    <!-- /block:chat -->

If content has no block delimiters, it is treated as a single markdown block.
"""

from __future__ import annotations

import re
import uuid

BLOCK_OPEN = re.compile(r"^<!-- block:(md|chat) -->$", re.MULTILINE)
BLOCK_CLOSE_MD = "<!-- /block:md -->"
BLOCK_CLOSE_CHAT = "<!-- /block:chat -->"
CHAT_ROLE = re.compile(r"^<!-- chat:(user|assistant) -->$", re.MULTILINE)
CHAT_PROMPT = re.compile(r"^<!-- chat:prompt -->$", re.MULTILINE)


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def parse_blocks(content: str) -> list[dict]:
    """Split content by HTML-comment delimiters into a list of block dicts.

    Each block is either:
      {"id": str, "type": "md", "content": str, "messages": []}
      {"id": str, "type": "chat", "content": "", "messages": [{"role": str, "content": str}, ...]}

    If content has no delimiters, returns a single md block wrapping the entire content.
    """
    if not content or "<!-- block:" not in content:
        return [{"id": _new_id(), "type": "md", "content": content or "", "messages": [], "initialPrompt": ""}]

    blocks: list[dict] = []
    pos = 0

    for m in BLOCK_OPEN.finditer(content):
        block_type = m.group(1)
        start = m.end()  # right after the opening tag

        if block_type == "md":
            close_tag = BLOCK_CLOSE_MD
        else:
            close_tag = BLOCK_CLOSE_CHAT

        end = content.find(close_tag, start)
        if end == -1:
            # Unclosed block -- take rest of content
            inner = content[start:]
        else:
            inner = content[start:end]

        inner = inner.strip("\n")

        if block_type == "md":
            blocks.append({
                "id": _new_id(),
                "type": "md",
                "content": inner,
                "messages": [],
                "initialPrompt": "",
            })
        else:
            messages, initial_prompt = _parse_chat_messages(inner)
            blocks.append({
                "id": _new_id(),
                "type": "chat",
                "content": "",
                "messages": messages,
                "initialPrompt": initial_prompt,
            })

        if end != -1:
            pos = end + len(close_tag)

    # If no blocks were found (regex matched nothing), fallback to single md block
    if not blocks:
        return [{"id": _new_id(), "type": "md", "content": content, "messages": [], "initialPrompt": ""}]

    return blocks


def _parse_chat_messages(inner: str) -> tuple[list[dict], str]:
    """Parse chat block content into a list of {role, content} dicts and initial prompt.

    Returns (messages, initialPrompt).
    """
    messages: list[dict] = []
    initial_prompt = ""

    # Check for prompt section first
    prompt_match = CHAT_PROMPT.search(inner)
    if prompt_match:
        # Find where the prompt content ends (at first chat:user/assistant tag or end)
        prompt_start = prompt_match.end()
        role_match = CHAT_ROLE.search(inner, prompt_start)
        if role_match:
            initial_prompt = inner[prompt_start:role_match.start()].strip()
            # Continue parsing messages from after prompt
            inner_for_messages = inner[role_match.start():]
        else:
            # No messages, just prompt
            initial_prompt = inner[prompt_start:].strip()
            return messages, initial_prompt
    else:
        inner_for_messages = inner

    parts = CHAT_ROLE.split(inner_for_messages)

    # parts alternates: [text_before, role, text, role, text, ...]
    # The first element is text before any role tag (usually empty)
    i = 1  # skip leading text
    while i < len(parts) - 1:
        role = parts[i]
        text = parts[i + 1].strip()
        if text:
            messages.append({"role": role, "content": text})
        i += 2

    return messages, initial_prompt


def serialize_blocks(blocks: list[dict]) -> str:
    """Convert a list of block dicts back into the delimited string format."""
    if not blocks:
        return ""

    # If there's exactly one markdown block, store as plain content (no delimiters)
    if len(blocks) == 1 and blocks[0].get("type") == "md":
        return blocks[0].get("content", "")

    parts: list[str] = []
    for block in blocks:
        btype = block.get("type", "md")
        if btype == "md":
            parts.append(f"<!-- block:md -->\n{block.get('content', '')}\n<!-- /block:md -->")
        elif btype == "chat":
            chat_lines: list[str] = []
            # Include initial prompt if present
            initial_prompt = block.get("initialPrompt", "")
            if initial_prompt:
                chat_lines.append("<!-- chat:prompt -->")
                chat_lines.append(initial_prompt)
            for msg in block.get("messages", []):
                chat_lines.append(f"<!-- chat:{msg['role']} -->")
                chat_lines.append(msg["content"])
            chat_inner = "\n".join(chat_lines)
            parts.append(f"<!-- block:chat -->\n{chat_inner}\n<!-- /block:chat -->")

    return "\n\n".join(parts)


def extract_markdown_text(content: str) -> str:
    """Extract only the markdown block text from content (for previews).

    Strips chat blocks entirely, returning only markdown content.
    """
    blocks = parse_blocks(content)
    md_parts = [b["content"] for b in blocks if b["type"] == "md" and b["content"]]
    return "\n\n".join(md_parts)
