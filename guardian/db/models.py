# guardian/db/models.py
"""
Postgres-only SQLAlchemy models for Guardian.

All schema is managed via Alembic migrations.
No raw DDL creation in application code.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from guardian.protocol_tokens import EmbeddingLifecycleStatus


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


EMBEDDING_LIFECYCLE_VALUES_SQL = "','".join(
    status.value for status in EmbeddingLifecycleStatus
)
UPLOADED_DOCUMENT_EMBEDDING_STATUS_CHECK = (
    f"embedding_status IN ('{EMBEDDING_LIFECYCLE_VALUES_SQL}')"
)


# =========================
# Projects
# =========================


class Project(Base):
    """Projects organize chat threads and resources."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(16))
    identity_depth: Mapped[str] = mapped_column(
        String(16), nullable=False, default="light", server_default="light"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "identity_depth IN ('light','deep')",
            name="projects_identity_depth_check",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


# =========================
# Chat Threads & Messages
# =========================


class ChatThread(Base):
    """Main conversation threads."""

    __tablename__ = "chat_threads"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(
        Text, server_default="", nullable=False
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id")
    )
    active_profile_id: Mapped[str | None] = mapped_column(String(128))
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chat_threads.id")
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    is_diary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    diary_mode: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    exclude_from_identity: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    modeling_excluded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    messages: Mapped[list[ChatMessage]] = relationship(
        "ChatMessage", back_populates="thread", cascade="all, delete-orphan"
    )
    children: Mapped[list[ChatThread]] = relationship(
        "ChatThread", back_populates="parent"
    )
    parent: Mapped[ChatThread | None] = relationship(
        "ChatThread",
        back_populates="children",
        foreign_keys=[parent_id],
        remote_side=[id],
    )

    __mapper_args__ = {"eager_defaults": True}


class ChatMessage(Base):
    """Individual messages within threads."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    thread_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # 'user', 'assistant', 'system'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    event_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    kind: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="chat"
    )
    extra_meta: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    thread: Mapped[ChatThread] = relationship(
        "ChatThread", back_populates="messages"
    )

    __mapper_args__ = {"eager_defaults": True}


# =========================
# Personal Facts
# =========================


class PersonalFact(Base):
    """Correctable facts about a user."""

    __tablename__ = "personal_facts"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="candidate"
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.5"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    last_confirmed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    evidence: Mapped[list[PersonalFactEvidence]] = relationship(
        "PersonalFactEvidence",
        back_populates="fact",
        cascade="all, delete-orphan",
    )
    revisions: Mapped[list[PersonalFactRevision]] = relationship(
        "PersonalFactRevision",
        back_populates="fact",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('candidate', 'verified', 'disputed', 'archived')",
            name="personal_facts_status_check",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="personal_facts_confidence_check",
        ),
        Index(
            "ix_personal_facts_user_status", "user_id", "status", "is_active"
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class PersonalFactEvidence(Base):
    """Evidence backing a personal fact."""

    __tablename__ = "personal_fact_evidence"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    fact_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("personal_facts.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
    )
    excerpt: Mapped[str | None] = mapped_column(Text)
    modality: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="text"
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.5"
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_meta: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    fact: Mapped[PersonalFact] = relationship(
        "PersonalFact", back_populates="evidence"
    )
    source_message: Mapped[ChatMessage | None] = relationship("ChatMessage")

    __mapper_args__ = {"eager_defaults": True}


class PersonalFactRevision(Base):
    """Audit trail for personal fact updates."""

    __tablename__ = "personal_fact_revisions"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    fact_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("personal_facts.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    field_changed: Mapped[str | None] = mapped_column(String(64))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    fact: Mapped[PersonalFact] = relationship(
        "PersonalFact", back_populates="revisions"
    )

    __mapper_args__ = {"eager_defaults": True}


# =========================
# Memory System
# =========================


class MemoryEntry(Base):
    """Memory entries organized by silo (ephemeral/midterm/longterm)."""

    __tablename__ = "memory_entries"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str | None] = mapped_column(String(255))
    silo: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(Text)
    pinned: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "silo IN ('ephemeral', 'midterm', 'longterm')",
            name="memory_entries_silo_check",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


# =========================
# Connectors
# =========================


class ConnectorConfig(Base):
    """Configuration for external service connectors (GitHub, GDrive, etc.)."""

    __tablename__ = "connector_configs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # 'github', 'gdrive', etc.
    config: Mapped[dict] = mapped_column(
        JSONB, server_default="{}", nullable=False
    )
    schedule: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    runs: Mapped[list[ConnectorRun]] = relationship(
        "ConnectorRun", back_populates="config", cascade="all, delete-orphan"
    )
    documents: Mapped[list[RawDocument]] = relationship(
        "RawDocument", back_populates="config", cascade="all, delete-orphan"
    )

    __mapper_args__ = {"eager_defaults": True}


class ConnectorRun(Base):
    """Track connector sync job executions."""

    __tablename__ = "connector_runs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    config_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("connector_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # 'running', 'succeeded', 'failed'
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    error: Mapped[str | None] = mapped_column(Text)
    document_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )

    # Relationship
    config: Mapped[ConnectorConfig] = relationship(
        "ConnectorConfig", back_populates="runs"
    )

    __mapper_args__ = {"eager_defaults": True}


class RawDocument(Base):
    """Raw documents ingested from connectors before processing."""

    __tablename__ = "raw_documents"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    config_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("connector_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(
        String(512), nullable=False
    )  # GitHub issue #123, etc.
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    config: Mapped[ConnectorConfig] = relationship(
        "ConnectorConfig", back_populates="documents"
    )

    __mapper_args__ = {"eager_defaults": True}


class SyncJob(Base):
    """Background sync job bookkeeping."""

    __tablename__ = "sync_jobs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    connector_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # 'pending', 'running', 'completed', 'failed'
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    attempts: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    job_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB
    )  # Column name is 'metadata', attribute is 'job_metadata'

    __mapper_args__ = {"eager_defaults": True}


class OAuthConnection(Base):
    """OAuth connection state per user/provider/mode."""

    __tablename__ = "oauth_connections"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="[]",
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="pending"
    )
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text)
    encrypted_access_token: Mapped[str | None] = mapped_column(Text)
    relay_grant_id: Mapped[str | None] = mapped_column(String(255))
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    last_refresh_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "provider",
            "mode",
            name="uq_oauth_connections_user_provider_mode",
        ),
        CheckConstraint(
            "mode IN ('node_local', 'relay_broker')",
            name="ck_oauth_connections_mode",
        ),
        CheckConstraint(
            "status IN ('pending', 'connected', 'error', 'disconnected')",
            name="ck_oauth_connections_status",
        ),
        Index("ix_oauth_connections_user_provider", "user_id", "provider"),
    )

    __mapper_args__ = {"eager_defaults": True}


class ToolJob(Base):
    """Durable tool orchestration job state."""

    __tablename__ = "tool_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tool_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    request_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result_json: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    error_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed')",
            name="tool_jobs_status_check",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


# =========================
# Inference Provider State
# =========================


class InferenceProvider(Base):
    """Provider configuration state used by inference routing control-plane."""

    __tablename__ = "inference_providers"

    provider_id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    provider_type: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="100"
    )
    default_model_id: Mapped[str | None] = mapped_column(Text)
    capabilities: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="{}",
    )
    provider_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    runtime_state: Mapped[InferenceProviderRuntime | None] = relationship(
        "InferenceProviderRuntime",
        back_populates="provider",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "priority >= 0",
            name="ck_inference_providers_priority_nonnegative",
        ),
        Index("ix_inference_providers_enabled", "enabled"),
        Index("ix_inference_providers_priority", "priority"),
    )

    __mapper_args__ = {"eager_defaults": True}


class InferenceProviderRuntime(Base):
    """Runtime health state for each configured inference provider."""

    __tablename__ = "inference_provider_runtime"

    provider_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("inference_providers.provider_id", ondelete="CASCADE"),
        primary_key=True,
    )
    health_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="unknown"
    )
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    last_success_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    last_failure_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    cooldown_until: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    avg_latency_ms: Mapped[float | None] = mapped_column(Float)
    error_rate: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    provider: Mapped[InferenceProvider] = relationship(
        "InferenceProvider", back_populates="runtime_state"
    )

    __table_args__ = (
        CheckConstraint(
            "health_status IN ('unknown','healthy','degraded','unavailable')",
            name="ck_inference_provider_runtime_health_status",
        ),
        CheckConstraint(
            "consecutive_failures >= 0",
            name="ck_inference_provider_runtime_consecutive_failures_nonnegative",
        ),
        CheckConstraint(
            "error_rate IS NULL OR (error_rate >= 0 AND error_rate <= 1)",
            name="ck_inference_provider_runtime_error_rate_bounds",
        ),
        Index(
            "ix_inference_provider_runtime_health_status",
            "health_status",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


# =========================
# Event Outbox & Audit
# =========================


class EventOutbox(Base):
    """Durable event outbox for SSE/event replay."""

    __tablename__ = "events_outbox"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    topic: Mapped[str | None] = mapped_column(String(128))
    payload: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(
        String(32), server_default="pending", nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64), server_default="default", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __mapper_args__ = {"eager_defaults": True}


class EventGraphEvent(Base):
    """Durable audit/lineage event row with idempotent write key."""

    __tablename__ = "event_graph_events"

    event_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    actor_user_id: Mapped[str | None] = mapped_column(String(255))
    project_id: Mapped[int | None] = mapped_column(Integer)
    thread_id: Mapped[int | None] = mapped_column(Integer)
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(255))
    idempotency_key: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    parent_event_id: Mapped[int | None] = mapped_column(BigInteger)
    payload_json: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql")
    )

    __mapper_args__ = {"eager_defaults": True}


class AuditLog(Base):
    """Generic audit trail for all entity changes."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    event: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # 'create', 'update', 'delete', 'archive'
    entity: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # 'chat_thread', 'chat_message', etc.
    entity_id: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __mapper_args__ = {"eager_defaults": True}


# New ORM model: BrowserApproval
class BrowserApproval(Base):
    """Control-plane approval records for browser/agent operations."""

    __tablename__ = "browser_approvals"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str | None] = mapped_column(String(512))

    # Matches index: ix_browser_approvals_status
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    requested_by: Mapped[str | None] = mapped_column(String(255))
    request_reason: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[str | None] = mapped_column(String(255))
    decision_reason: Mapped[str | None] = mapped_column(Text)

    # Matches index: ix_browser_approvals_created_at
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','APPROVED','DENIED')",
            name="browser_approvals_status_check",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


