import io
import json
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import select, text, delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.database import get_db
from api.models.note import Note, Tag, NoteTag, NoteLink
from api.models.task import Task, TaskChecklist
from api.models.project import Project, ProjectMilestone
from api.models.calendar import CalendarEvent, NoteCalendarLink
from api.models.settings import UserSettings
from api.utils.auth import get_current_user

router = APIRouter(tags=["workspace"], dependencies=[Depends(get_current_user)])

WORKSPACE_DIR = Path(settings.WORKSPACE_DIR)


def _row_to_dict(row) -> dict:
    """Convert a SQLAlchemy model instance to a JSON-serializable dict."""
    d = {}
    for col in row.__table__.columns:
        val = getattr(row, col.name)
        if val is not None and hasattr(val, 'isoformat'):
            val = val.isoformat()
        d[col.name] = val
    return d


@router.get("/export/workspace")
async def export_workspace(db: AsyncSession = Depends(get_db)):
    """Export the entire workspace as a ZIP file containing data.json and note files."""
    data: dict[str, list[dict]] = {}

    # Export all tables
    tables = [
        ("notes", Note),
        ("tags", Tag),
        ("note_tags", NoteTag),
        ("note_links", NoteLink),
        ("tasks", Task),
        ("task_checklists", TaskChecklist),
        ("projects", Project),
        ("project_milestones", ProjectMilestone),
        ("calendar_events", CalendarEvent),
        ("note_calendar_links", NoteCalendarLink),
        ("user_settings", UserSettings),
    ]

    for key, model in tables:
        result = await db.execute(select(model))
        rows = result.scalars().all()
        data[key] = [_row_to_dict(r) for r in rows]

    # Build ZIP in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add data.json
        zf.writestr("data.json", json.dumps(data, indent=2, default=str))

        # Add note files from workspace/notes/
        notes_dir = WORKSPACE_DIR / "notes"
        if notes_dir.is_dir():
            for filepath in notes_dir.rglob("*"):
                if filepath.is_file():
                    arcname = "notes/" + str(filepath.relative_to(notes_dir))
                    zf.write(filepath, arcname)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=sundial-backup.zip"},
    )


@router.post("/import/workspace")
async def import_workspace(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Restore workspace from a ZIP backup. Clears existing data first."""
    content = await file.read()
    buf = io.BytesIO(content)

    with zipfile.ZipFile(buf, 'r') as zf:
        # Validate structure
        names = zf.namelist()
        if "data.json" not in names:
            return {"error": "Invalid backup: missing data.json"}

        raw = zf.read("data.json")
        data = json.loads(raw)

    # Clear existing data in reverse dependency order
    await db.execute(delete(NoteCalendarLink))
    await db.execute(delete(TaskChecklist))
    await db.execute(delete(NoteTag))
    await db.execute(delete(NoteLink))
    await db.execute(delete(Task))
    await db.execute(delete(CalendarEvent))
    await db.execute(delete(ProjectMilestone))
    await db.execute(delete(Project))
    await db.execute(delete(Tag))
    await db.execute(delete(Note))
    await db.execute(delete(UserSettings))
    await db.commit()

    # Restore data from JSON
    model_map = {
        "projects": Project,
        "project_milestones": ProjectMilestone,
        "tags": Tag,
        "notes": Note,
        "note_tags": NoteTag,
        "note_links": NoteLink,
        "tasks": Task,
        "task_checklists": TaskChecklist,
        "calendar_events": CalendarEvent,
        "note_calendar_links": NoteCalendarLink,
        "user_settings": UserSettings,
    }

    counts: dict[str, int] = {}
    for key, model in model_map.items():
        rows = data.get(key, [])
        for row_data in rows:
            # Filter to only known columns
            valid_cols = {c.name for c in model.__table__.columns}
            filtered = {k: v for k, v in row_data.items() if k in valid_cols}
            db.add(model(**filtered))
        counts[key] = len(rows)

    await db.commit()

    # Restore note files
    notes_dir = WORKSPACE_DIR / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(content), 'r') as zf:
        restored_files = 0
        for name in zf.namelist():
            if name.startswith("notes/") and not name.endswith("/"):
                rel = name[len("notes/"):]
                target = notes_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(name))
                restored_files += 1

    # Rebuild FTS5 index
    try:
        await db.execute(text("DELETE FROM notes_fts"))
        await db.execute(text("""
            INSERT INTO notes_fts (id, title, content, tags)
            SELECT n.id, n.title, n.content,
                   COALESCE((SELECT GROUP_CONCAT(t.name, ' ')
                             FROM note_tags nt JOIN tags t ON nt.tag_id = t.id
                             WHERE nt.note_id = n.id), '')
            FROM notes n
        """))
        await db.commit()
    except Exception:
        pass

    return {
        "status": "ok",
        "restored": counts,
        "files": restored_files,
    }
