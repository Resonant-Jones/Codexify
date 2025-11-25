# guardian/db/models.py
"""
Postgres-only SQLAlchemy models for Guardian.

All schema is managed via Alembic migrations.
No raw DDL creation in application code.
"""
from __future__ import annotations
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    Text,
    TIMESTAMP,
    Integer,
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    func,
    CheckConstraint,
    UniqueConstraint,
    Float,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# =========================
# Projects
# =========================

class Project(Base):
    """Projects organize chat threads and resources."""
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon: Mapped[Optional[str]] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __mapper_args__ = {"eager_defaults": True}


# =========================
# Chat Threads & Messages
# =========================

class ChatThread(Base):
    """Main conversation threads."""
    __tablename__ = "chat_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    project_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('projects.id'))
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('chat_threads.id'))
    archived_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", back_populates="thread", cascade="all, delete-orphan")
    children: Mapped[list["ChatThread"]] = relationship("ChatThread", back_populates="parent")
    parent: Mapped[Optional["ChatThread"]] = relationship("ChatThread", back_populates="children", foreign_keys=[parent_id], remote_side=[id])

    __mapper_args__ = {"eager_defaults": True}


class ChatMessage(Base):
    """Individual messages within threads."""
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(Integer, ForeignKey('chat_threads.id', ondelete='CASCADE'), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # 'user', 'assistant', 'system'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    thread: Mapped["ChatThread"] = relationship("ChatThread", back_populates="messages")

    __mapper_args__ = {"eager_defaults": True}


# =========================
# Memory System
# =========================

class MemoryEntry(Base):
    """Memory entries organized by silo (ephemeral/midterm/longterm)."""
    __tablename__ = "memory_entries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255))
    silo: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(Text)
    pinned: Mapped[bool] = mapped_column(Boolean, server_default='false', nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("silo IN ('ephemeral', 'midterm', 'longterm')", name='memory_entries_silo_check'),
    )
    __mapper_args__ = {"eager_defaults": True}


# =========================
# Connectors
# =========================

class ConnectorConfig(Base):
    """Configuration for external service connectors (GitHub, GDrive, etc.)."""
    __tablename__ = "connector_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)  # 'github', 'gdrive', etc.
    config: Mapped[dict] = mapped_column(JSONB, server_default='{}', nullable=False)
    schedule: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    runs: Mapped[list["ConnectorRun"]] = relationship("ConnectorRun", back_populates="config", cascade="all, delete-orphan")
    documents: Mapped[list["RawDocument"]] = relationship("RawDocument", back_populates="config", cascade="all, delete-orphan")

    __mapper_args__ = {"eager_defaults": True}


class ConnectorRun(Base):
    """Track connector sync job executions."""
    __tablename__ = "connector_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    config_id: Mapped[int] = mapped_column(Integer, ForeignKey('connector_configs.id', ondelete='CASCADE'), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # 'running', 'succeeded', 'failed'
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    error: Mapped[Optional[str]] = mapped_column(Text)
    document_count: Mapped[int] = mapped_column(Integer, server_default='0', nullable=False)

    # Relationship
    config: Mapped["ConnectorConfig"] = relationship("ConnectorConfig", back_populates="runs")

    __mapper_args__ = {"eager_defaults": True}


class RawDocument(Base):
    """Raw documents ingested from connectors before processing."""
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
    """Background sync job bookkeeping."""
    __tablename__ = "sync_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connector_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # 'pending', 'running', 'completed', 'failed'
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, server_default='0', nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    job_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)  # Column name is 'metadata', attribute is 'job_metadata'

    __mapper_args__ = {"eager_defaults": True}


# =========================
# Event Outbox & Audit
# =========================

class EventOutbox(Base):
    """Durable event outbox for SSE/event replay."""
    __tablename__ = "events_outbox"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic: Mapped[Optional[str]] = mapped_column(String(128))
    payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(32), server_default="pending", nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), server_default="default", nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __mapper_args__ = {"eager_defaults": True}