# =========================
# Browser Audit Log & Guardian Event Log
# =========================


class BrowserAuditLog(Base):
    """Control-plane audit log for browser/agent operations."""

    __tablename__ = "browser_audit_log"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    approval_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("browser_approvals.id", ondelete="SET NULL"),
        nullable=True,
    )

    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str | None] = mapped_column(String(512))

    # Matches index: ix_browser_audit_log_status
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    actor: Mapped[str | None] = mapped_column(String(255))
    detail: Mapped[str | None] = mapped_column(Text)

    # Matches index: ix_browser_audit_log_created_at
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    __mapper_args__ = {"eager_defaults": True}


class GuardianEventLog(Base):
    """Append-only event log for Guardian control-plane diagnostics."""

    __tablename__ = "guardian_event_log"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    ts: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    persona_tag: Mapped[str] = mapped_column(Text, nullable=False)
    thread_id: Mapped[str | None] = mapped_column(Text)
    message_id: Mapped[str | None] = mapped_column(Text)

    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    payload: Mapped[dict | None] = mapped_column(JSONB)

    __mapper_args__ = {"eager_defaults": True}


# Legacy model (kept for backwards compat, consider deprecating)
class Message(Base):
    """
    Generic messages table (legacy).
    NOTE: Most code uses ChatMessage instead. This may be deprecated.
    """

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    thread_id: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64), server_default="default", nullable=False
    )

    __mapper_args__ = {"eager_defaults": True}


