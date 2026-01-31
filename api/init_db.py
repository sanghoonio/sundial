from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from api.config import settings
from api.database import Base, engine
from api.models import *  # noqa: F401, F403 - import all models so Base.metadata is populated


async def init_database():
    """Create tables, default data, and workspace directories."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Create standalone FTS5 virtual table (no content-sync, no triggers)
        await conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
            USING fts5(id, title, content, tags)
        """))

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
        for key, value in [("ai_enabled", "false"), ("calendar_sync_enabled", "false")]:
            result = await session.execute(select(UserSettings).where(UserSettings.key == key))
            if result.scalar_one_or_none() is None:
                session.add(UserSettings(key=key, value=value))

        await session.commit()

    # Create workspace directories
    workspace = Path(settings.WORKSPACE_DIR).resolve()
    (workspace / "notes").mkdir(parents=True, exist_ok=True)
