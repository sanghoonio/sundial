import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from api.database import Base


def generate_event_id() -> str:
    return f"event_{uuid.uuid4().hex[:12]}"


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(String, primary_key=True, default=generate_event_id)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    all_day = Column(Boolean, default=False)
    location = Column(String, default="")
    calendar_source = Column(String, default="local")  # local, caldav
    calendar_id = Column(String, default="")
    external_id = Column(String, nullable=True)
    caldav_href = Column(String, nullable=True)
    etag = Column(String, nullable=True)
    synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    note_links = relationship("NoteCalendarLink", back_populates="event", cascade="all, delete-orphan")


class NoteCalendarLink(Base):
    __tablename__ = "note_calendar_links"

    note_id = Column(String, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    event_id = Column(String, ForeignKey("calendar_events.id", ondelete="CASCADE"), primary_key=True)
    ai_suggested = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    note = relationship("Note", back_populates="calendar_links")
    event = relationship("CalendarEvent", back_populates="note_links")