# =========================
# Media Tables (Images & Documents)
# =========================


class MediaAsset(Base):
    """Canonical identity for ingested media assets."""

    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    thread_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chat_threads.id", ondelete="CASCADE")
    )
    user_id: Mapped[str | None] = mapped_column(String(255))
    media_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    provenance: Mapped[str] = mapped_column(String(32), nullable=False)
    source_tag: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="uploaded"
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    deterministic_id: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    system_name: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_prefix: Mapped[str] = mapped_column(String(255), nullable=False)
    src_url: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128))
    filesize: Mapped[int | None] = mapped_column(BigInteger)
    ingested_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    __table_args__ = (
        CheckConstraint(
            "media_kind IN ('document', 'image', 'audio', 'video', 'other')",
            name="media_assets_media_kind_check",
        ),
        CheckConstraint(
            "provenance IN ('uploaded', 'generated', 'imported', 'system')",
            name="media_assets_provenance_check",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class MediaAlias(Base):
    """Human-facing aliases bound to canonical media assets."""

    __tablename__ = "media_aliases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    asset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    alias_normalized: Mapped[str] = mapped_column(String(512), nullable=False)
    alias_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "alias_type IN ('original_name', 'prompt', 'user_alias', 'system_generated')",
            name="media_aliases_alias_type_check",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class GeneratedImage(Base):
    """AI-generated images (DALL-E, Stable Diffusion, etc.)."""

    __tablename__ = "generated_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    thread_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    src_url: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Path or URL to image file
    prompt: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Generation prompt
    model: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Model used (dall-e-3, sd-xl, etc.)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )  # Soft delete

    # Relationships
    project: Mapped[Project] = relationship("Project")
    thread: Mapped[ChatThread] = relationship("ChatThread")

    __mapper_args__ = {"eager_defaults": True}


class UploadedImage(Base):
    """User-uploaded images."""

    __tablename__ = "uploaded_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    thread_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    src_url: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Path or URL to image file
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    filesize: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Bytes
    mime_type: Mapped[str] = mapped_column(
        String(128), nullable=False
    )  # image/png, image/jpeg, etc.
    source_tag: Mapped[str | None] = mapped_column(
        String(64)
    )  # uploaded | generated | other
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )  # Soft delete

    # Relationships
    project: Mapped[Project] = relationship("Project")
    thread: Mapped[ChatThread] = relationship("ChatThread")

    __mapper_args__ = {"eager_defaults": True}


