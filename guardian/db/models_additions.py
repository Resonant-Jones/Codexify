"""
Proposed additions to guardian/db/models.py

These models align with tables currently created by GuardianDB
and heavily used in the API layer.

After review, merge these into guardian/db/models.py
"""
from __future__ import annotations
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Text, TIMESTAMP, Integer, BigInteger, Boolean, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

# Assuming Base is imported from guardian.db.models
# from guardian.db.models import Base

class ChatThread(Base):
    """
    Core conversation threads.

    Replaces raw SQL in GuardianDB.upgrade_db_schema()
    """
    __tablename__ = "chat_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    project_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('projects.id'))
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('chat_threads.id'))
    archived_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", back_populates="thread", cascade="all, delete-orphan")
    children: Mapped[list["ChatThread"]] = relationship("ChatThread", back_populates="parent", remote_side=[id])
    parent: Mapped["ChatThread | None"] = relationship("ChatThread", back_populates="children", remote_side=[parent_id])

    __mapper_args__ = {"eager_defaults": True}


class ChatMessage(Base):
    """
    Individual messages within threads.

    Replaces raw SQL in GuardianDB.upgrade_db_schema()
    """
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(Integer, ForeignKey('chat_threads.id', ondelete='CASCADE'), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # 'user', 'assistant', 'system'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    thread: Mapped["ChatThread"] = relationship("ChatThread", back_populates="messages")

    __mapper_args__ = {"eager_defaults": True}


class ConnectorConfig(Base):
    """
    Configuration for external service connectors (GitHub, GDrive, etc.)

    Replaces raw SQL in GuardianDB._ensure_connector_tables()
    """
    __tablename__ = "connector_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)  # 'github', 'gdrive', etc.
    config: Mapped[dict] = mapped_column(JSONB, server_default='{}', nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    runs: Mapped[list["ConnectorRun"]] = relationship("ConnectorRun", back_populates="config", cascade="all, delete-orphan")
    documents: Mapped[list["RawDocument"]] = relationship("RawDocument", back_populates="config", cascade="all, delete-orphan")

    __mapper_args__ = {"eager_defaults": True}


class ConnectorRun(Base):
    """
    Track connector sync job executions.

    Replaces raw SQL in GuardianDB._ensure_connector_tables()
    """
    __tablename__ = "connector_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    config_id: Mapped[int] = mapped_column(Integer, ForeignKey('connector_configs.id', ondelete='CASCADE'), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # 'running', 'succeeded', 'failed'
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    document_count: Mapped[int] = mapped_column(Integer, server_default='0', nullable=False)

    # Relationship
    config: Mapped["ConnectorConfig"] = relationship("ConnectorConfig", back_populates="runs")

    __mapper_args__ = {"eager_defaults": True}


class RawDocument(Base):
    """
    Raw documents ingested from connectors before processing.

    Replaces raw SQL in GuardianDB._ensure_connector_tables()
    """
    __tablename__ = "raw_documents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    config_id: Mapped[int] = mapped_column(Integer, ForeignKey('connector_configs.id', ondelete='CASCADE'), nullable=False)
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)  # GitHub issue #123, etc.
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    config: Mapped["ConnectorConfig"] = relationship("ConnectorConfig", back_populates="documents")

    __mapper_args__ = {"eager_defaults": True}


class SyncJob(Base):
    """
    Background sync job bookkeeping.

    Replaces raw SQL in GuardianDB.upgrade_db_schema()
    """
    __tablename__ = "sync_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connector_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # 'pending', 'running', 'completed', 'failed'
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, server_default='0', nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    metadata: Mapped[dict | None] = mapped_column(JSONB)

    __mapper_args__ = {"eager_defaults": True}


class AuditLog(Base):
    """
    Generic audit trail for all entity changes.

    Replaces migration 2fa2ab3faac6_add_audit_log_table.py
    """
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event: Mapped[str] = mapped_column(Text, nullable=False)  # 'create', 'update', 'delete', 'archive'
    entity: Mapped[str] = mapped_column(Text, nullable=False)  # 'chat_thread', 'chat_message', etc.
    entity_id: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __mapper_args__ = {"eager_defaults": True}


# Indexes
Index("ix_chat_messages_thread_id", ChatMessage.thread_id)
Index("ix_chat_messages_thread_created", ChatMessage.thread_id, ChatMessage.created_at)
Index("ix_chat_threads_parent_id", ChatThread.parent_id)
Index("ix_chat_threads_project_id", ChatThread.project_id)
Index("ix_chat_threads_user_id", ChatThread.user_id)
Index("ix_connector_runs_config_started", ConnectorRun.config_id, ConnectorRun.started_at)
Index("ix_raw_documents_config_external", RawDocument.config_id, RawDocument.external_id, unique=True)
Index("ix_sync_jobs_connector_created", SyncJob.connector_id, SyncJob.created_at)
Index("ix_audit_log_timestamp", AuditLog.timestamp.desc())
Index("ix_audit_log_entity", AuditLog.entity, AuditLog.entity_id)
