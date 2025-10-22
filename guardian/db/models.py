# guardian/db/models.py
from __future__ import annotations
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, TIMESTAMP, JSON, BigInteger, Integer, func, Index

class Base(DeclarativeBase):
    pass

# Matches queries you’re already doing: SELECT id,name,description,created_at,updated_at FROM projects...
class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    __mapper_args__ = {"eager_defaults": True}

# Your logs show you ALTERing this to add tenant_id; include it at creation so no ALTER is needed.
class EventOutbox(Base):
    __tablename__ = "events_outbox"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic: Mapped[str | None] = mapped_column(String(128))
    payload: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), server_default="pending", nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), server_default="default", nullable=False)
    created_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    __mapper_args__ = {"eager_defaults": True}

# Your startup does: DELETE FROM memory_entries WHERE silo = 'midterm' AND updated_at < ...
class MemoryEntry(Base):
    __tablename__ = "memory_entries"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    silo: Mapped[str] = mapped_column(String(64), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value_json: Mapped[dict | None] = mapped_column("value_json", JSON)  # or Text if you prefer
    updated_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    __mapper_args__ = {"eager_defaults": True}

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    thread_id: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. "user", "assistant", "system"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), server_default="default", nullable=False)
    __mapper_args__ = {"eager_defaults": True}

Index("ix_memory_entries_silo_updated_at", MemoryEntry.silo, MemoryEntry.updated_at)
Index("ix_events_outbox_tenant_id", EventOutbox.tenant_id)
Index("ix_messages_thread_id_timestamp", Message.thread_id, Message.timestamp)