class GeneratedDocument(Base):
    """AI-generated documents (reports, summaries, etc.)."""

    __tablename__ = "generated_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    thread_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chat_threads.id", ondelete="CASCADE")
    )
    user_id: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Full document content
    format: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # txt, md, docx, pdf, html, json
    model: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Model used for generation
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )  # Soft delete

    # Relationships
    project: Mapped[Project] = relationship("Project")
    thread: Mapped[ChatThread | None] = relationship("ChatThread")

    __table_args__ = (
        CheckConstraint(
            "format IN ('txt', 'md', 'docx', 'pdf', 'html', 'json')",
            name="generated_documents_format_check",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class UploadedDocument(Base):
    """User-uploaded documents with full-text search."""

    __tablename__ = "uploaded_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE")
    )
    thread_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chat_threads.id", ondelete="CASCADE")
    )
    user_id: Mapped[str | None] = mapped_column(String(255))
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    filesize: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Bytes
    mime_type: Mapped[str] = mapped_column(
        String(128), nullable=False
    )  # application/pdf, text/plain, etc.
    src_url: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Path or URL to file
    source_tag: Mapped[str | None] = mapped_column(
        String(64)
    )  # uploaded | generated | other
    parsed_text: Mapped[str | None] = mapped_column(
        Text
    )  # Extracted text for FTS
    embedding_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=EmbeddingLifecycleStatus.PENDING.value,
    )
    embedding_error: Mapped[str | None] = mapped_column(Text)
    embedding_started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    embedding_completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )  # Soft delete

    # Relationships
    project: Mapped[Project | None] = relationship("Project")
    thread: Mapped[ChatThread | None] = relationship("ChatThread")

    __table_args__ = (
        CheckConstraint(
            UPLOADED_DOCUMENT_EMBEDDING_STATUS_CHECK,
            name="uploaded_documents_embedding_status_check",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class TTSOutput(Base):
    """Text-to-speech synthesis outputs."""

    __tablename__ = "tts_outputs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE")
    )
    thread_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chat_threads.id", ondelete="CASCADE")
    )
    user_id: Mapped[str | None] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Text that was synthesized
    voice: Mapped[str | None] = mapped_column(
        String(128)
    )  # Voice ID (e.g., "josh", "en-US-Standard-A")
    provider: Mapped[str | None] = mapped_column(
        String(128)
    )  # elevenlabs, google, local
    model: Mapped[str | None] = mapped_column(
        String(255)
    )  # Model version if applicable
    src_url: Mapped[str | None] = mapped_column(
        Text
    )  # Path or URL to audio file
    duration_seconds: Mapped[float | None] = mapped_column(
        Integer
    )  # Audio duration
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    project: Mapped[Project | None] = relationship("Project")
    thread: Mapped[ChatThread | None] = relationship("ChatThread")

    __mapper_args__ = {"eager_defaults": True}


class MessageAudioAsset(Base):
    """Message-linked synthesized audio assets for cacheable playback."""

    __tablename__ = "message_audio_assets"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    voice: Mapped[str] = mapped_column(String(128), nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    src_url: Mapped[str] = mapped_column(Text, nullable=False)
    internal_format: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="wav"
    )
    delivery_variants_json: Mapped[dict] = mapped_column(
        JSONB, server_default="{}", nullable=False
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    filesize_bytes: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    message: Mapped[ChatMessage] = relationship("ChatMessage")

    __table_args__ = (
        UniqueConstraint(
            "message_id",
            "provider",
            "voice",
            "text_hash",
            name="uq_message_audio_assets_message_provider_voice_texthash",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


# =========================
# Document Linkage
# =========================


class ThreadDocument(Base):
    """Link chat threads to documents (autosave notes, attached files, etc.)."""

    __tablename__ = "thread_documents"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    thread_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )  # UUID of GeneratedDocument or UploadedDocument
    relation: Mapped[str] = mapped_column(
        String(64), server_default="autosave", nullable=False
    )  # 'autosave', 'attached', 'reference'
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "relation IN ('autosave', 'attached', 'reference')",
            name="thread_documents_relation_check",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class ProjectDocumentLink(Base):
    """Explicit project-level attachment for documents used by project RAG."""

    __tablename__ = "project_document_links"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    attached_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    attached_by: Mapped[str | None] = mapped_column(String(255))

    __table_args__ = (
        CheckConstraint(
            "document_type IN ('generated', 'uploaded')",
            name="project_document_links_type_check",
        ),
        UniqueConstraint(
            "project_id",
            "document_id",
            "document_type",
            name="uq_project_document_links_scope",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


# =========================
# Imprints, Personas, System Docs
# =========================


class Imprint(Base):
    """Imprint_Zero outputs persisted per user/project."""

    __tablename__ = "imprints"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    guardian_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    style: Mapped[str | None] = mapped_column(Text, nullable=True)
    grammar_prefs: Mapped[dict] = mapped_column(
        JSON, server_default="{}", nullable=False
    )
    metrics: Mapped[dict] = mapped_column(
        JSON, server_default="{}", nullable=False
    )
    heat_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','superseded')",
            name="imprints_status_check",
        ),
    )


class Persona(Base):
    """User-editable persona text."""

    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        String(64), nullable=False, default="user"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SystemDoc(Base):
    """Long-form system documents (constitutions, guidelines)."""

    __tablename__ = "system_docs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "scope IN ('global','project','user')",
            name="system_docs_scope_check",
        ),
        UniqueConstraint(
            "scope",
            "owner_user_id",
            "project_id",
            "slug",
            name="uq_system_docs_scope_owner_project_slug",
        ),
    )


