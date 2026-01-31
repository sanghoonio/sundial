import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from api.database import Base


def generate_note_id() -> str:
    return f"note_{uuid.uuid4().hex[:12]}"


class Note(Base):
    __tablename__ = "notes"

    id = Column(String, primary_key=True, default=generate_note_id)
    title = Column(String, nullable=False)
    filepath = Column(String, unique=True, nullable=False)
    content = Column(Text, default="")
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tags = relationship("Tag", secondary="note_tags", back_populates="notes")
    outgoing_links = relationship("NoteLink", foreign_keys="NoteLink.source_note_id", back_populates="source_note", cascade="all, delete-orphan")
    incoming_links = relationship("NoteLink", foreign_keys="NoteLink.target_note_id", back_populates="target_note", cascade="all, delete-orphan")
    calendar_links = relationship("NoteCalendarLink", back_populates="note", cascade="all, delete-orphan")
    project = relationship("Project", back_populates="notes")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(String, primary_key=True, default=lambda: f"tag_{uuid.uuid4().hex[:8]}")
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    notes = relationship("Note", secondary="note_tags", back_populates="tags")


class NoteTag(Base):
    __tablename__ = "note_tags"

    note_id = Column(String, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(String, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    ai_suggested = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class NoteLink(Base):
    __tablename__ = "note_links"

    id = Column(String, primary_key=True, default=lambda: f"link_{uuid.uuid4().hex[:8]}")
    source_note_id = Column(String, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    target_note_id = Column(String, ForeignKey("notes.id", ondelete="CASCADE"), nullable=True)
    target_identifier = Column(String, nullable=False)  # raw [[link]] text
    link_type = Column(String, default="note")  # note, task, event

    source_note = relationship("Note", foreign_keys=[source_note_id], back_populates="outgoing_links")
    target_note = relationship("Note", foreign_keys=[target_note_id], back_populates="incoming_links")
