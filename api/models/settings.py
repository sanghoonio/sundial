import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from api.database import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    key = Column(String, primary_key=True)
    value = Column(Text, default="")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id = Column(String, primary_key=True, default=lambda: f"tok_{secrets.token_hex(8)}")
    token_hash = Column(String, unique=True, index=True, nullable=False)
    token_type = Column(String, nullable=False, default="session")  # session | api_key
    name = Column(String, nullable=True)
    scope = Column(String, nullable=False, default="read_write")  # read | read_write
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AIProcessingQueue(Base):
    __tablename__ = "ai_processing_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String, nullable=False, default="note")
    entity_id = Column(String, nullable=False)
    operation = Column(String, nullable=False)  # auto_tag, extract_tasks, link_events
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