class SystemDocLink(Base):
    """Links docs to user/project selections."""

    __tablename__ = "system_doc_links"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    system_doc_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("system_docs.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    doc: Mapped[SystemDoc] = relationship("SystemDoc")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "project_id",
            "system_doc_id",
            name="uq_system_doc_links_attachment",
        ),
    )


# =========================
# Agent Orchestration
# =========================


class AgentDeployment(Base):
    """Immutable deployment definition for delegated agent flows."""

    __tablename__ = "agent_deployments"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    deployment_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    flow_id: Mapped[str] = mapped_column(String(128), nullable=False)
    thread_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chat_threads.id", ondelete="SET NULL")
    )
    spec_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    spec_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_state: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="supervised"
    )
    unlocked_for_unsupervised: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    unlocked_by: Mapped[str | None] = mapped_column(String(255))
    unlocked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "trust_state IN ('supervised', 'unlocked')",
            name="agent_deployments_trust_state_check",
        ),
        CheckConstraint(
            "status IN ('active', 'canceled', 'archived')",
            name="agent_deployments_status_check",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class AgentRun(Base):
    """Durable run state for a deployed delegated agent execution."""

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    deployment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("agent_deployments.id", ondelete="CASCADE"),
        nullable=False,
    )
    thread_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chat_threads.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="queued"
    )
    runtime_target: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="container"
    )
    rollback_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="auto"
    )
    rollback_applied: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    rollback_reason: Mapped[str | None] = mapped_column(Text)
    worktree_id: Mapped[str | None] = mapped_column(String(128))
    worktree_path: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'escalated', 'canceled', 'failed', 'succeeded')",
            name="agent_runs_status_check",
        ),
        CheckConstraint(
            "runtime_target IN ('container', 'terminal')",
            name="agent_runs_runtime_target_check",
        ),
        CheckConstraint(
            "rollback_mode IN ('auto', 'manual')",
            name="agent_runs_rollback_mode_check",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class AgentRunStep(Base):
    """Step-level lifecycle records for a delegated run."""

    __tablename__ = "agent_run_steps"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    step_id: Mapped[str] = mapped_column(String(128), nullable=False)
    primitive: Mapped[str] = mapped_column(String(64), nullable=False)
    is_mutating: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="pending"
    )
    schema_valid: Mapped[bool | None] = mapped_column(Boolean)
    spec_alignment_ok: Mapped[bool | None] = mapped_column(Boolean)
    tests_passed: Mapped[bool | None] = mapped_column(Boolean)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "step_index",
            name="uq_agent_run_steps_run_step_index",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'escalated', 'canceled')",
            name="agent_run_steps_status_check",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class AgentRunAttempt(Base):
    """Attempt-level diagnostics for deterministic adaptive retry."""

    __tablename__ = "agent_run_attempts"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    run_step_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("agent_run_steps.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="running"
    )
    fail_count: Mapped[int | None] = mapped_column(Integer)
    fail_signature: Mapped[str | None] = mapped_column(String(128))
    diff_added: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    diff_deleted: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    error_category: Mapped[str | None] = mapped_column(String(64))
    progress_made: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    stderr_excerpt: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "run_step_id",
            "attempt_index",
            name="uq_agent_run_attempts_step_attempt_index",
        ),
        CheckConstraint(
            "status IN ('running', 'failed', 'succeeded', 'escalated')",
            name="agent_run_attempts_status_check",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class AgentRunArtifact(Base):
    """Artifacts and receipts emitted by delegated runs and steps."""

    __tablename__ = "agent_run_artifacts"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_step_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent_run_steps.id", ondelete="CASCADE")
    )
    attempt_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent_run_attempts.id", ondelete="SET NULL")
    )
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    uri: Mapped[str | None] = mapped_column(Text)
    content_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __mapper_args__ = {"eager_defaults": True}