class AuditLog(Base):
    """Generic audit trail for all entity changes."""
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event: Mapped[str] = mapped_column(Text, nullable=False)  # 'create', 'update', 'delete', 'archive'
    entity: Mapped[str] = mapped_column(Text, nullable=False)  # 'chat_thread', 'chat_message', etc.
    entity_id: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __mapper_args__ = {"eager_defaults": True}


# Legacy model (kept for backwards compat, consider deprecating)
class Message(Base):
    """
    Generic messages table (legacy).
    NOTE: Most code uses ChatMessage instead. This may be deprecated.
    """
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    thread_id: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), server_default="default", nullable=False)

    __mapper_args__ = {"eager_defaults": True}


# =========================
# Media Tables (Images & Documents)
# =========================

class GeneratedImage(Base):
    """AI-generated images (DALL-E, Stable Diffusion, etc.)."""
    __tablename__ = "generated_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    thread_id: Mapped[int] = mapped_column(Integer, ForeignKey('chat_threads.id', ondelete='CASCADE'), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    src_url: Mapped[str] = mapped_column(Text, nullable=False)  # Path or URL to image file
    prompt: Mapped[str] = mapped_column(Text, nullable=False)  # Generation prompt
    model: Mapped[str] = mapped_column(String(255), nullable=False)  # Model used (dall-e-3, sd-xl, etc.)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))  # Soft delete

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    thread: Mapped["ChatThread"] = relationship("ChatThread")

    __mapper_args__ = {"eager_defaults": True}


class UploadedImage(Base):
    """User-uploaded images."""
    __tablename__ = "uploaded_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    thread_id: Mapped[int] = mapped_column(Integer, ForeignKey('chat_threads.id', ondelete='CASCADE'), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    src_url: Mapped[str] = mapped_column(Text, nullable=False)  # Path or URL to image file
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    filesize: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Bytes
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)  # image/png, image/jpeg, etc.
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))  # Soft delete

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    thread: Mapped["ChatThread"] = relationship("ChatThread")

    __mapper_args__ = {"eager_defaults": True}


class GeneratedDocument(Base):
    """AI-generated documents (reports, summaries, etc.)."""
    __tablename__ = "generated_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    project_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('projects.id', ondelete='CASCADE'))
    thread_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('chat_threads.id', ondelete='CASCADE'))
    user_id: Mapped[Optional[str]] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Full document content
    format: Mapped[str] = mapped_column(String(32), nullable=False)  # txt, md, docx, pdf, html, json
    model: Mapped[str] = mapped_column(String(255), nullable=False)  # Model used for generation
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))  # Soft delete

    # Relationships
    project: Mapped[Optional["Project"]] = relationship("Project")
    thread: Mapped[Optional["ChatThread"]] = relationship("ChatThread")

    __table_args__ = (
        CheckConstraint("format IN ('txt', 'md', 'docx', 'pdf', 'html', 'json')", name='generated_documents_format_check'),
    )
    __mapper_args__ = {"eager_defaults": True}


class UploadedDocument(Base):
    """User-uploaded documents with full-text search."""
    __tablename__ = "uploaded_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    project_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('projects.id', ondelete='CASCADE'))
    thread_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('chat_threads.id', ondelete='CASCADE'))
    user_id: Mapped[Optional[str]] = mapped_column(String(255))
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    filesize: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Bytes
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)  # application/pdf, text/plain, etc.
    src_url: Mapped[str] = mapped_column(Text, nullable=False)  # Path or URL to file
    parsed_text: Mapped[Optional[str]] = mapped_column(Text)  # Extracted text for FTS
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))  # Soft delete

    # Relationships
    project: Mapped[Optional["Project"]] = relationship("Project")
    thread: Mapped[Optional["ChatThread"]] = relationship("ChatThread")

    __mapper_args__ = {"eager_defaults": True}


