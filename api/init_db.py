from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from api.config import settings
from api.database import Base, engine
from api.models import *  # noqa: F401, F403 - import all models so Base.metadata is populated


async def init_database():
    """Create tables, default data, and workspace directories."""
    # Ensure workspace directory exists before DB connection (SQLite needs it)
    workspace = Path(settings.WORKSPACE_DIR).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Create standalone FTS5 virtual table (no content-sync, no triggers)
        await conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
            USING fts5(id, title, content, tags)
        """))

        # Migrate: add caldav_href and etag columns to calendar_events
        for col, coltype in [("caldav_href", "VARCHAR"), ("etag", "VARCHAR")]:
            try:
                await conn.execute(text(
                    f"ALTER TABLE calendar_events ADD COLUMN {col} {coltype}"
                ))
            except Exception:
                pass  # column already exists

        # Migrate: add icon column to projects
        try:
            await conn.execute(text(
                "ALTER TABLE projects ADD COLUMN icon VARCHAR DEFAULT 'folder-kanban'"
            ))
        except Exception:
            pass  # column already exists

        # Migrate: add position column to projects
        try:
            await conn.execute(text(
                "ALTER TABLE projects ADD COLUMN position INTEGER DEFAULT 0"
            ))
            # Set initial positions based on created_at order
            await conn.execute(text("""
                UPDATE projects SET position = (
                    SELECT COUNT(*) FROM projects p2
                    WHERE p2.created_at < projects.created_at
                )
            """))
        except Exception:
            pass  # column already exists

        # Migrate: add recurrence columns to calendar_events
        for col, coltype in [
            ("rrule", "TEXT"),
            ("original_timezone", "VARCHAR"),
            ("recurrence_id", "VARCHAR"),
            ("recurring_event_id", "VARCHAR REFERENCES calendar_events(id) ON DELETE CASCADE"),
        ]:
            try:
                await conn.execute(text(
                    f"ALTER TABLE calendar_events ADD COLUMN {col} {coltype}"
                ))
            except Exception:
                pass  # column already exists

        # Migrate: add ip_address and user_agent columns to auth_tokens
        for col, coltype in [("ip_address", "VARCHAR"), ("user_agent", "VARCHAR")]:
            try:
                await conn.execute(text(
                    f"ALTER TABLE auth_tokens ADD COLUMN {col} {coltype}"
                ))
            except Exception:
                pass  # column already exists

        # Migrate: create task_notes junction table for multiple linked notes
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS task_notes (
                id VARCHAR PRIMARY KEY,
                task_id VARCHAR NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                note_id VARCHAR NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
                created_at DATETIME
            )
        """))

        # Migrate: copy existing source_note_id values to task_notes
        try:
            await conn.execute(text("""
                INSERT OR IGNORE INTO task_notes (id, task_id, note_id, created_at)
                SELECT 'tn_' || substr(hex(randomblob(4)), 1, 8), id, source_note_id, created_at
                FROM tasks
                WHERE source_note_id IS NOT NULL
            """))
        except Exception:
            pass  # already migrated

    # Seed default data
    from api.database import async_session
    from api.models.project import Project, ProjectMilestone
    from api.models.settings import UserSettings

    async with async_session() as session:
        # Create default Inbox project if it doesn't exist
        existing = await session.get(Project, "proj_inbox")
        if existing is None:
            inbox = Project(id="proj_inbox", name="Inbox", description="Default project for uncategorized tasks")
            session.add(inbox)
            await session.flush()

            for i, name in enumerate(["To Do", "In Progress", "Done"]):
                session.add(ProjectMilestone(project_id="proj_inbox", name=name, position=i))

        # Seed default user_settings
        from sqlalchemy import select
        for key, value in [("ai_enabled", "false"), ("calendar_sync_enabled", "false"), ("username", "admin")]:
            result = await session.execute(select(UserSettings).where(UserSettings.key == key))
            if result.scalar_one_or_none() is None:
                session.add(UserSettings(key=key, value=value))

        await session.commit()

    # Create workspace directories
    workspace = Path(settings.WORKSPACE_DIR).resolve()
    (workspace / "notes").mkdir(parents=True, exist_ok=True)