class AgentConfidenceReport(Base):
    """Guardian-derived confidence reports for step and task decisions."""

    __tablename__ = "agent_confidence_reports"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_step_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent_run_steps.id", ondelete="CASCADE")
    )
    step_index: Mapped[int | None] = mapped_column(Integer)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String(64), nullable=False)
    factors_json: Mapped[dict] = mapped_column(
        "factors", JSONB, nullable=False, server_default="{}"
    )
    model_self_confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "scope IN ('step', 'task')",
            name="agent_confidence_reports_scope_check",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class AgentEscalation(Base):
    """Durable escalation records for paused or blocked delegated runs."""

    __tablename__ = "agent_escalations"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_step_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent_run_steps.id", ondelete="CASCADE")
    )
    step_index: Mapped[int | None] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="open"
    )
    preserved_worktree: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    payload_json: Mapped[dict] = mapped_column(
        "payload", JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    __table_args__ = (
        CheckConstraint(
            "severity IN ('soft', 'hard')",
            name="agent_escalations_severity_check",
        ),
        CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved', 'canceled')",
            name="agent_escalations_status_check",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class AgentEvent(Base):
    """Append-only event graph stream for delegated run lifecycle events."""

    __tablename__ = "agent_events"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_step_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent_run_steps.id", ondelete="CASCADE")
    )
    attempt_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent_run_attempts.id", ondelete="SET NULL")
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(
        "payload", JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __mapper_args__ = {"eager_defaults": True}


class AgentReflection(Base):
    """Derived reflection notes for steps and runs (non-canonical)."""

    __tablename__ = "agent_reflections"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_step_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent_run_steps.id", ondelete="CASCADE")
    )
    reflection_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    derived_from: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "reflection_kind IN ('step_note', 'session_summary')",
            name="agent_reflections_kind_check",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


# =========================
# Indexes
# =========================

# Chat indexes
Index("ix_chat_messages_thread_id", ChatMessage.thread_id)
Index(
    "ix_chat_messages_thread_created",
    ChatMessage.thread_id,
    ChatMessage.created_at,
)
Index("ix_chat_threads_parent_id", ChatThread.parent_id)
Index("ix_chat_threads_project_id", ChatThread.project_id)
Index("ix_chat_threads_user_id", ChatThread.user_id)
Index("ix_chat_threads_updated", ChatThread.updated_at.desc())

# Memory indexes
Index("ix_memory_entries_silo", MemoryEntry.silo)
Index(
    "ix_memory_entries_silo_updated", MemoryEntry.silo, MemoryEntry.updated_at
)
Index("ix_memory_entries_user_silo", MemoryEntry.user_id, MemoryEntry.silo)

# Connector indexes
Index(
    "ix_connector_runs_config_started",
    ConnectorRun.config_id,
    ConnectorRun.started_at.desc(),
)
Index(
    "ix_raw_documents_config_external",
    RawDocument.config_id,
    RawDocument.external_id,
    unique=True,
)
Index(
    "ix_sync_jobs_connector_created", SyncJob.connector_id, SyncJob.created_at
)
Index("ix_tool_jobs_created_at", ToolJob.created_at)
Index("ix_tool_jobs_status", ToolJob.status)

# Audit indexes
Index("ix_audit_log_timestamp", AuditLog.timestamp.desc())
Index("ix_audit_log_entity", AuditLog.entity, AuditLog.entity_id)

# Event outbox indexes
Index("ix_events_outbox_tenant_id", EventOutbox.tenant_id)
Index(
    "ix_events_outbox_status_created",
    EventOutbox.status,
    EventOutbox.created_at,
)
Index(
    "ix_event_graph_event_type_occurred",
    EventGraphEvent.event_type,
    EventGraphEvent.occurred_at,
)
Index(
    "ix_event_graph_thread_occurred",
    EventGraphEvent.thread_id,
    EventGraphEvent.occurred_at,
)
Index(
    "ix_event_graph_entity",
    EventGraphEvent.entity_type,
    EventGraphEvent.entity_id,
)

# Legacy indexes
Index("ix_messages_thread_id_timestamp", Message.thread_id, Message.timestamp)

# Media indexes
Index("ix_media_assets_project", MediaAsset.project_id)
Index("ix_media_assets_thread", MediaAsset.thread_id)
Index("ix_media_assets_content_hash", MediaAsset.content_hash)
Index("ix_media_assets_deterministic_id", MediaAsset.deterministic_id)
Index("ix_media_assets_ingested", MediaAsset.ingested_at.desc())
Index(
    "ix_media_assets_kind_provenance",
    MediaAsset.media_kind,
    MediaAsset.provenance,
)
Index(
    "uq_media_assets_active_identity",
    MediaAsset.project_id,
    MediaAsset.media_kind,
    MediaAsset.provenance,
    MediaAsset.content_hash,
    unique=True,
    postgresql_where=text("deleted_at IS NULL"),
)
Index("ix_media_aliases_asset_id", MediaAlias.asset_id)
Index("ix_media_aliases_alias_normalized", MediaAlias.alias_normalized)
Index("ix_media_aliases_alias_type", MediaAlias.alias_type)

Index("ix_generated_images_asset_id", GeneratedImage.asset_id)
Index("ix_generated_images_project", GeneratedImage.project_id)
Index("ix_generated_images_thread", GeneratedImage.thread_id)
Index("ix_generated_images_user", GeneratedImage.user_id)
Index("ix_generated_images_created", GeneratedImage.created_at.desc())

Index("ix_uploaded_images_asset_id", UploadedImage.asset_id)
Index("ix_uploaded_images_project", UploadedImage.project_id)
Index("ix_uploaded_images_thread", UploadedImage.thread_id)
Index("ix_uploaded_images_user", UploadedImage.user_id)
Index("ix_uploaded_images_mime", UploadedImage.mime_type)
Index("ix_uploaded_images_created", UploadedImage.created_at.desc())

Index("ix_generated_documents_project", GeneratedDocument.project_id)
Index("ix_generated_documents_thread", GeneratedDocument.thread_id)
Index("ix_generated_documents_format", GeneratedDocument.format)
Index("ix_generated_documents_created", GeneratedDocument.created_at.desc())

Index("ix_uploaded_documents_asset_id", UploadedDocument.asset_id)
Index("ix_uploaded_documents_project", UploadedDocument.project_id)
Index("ix_uploaded_documents_thread", UploadedDocument.thread_id)
Index("ix_uploaded_documents_mime", UploadedDocument.mime_type)
Index("ix_uploaded_documents_created", UploadedDocument.created_at.desc())

Index(
    "ix_project_document_links_project_enabled",
    ProjectDocumentLink.project_id,
    ProjectDocumentLink.is_enabled,
)
Index(
    "ix_project_document_links_document",
    ProjectDocumentLink.document_type,
    ProjectDocumentLink.document_id,
)
Index(
    "ix_project_document_links_attached",
    ProjectDocumentLink.attached_at.desc(),
)

Index("ix_tts_outputs_project", TTSOutput.project_id)
Index("ix_tts_outputs_thread", TTSOutput.thread_id)
Index("ix_tts_outputs_provider", TTSOutput.provider)
Index("ix_tts_outputs_created", TTSOutput.created_at.desc())
Index("ix_agent_deployments_thread_id", AgentDeployment.thread_id)
Index("ix_agent_deployments_spec_hash", AgentDeployment.spec_hash)
Index("ix_agent_deployments_status", AgentDeployment.status)
Index("ix_agent_runs_deployment_id", AgentRun.deployment_id)
Index("ix_agent_runs_thread_id", AgentRun.thread_id)
Index("ix_agent_runs_status", AgentRun.status)
Index("ix_agent_run_steps_run_id", AgentRunStep.run_id)
Index("ix_agent_run_steps_status", AgentRunStep.status)
Index("ix_agent_run_attempts_step_id", AgentRunAttempt.run_step_id)
Index("ix_agent_run_attempts_signature", AgentRunAttempt.fail_signature)
Index("ix_agent_run_artifacts_run_id", AgentRunArtifact.run_id)
Index("ix_agent_run_artifacts_type", AgentRunArtifact.artifact_type)
Index("ix_agent_confidence_reports_run_id", AgentConfidenceReport.run_id)
Index(
    "ix_agent_confidence_reports_scope_step",
    AgentConfidenceReport.scope,
    AgentConfidenceReport.step_index,
)
Index("ix_agent_escalations_run_id", AgentEscalation.run_id)
Index("ix_agent_escalations_status", AgentEscalation.status)
Index("ix_agent_events_run_id", AgentEvent.run_id)
Index("ix_agent_events_type", AgentEvent.event_type)
Index("ix_agent_reflections_run_id", AgentReflection.run_id)
Index("ix_message_audio_assets_message", MessageAudioAsset.message_id)
Index(
    "ix_message_audio_assets_provider_voice_created",
    MessageAudioAsset.provider,
    MessageAudioAsset.voice,
    MessageAudioAsset.created_at.desc(),
)


class SharedLink(Base):
    """Secure shareable links for threads and documents with optional expiry."""

    __tablename__ = "shared_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    target_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # 'thread' or 'document'
    target_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # ID of thread or document
    token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )  # URL-safe secure token
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )  # Optional expiry
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "target_type IN ('thread', 'document')",
            name="shared_links_target_type_check",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