class TTSOutput(Base):
    """Text-to-speech synthesis outputs."""
    __tablename__ = "tts_outputs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('projects.id', ondelete='CASCADE'))
    thread_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('chat_threads.id', ondelete='CASCADE'))
    user_id: Mapped[Optional[str]] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text, nullable=False)  # Text that was synthesized
    voice: Mapped[Optional[str]] = mapped_column(String(128))  # Voice ID (e.g., "josh", "en-US-Standard-A")
    provider: Mapped[Optional[str]] = mapped_column(String(128))  # elevenlabs, google, local
    model: Mapped[Optional[str]] = mapped_column(String(255))  # Model version if applicable
    src_url: Mapped[Optional[str]] = mapped_column(Text)  # Path or URL to audio file
    duration_seconds: Mapped[Optional[float]] = mapped_column(Integer)  # Audio duration
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project: Mapped[Optional["Project"]] = relationship("Project")
    thread: Mapped[Optional["ChatThread"]] = relationship("ChatThread")

    __mapper_args__ = {"eager_defaults": True}


# =========================
# Document Linkage
# =========================

class ThreadDocument(Base):
    """Link chat threads to documents (autosave notes, attached files, etc.)."""
    __tablename__ = "thread_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(Integer, ForeignKey('chat_threads.id', ondelete='CASCADE'), nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)  # UUID of GeneratedDocument or UploadedDocument
    relation: Mapped[str] = mapped_column(String(64), server_default='autosave', nullable=False)  # 'autosave', 'attached', 'reference'
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("relation IN ('autosave', 'attached', 'reference')", name='thread_documents_relation_check'),
    )
    __mapper_args__ = {"eager_defaults": True}


# =========================
# Imprints, Personas, System Docs
# =========================


class Imprint(Base):
    """Imprint_Zero outputs persisted per user/project."""
    __tablename__ = "imprints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    guardian_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    style: Mapped[str | None] = mapped_column(Text, nullable=True)
    grammar_prefs: Mapped[dict] = mapped_column(JSON, server_default="{}", nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, server_default="{}", nullable=False)
    heat_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('draft','active','superseded')", name='imprints_status_check'),
    )


class Persona(Base):
    """User-editable persona text."""
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SystemDoc(Base):
    """Long-form system documents (constitutions, guidelines)."""
    __tablename__ = "system_docs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("scope IN ('global','project','user')", name='system_docs_scope_check'),
        UniqueConstraint('scope', 'owner_user_id', 'project_id', 'slug', name='uq_system_docs_scope_owner_project_slug'),
    )


class SystemDocLink(Base):
    """Links docs to user/project selections."""
    __tablename__ = "system_doc_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    system_doc_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_docs.id", ondelete="CASCADE"), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    doc: Mapped[SystemDoc] = relationship("SystemDoc")

    __table_args__ = (
        UniqueConstraint('user_id', 'project_id', 'system_doc_id', name='uq_system_doc_links_attachment'),
    )


# =========================
# Indexes
# =========================

# Chat indexes
Index("ix_chat_messages_thread_id", ChatMessage.thread_id)
Index("ix_chat_messages_thread_created", ChatMessage.thread_id, ChatMessage.created_at)
Index("ix_chat_threads_parent_id", ChatThread.parent_id)
Index("ix_chat_threads_project_id", ChatThread.project_id)
Index("ix_chat_threads_user_id", ChatThread.user_id)
Index("ix_chat_threads_updated", ChatThread.updated_at.desc())

# Memory indexes
Index("ix_memory_entries_silo", MemoryEntry.silo)
Index("ix_memory_entries_silo_updated", MemoryEntry.silo, MemoryEntry.updated_at)
Index("ix_memory_entries_user_silo", MemoryEntry.user_id, MemoryEntry.silo)

