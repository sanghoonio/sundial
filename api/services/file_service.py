import os
import re
from datetime import datetime, timezone
from pathlib import Path

import frontmatter

from api.config import settings


def _workspace_path() -> Path:
    return Path(settings.WORKSPACE_DIR).resolve()


def _notes_dir() -> Path:
    return _workspace_path() / "notes"


def _slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:80]


def _date_subdir(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%d")


def build_filepath(title: str, created_at: datetime | None = None) -> str:
    """Build a relative filepath like notes/2025-01-30/my-note-title.md"""
    date_dir = _date_subdir(created_at)
    slug = _slugify(title)
    return f"notes/{date_dir}/{slug}.md"


def ensure_dir(filepath: str) -> None:
    full = _workspace_path() / filepath
    full.parent.mkdir(parents=True, exist_ok=True)


def write_note_file(
    filepath: str,
    note_id: str,
    title: str,
    content: str,
    created_at: datetime,
    updated_at: datetime,
    tags: list[str] | None = None,
    project_id: str | None = None,
    linked_tasks: list[str] | None = None,
    linked_events: list[str] | None = None,
) -> None:
    metadata = {
        "id": note_id,
        "title": title,
        "created": created_at.isoformat(),
        "updated": updated_at.isoformat(),
    }
    if tags:
        metadata["tags"] = tags
    if project_id:
        metadata["project_id"] = project_id
    if linked_tasks:
        metadata["linked_tasks"] = linked_tasks
    if linked_events:
        metadata["linked_events"] = linked_events

    post = frontmatter.Post(content, **metadata)

    full_path = _workspace_path() / filepath
    ensure_dir(filepath)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))


def read_note_file(filepath: str) -> dict | None:
    full_path = _workspace_path() / filepath
    if not full_path.exists():
        return None

    with open(full_path, "r", encoding="utf-8") as f:
        post = frontmatter.load(f)

    return {
        "metadata": dict(post.metadata),
        "content": post.content,
    }


def delete_note_file(filepath: str) -> bool:
    full_path = _workspace_path() / filepath
    if full_path.exists():
        full_path.unlink()
        # Clean up empty date directories
        parent = full_path.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
        return True
    return False


def list_note_files() -> list[str]:
    notes_dir = _notes_dir()
    if not notes_dir.exists():
        return []
    return [
        str(p.relative_to(_workspace_path()))
        for p in notes_dir.rglob("*.md")
    ]