# =========================
# Collaboration Permissions & Audit
# =========================


class CollaborationPermission(Base):
    """Per-document permissions for collaborative editing."""

    __tablename__ = "collaboration_permissions"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )  # UUID of GeneratedDocument
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    can_edit: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    can_comment: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    granted_by: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # User ID who granted access
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_collab_perms_doc_user", "document_id", "user_id", unique=True
        ),
        Index("ix_collab_perms_document", "document_id"),
        Index("ix_collab_perms_user", "user_id"),
    )
    __mapper_args__ = {"eager_defaults": True}


class CollaborationAuditLog(Base):
    """Audit trail for all collaboration session events."""

    __tablename__ = "collaboration_audit_log"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # 'presence.join', 'presence.leave', 'update', 'permission.granted', 'permission.revoked'
    payload: Mapped[dict | None] = mapped_column(
        JSONB
    )  # Action-specific data (e.g., content hash, permission details)
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_collab_audit_doc", "document_id"),
        Index("ix_collab_audit_doc_timestamp", "document_id", "timestamp"),
        Index("ix_collab_audit_user", "user_id"),
    )
    __mapper_args__ = {"eager_defaults": True}


class WSAuditLog(Base):
    """Audit trail for websocket RPC requests."""

    __tablename__ = "ws_audit_log"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    connection_id: Mapped[str] = mapped_column(String(128), nullable=False)
    identity: Mapped[str | None] = mapped_column(String(255))
    method: Mapped[str] = mapped_column(String(128), nullable=False)
    params_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_ws_audit_connection_id", "connection_id"),
        Index("ix_ws_audit_identity", "identity"),
        Index("ix_ws_audit_created_at", "created_at"),
    )
    __mapper_args__ = {"eager_defaults": True}