# Connector indexes
Index("ix_connector_runs_config_started", ConnectorRun.config_id, ConnectorRun.started_at.desc())
Index("ix_raw_documents_config_external", RawDocument.config_id, RawDocument.external_id, unique=True)
Index("ix_sync_jobs_connector_created", SyncJob.connector_id, SyncJob.created_at)

# Audit indexes
Index("ix_audit_log_timestamp", AuditLog.timestamp.desc())
Index("ix_audit_log_entity", AuditLog.entity, AuditLog.entity_id)

# Event outbox indexes
Index("ix_events_outbox_tenant_id", EventOutbox.tenant_id)
Index("ix_events_outbox_status_created", EventOutbox.status, EventOutbox.created_at)

# Legacy indexes
Index("ix_messages_thread_id_timestamp", Message.thread_id, Message.timestamp)

# Media indexes
Index("ix_generated_images_project", GeneratedImage.project_id)
Index("ix_generated_images_thread", GeneratedImage.thread_id)
Index("ix_generated_images_user", GeneratedImage.user_id)
Index("ix_generated_images_created", GeneratedImage.created_at.desc())

Index("ix_uploaded_images_project", UploadedImage.project_id)
Index("ix_uploaded_images_thread", UploadedImage.thread_id)
Index("ix_uploaded_images_user", UploadedImage.user_id)
Index("ix_uploaded_images_mime", UploadedImage.mime_type)
Index("ix_uploaded_images_created", UploadedImage.created_at.desc())

Index("ix_generated_documents_project", GeneratedDocument.project_id)
Index("ix_generated_documents_thread", GeneratedDocument.thread_id)
Index("ix_generated_documents_format", GeneratedDocument.format)
Index("ix_generated_documents_created", GeneratedDocument.created_at.desc())

Index("ix_uploaded_documents_project", UploadedDocument.project_id)
Index("ix_uploaded_documents_thread", UploadedDocument.thread_id)
Index("ix_uploaded_documents_mime", UploadedDocument.mime_type)
Index("ix_uploaded_documents_created", UploadedDocument.created_at.desc())

Index("ix_tts_outputs_project", TTSOutput.project_id)
Index("ix_tts_outputs_thread", TTSOutput.thread_id)
Index("ix_tts_outputs_provider", TTSOutput.provider)
Index("ix_tts_outputs_created", TTSOutput.created_at.desc())

class SharedLink(Base):
    """Secure shareable links for threads and documents with optional expiry."""
    __tablename__ = "shared_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 'thread' or 'document'
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)  # ID of thread or document
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # URL-safe secure token
    expires_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))  # Optional expiry
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("target_type IN ('thread', 'document')", name='shared_links_target_type_check'),
    )
    __mapper_args__ = {"eager_defaults": True}


# =========================
# Collaboration Permissions & Audit
# =========================

class CollaborationPermission(Base):
    """Per-document permissions for collaborative editing."""
    __tablename__ = "collaboration_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)  # UUID of GeneratedDocument
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    can_edit: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    can_comment: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    granted_by: Mapped[str] = mapped_column(String(255), nullable=False)  # User ID who granted access
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_collab_perms_doc_user", "document_id", "user_id", unique=True),
        Index("ix_collab_perms_document", "document_id"),
        Index("ix_collab_perms_user", "user_id"),
    )
    __mapper_args__ = {"eager_defaults": True}


class CollaborationAuditLog(Base):
    """Audit trail for all collaboration session events."""
    __tablename__ = "collaboration_audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(64), nullable=False)  # 'presence.join', 'presence.leave', 'update', 'permission.granted', 'permission.revoked'
    payload: Mapped[Optional[dict]] = mapped_column(JSONB)  # Action-specific data (e.g., content hash, permission details)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_collab_audit_doc", "document_id"),
        Index("ix_collab_audit_doc_timestamp", "document_id", "timestamp"),
        Index("ix_collab_audit_user", "user_id"),
    )
    __mapper_args__ = {"eager_defaults": True}