class CronJob(Base):
    """Persisted cron job definitions."""

    __tablename__ = "cron_jobs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    schedule: Mapped[str] = mapped_column(String(128), nullable=False)
    job_type: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="noop"
    )
    payload: Mapped[dict] = mapped_column(
        JSON, nullable=False, server_default="{}"
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    runs: Mapped[list[CronRun]] = relationship(
        "CronRun", back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_cron_jobs_is_enabled", "is_enabled"),
        Index("ix_cron_jobs_updated_at", "updated_at"),
    )
    __mapper_args__ = {"eager_defaults": True}


class CronRun(Base):
    """Execution records for cron job runs."""

    __tablename__ = "cron_runs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cron_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="queued"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    error: Mapped[str | None] = mapped_column(Text)
    result: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped[CronJob] = relationship("CronJob", back_populates="runs")

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="cron_runs_status_check",
        ),
        Index("ix_cron_runs_job_id", "job_id"),
        Index("ix_cron_runs_status", "status"),
        Index("ix_cron_runs_created_at", "created_at"),
    )
    __mapper_args__ = {"eager_defaults": True}


class CommandRun(Base):
    """Durable command invocation run records."""

    __tablename__ = "command_runs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    command_id: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="queued"
    )
    actor_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_session_id: Mapped[str | None] = mapped_column(String(255))
    delegated_by: Mapped[str | None] = mapped_column(String(255))
    auth_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    invoke_version: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(255))
    args_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    args_redacted: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    result_json: Mapped[dict | None] = mapped_column(JSONB)
    error_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'blocked')",
            name="command_runs_status_check",
        ),
        UniqueConstraint(
            "command_id",
            "idempotency_key",
            name="uq_command_idempotency_key",
        ),
        Index("ix_command_runs_command_id", "command_id"),
        Index("ix_command_runs_status", "status"),
        Index("ix_command_runs_created_at", "created_at"),
    )
    __mapper_args__ = {"eager_defaults": True}


class CommandRunEvent(Base):
    """Ordered append-only event records for command run streaming."""

    __tablename__ = "command_run_events"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("command_runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "sequence",
            name="uq_command_run_events_run_sequence",
        ),
        Index("ix_command_run_events_run_id", "run_id"),
        Index("ix_command_run_events_created_at", "created_at"),
    )
    __mapper_args__ = {"eager_defaults": True}


class ChannelConfig(Base):
    """Per-user channel adapter configuration blobs."""

    __tablename__ = "channel_configs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    config_json: Mapped[dict] = mapped_column(
        JSON, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "channel",
            name="uq_channel_configs_user_channel",
        ),
        Index("ix_channel_configs_user_id", "user_id"),
        Index("ix_channel_configs_channel", "channel"),
    )
    __mapper_args__ = {"eager_defaults": True}


class ChannelAllowlist(Base):
    """Approved external identities for a user's channel."""

    __tablename__ = "channel_allowlists"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "channel",
            "external_id",
            name="uq_channel_allowlists_user_channel_external",
        ),
        Index("ix_channel_allowlists_user_channel", "user_id", "channel"),
    )
    __mapper_args__ = {"eager_defaults": True}


class ChannelPairing(Base):
    """Pairing request/approval state for channel identities."""

    __tablename__ = "channel_pairings"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'revoked')",
            name="channel_pairings_status_check",
        ),
        UniqueConstraint(
            "user_id",
            "channel",
            "external_id",
            name="uq_channel_pairings_user_channel_external",
        ),
        Index("ix_channel_pairings_user_channel", "user_id", "channel"),
        Index("ix_channel_pairings_status", "status"),
    )
    __mapper_args__ = {"eager_defaults": True}


class ChannelMessage(Base):
    """Inbound/outbound channel message audit entries."""

    __tablename__ = "channel_messages"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255))
    thread_id: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="channel_messages_direction_check",
        ),
        Index("ix_channel_messages_user_channel", "user_id", "channel"),
        Index("ix_channel_messages_created_at", "created_at"),
    )
    __mapper_args__ = {"eager_defaults": True}
