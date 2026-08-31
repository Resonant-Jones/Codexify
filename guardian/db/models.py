# guardian/db/models.py
"""
Postgres-only SQLAlchemy models for Guardian.

All schema is managed via Alembic migrations.
No raw DDL creation in application code.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

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

from guardian.account_observability.tokens import (
    ATTRIBUTION_CONFIDENCES,
    ATTRIBUTION_METHODS,
    INVITE_STATUSES,
    AccountObservabilityInviteStatus,
)
from guardian.agents.work_orders import WORK_ORDER_STATUSES
from guardian.agents.worktree_leases import (
    WORKTREE_LEASE_CLEANUP_POLICIES,
    WORKTREE_LEASE_STATUSES,
)
from guardian.core.capability_tokens import (
    CapabilityFamily,
    CapabilityGrantKind,
    CapabilityGrantScope,
    CapabilityGrantStatus,
)
from guardian.extensions.tokens import (
    CAPABILITY_ENTRY_PROVENANCE_CLASSES,
    CAPABILITY_REGISTRY_STATUSES,
    EXTENSION_INSTALL_BINDING_SCOPES,
    EXTENSION_INSTALL_BINDING_STATUSES,
    EXTENSION_PROPOSAL_SCOPES,
    EXTENSION_PROPOSAL_STATUSES,
    EXTENSION_TARGET_SURFACES,
    INSTALL_GATE_DECISION_TOKENS,
)
from guardian.messaging.tokens import (
    DM_CONTENT_TYPES,
    DM_CONVERSATION_KINDS,
    USERNAME_STATES,
)
from guardian.protocol_tokens import (
    ACCEPTANCE_STATUSES,
    ACCOUNT_IMPORT_STATUSES,
    CAMPAIGN_EXECUTION_ATTEMPT_STATUSES,
    CAMPAIGN_GOAL_STATUSES,
    CAMPAIGN_STATUSES,
    GUARDIAN_DELEGATION_APPROVAL_MODES,
    GUARDIAN_DELEGATION_APPROVAL_SOURCES,
    GUARDIAN_DELEGATION_APPROVAL_STATES,
    GUARDIAN_DELEGATION_CONTEXT_SOURCE_TYPES,
    GUARDIAN_DELEGATION_INTENT_STATUSES,
    GUARDIAN_DELEGATION_INTERACTION_MODES,
    GUARDIAN_DELEGATION_VISIBILITY_STATUSES,
    AccountImportStatus,
    DelegationJobStatus,
    EmbeddingLifecycleStatus,
)
from guardian.tts.contracts import (
    TTS_LOCAL_BACKEND_IDS,
    TTS_OUTPUT_FORMATS,
    TTS_VOICE_MODES,
)
from guardian.threadspace.membership_tokens import NODE_STATUSES
from guardian.user_profile_tokens import (
    DEFAULT_USER_ACCENT_COLOR,
    USER_ACCENT_COLORS,
)
from guardian.watchdog.contracts import (
    WATCHDOG_ESCALATION_MODES,
    WATCHDOG_MODEL_SELECTION_SOURCES,
    WATCHDOG_POLICY_BLOCK_REASONS,
    WATCHDOG_POLICY_RESOLUTION_STATES,
    WATCHDOG_REVIEW_ATTEMPT_STATES,
    WATCHDOG_REVIEW_DISPATCH_ERROR_CODES,
    WATCHDOG_REVIEW_DISPATCH_STATES,
    WATCHDOG_REVIEW_EXECUTION_ERROR_CODES,
    WATCHDOG_REVIEW_INPUT_CAPTURE_ERROR_CODES,
    WATCHDOG_REVIEW_INPUT_SNAPSHOT_STATES,
    WATCHDOG_REVIEW_RESULT_STATES,
    WatchdogOperation,
)

WATCHDOG_REVIEW_DISPATCH_STATE_VALUES_SQL = "','".join(
    sorted(WATCHDOG_REVIEW_DISPATCH_STATES)
)
WATCHDOG_REVIEW_DISPATCH_STATE_CHECK = (
    f"dispatch_state IN ('{WATCHDOG_REVIEW_DISPATCH_STATE_VALUES_SQL}')"
)
WATCHDOG_REVIEW_DISPATCH_ERROR_CODE_VALUES_SQL = "','".join(
    sorted(WATCHDOG_REVIEW_DISPATCH_ERROR_CODES)
)
WATCHDOG_REVIEW_DISPATCH_ERROR_CODE_CHECK = (
    "terminal_error_code IS NULL OR terminal_error_code IN "
    f"('{WATCHDOG_REVIEW_DISPATCH_ERROR_CODE_VALUES_SQL}')"
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class User(Base):
    """Canonical user account boundary."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    username: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    email: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, default="guest", server_default="guest"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'guest')", name="users_role_check"),
    )


# =========================
# User Profiles
# =========================


USER_ACCENT_COLOR_VALUES_SQL = "','".join(sorted(USER_ACCENT_COLORS))
USER_ACCENT_COLOR_CHECK = f"accent_color IN ('{USER_ACCENT_COLOR_VALUES_SQL}')"

# Social identity state for the canonical person-facing profile.
# ``username`` is a deliberate Node-scoped discovery alias (lowercase-only
# canonical form); ``username_state`` records whether one has been claimed.
THREADSPACE_NODE_STATUS_VALUES_SQL = "','".join(sorted(NODE_STATUSES))
THREADSPACE_NODE_STATUS_CHECK = (
    "status IN ('" + THREADSPACE_NODE_STATUS_VALUES_SQL + "')"
)
USERNAME_STATE_VALUES_SQL = "','".join(sorted(USERNAME_STATES))
USERNAME_STATE_CHECK = (
    "username_state IS NULL OR username_state IN "
    f"('{USERNAME_STATE_VALUES_SQL}')"
)
# The username grammar CHECK is Postgres-native (regex ``~``) and lives only
# in the migration (a1b7c9d2e4f6); application validation in
# ``guardian.messaging.tokens.normalize_username`` enforces the same grammar
# on every write path.
USERNAME_STATE_USERNAME_CONSISTENCY_CHECK = (
    "(username_state = 'active') = (username IS NOT NULL)"
)


class UserProfile(Base):
    """Account-owned presentation and social identity for a canonical user.

    ``id`` remains the internal row key.  ``profile_id`` is the durable
    social actor token that participates in the ``Node_ID + Profile_ID``
    protocol address; ``node_id`` anchors the profile to its host node.
    ``user_id`` stays private account ownership authority and is never a
    social address field.
    """

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile_id: Mapped[str | None] = mapped_column(String(36))
    node_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("threadspace_nodes.node_id", ondelete="RESTRICT"),
    )
    username: Mapped[str | None] = mapped_column(String(32))
    username_state: Mapped[str | None] = mapped_column(String(16))
    display_name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(2048))
    timezone: Mapped[str | None] = mapped_column(String(128))
    accent_color: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=DEFAULT_USER_ACCENT_COLOR,
        server_default=DEFAULT_USER_ACCENT_COLOR,
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

    user: Mapped[User] = relationship("User")

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
        UniqueConstraint("profile_id", name="uq_user_profiles_profile_id"),
        UniqueConstraint(
            "node_id", "username", name="uq_user_profiles_node_username"
        ),
        CheckConstraint(
            USER_ACCENT_COLOR_CHECK,
            name="ck_user_profiles_accent_color",
        ),
        CheckConstraint(
            USERNAME_STATE_CHECK,
            name="ck_user_profiles_username_state",
        ),
        CheckConstraint(
            USERNAME_STATE_USERNAME_CONSISTENCY_CHECK,
            name="ck_user_profiles_username_state_consistency",
        ),
        Index("ix_user_profiles_node_id", "node_id"),
    )

    __mapper_args__ = {"eager_defaults": True}


class ThreadSpaceNode(Base):
    """Durable ThreadSpace Node record — the canonical local Node_ID.

    ``node_id`` identifies the Codexify node authority.  It is never an
    endpoint, hostname, IP, URL, container identity, account, or profile.
    """

    __tablename__ = "threadspace_nodes"

    node_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", server_default="active"
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
            THREADSPACE_NODE_STATUS_CHECK,
            name="threadspace_nodes_status_check",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="threadspace_nodes_name_check",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


EMBEDDING_LIFECYCLE_VALUES_SQL = "','".join(
    status.value for status in EmbeddingLifecycleStatus
)
UPLOADED_DOCUMENT_EMBEDDING_STATUS_CHECK = (
    f"embedding_status IN ('{EMBEDDING_LIFECYCLE_VALUES_SQL}')"
)

DELEGATION_STATUS_VALUES_SQL = "','".join(
    status.value for status in DelegationJobStatus
)
DELEGATION_STATUS_CHECK = f"status IN ('{DELEGATION_STATUS_VALUES_SQL}')"
WORKTREE_LEASE_STATUS_VALUES_SQL = "','".join(sorted(WORKTREE_LEASE_STATUSES))
WORKTREE_LEASE_STATUS_CHECK = (
    f"status IN ('{WORKTREE_LEASE_STATUS_VALUES_SQL}')"
)
WORKTREE_LEASE_CLEANUP_POLICY_VALUES_SQL = "','".join(
    sorted(WORKTREE_LEASE_CLEANUP_POLICIES)
)
WORKTREE_LEASE_CLEANUP_POLICY_CHECK = (
    f"cleanup_policy IN ('{WORKTREE_LEASE_CLEANUP_POLICY_VALUES_SQL}')"
)
WORK_ORDER_STATUS_VALUES_SQL = "','".join(sorted(WORK_ORDER_STATUSES))
WORK_ORDER_STATUS_CHECK = f"status IN ('{WORK_ORDER_STATUS_VALUES_SQL}')"
CAMPAIGN_GOAL_STATUS_VALUES_SQL = "','".join(sorted(CAMPAIGN_GOAL_STATUSES))
CAMPAIGN_GOAL_STATUS_CHECK = f"status IN ('{CAMPAIGN_GOAL_STATUS_VALUES_SQL}')"
CAMPAIGN_STATUS_VALUES_SQL = "','".join(sorted(CAMPAIGN_STATUSES))
CAMPAIGN_STATUS_CHECK = f"status IN ('{CAMPAIGN_STATUS_VALUES_SQL}')"
CAMPAIGN_EXECUTION_ATTEMPT_STATUS_VALUES_SQL = "','".join(
    sorted(CAMPAIGN_EXECUTION_ATTEMPT_STATUSES)
)
CAMPAIGN_EXECUTION_ATTEMPT_STATUS_CHECK = (
    "status IN " f"('{CAMPAIGN_EXECUTION_ATTEMPT_STATUS_VALUES_SQL}')"
)
TTS_LOCAL_BACKEND_IDS_VALUES_SQL = "','".join(TTS_LOCAL_BACKEND_IDS)
TTS_LOCAL_BACKEND_ID_CHECK = (
    f"backend_id IN ('{TTS_LOCAL_BACKEND_IDS_VALUES_SQL}')"
)
TTS_VOICE_MODE_VALUES_SQL = "','".join(TTS_VOICE_MODES)
TTS_VOICE_MODE_CHECK = f"voice_mode IN ('{TTS_VOICE_MODE_VALUES_SQL}')"
TTS_OUTPUT_FORMAT_VALUES_SQL = "','".join(TTS_OUTPUT_FORMATS)
TTS_OUTPUT_FORMAT_CHECK = f"output_format IN ('{TTS_OUTPUT_FORMAT_VALUES_SQL}')"
WATCHDOG_REVIEW_ATTEMPT_STATE_VALUES_SQL = "','".join(
    sorted(WATCHDOG_REVIEW_ATTEMPT_STATES)
)
WATCHDOG_REVIEW_ATTEMPT_STATE_CHECK = (
    "attempt_state IN " f"('{WATCHDOG_REVIEW_ATTEMPT_STATE_VALUES_SQL}')"
)
WATCHDOG_POLICY_RESOLUTION_STATE_VALUES_SQL = "','".join(
    sorted(WATCHDOG_POLICY_RESOLUTION_STATES)
)
WATCHDOG_POLICY_RESOLUTION_STATE_CHECK = (
    "policy_resolution_state IN "
    f"('{WATCHDOG_POLICY_RESOLUTION_STATE_VALUES_SQL}')"
)
WATCHDOG_ESCALATION_MODE_VALUES_SQL = "','".join(
    sorted(WATCHDOG_ESCALATION_MODES)
)
WATCHDOG_ESCALATION_MODE_CHECK = (
    "escalation_mode IN " f"('{WATCHDOG_ESCALATION_MODE_VALUES_SQL}')"
)
WATCHDOG_MODEL_SELECTION_SOURCE_VALUES_SQL = "','".join(
    sorted(WATCHDOG_MODEL_SELECTION_SOURCES)
)
WATCHDOG_MODEL_SELECTION_SOURCE_CHECK = (
    "model_selection_source IN "
    f"('{WATCHDOG_MODEL_SELECTION_SOURCE_VALUES_SQL}')"
)
WATCHDOG_POLICY_BLOCK_REASON_VALUES_SQL = "','".join(
    sorted(WATCHDOG_POLICY_BLOCK_REASONS)
)
WATCHDOG_POLICY_BLOCK_REASON_CHECK = (
    "policy_reason_code IS NULL OR policy_reason_code IN "
    f"('{WATCHDOG_POLICY_BLOCK_REASON_VALUES_SQL}')"
)
WATCHDOG_REVIEW_INPUT_SNAPSHOT_STATE_VALUES_SQL = "','".join(
    sorted(WATCHDOG_REVIEW_INPUT_SNAPSHOT_STATES)
)
WATCHDOG_REVIEW_INPUT_SNAPSHOT_STATE_CHECK = (
    "capture_state IN " f"('{WATCHDOG_REVIEW_INPUT_SNAPSHOT_STATE_VALUES_SQL}')"
)
WATCHDOG_REVIEW_INPUT_CAPTURE_ERROR_CODE_VALUES_SQL = "','".join(
    sorted(WATCHDOG_REVIEW_INPUT_CAPTURE_ERROR_CODES)
)
WATCHDOG_REVIEW_INPUT_CAPTURE_ERROR_CODE_CHECK = (
    "block_error_code IS NULL OR block_error_code IN "
    f"('{WATCHDOG_REVIEW_INPUT_CAPTURE_ERROR_CODE_VALUES_SQL}')"
)
WATCHDOG_REVIEW_RESULT_STATE_VALUES_SQL = "','".join(
    sorted(WATCHDOG_REVIEW_RESULT_STATES)
)
WATCHDOG_REVIEW_RESULT_STATE_CHECK = (
    "result_state IN " f"('{WATCHDOG_REVIEW_RESULT_STATE_VALUES_SQL}')"
)
WATCHDOG_REVIEW_EXECUTION_ERROR_CODE_VALUES_SQL = "','".join(
    sorted(WATCHDOG_REVIEW_EXECUTION_ERROR_CODES)
)
WATCHDOG_REVIEW_EXECUTION_ERROR_CODE_CHECK = (
    "terminal_error_code IS NULL OR terminal_error_code IN "
    f"('{WATCHDOG_REVIEW_EXECUTION_ERROR_CODE_VALUES_SQL}')"
)
GUARDIAN_DELEGATION_ACCEPTANCE_STATUS_VALUES_SQL = "','".join(
    sorted(ACCEPTANCE_STATUSES)
)
GUARDIAN_DELEGATION_ACCEPTANCE_STATUS_CHECK = (
    "acceptance_status IN "
    f"('{GUARDIAN_DELEGATION_ACCEPTANCE_STATUS_VALUES_SQL}')"
)
GUARDIAN_DELEGATION_INTERACTION_MODE_VALUES_SQL = "','".join(
    sorted(GUARDIAN_DELEGATION_INTERACTION_MODES)
)
GUARDIAN_DELEGATION_INTERACTION_MODE_CHECK = (
    "interaction_mode IN "
    f"('{GUARDIAN_DELEGATION_INTERACTION_MODE_VALUES_SQL}')"
)
GUARDIAN_DELEGATION_APPROVAL_MODE_VALUES_SQL = "','".join(
    sorted(GUARDIAN_DELEGATION_APPROVAL_MODES)
)
GUARDIAN_DELEGATION_APPROVAL_MODE_CHECK = (
    "approval_mode IN " f"('{GUARDIAN_DELEGATION_APPROVAL_MODE_VALUES_SQL}')"
)
GUARDIAN_DELEGATION_APPROVAL_STATE_VALUES_SQL = "','".join(
    sorted(GUARDIAN_DELEGATION_APPROVAL_STATES)
)
GUARDIAN_DELEGATION_APPROVAL_STATE_CHECK = (
    "approval_state IN " f"('{GUARDIAN_DELEGATION_APPROVAL_STATE_VALUES_SQL}')"
)
GUARDIAN_DELEGATION_APPROVAL_SOURCE_VALUES_SQL = "','".join(
    sorted(GUARDIAN_DELEGATION_APPROVAL_SOURCES)
)
GUARDIAN_DELEGATION_APPROVAL_SOURCE_CHECK = (
    "approval_source IN "
    f"('{GUARDIAN_DELEGATION_APPROVAL_SOURCE_VALUES_SQL}')"
)
GUARDIAN_DELEGATION_INTENT_STATUS_VALUES_SQL = "','".join(
    sorted(GUARDIAN_DELEGATION_INTENT_STATUSES)
)
GUARDIAN_DELEGATION_INTENT_STATUS_CHECK = (
    "intent_status IN " f"('{GUARDIAN_DELEGATION_INTENT_STATUS_VALUES_SQL}')"
)
GUARDIAN_DELEGATION_VISIBILITY_STATUS_VALUES_SQL = "','".join(
    sorted(GUARDIAN_DELEGATION_VISIBILITY_STATUSES)
)
GUARDIAN_DELEGATION_VISIBILITY_STATUS_CHECK = (
    "visibility_status IN "
    f"('{GUARDIAN_DELEGATION_VISIBILITY_STATUS_VALUES_SQL}')"
)
GUARDIAN_DELEGATION_CONTEXT_SOURCE_TYPE_VALUES_SQL = "','".join(
    sorted(GUARDIAN_DELEGATION_CONTEXT_SOURCE_TYPES)
)
CAPABILITY_FAMILY_VALUES_SQL = "','".join(
    family.value for family in CapabilityFamily
)
CAPABILITY_GRANT_SCOPE_VALUES_SQL = "','".join(
    scope.value for scope in CapabilityGrantScope
)
CAPABILITY_GRANT_KIND_VALUES_SQL = "','".join(
    kind.value for kind in CapabilityGrantKind
)
CAPABILITY_GRANT_STATUS_VALUES_SQL = "','".join(
    status.value for status in CapabilityGrantStatus
)
CAPABILITY_FAMILY_CHECK = (
    f"capability_family IN ('{CAPABILITY_FAMILY_VALUES_SQL}')"
)
CAPABILITY_GRANT_SCOPE_CHECK = (
    f"grant_scope IN ('{CAPABILITY_GRANT_SCOPE_VALUES_SQL}')"
)
CAPABILITY_GRANT_KIND_CHECK = (
    f"grant_kind IN ('{CAPABILITY_GRANT_KIND_VALUES_SQL}')"
)
CAPABILITY_GRANT_STATUS_CHECK = (
    f"grant_status IN ('{CAPABILITY_GRANT_STATUS_VALUES_SQL}')"
)
EXTENSION_TARGET_SURFACE_VALUES_SQL = "','".join(
    sorted(EXTENSION_TARGET_SURFACES)
)
EXTENSION_PROPOSAL_SCOPE_VALUES_SQL = "','".join(
    sorted(EXTENSION_PROPOSAL_SCOPES)
)
EXTENSION_PROPOSAL_STATUS_VALUES_SQL = "','".join(
    sorted(EXTENSION_PROPOSAL_STATUSES)
)
EXTENSION_TARGET_SURFACE_CHECK = (
    f"target_surface_token IN ('{EXTENSION_TARGET_SURFACE_VALUES_SQL}')"
)
EXTENSION_PROPOSAL_SCOPE_CHECK = (
    f"scope_token IN ('{EXTENSION_PROPOSAL_SCOPE_VALUES_SQL}')"
)
EXTENSION_PROPOSAL_STATUS_CHECK = (
    f"status_token IN ('{EXTENSION_PROPOSAL_STATUS_VALUES_SQL}')"
)
INSTALL_GATE_DECISION_VALUES_SQL = "','".join(
    sorted(INSTALL_GATE_DECISION_TOKENS)
)
CAPABILITY_REGISTRY_STATUS_VALUES_SQL = "','".join(
    sorted(CAPABILITY_REGISTRY_STATUSES)
)
CAPABILITY_ENTRY_PROVENANCE_CLASS_VALUES_SQL = "','".join(
    sorted(CAPABILITY_ENTRY_PROVENANCE_CLASSES)
)
EXTENSION_INSTALL_BINDING_SCOPE_VALUES_SQL = "','".join(
    sorted(EXTENSION_INSTALL_BINDING_SCOPES)
)
EXTENSION_INSTALL_BINDING_STATUS_VALUES_SQL = "','".join(
    sorted(EXTENSION_INSTALL_BINDING_STATUSES)
)
INSTALL_GATE_DECISION_CHECK = (
    f"decision_token IN ('{INSTALL_GATE_DECISION_VALUES_SQL}')"
)
CAPABILITY_REGISTRY_STATUS_CHECK = (
    f"status_token IN ('{CAPABILITY_REGISTRY_STATUS_VALUES_SQL}')"
)
CAPABILITY_ENTRY_PROVENANCE_CLASS_CHECK = f"provenance_class_token IN ('{CAPABILITY_ENTRY_PROVENANCE_CLASS_VALUES_SQL}')"
EXTENSION_INSTALL_BINDING_SCOPE_CHECK = (
    f"scope_token IN ('{EXTENSION_INSTALL_BINDING_SCOPE_VALUES_SQL}')"
)
EXTENSION_INSTALL_BINDING_STATUS_CHECK = (
    f"binding_status_token IN ('{EXTENSION_INSTALL_BINDING_STATUS_VALUES_SQL}')"
)
EXTENSION_INSTALL_BINDING_SCOPE_TARGET_CHECK = """
(
    scope_token <> 'project_scoped'
    OR (
        project_id IS NOT NULL
        AND profile_id IS NULL
        AND account_scope_target_id IS NULL
    )
)
AND (
    scope_token <> 'profile_scoped'
    OR (
        profile_id IS NOT NULL
        AND project_id IS NULL
        AND account_scope_target_id IS NULL
    )
)
AND (
    scope_token <> 'account_scoped'
    OR (
        account_scope_target_id IS NOT NULL
        AND project_id IS NULL
        AND profile_id IS NULL
    )
)
""".strip()

HOSTED_ROOM_STATUSES = frozenset({"active", "closed"})
HOSTED_ROOM_INVITE_STATUSES = frozenset(
    {"pending", "accepted", "revoked", "expired"}
)
HOSTED_ROOM_PARTICIPANT_KINDS = frozenset({"human", "agent"})
HOSTED_ROOM_PARTICIPANT_ROLES = frozenset({"owner", "member", "agent"})
HOSTED_ROOM_PARTICIPANT_STATES = frozenset({"active", "removed"})

HOSTED_ROOM_STATUS_CHECK = (
    "status IN "
    f"({','.join(repr(value) for value in sorted(HOSTED_ROOM_STATUSES))})"
)
HOSTED_ROOM_INVITE_STATUS_CHECK = (
    "status IN "
    f"({','.join(repr(value) for value in sorted(HOSTED_ROOM_INVITE_STATUSES))})"
)
HOSTED_ROOM_PARTICIPANT_KIND_CHECK = (
    "kind IN "
    f"({','.join(repr(value) for value in sorted(HOSTED_ROOM_PARTICIPANT_KINDS))})"
)
HOSTED_ROOM_PARTICIPANT_ROLE_CHECK = (
    "role IN "
    f"({','.join(repr(value) for value in sorted(HOSTED_ROOM_PARTICIPANT_ROLES))})"
)
HOSTED_ROOM_PARTICIPANT_STATE_CHECK = (
    "state IN "
    f"({','.join(repr(value) for value in sorted(HOSTED_ROOM_PARTICIPANT_STATES))})"
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
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(16))
    identity_depth: Mapped[str] = mapped_column(
        String(16), nullable=False, default="light", server_default="light"
    )
    system_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
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

    user: Mapped[User] = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "identity_depth IN ('light','deep')",
            name="projects_identity_depth_check",
        ),
        CheckConstraint(
            "system_role IS NULL OR system_role IN ('general','imports')",
            name="projects_system_role_check",
        ),
        Index(
            "uq_projects_user_id_system_role",
            "user_id",
            "system_role",
            unique=True,
            postgresql_where=text("system_role IS NOT NULL"),
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


# =========================
# Repository Bindings (Stage 2K.1 / ADR-065)
# =========================


REPOSITORY_BINDING_SOURCE_CLASS_GUARDIAN_MANAGED = "guardian_managed"
REPOSITORY_BINDING_SOURCE_CLASS_EXTERNAL_LINKED = "external_linked"
REPOSITORY_BINDING_SOURCE_CLASSES_SQL = (
    f"'{REPOSITORY_BINDING_SOURCE_CLASS_GUARDIAN_MANAGED}',"
    f"'{REPOSITORY_BINDING_SOURCE_CLASS_EXTERNAL_LINKED}'"
)
REPOSITORY_BINDING_SOURCE_CLASS_CHECK = (
    f"source_class IN ({REPOSITORY_BINDING_SOURCE_CLASSES_SQL})"
)


class RepositoryBinding(Base):
    """Stage 2K.1 (ADR-065) durable Project-to-Git-working-tree authority.

    A repository is available to Guardian only through an explicit,
    account/project-owned ``RepositoryBinding``. Cardinality is one active
    binding per Project; inactive historical bindings may coexist. The
    binding resolves one authorized working-tree root and is Guardian-owned
    durable authority state, never model input or conversational context.

    Discovery candidates (``discovery_candidate``) are NOT stored here —
    they are not bindings and never gain tool eligibility. Existing
    Projects receive no automatic binding; ``General`` receives no implicit
    binding.
    """

    __tablename__ = "repository_bindings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_class: Mapped[str] = mapped_column(
        String(32), nullable=False
    )
    canonical_root: Mapped[str] = mapped_column(
        String(4096), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
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

    project: Mapped[Project] = relationship("Project")

    __table_args__ = (
        CheckConstraint(
            REPOSITORY_BINDING_SOURCE_CLASS_CHECK,
            name="ck_repository_bindings_source_class",
        ),
        Index(
            "ix_repository_bindings_project_id",
            "project_id",
        ),
        Index(
            "uq_repository_bindings_one_active_per_project",
            "project_id",
            unique=True,
            postgresql_where=text("is_active IS TRUE"),
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


# =========================
# Capability Grants
# =========================


class CapabilityTier(Base):
    """Reusable package/tier definition for grant issuance."""

    __tablename__ = "capability_tiers"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    capability_family: Mapped[str] = mapped_column(String(64), nullable=False)
    tier_key: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    capabilities_json: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    limits_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="100"
    )
    is_active: Mapped[bool] = mapped_column(
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

    grants: Mapped[list[CapabilityGrant]] = relationship(
        "CapabilityGrant", back_populates="tier"
    )

    __table_args__ = (
        CheckConstraint(
            CAPABILITY_FAMILY_CHECK,
            name="capability_tiers_capability_family_check",
        ),
        Index(
            "ix_capability_tiers_family_active",
            "capability_family",
            "is_active",
        ),
        Index("ix_capability_tiers_priority", "priority"),
    )

    __mapper_args__ = {"eager_defaults": True}


class CapabilityGrant(Base):
    """Durable account-scoped grant issuance record."""

    __tablename__ = "capability_grants"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    account_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("authenticated_principals.account_id", ondelete="CASCADE"),
        nullable=False,
    )
    tier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("capability_tiers.id", ondelete="CASCADE"),
        nullable=False,
    )
    grant_scope: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=CapabilityGrantScope.ACCOUNT.value,
    )
    grant_kind: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=CapabilityGrantKind.PERMANENT.value,
    )
    grant_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=CapabilityGrantStatus.ACTIVE.value,
    )
    starts_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    issued_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    provenance_source: Mapped[str | None] = mapped_column(String(64))
    provenance_ref: Mapped[str | None] = mapped_column(String(255))
    provenance_reason: Mapped[str | None] = mapped_column(Text)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
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

    tier: Mapped[CapabilityTier] = relationship(
        "CapabilityTier", back_populates="grants"
    )

    __table_args__ = (
        CheckConstraint(
            CAPABILITY_GRANT_SCOPE_CHECK,
            name="capability_grants_scope_check",
        ),
        CheckConstraint(
            CAPABILITY_GRANT_KIND_CHECK,
            name="capability_grants_kind_check",
        ),
        CheckConstraint(
            CAPABILITY_GRANT_STATUS_CHECK,
            name="capability_grants_status_check",
        ),
        Index(
            "ix_capability_grants_account_status",
            "account_id",
            "grant_status",
        ),
        Index(
            "ix_capability_grants_account_ends_at",
            "account_id",
            "ends_at",
        ),
        Index("ix_capability_grants_tier_id", "tier_id"),
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
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(
        Text, server_default="", nullable=False
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id")
    )
    last_interaction_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    active_profile_id: Mapped[str | None] = mapped_column(String(128))
    thread_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
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
    # Canonical conversation-origin registry. Set at canonical creation only;
    # immutable under ordinary thread mutation. See
    # ``guardian.conversation_origin`` for the bounded value registry.
    origin_system: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="codexify",
        server_default="codexify",
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
    project: Mapped[Project | None] = relationship("Project")
    user: Mapped[User] = relationship("User")
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

    __table_args__ = (
        CheckConstraint(
            "origin_system IN ('codexify', 'openai', 'anthropic')",
            name="ck_chat_threads_origin_system_canonical",
        ),
        Index(
            "ix_chat_threads_user_origin",
            "user_id",
            "origin_system",
        ),
    )


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
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
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
        # Assistant-side coding_result rows use this JSONB blob for durable
        # source-thread / source-message / attempt lineage and capture flags.
        JSONB,
        nullable=False,
        server_default="{}",
    )
    # Hosted Room participant provenance (optional, paired-null constraint)
    hosted_room_participant_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "hosted_room_participants.id", ondelete="SET NULL"
        ),
        nullable=True,
        index=True,
    )
    sender_display_name_snapshot: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    thread: Mapped[ChatThread] = relationship(
        "ChatThread", back_populates="messages"
    )
    user: Mapped[User] = relationship("User")
    hosted_room_participant: Mapped[HostedRoomParticipant | None] = relationship(
        "HostedRoomParticipant",
        foreign_keys=[hosted_room_participant_id],
        lazy="raise",
    )

    __mapper_args__ = {"eager_defaults": True}

    __table_args__ = (
        CheckConstraint(
            "("
            "hosted_room_participant_id IS NULL "
            "AND sender_display_name_snapshot IS NULL"
            ") OR ("
            "hosted_room_participant_id IS NOT NULL "
            "AND sender_display_name_snapshot IS NOT NULL "
            "AND sender_display_name_snapshot <> ''"
            ")",
            name="ck_chat_messages_paired_provenance",
        ),
    )


# =========================
# Hosted Rooms
# =========================


class HostedRoom(Base):
    """Account-owned collaboration boundary backed by one canonical thread."""

    __tablename__ = "hosted_rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_account_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    backing_thread_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    enabled_agent_ids: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
        server_default="[]",
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
    closed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    owner: Mapped[User] = relationship("User")
    backing_thread: Mapped[ChatThread] = relationship("ChatThread")
    invitations: Mapped[list[HostedRoomInvite]] = relationship(
        "HostedRoomInvite",
        back_populates="room",
        cascade="all, delete-orphan",
    )
    participants: Mapped[list[HostedRoomParticipant]] = relationship(
        "HostedRoomParticipant",
        back_populates="room",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("slug", name="uq_hosted_rooms_slug"),
        UniqueConstraint(
            "backing_thread_id",
            name="uq_hosted_rooms_backing_thread_id",
        ),
        CheckConstraint(
            HOSTED_ROOM_STATUS_CHECK,
            name="hosted_rooms_status_check",
        ),
        CheckConstraint(
            "(status = 'active' AND closed_at IS NULL) "
            "OR (status = 'closed' AND closed_at IS NOT NULL)",
            name="hosted_rooms_lifecycle_check",
        ),
        CheckConstraint(
            "slug <> '' AND slug NOT LIKE '% %'",
            name="hosted_rooms_slug_check",
        ),
        CheckConstraint(
            "length(CAST(enabled_agent_ids AS TEXT)) <= 4096",
            name="hosted_rooms_enabled_agent_ids_size_check",
        ),
        Index("ix_hosted_rooms_owner_account_id", "owner_account_id"),
    )

    __mapper_args__ = {"eager_defaults": True}


class HostedRoomInvite(Base):
    """Room-scoped invitation metadata with only a stored token verifier."""

    __tablename__ = "hosted_room_invites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    room_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hosted_rooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    intended_display_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    expired_at: Mapped[datetime | None] = mapped_column(
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

    room: Mapped[HostedRoom] = relationship(
        "HostedRoom", back_populates="invitations"
    )
    participant: Mapped[HostedRoomParticipant | None] = relationship(
        "HostedRoomParticipant",
        back_populates="originating_invitation",
        uselist=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "token_hash",
            name="uq_hosted_room_invites_token_hash",
        ),
        CheckConstraint(
            HOSTED_ROOM_INVITE_STATUS_CHECK,
            name="hosted_room_invites_status_check",
        ),
        CheckConstraint(
            "("
            "status = 'pending' "
            "AND accepted_at IS NULL "
            "AND revoked_at IS NULL "
            "AND expired_at IS NULL"
            ") OR ("
            "status = 'accepted' "
            "AND accepted_at IS NOT NULL "
            "AND revoked_at IS NULL "
            "AND expired_at IS NULL"
            ") OR ("
            "status = 'revoked' "
            "AND revoked_at IS NOT NULL "
            "AND expired_at IS NULL"
            ") OR ("
            "status = 'expired' "
            "AND expired_at IS NOT NULL "
            "AND accepted_at IS NULL "
            "AND revoked_at IS NULL"
            ")",
            name="hosted_room_invites_lifecycle_check",
        ),
        Index("ix_hosted_room_invites_room_id", "room_id"),
    )

    __mapper_args__ = {"eager_defaults": True}


class HostedRoomParticipant(Base):
    """Room-scoped human or resident-agent identity record."""

    __tablename__ = "hosted_room_participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    room_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hosted_rooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    invitation_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("hosted_room_invites.id", ondelete="SET NULL"),
    )
    bound_account_id: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    joined_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    removed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    actor_source: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    actor_ref: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )

    room: Mapped[HostedRoom] = relationship(
        "HostedRoom", back_populates="participants"
    )
    originating_invitation: Mapped[HostedRoomInvite | None] = relationship(
        "HostedRoomInvite", back_populates="participant"
    )
    bound_account: Mapped[User | None] = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "invitation_id",
            name="uq_hosted_room_participants_invitation_id",
        ),
        UniqueConstraint(
            "room_id", "actor_source", "actor_ref",
            name="uq_hosted_room_participants_room_actor",
        ),
        CheckConstraint(
            "("
            "kind = 'agent' AND role = 'agent' "
            "AND actor_source IS NOT NULL AND actor_ref IS NOT NULL"
            ") OR ("
            "kind = 'human' "
            "AND actor_source IS NULL AND actor_ref IS NULL"
            ")",
            name="hosted_room_participants_actor_check",
        ),
        CheckConstraint(
            HOSTED_ROOM_PARTICIPANT_KIND_CHECK,
            name="hosted_room_participants_kind_check",
        ),
        CheckConstraint(
            HOSTED_ROOM_PARTICIPANT_ROLE_CHECK,
            name="hosted_room_participants_role_check",
        ),
        CheckConstraint(
            HOSTED_ROOM_PARTICIPANT_STATE_CHECK,
            name="hosted_room_participants_state_check",
        ),
        CheckConstraint(
            "("
            "kind = 'human' "
            "AND role = 'owner' "
            "AND bound_account_id IS NOT NULL"
            ") OR ("
            "kind = 'human' "
            "AND role = 'member'"
            ") OR ("
            "kind = 'agent' "
            "AND role = 'agent' "
            "AND bound_account_id IS NULL"
            ")",
            name="hosted_room_participants_kind_role_check",
        ),
        CheckConstraint(
            "(state = 'active' AND removed_at IS NULL) "
            "OR (state = 'removed' AND removed_at IS NOT NULL)",
            name="hosted_room_participants_lifecycle_check",
        ),
        Index("ix_hosted_room_participants_room_id", "room_id"),
        Index(
            "ix_hosted_room_participants_room_state",
            "room_id",
            "state",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


class EvalTraceSnapshot(Base):
    """Durable post-completion trace snapshot for inspection-only evals."""

    __tablename__ = "eval_trace_snapshots"

    trace_snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    thread_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_message_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("chat_messages.id", ondelete="SET NULL")
    )
    assistant_message_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("chat_messages.id", ondelete="SET NULL")
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="SET NULL")
    )
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    source_mode: Mapped[str | None] = mapped_column(String(64))
    widen_reason: Mapped[str | None] = mapped_column(String(128))
    retrieval_summary_json: Mapped[dict] = mapped_column(
        "retrieval_summary", JSONB, nullable=False, server_default="{}"
    )
    assistant_output_text: Mapped[str] = mapped_column(Text, nullable=False)
    trace_json: Mapped[dict] = mapped_column(
        "trace", JSONB, nullable=False, server_default="{}"
    )
    payload_summary_json: Mapped[dict] = mapped_column(
        "payload_summary", JSONB, nullable=False, server_default="{}"
    )
    timestamps_json: Mapped[dict] = mapped_column(
        "timestamps", JSONB, nullable=False, server_default="{}"
    )
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    thread: Mapped[ChatThread] = relationship("ChatThread")
    user_message: Mapped[ChatMessage | None] = relationship(
        "ChatMessage", foreign_keys=[user_message_id]
    )
    assistant_message: Mapped[ChatMessage | None] = relationship(
        "ChatMessage", foreign_keys=[assistant_message_id]
    )
    project: Mapped[Project | None] = relationship("Project")

    __table_args__ = (
        Index(
            "ix_eval_trace_snapshots_thread_created", "thread_id", "created_at"
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


class EvalVerdict(Base):
    """Attempt-scoped verdict rows produced by post-completion evaluators."""

    __tablename__ = "eval_verdicts"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    eval_run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    trace_snapshot_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            "eval_trace_snapshots.trace_snapshot_id", ondelete="CASCADE"
        ),
        nullable=False,
    )
    request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    thread_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_message_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("chat_messages.id", ondelete="SET NULL")
    )
    assistant_message_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("chat_messages.id", ondelete="SET NULL")
    )
    evaluator_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    evaluator_name: Mapped[str] = mapped_column(String(128), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    structured_findings_json: Mapped[dict] = mapped_column(
        "structured_findings", JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    trace_snapshot: Mapped[EvalTraceSnapshot] = relationship(
        "EvalTraceSnapshot"
    )
    thread: Mapped[ChatThread] = relationship("ChatThread")
    user_message: Mapped[ChatMessage | None] = relationship(
        "ChatMessage", foreign_keys=[user_message_id]
    )
    assistant_message: Mapped[ChatMessage | None] = relationship(
        "ChatMessage", foreign_keys=[assistant_message_id]
    )

    __table_args__ = (
        CheckConstraint(
            "evaluator_kind IN ('code','llm_judge')",
            name="eval_verdicts_evaluator_kind_check",
        ),
        CheckConstraint(
            "status IN ('succeeded','failed')",
            name="eval_verdicts_status_check",
        ),
        UniqueConstraint(
            "eval_run_id",
            "evaluator_name",
            name="uq_eval_verdicts_run_evaluator",
        ),
        Index(
            "ix_eval_verdicts_thread_created",
            "thread_id",
            "created_at",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


class ThreadMove(Base):
    """Explicit project move audit trail for chat threads."""

    __tablename__ = "thread_moves"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    thread_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="SET NULL")
    )
    to_project_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __mapper_args__ = {"eager_defaults": True}


# =========================
# Direct Messaging
# =========================


DM_CONVERSATION_KIND_VALUES_SQL = "','".join(sorted(DM_CONVERSATION_KINDS))
DM_CONVERSATION_KIND_CHECK = (
    f"kind IN ('{DM_CONVERSATION_KIND_VALUES_SQL}')"
)
DM_CONTENT_TYPE_VALUES_SQL = "','".join(sorted(DM_CONTENT_TYPES))
DM_CONTENT_TYPE_CHECK = (
    f"content_type IN ('{DM_CONTENT_TYPE_VALUES_SQL}')"
)


class DirectMessageRelationship(Base):
    """Canonical direct relationship for one unordered social-address pair."""

    __tablename__ = "direct_message_relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    participant_pair_key: Mapped[str] = mapped_column(
        String(256), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    participants: Mapped[list[DirectMessageRelationshipParticipant]] = (
        relationship(
            "DirectMessageRelationshipParticipant",
            back_populates="relationship",
            cascade="all, delete-orphan",
        )
    )

    __table_args__ = (
        UniqueConstraint(
            "participant_pair_key",
            name="uq_direct_message_relationships_participant_pair_key",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


class DirectMessageRelationshipParticipant(Base):
    """One canonical social-address participant in a direct relationship."""

    __tablename__ = "direct_message_relationship_participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    relationship_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("direct_message_relationships.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    relationship: Mapped[DirectMessageRelationship] = relationship(
        "DirectMessageRelationship", back_populates="participants"
    )

    __table_args__ = (
        UniqueConstraint(
            "relationship_id",
            "profile_id",
            name="uq_direct_message_relationship_participants_member",
        ),
        Index(
            "ix_direct_message_relationship_participants_profile",
            "profile_id",
        ),
        Index(
            "ix_direct_message_relationship_participants_relationship",
            "relationship_id",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


class DirectMessageConversation(Base):
    """One discussion inside a canonical direct relationship.

    Pair uniqueness lives on the Relationship; a Relationship may own many
    Conversations.  Conversation identity never depends on username,
    display name, Project placement, or origin provenance.
    """

    __tablename__ = "direct_message_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    relationship_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("direct_message_relationships.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user_profiles.profile_id", ondelete="SET NULL"),
    )
    origin_project_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
    )
    origin_thread_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("chat_threads.id", ondelete="SET NULL"),
    )
    kind: Mapped[str] = mapped_column(
        String(16), nullable=False, default="direct", server_default="direct"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    latest_activity_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    placements: Mapped[list[DirectMessageConversationPlacement]] = relationship(
        "DirectMessageConversationPlacement",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            DM_CONVERSATION_KIND_CHECK,
            name="ck_direct_message_conversations_kind",
        ),
        Index(
            "ix_direct_message_conversations_relationship_activity",
            "relationship_id",
            "latest_activity_at",
            "id",
        ),
        Index(
            "ix_direct_message_conversations_origin_project",
            "origin_project_id",
        ),
        Index(
            "ix_direct_message_conversations_origin_thread",
            "origin_thread_id",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


class DirectMessageConversationPlacement(Base):
    """Participant-local Project organization for one direct Conversation."""

    __tablename__ = "direct_message_conversation_placements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("direct_message_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped[DirectMessageConversation] = relationship(
        "DirectMessageConversation", back_populates="placements"
    )

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "profile_id",
            name="uq_direct_message_conversation_placements_member",
        ),
        Index(
            "ix_direct_message_conversation_placements_profile",
            "profile_id",
        ),
        Index(
            "ix_direct_message_conversation_placements_project",
            "project_id",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


class DirectMessage(Base):
    """One durable plain-text private message.

    Sender authority is derived server-side from the authenticated user's
    owned profile; it is never accepted from caller-supplied identity.
    ``client_message_key`` makes retries idempotent per sender conversation.
    """

    __tablename__ = "direct_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("direct_message_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    sender_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
    )
    content_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="text/plain",
        server_default="text/plain",
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    client_message_key: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped[DirectMessageConversation] = relationship(
        "DirectMessageConversation"
    )

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "sender_profile_id",
            "client_message_key",
            name="uq_direct_messages_idempotency",
        ),
        CheckConstraint(
            DM_CONTENT_TYPE_CHECK,
            name="ck_direct_messages_content_type",
        ),
        CheckConstraint(
            "length(trim(body)) > 0",
            name="ck_direct_messages_body_nonblank",
        ),
        CheckConstraint(
            "client_message_key IS NULL OR length(trim(client_message_key)) > 0",
            name="ck_direct_messages_client_key_nonblank",
        ),
        Index(
            "ix_direct_messages_conversation_chronological",
            "conversation_id",
            "created_at",
            "id",
        ),
        Index("ix_direct_messages_sender_profile_id", "sender_profile_id"),
    )

    __mapper_args__ = {"eager_defaults": True}


# =========================
# Delegations
# =========================


class DelegationPacket(Base):
    """Draft packet captured before approval into a runnable job."""

    __tablename__ = "delegation_packets"

    packet_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, nullable=False
    )
    thread_id: Mapped[int | None] = mapped_column(Integer)
    conversation_id: Mapped[str | None] = mapped_column(String(255))
    project_id: Mapped[int | None] = mapped_column(Integer)
    repo_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    executor: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="draft"
    )
    task_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    context_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            DELEGATION_STATUS_CHECK,
            name="delegation_packets_status_check",
        ),
        Index("ix_delegation_packets_status", "status", unique=False),
        Index(
            "ix_delegation_packets_created_at",
            "created_at",
            unique=False,
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


class DelegationJob(Base):
    """Durable queue row for an approved delegation."""

    __tablename__ = "delegation_jobs"

    delegation_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, nullable=False
    )
    packet_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("delegation_packets.packet_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    task_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    thread_id: Mapped[int | None] = mapped_column(Integer)
    conversation_id: Mapped[str | None] = mapped_column(String(255))
    project_id: Mapped[int | None] = mapped_column(Integer)
    repo_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    executor: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="approved"
    )
    task_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    queued_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            DELEGATION_STATUS_CHECK,
            name="delegation_jobs_status_check",
        ),
        Index("ix_delegation_jobs_status", "status", unique=False),
        Index("ix_delegation_jobs_created_at", "created_at", unique=False),
    )

    __mapper_args__ = {"eager_defaults": True}


class DelegationSummary(Base):
    """Terminal summary row for a completed delegation."""

    __tablename__ = "delegation_summaries"

    delegation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("delegation_jobs.delegation_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="completed"
    )
    summary_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            DELEGATION_STATUS_CHECK,
            name="delegation_summaries_status_check",
        ),
        Index("ix_delegation_summaries_status", "status", unique=False),
        Index(
            "ix_delegation_summaries_created_at",
            "created_at",
            unique=False,
        ),
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
    guardrail_metadata: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
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
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
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
    user: Mapped[User] = relationship("User")
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


class NotionConnectionCredential(Base):
    """One encrypted Notion integration token per user.

    This intentionally does not reuse ``oauth_connections``: a Notion
    integration token is not an OAuth grant, refresh token, or relay grant.
    Validation status is a bounded operational projection; raw provider
    responses and token material never leave this record.
    """

    __tablename__ = "notion_connection_credentials"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_integration_token: Mapped[str] = mapped_column(Text, nullable=False)
    validation_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="unvalidated"
    )
    last_validated_at: Mapped[datetime | None] = mapped_column(
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

    __table_args__ = (
        UniqueConstraint(
            "user_id", name="uq_notion_connection_credentials_user"
        ),
        CheckConstraint(
            "validation_status IN "
            "('unvalidated', 'valid', 'authorization_error', "
            "'transport_error', 'provider_error')",
            name="ck_notion_connection_credentials_validation_status",
        ),
    )


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


class InferenceModelOverride(Base):
    """User-editable model metadata overrides for provider catalogs."""

    __tablename__ = "inference_model_overrides"

    provider_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("inference_providers.provider_id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_label: Mapped[str | None] = mapped_column(Text)
    picker_label: Mapped[str | None] = mapped_column(Text)
    supports_chat: Mapped[bool | None] = mapped_column(Boolean)
    supports_vision: Mapped[bool | None] = mapped_column(Boolean)
    supports_text_input: Mapped[bool | None] = mapped_column(Boolean)
    model_kind: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    provider: Mapped[InferenceProvider] = relationship("InferenceProvider")

    __table_args__ = (
        CheckConstraint(
            "model_kind IS NULL OR model_kind IN ('chat','vision_chat','utility')",
            name="ck_inference_model_overrides_model_kind",
        ),
        Index("ix_inference_model_overrides_provider_id", "provider_id"),
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


class GitHubWatchdogDeliveryReceipt(Base):
    """Durable, bounded receipt for one authenticated GitHub delivery."""

    __tablename__ = "github_watchdog_delivery_receipts"

    receipt_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    github_delivery_id: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    event_name: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    installation_id: Mapped[str | None] = mapped_column(String(64))
    repository_id: Mapped[str | None] = mapped_column(String(64))
    repository_full_name: Mapped[str | None] = mapped_column(String(512))
    trigger_actor_id: Mapped[str | None] = mapped_column(String(64))
    trigger_actor_login: Mapped[str | None] = mapped_column(String(255))
    pull_request_number: Mapped[int | None] = mapped_column(Integer)
    head_sha: Mapped[str | None] = mapped_column(String(64))
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    first_received_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    last_received_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    redelivery_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_github_watchdog_delivery_receipts_idempotency_key",
        ),
        Index(
            "ix_github_watchdog_delivery_receipts_github_delivery_id",
            "github_delivery_id",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class GitHubWatchdogReviewAttempt(Base):
    """Immutable policy snapshot prepared from one Watchdog delivery receipt."""

    __tablename__ = "github_watchdog_review_attempts"

    review_attempt_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trigger_receipt_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "github_watchdog_delivery_receipts.receipt_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    github_delivery_id: Mapped[str] = mapped_column(String(255), nullable=False)
    installation_id: Mapped[str | None] = mapped_column(String(64))
    repository_id: Mapped[str | None] = mapped_column(String(64))
    repository_full_name: Mapped[str | None] = mapped_column(String(512))
    pull_request_number: Mapped[int | None] = mapped_column(Integer)
    head_sha: Mapped[str | None] = mapped_column(String(64))
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_state: Mapped[str] = mapped_column(String(32), nullable=False)
    policy_resolution_state: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_id: Mapped[str | None] = mapped_column(String(64))
    model_id: Mapped[str | None] = mapped_column(String(512))
    inference_mode: Mapped[str | None] = mapped_column(String(64))
    model_selection_source: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    policy_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    escalation_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    escalation_provider_id: Mapped[str | None] = mapped_column(String(64))
    escalation_model_id: Mapped[str | None] = mapped_column(String(512))
    policy_reason_code: Mapped[str | None] = mapped_column(String(64))
    superseded_by_attempt_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "github_watchdog_review_attempts.review_attempt_id",
            ondelete="SET NULL",
        ),
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
        UniqueConstraint(
            "trigger_receipt_id",
            name="uq_github_watchdog_review_attempts_trigger_receipt_id",
        ),
        CheckConstraint(
            f"operation = '{WatchdogOperation.AUTOMATED_REVIEW.value}'",
            name="ck_github_watchdog_review_attempts_operation",
        ),
        CheckConstraint(
            WATCHDOG_REVIEW_ATTEMPT_STATE_CHECK,
            name="ck_github_watchdog_review_attempts_state",
        ),
        CheckConstraint(
            WATCHDOG_POLICY_RESOLUTION_STATE_CHECK,
            name="ck_github_watchdog_review_attempts_policy_resolution_state",
        ),
        CheckConstraint(
            WATCHDOG_ESCALATION_MODE_CHECK,
            name="ck_github_watchdog_review_attempts_escalation_mode",
        ),
        CheckConstraint(
            WATCHDOG_MODEL_SELECTION_SOURCE_CHECK,
            name="ck_github_watchdog_review_attempts_model_selection_source",
        ),
        CheckConstraint(
            WATCHDOG_POLICY_BLOCK_REASON_CHECK,
            name="ck_github_watchdog_review_attempts_policy_reason_code",
        ),
        Index(
            "ix_github_watchdog_review_attempts_repository_pr",
            "repository_id",
            "pull_request_number",
        ),
        Index(
            "ix_github_watchdog_review_attempts_state",
            "attempt_state",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class GitHubWatchdogReviewInputSnapshot(Base):
    """One immutable terminal source-evidence record for a review attempt."""

    __tablename__ = "github_watchdog_review_input_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    review_attempt_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "github_watchdog_review_attempts.review_attempt_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    installation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    repository_id: Mapped[str] = mapped_column(String(64), nullable=False)
    repository_full_name: Mapped[str] = mapped_column(String(512), nullable=False)
    pull_request_number: Mapped[int] = mapped_column(Integer, nullable=False)
    capture_state: Mapped[str] = mapped_column(String(32), nullable=False)
    expected_head_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_head_sha: Mapped[str | None] = mapped_column(String(64))
    base_sha: Mapped[str | None] = mapped_column(String(64))
    observed_base_sha: Mapped[str | None] = mapped_column(String(64))
    pull_request_title: Mapped[str | None] = mapped_column(Text)
    pull_request_body: Mapped[str | None] = mapped_column(Text)
    author_id: Mapped[str | None] = mapped_column(String(64))
    author_login: Mapped[str | None] = mapped_column(String(255))
    draft: Mapped[bool | None] = mapped_column(Boolean)
    changed_file_count: Mapped[int | None] = mapped_column(Integer)
    files_without_patch_count: Mapped[int | None] = mapped_column(Integer)
    aggregate_additions: Mapped[int | None] = mapped_column(Integer)
    aggregate_deletions: Mapped[int | None] = mapped_column(Integer)
    aggregate_changes: Mapped[int | None] = mapped_column(Integer)
    changed_files_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql")
    )
    captured_patch_bytes: Mapped[int | None] = mapped_column(Integer)
    snapshot_sha256: Mapped[str | None] = mapped_column(String(64))
    block_error_code: Mapped[str | None] = mapped_column(String(64))
    captured_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "review_attempt_id",
            name="uq_github_watchdog_review_input_snapshots_review_attempt_id",
        ),
        CheckConstraint(
            WATCHDOG_REVIEW_INPUT_SNAPSHOT_STATE_CHECK,
            name="ck_github_watchdog_review_input_snapshots_state",
        ),
        CheckConstraint(
            WATCHDOG_REVIEW_INPUT_CAPTURE_ERROR_CODE_CHECK,
            name="ck_github_watchdog_review_input_snapshots_block_error_code",
        ),
        CheckConstraint(
            "(capture_state = 'captured' AND snapshot_sha256 IS NOT NULL "
            "AND block_error_code IS NULL) OR "
            "(capture_state != 'captured' AND snapshot_sha256 IS NULL "
            "AND block_error_code IS NOT NULL)",
            name="ck_github_watchdog_review_input_snapshots_terminal_shape",
        ),
        Index(
            "ix_github_watchdog_review_input_snapshots_capture_state",
            "capture_state",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class GitHubWatchdogReviewResult(Base):
    """One immutable model-execution record for a Watchdog review attempt."""

    __tablename__ = "github_watchdog_review_results"

    result_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    review_attempt_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "github_watchdog_review_attempts.review_attempt_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    review_input_snapshot_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "github_watchdog_review_input_snapshots.snapshot_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    snapshot_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    result_state: Mapped[str] = mapped_column(String(32), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    invoked_provider_id: Mapped[str] = mapped_column(String(64), nullable=False)
    invoked_model_id: Mapped[str] = mapped_column(String(512), nullable=False)
    inference_mode: Mapped[str | None] = mapped_column(String(64))
    requested_max_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_output_text: Mapped[str | None] = mapped_column(Text)
    raw_output_sha256: Mapped[str | None] = mapped_column(String(64))
    raw_output_bytes: Mapped[int | None] = mapped_column(Integer)
    structured_review_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql")
    )
    provider_input_tokens: Mapped[int | None] = mapped_column(Integer)
    provider_output_tokens: Mapped[int | None] = mapped_column(Integer)
    provider_total_tokens: Mapped[int | None] = mapped_column(Integer)
    provider_request_id: Mapped[str | None] = mapped_column(String(128))
    terminal_error_code: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    __table_args__ = (
        UniqueConstraint(
            "review_attempt_id",
            name="uq_github_watchdog_review_results_review_attempt_id",
        ),
        CheckConstraint(
            WATCHDOG_REVIEW_RESULT_STATE_CHECK,
            name="ck_github_watchdog_review_results_state",
        ),
        CheckConstraint(
            WATCHDOG_REVIEW_EXECUTION_ERROR_CODE_CHECK,
            name="ck_github_watchdog_review_results_terminal_error_code",
        ),
        CheckConstraint(
            "(result_state = 'running' AND completed_at IS NULL) OR "
            "(result_state != 'running' AND completed_at IS NOT NULL)",
            name="ck_github_watchdog_review_results_terminal_shape",
        ),
        Index(
            "ix_github_watchdog_review_results_state",
            "result_state",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class GitHubWatchdogReviewDispatch(Base):
    """Durable transport lineage for one captured Watchdog review attempt."""

    __tablename__ = "github_watchdog_review_dispatches"

    dispatch_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    review_attempt_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "github_watchdog_review_attempts.review_attempt_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    review_input_snapshot_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "github_watchdog_review_input_snapshots.snapshot_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    snapshot_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    head_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    dispatch_state: Mapped[str] = mapped_column(String(32), nullable=False)
    queue_task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    enqueue_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    last_enqueue_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    worker_id: Mapped[str | None] = mapped_column(String(255))
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    review_result_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "github_watchdog_review_results.result_id",
            ondelete="RESTRICT",
        ),
    )
    terminal_error_code: Mapped[str | None] = mapped_column(String(64))
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
        UniqueConstraint(
            "review_attempt_id",
            name="uq_github_watchdog_review_dispatches_review_attempt_id",
        ),
        CheckConstraint(
            WATCHDOG_REVIEW_DISPATCH_STATE_CHECK,
            name="ck_github_watchdog_review_dispatches_state",
        ),
        CheckConstraint(
            WATCHDOG_REVIEW_DISPATCH_ERROR_CODE_CHECK,
            name="ck_github_watchdog_review_dispatches_terminal_error_code",
        ),
        CheckConstraint(
            "(dispatch_state IN ('completed','failed','blocked',"
            "'discarded_superseded','enqueue_failed') AND completed_at IS NOT NULL) "
            "OR (dispatch_state IN ('pending_enqueue','queued','running') "
            "AND completed_at IS NULL)",
            name="ck_github_watchdog_review_dispatches_terminal_shape",
        ),
        Index(
            "ix_github_watchdog_review_dispatches_state",
            "dispatch_state",
        ),
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
# Durable Account Imports
# =========================


class OpenAIAccountImportJob(Base):
    """Account-owned durable intake and worker checkpoint for an OpenAI export."""

    __tablename__ = "openai_account_import_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source_system: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="openai"
    )
    source_export_fingerprint: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=AccountImportStatus.RECEIVING.value,
    )
    staging_locator: Mapped[str] = mapped_column(Text, nullable=False)
    total_file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_byte_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_file_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    uploaded_byte_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0"
    )
    imported_thread_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    imported_message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    imported_media_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    duplicate_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    skipped_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    warning_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    failure_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    warning_details: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
        server_default="[]",
    )
    error_details: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
        server_default="[]",
    )
    staged_manifest: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
        server_default="[]",
    )
    checkpoint: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    queued_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    __table_args__ = (
        CheckConstraint(
            f"status IN ({','.join(repr(value) for value in sorted(ACCOUNT_IMPORT_STATUSES))})",
            name="openai_account_import_jobs_status_check",
        ),
        CheckConstraint(
            "total_file_count > 0 AND total_byte_count >= 0",
            name="openai_account_import_jobs_declared_counts_check",
        ),
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
    import_job_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("openai_account_import_jobs.id", ondelete="SET NULL"),
    )
    source_relative_path: Mapped[str | None] = mapped_column(Text)
    source_export_id: Mapped[str | None] = mapped_column(String(255))
    source_message_id: Mapped[str | None] = mapped_column(String(255))
    source_thread_id: Mapped[str | None] = mapped_column(String(255))
    import_lineage: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
        server_default="[]",
    )
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
    thread_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=True,
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
    thread: Mapped[ChatThread | None] = relationship("ChatThread")

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
    thread_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=True,
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
    thread: Mapped[ChatThread | None] = relationship("ChatThread")

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

    # Origin identity for document-centric APIs (for example GET /api/documents/{id}).
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    # Canonical media-asset linkage used for dedupe/provenance.
    asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE")
    )
    thread_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chat_threads.id", ondelete="CASCADE")
    )
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
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
    user: Mapped[User] = relationship("User")

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


class TTSVoiceProfile(Base):
    """Persistent local TTS voice profile consumed by the TTS adapter."""

    __tablename__ = "tts_voice_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    backend_id: Mapped[str] = mapped_column(String(64), nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    description: Mapped[str | None] = mapped_column(Text)
    voice_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="preset"
    )
    speaker: Mapped[str | None] = mapped_column(String(128))
    voice_prompt: Mapped[str | None] = mapped_column(Text)
    style_instructions: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(64))
    speed: Mapped[float | None] = mapped_column(Float)
    temperature: Mapped[float | None] = mapped_column(Float)
    top_k: Mapped[int | None] = mapped_column(Integer)
    top_p: Mapped[float | None] = mapped_column(Float)
    repetition_penalty: Mapped[float | None] = mapped_column(Float)
    max_new_tokens: Mapped[int | None] = mapped_column(Integer)
    do_sample: Mapped[bool | None] = mapped_column(Boolean)
    backend_params: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    reference_audio_asset_id: Mapped[str | None] = mapped_column(String(128))
    reference_text: Mapped[str | None] = mapped_column(Text)
    x_vector_only_mode: Mapped[bool | None] = mapped_column(Boolean)
    sample_rate: Mapped[int | None] = mapped_column(Integer)
    output_format: Mapped[str | None] = mapped_column(
        String(16), server_default="wav"
    )
    loudness_normalization: Mapped[bool | None] = mapped_column(Boolean)
    pause_profile: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql")
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
            TTS_LOCAL_BACKEND_ID_CHECK,
            name="tts_voice_profiles_backend_id_check",
        ),
        CheckConstraint(
            TTS_VOICE_MODE_CHECK,
            name="tts_voice_profiles_voice_mode_check",
        ),
        CheckConstraint(
            TTS_OUTPUT_FORMAT_CHECK,
            name="tts_voice_profiles_output_format_check",
        ),
        CheckConstraint(
            "speed IS NULL OR (speed > 0.0 AND speed <= 4.0)",
            name="tts_voice_profiles_speed_check",
        ),
        CheckConstraint(
            "temperature IS NULL OR (temperature >= 0.0 AND temperature <= 2.0)",
            name="tts_voice_profiles_temperature_check",
        ),
        CheckConstraint(
            "top_k IS NULL OR top_k >= 0",
            name="tts_voice_profiles_top_k_check",
        ),
        CheckConstraint(
            "top_p IS NULL OR (top_p >= 0.0 AND top_p <= 1.0)",
            name="tts_voice_profiles_top_p_check",
        ),
        CheckConstraint(
            "repetition_penalty IS NULL OR repetition_penalty > 0.0",
            name="tts_voice_profiles_repetition_penalty_check",
        ),
        CheckConstraint(
            "max_new_tokens IS NULL OR max_new_tokens > 0",
            name="tts_voice_profiles_max_new_tokens_check",
        ),
        CheckConstraint(
            "sample_rate IS NULL OR sample_rate > 0",
            name="tts_voice_profiles_sample_rate_check",
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
# Control Plane State
# =========================


class UserSettings(Base):
    """Durable user-global policy controls for identity modeling."""

    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(
        String(255), primary_key=True, nullable=False
    )
    memory_mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default="deep", server_default="deep"
    )
    diary_requires_unlock: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    allow_sensitive_modeling: Mapped[bool] = mapped_column(
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

    __table_args__ = (
        CheckConstraint(
            "memory_mode IN ('none','light','deep')",
            name="user_settings_memory_mode_check",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


class AuthenticatedPrincipal(Base):
    """Durable mapping from an authenticated subject to a stable account."""

    __tablename__ = "authenticated_principals"

    account_id: Mapped[str] = mapped_column(
        String(255), primary_key=True, nullable=False
    )
    subject_id: Mapped[str] = mapped_column(String(255), nullable=False)
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
            "subject_id", name="uq_authenticated_principals_subject_id"
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


# =========================
# Imprint Semantic Core
# =========================


class ImprintObservation(Base):
    """Append-only durable imprint signal evidence."""

    __tablename__ = "imprint_observations"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schema_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    provenance: Mapped[dict] = mapped_column(
        JSON, nullable=False, server_default="{}"
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False)
    signal_payload: Mapped[dict] = mapped_column(
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
        CheckConstraint(
            "schema_version >= 1",
            name="imprint_observations_schema_version_check",
        ),
        UniqueConstraint(
            "idempotency_key",
            name="uq_imprint_observations_idempotency_key",
        ),
        Index(
            "ix_imprint_observations_user_project_created",
            "user_id",
            "project_id",
            "created_at",
        ),
        Index(
            "ix_imprint_observations_user_scope",
            "user_id",
            "project_id",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class ImprintFoldState(Base):
    """Materialized imprint state folded from append-only observations."""

    __tablename__ = "imprint_fold_states"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    scope_key: Mapped[str] = mapped_column(String(255), nullable=False)
    scope_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fold_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    source_observation_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    source_observation_max_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    state_payload: Mapped[dict] = mapped_column(
        JSON, nullable=False, server_default="{}"
    )
    state_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default=""
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
            "scope_kind IN ('user_global','project_scoped')",
            name="imprint_fold_states_scope_kind_check",
        ),
        UniqueConstraint(
            "scope_key",
            name="uq_imprint_fold_states_scope_key",
        ),
        Index("ix_imprint_fold_states_user_scope", "user_id", "scope_kind"),
    )
    __mapper_args__ = {"eager_defaults": True}


# =========================
# Persona Profiles
# =========================


class PersonaProfile(Base):
    """Backend-backed persona profile used by Persona Studio."""

    __tablename__ = "persona_profiles"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "temperature >= 0.0 AND temperature <= 2.0",
            name="persona_profiles_temperature_check",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


# =========================
# Extension Proposals
# =========================


class AgentExtensionProposal(Base):
    """Durable proposal draft for a self-extending capability."""

    __tablename__ = "agent_extension_proposals"

    proposal_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, nullable=False
    )
    account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_thread_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_message_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    target_surface_token: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    scope_token: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="project_scoped"
    )
    status_token: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="draft"
    )
    requested_permissions_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="[]",
    )
    declared_dependencies_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="[]",
    )
    rollback_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    test_evidence_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    manifest_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="{}",
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
            EXTENSION_TARGET_SURFACE_CHECK,
            name="agent_extension_proposals_target_surface_check",
        ),
        CheckConstraint(
            EXTENSION_PROPOSAL_SCOPE_CHECK,
            name="agent_extension_proposals_scope_check",
        ),
        CheckConstraint(
            EXTENSION_PROPOSAL_STATUS_CHECK,
            name="agent_extension_proposals_status_check",
        ),
        Index(
            "ix_agent_extension_proposals_account_created_at",
            "account_id",
            "created_at",
        ),
        Index(
            "ix_agent_extension_proposals_project_created_at",
            "project_id",
            "created_at",
        ),
        Index(
            "ix_agent_extension_proposals_profile_created_at",
            "profile_id",
            "created_at",
        ),
        Index(
            "ix_agent_extension_proposals_status_created_at",
            "status_token",
            "created_at",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


class AgentExtensionInstallGateDecision(Base):
    """Durable install-gate decision for an extension proposal."""

    __tablename__ = "agent_extension_install_gate_decisions"

    decision_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, nullable=False
    )
    account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    proposal_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agent_extension_proposals.proposal_id", ondelete="CASCADE"),
        nullable=False,
    )
    decision_token: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="approved"
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="{}",
    )
    requested_permissions_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="[]",
    )
    approved_permissions_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="[]",
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
            INSTALL_GATE_DECISION_CHECK,
            name="agent_extension_install_gate_decisions_decision_check",
        ),
        Index(
            "ix_agent_extension_install_gate_decisions_account_created_at",
            "account_id",
            "created_at",
        ),
        Index(
            "ix_agent_extension_install_gate_decisions_proposal_created_at",
            "proposal_id",
            "created_at",
        ),
        Index(
            "ix_agent_extension_install_gate_decisions_decision_created_at",
            "decision_token",
            "created_at",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


class AgentExtensionRegistryEntry(Base):
    """Durable registry entry for an approved extension."""

    __tablename__ = "agent_extension_registry_entries"

    registry_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, nullable=False
    )
    account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    proposal_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agent_extension_proposals.proposal_id", ondelete="CASCADE"),
        nullable=False,
    )
    decision_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            "agent_extension_install_gate_decisions.decision_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_thread_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_message_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    target_surface_token: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    scope_token: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="project_scoped"
    )
    status_token: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="registered"
    )
    requested_permissions_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="[]",
    )
    approved_permissions_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="[]",
    )
    manifest_snapshot_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="{}",
    )
    registration_metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="{}",
    )
    provenance_class_token: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="proposal_approval"
    )
    provenance_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="{}",
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
            EXTENSION_TARGET_SURFACE_CHECK,
            name="agent_extension_registry_entries_target_surface_check",
        ),
        CheckConstraint(
            EXTENSION_PROPOSAL_SCOPE_CHECK,
            name="agent_extension_registry_entries_scope_check",
        ),
        CheckConstraint(
            CAPABILITY_REGISTRY_STATUS_CHECK,
            name="agent_extension_registry_entries_status_check",
        ),
        CheckConstraint(
            CAPABILITY_ENTRY_PROVENANCE_CLASS_CHECK,
            name="agent_extension_registry_entries_provenance_class_check",
        ),
        Index(
            "ix_agent_extension_registry_entries_account_created_at",
            "account_id",
            "created_at",
        ),
        Index(
            "ix_agent_extension_registry_entries_proposal_created_at",
            "proposal_id",
            "created_at",
        ),
        Index(
            "ix_agent_extension_registry_entries_project_created_at",
            "project_id",
            "created_at",
        ),
        Index(
            "ix_agent_extension_registry_entries_profile_created_at",
            "profile_id",
            "created_at",
        ),
        Index(
            "ix_agent_extension_registry_entries_status_created_at",
            "status_token",
            "created_at",
        ),
        Index(
            "ix_agent_extension_registry_entries_decision_created_at",
            "decision_id",
            "created_at",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


class AgentExtensionInstallBinding(Base):
    """Durable scope binding for an approved registry entry."""

    __tablename__ = "agent_extension_install_bindings"

    binding_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, nullable=False
    )
    account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    registry_entry_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            "agent_extension_registry_entries.registry_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    proposal_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agent_extension_proposals.proposal_id", ondelete="CASCADE"),
        nullable=False,
    )
    scope_token: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="project_scoped"
    )
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    account_scope_target_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    binding_status_token: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="active"
    )
    bind_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    bind_notes_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="{}",
    )
    bind_metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="{}",
    )
    unbind_metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="{}",
    )
    source_thread_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_message_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
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
    unbound_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            EXTENSION_INSTALL_BINDING_SCOPE_CHECK,
            name="agent_extension_install_bindings_scope_check",
        ),
        CheckConstraint(
            EXTENSION_INSTALL_BINDING_STATUS_CHECK,
            name="agent_extension_install_bindings_status_check",
        ),
        CheckConstraint(
            EXTENSION_INSTALL_BINDING_SCOPE_TARGET_CHECK,
            name="agent_extension_install_bindings_scope_target_check",
        ),
        Index(
            "ix_agent_extension_install_bindings_account_created_at",
            "account_id",
            "created_at",
        ),
        Index(
            "ix_agent_extension_install_bindings_registry_created_at",
            "registry_entry_id",
            "created_at",
        ),
        Index(
            "ix_agent_extension_install_bindings_scope_created_at",
            "scope_token",
            "created_at",
        ),
        Index(
            "ix_agent_extension_install_bindings_project_created_at",
            "project_id",
            "created_at",
        ),
        Index(
            "ix_agent_extension_install_bindings_profile_created_at",
            "profile_id",
            "created_at",
        ),
        Index(
            "ix_agent_extension_install_bindings_account_target_created_at",
            "account_scope_target_id",
            "created_at",
        ),
        Index(
            "ix_agent_extension_install_bindings_status_created_at",
            "binding_status_token",
            "created_at",
        ),
        Index(
            "uq_agent_extension_install_bindings_active_tuple",
            "account_id",
            "registry_entry_id",
            "scope_token",
            "project_id",
            "profile_id",
            "account_scope_target_id",
            unique=True,
            postgresql_where=text("binding_status_token = 'active'"),
            sqlite_where=text("binding_status_token = 'active'"),
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
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
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

    user: Mapped[User] = relationship("User")


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


class GuardianDelegationIntent(Base):
    """Guardian-owned delegation intake artifact for the direct v1 route."""

    __tablename__ = "guardian_delegation_intents"

    intent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thread_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="SET NULL")
    )
    interaction_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="non_blocking"
    )
    approval_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="scoped_auto"
    )
    approval_state: Mapped[str] = mapped_column(String(32), nullable=False)
    approval_source: Mapped[str] = mapped_column(String(32), nullable=False)
    acceptance_status: Mapped[str] = mapped_column(String(32), nullable=False)
    intent_status: Mapped[str] = mapped_column(String(32), nullable=False)
    # Phase 2A links by AgentRun external run_id because agent_runs uses an
    # internal numeric PK; a DB-level FK to run_id is deferred until the
    # linkage contract is reconciled more broadly.
    run_id: Mapped[str | None] = mapped_column(String(64), index=True)
    visibility_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="not_posted"
    )
    result_message_id: Mapped[int | None] = mapped_column(
        BigInteger, index=True
    )
    result_delivered_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    result_delivery_key: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True
    )
    delivery_error: Mapped[str | None] = mapped_column(Text)
    plan_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    context_basis: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
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
            GUARDIAN_DELEGATION_INTERACTION_MODE_CHECK,
            name="guardian_delegation_intents_interaction_mode_check",
        ),
        CheckConstraint(
            GUARDIAN_DELEGATION_APPROVAL_MODE_CHECK,
            name="guardian_delegation_intents_approval_mode_check",
        ),
        CheckConstraint(
            GUARDIAN_DELEGATION_APPROVAL_STATE_CHECK,
            name="guardian_delegation_intents_approval_state_check",
        ),
        CheckConstraint(
            GUARDIAN_DELEGATION_APPROVAL_SOURCE_CHECK,
            name="guardian_delegation_intents_approval_source_check",
        ),
        CheckConstraint(
            GUARDIAN_DELEGATION_ACCEPTANCE_STATUS_CHECK,
            name="guardian_delegation_intents_acceptance_status_check",
        ),
        CheckConstraint(
            GUARDIAN_DELEGATION_INTENT_STATUS_CHECK,
            name="guardian_delegation_intents_intent_status_check",
        ),
        CheckConstraint(
            GUARDIAN_DELEGATION_VISIBILITY_STATUS_CHECK,
            name="guardian_delegation_intents_visibility_status_check",
        ),
        Index(
            "ix_guardian_delegation_intents_thread_source",
            "thread_id",
            "source_message_id",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


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
        # Agent orchestration events can carry source thread/message lineage
        # and attempt metadata without widening the relational schema.
        "payload",
        JSONB,
        nullable=False,
        server_default="{}",
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
Index(
    "ix_chat_threads_last_interaction_at", ChatThread.last_interaction_at.desc()
)
Index("ix_chat_threads_user_id", ChatThread.user_id)
Index("ix_chat_threads_updated", ChatThread.updated_at.desc())
Index("ix_thread_moves_thread_id", ThreadMove.thread_id)
Index("ix_thread_moves_timestamp", ThreadMove.timestamp.desc())

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
Index("ix_media_assets_import_job", MediaAsset.import_job_id)
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

Index("ix_openai_account_import_jobs_user", OpenAIAccountImportJob.user_id)
Index("ix_openai_account_import_jobs_status", OpenAIAccountImportJob.status)
Index(
    "ix_openai_account_import_jobs_fingerprint",
    OpenAIAccountImportJob.user_id,
    OpenAIAccountImportJob.source_export_fingerprint,
)

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
Index("ix_tts_voice_profiles_backend", TTSVoiceProfile.backend_id)
Index("ix_tts_voice_profiles_default", TTSVoiceProfile.is_default)
Index("ix_tts_voice_profiles_updated", TTSVoiceProfile.updated_at.desc())


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


class CampaignGoal(Base):
    """User-authored goal container for Campaign Runner work."""

    __tablename__ = "campaign_goals"

    goal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="active"
    )
    source_thread_id: Mapped[str | None] = mapped_column(String(128))
    source_message_id: Mapped[str | None] = mapped_column(String(128))
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
            CAMPAIGN_GOAL_STATUS_CHECK,
            name="campaign_goals_status_check",
        ),
        Index("ix_campaign_goals_status", "status"),
        Index("ix_campaign_goals_source_thread_id", "source_thread_id"),
    )
    __mapper_args__ = {"eager_defaults": True}


class Campaign(Base):
    """Grouped execution arc for ordered coding work orders."""

    __tablename__ = "campaigns"

    campaign_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    goal_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("campaign_goals.goal_id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="active"
    )
    source_thread_id: Mapped[str | None] = mapped_column(String(128))
    source_message_id: Mapped[str | None] = mapped_column(String(128))
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
            CAMPAIGN_STATUS_CHECK,
            name="campaigns_status_check",
        ),
        Index("ix_campaigns_goal_id", "goal_id"),
        Index("ix_campaigns_status", "status"),
    )
    __mapper_args__ = {"eager_defaults": True}


class CampaignExecutionAttempt(Base):
    """Durable append-friendly execution evidence for campaign work orders."""

    __tablename__ = "campaign_execution_attempts"

    attempt_record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    campaign_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("campaigns.campaign_id", ondelete="SET NULL"),
    )
    goal_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("campaign_goals.goal_id", ondelete="SET NULL"),
    )
    work_order_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("coding_work_orders.work_order_id", ondelete="SET NULL"),
    )
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_id: Mapped[str] = mapped_column(String(128), nullable=False)
    coding_task_id: Mapped[str | None] = mapped_column(String(128))
    adapter_kind: Mapped[str | None] = mapped_column(String(64))
    runtime_target: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="running"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    failed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    validation_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
    )
    commit_hash: Mapped[str | None] = mapped_column(String(64))
    delivery_ok: Mapped[bool | None] = mapped_column(Boolean)
    delivered_message_id: Mapped[int | None] = mapped_column(BigInteger)
    delivery_reason: Mapped[str | None] = mapped_column(String(255))
    source_thread_id: Mapped[int | None] = mapped_column(Integer)
    source_message_id: Mapped[int | None] = mapped_column(BigInteger)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
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
            CAMPAIGN_EXECUTION_ATTEMPT_STATUS_CHECK,
            name="campaign_execution_attempts_status_check",
        ),
        UniqueConstraint(
            "run_id",
            "attempt_id",
            name="uq_campaign_execution_attempts_run_attempt",
        ),
        Index("ix_campaign_execution_attempts_campaign_id", "campaign_id"),
        Index("ix_campaign_execution_attempts_goal_id", "goal_id"),
        Index("ix_campaign_execution_attempts_work_order_id", "work_order_id"),
        Index("ix_campaign_execution_attempts_status", "status"),
        Index("ix_campaign_execution_attempts_created_at", "created_at"),
    )
    __mapper_args__ = {"eager_defaults": True}


class CodingWorktreeLease(Base):
    """Durable control-plane lease metadata for coding worktrees."""

    __tablename__ = "coding_worktree_leases"

    lease_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    work_order_id: Mapped[str] = mapped_column(String(64), nullable=False)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    worker_id: Mapped[str] = mapped_column(String(255), nullable=False)
    base_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    branch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    worktree_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    preserve_on_failure: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    cleanup_policy: Mapped[str] = mapped_column(String(64), nullable=False)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    released_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    cleanup_completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    cleanup_error: Mapped[str | None] = mapped_column(Text)
    extra_meta: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql")
    )

    __table_args__ = (
        CheckConstraint(
            WORKTREE_LEASE_STATUS_CHECK,
            name="coding_worktree_leases_status_check",
        ),
        CheckConstraint(
            WORKTREE_LEASE_CLEANUP_POLICY_CHECK,
            name="coding_worktree_leases_cleanup_policy_check",
        ),
        Index(
            "ix_coding_worktree_leases_work_order_id",
            "work_order_id",
        ),
        Index(
            "ix_coding_worktree_leases_run_id",
            "run_id",
        ),
        Index(
            "ix_coding_worktree_leases_worker_id",
            "worker_id",
        ),
        Index(
            "ix_coding_worktree_leases_status",
            "status",
        ),
        Index(
            "ix_coding_worktree_leases_branch_name",
            "branch_name",
        ),
        Index(
            "ix_coding_worktree_leases_worktree_path",
            "worktree_path",
        ),
        Index(
            "uq_coding_worktree_leases_active_branch_name",
            "branch_name",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
        Index(
            "uq_coding_worktree_leases_active_worktree_path",
            "worktree_path",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


class CodingWorkOrder(Base):
    """Durable task-board control-plane state for coding work orders."""

    __tablename__ = "coding_work_orders"

    work_order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    campaign_id: Mapped[str | None] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="ready"
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    created_by: Mapped[str | None] = mapped_column(String(255))
    assigned_worker_id: Mapped[str | None] = mapped_column(String(255))
    source_thread_id: Mapped[str | None] = mapped_column(String(128))
    source_message_id: Mapped[str | None] = mapped_column(String(128))
    dependency_ids: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
        server_default="[]",
    )
    file_scope: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
        server_default="[]",
    )
    validation_command: Mapped[str | None] = mapped_column(Text)
    adapter_kind: Mapped[str | None] = mapped_column(String(64))
    max_validation_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    require_worktree_lease: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    commit_after_validation: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    require_human_review_before_merge: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    latest_run_id: Mapped[str | None] = mapped_column(String(64))
    latest_lease_id: Mapped[str | None] = mapped_column(String(64))
    latest_receipt_id: Mapped[str | None] = mapped_column(String(64))
    blocked_reason: Mapped[str | None] = mapped_column(Text)
    extra_meta: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
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
    archived_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    __table_args__ = (
        CheckConstraint(
            WORK_ORDER_STATUS_CHECK,
            name="coding_work_orders_status_check",
        ),
        Index("ix_coding_work_orders_campaign_id", "campaign_id"),
        Index("ix_coding_work_orders_status", "status"),
        Index("ix_coding_work_orders_priority", "priority"),
        Index(
            "ix_coding_work_orders_assigned_worker_id",
            "assigned_worker_id",
        ),
        Index("ix_coding_work_orders_source_thread_id", "source_thread_id"),
        Index("ix_coding_work_orders_latest_run_id", "latest_run_id"),
        Index("ix_coding_work_orders_latest_lease_id", "latest_lease_id"),
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


class WorkOrderResultReceipt(Base):
    """Immutable observation records for work-order-linked CommandRun results."""

    __tablename__ = "work_order_result_receipts"

    receipt_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    work_order_id: Mapped[str] = mapped_column(String(64), nullable=False)
    command_run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    receipt_kind: Mapped[str] = mapped_column(
        String(32), nullable=False, default="command_run_observation"
    )
    observed_command_id: Mapped[str] = mapped_column(
        String(512), nullable=False
    )
    observed_run_status: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_result_summary: Mapped[str] = mapped_column(Text, nullable=False)
    observed_error_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    source_thread_id: Mapped[str | None] = mapped_column(String(128))
    source_message_id: Mapped[str | None] = mapped_column(String(128))
    provenance_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    redaction_summary_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    integrity_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    artifact_ids_json: Mapped[dict | None] = mapped_column(JSONB)
    review_state: Mapped[str | None] = mapped_column(String(32))
    operator_note: Mapped[str | None] = mapped_column(Text)
    supersedes_receipt_id: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        Index("ix_receipts_work_order_id", "work_order_id"),
        Index("ix_receipts_command_run_id", "command_run_id"),
        Index("ix_receipts_created_at", "created_at"),
        UniqueConstraint(
            "work_order_id",
            "command_run_id",
            "receipt_kind",
            "schema_version",
            name="uq_receipt_work_order_source",
        ),
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


# =========================
# Continuity Phase A Tables
# =========================
#
# These tables store the durable envelope records for the Continuity Protocol
# Suite.  Phase A includes only the four tables below.  Phase B normalisation
# tables are deferred.  See ADR-031 and continuity-storage-schema-proposal.md.


class ContinuityContextPacket(Base):
    """Persisted Context Packet envelopes with indexed envelope fields."""

    __tablename__ = "continuity_context_packets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(128))
    thread_id: Mapped[str | None] = mapped_column(String(128))
    task_id: Mapped[str | None] = mapped_column(String(128))
    tab_id: Mapped[str | None] = mapped_column(String(128))
    persona_id: Mapped[str | None] = mapped_column(String(128))
    node_id: Mapped[str | None] = mapped_column(String(128))
    team_id: Mapped[str | None] = mapped_column(String(128))
    dyad_id: Mapped[str | None] = mapped_column(String(128))
    source_system: Mapped[str] = mapped_column(String(128), nullable=False)
    source_plugin: Mapped[str | None] = mapped_column(String(128))
    source_provider: Mapped[str | None] = mapped_column(String(128))
    origin_ref: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    provenance_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(32), nullable=False)
    retention: Mapped[str] = mapped_column(String(32), nullable=False)
    integrity_json: Mapped[dict | None] = mapped_column(JSONB)
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    __mapper_args__ = {"eager_defaults": True}


class ContinuityRealityState(Base):
    """Compiled Reality State snapshots with extracted JSON sub-records."""

    __tablename__ = "continuity_reality_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(128))
    thread_id: Mapped[str | None] = mapped_column(String(128))
    task_id: Mapped[str | None] = mapped_column(String(128))
    node_id: Mapped[str | None] = mapped_column(String(128))
    team_id: Mapped[str | None] = mapped_column(String(128))
    dyad_id: Mapped[str | None] = mapped_column(String(128))
    compiled_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    active_branch: Mapped[str | None] = mapped_column(String(256))
    source_packet_ids_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    state_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    accepted_decisions_json: Mapped[dict | None] = mapped_column(JSONB)
    open_loops_json: Mapped[dict | None] = mapped_column(JSONB)
    rejected_paths_json: Mapped[dict | None] = mapped_column(JSONB)
    active_artifacts_json: Mapped[dict | None] = mapped_column(JSONB)
    assumptions_json: Mapped[dict | None] = mapped_column(JSONB)
    risks_json: Mapped[dict | None] = mapped_column(JSONB)
    next_actions_json: Mapped[dict | None] = mapped_column(JSONB)
    confidence: Mapped[float | None] = mapped_column(Float)
    provenance_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    expires_or_decays_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    __mapper_args__ = {"eager_defaults": True}


class ContinuityRealityCommit(Base):
    """Durable Reality Commit records with trigger, kind, and provenance."""

    __tablename__ = "continuity_reality_commits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(128))
    thread_id: Mapped[str | None] = mapped_column(String(128))
    task_id: Mapped[str | None] = mapped_column(String(128))
    node_id: Mapped[str | None] = mapped_column(String(128))
    team_id: Mapped[str | None] = mapped_column(String(128))
    dyad_id: Mapped[str | None] = mapped_column(String(128))
    source_packet_ids_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    previous_state_id: Mapped[str | None] = mapped_column(String(36))
    new_state_id: Mapped[str | None] = mapped_column(String(36))
    provenance_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )

    __mapper_args__ = {"eager_defaults": True}


class ContinuityStatePacketLink(Base):
    """Many-to-many provenance link between states and contributing packets."""

    __tablename__ = "continuity_state_packet_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    state_id: Mapped[str] = mapped_column(String(36), nullable=False)
    packet_id: Mapped[str] = mapped_column(String(36), nullable=False)
    relationship: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "state_id",
            "packet_id",
            "relationship",
            name="uq_cty_state_packet_link",
        ),
    )
    __mapper_args__ = {"eager_defaults": True}


# =========================
# Account Observability
# =========================

ACCOUNT_OBSERVABILITY_INVITE_STATUS_VALUES_SQL = "','".join(
    sorted(INVITE_STATUSES)
)
ACCOUNT_OBSERVABILITY_ATTRIBUTION_METHOD_VALUES_SQL = "','".join(
    sorted(ATTRIBUTION_METHODS)
)
ACCOUNT_OBSERVABILITY_ATTRIBUTION_CONFIDENCE_VALUES_SQL = "','".join(
    sorted(ATTRIBUTION_CONFIDENCES)
)


class AccountObservabilityInviteLink(Base):
    """Operator-authored invite source with one-way token persistence."""

    __tablename__ = "account_observability_invite_links"

    invite_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_label: Mapped[str | None] = mapped_column(String(255))
    placement_label: Mapped[str | None] = mapped_column(String(255))
    created_by_user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=AccountObservabilityInviteStatus.ACTIVE.value,
        server_default=AccountObservabilityInviteStatus.ACTIVE.value,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    disabled_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
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

    __table_args__ = (
        UniqueConstraint(
            "token_hash",
            name="uq_account_observability_invite_links_token_hash",
        ),
        CheckConstraint(
            f"status IN ('{ACCOUNT_OBSERVABILITY_INVITE_STATUS_VALUES_SQL}')",
            name="account_observability_invite_status_check",
        ),
        CheckConstraint(
            "((status = 'active' AND disabled_at IS NULL AND revoked_at IS NULL) "
            "OR (status = 'disabled' AND disabled_at IS NOT NULL AND revoked_at IS NULL) "
            "OR (status = 'revoked' AND revoked_at IS NOT NULL))",
            name="account_observability_invite_lifecycle_check",
        ),
        Index(
            "ix_account_observability_invite_links_status_created_at",
            "status",
            "created_at",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


class AccountObservabilityGuestIdentity(Base):
    """Server-issued pseudonymous guest identity for future attribution."""

    __tablename__ = "account_observability_guest_identities"

    guest_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    first_invite_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "account_observability_invite_links.invite_id",
            ondelete="RESTRICT",
        ),
    )
    converted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
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

    __table_args__ = (
        Index(
            "ix_account_observability_guest_identities_first_invite_id",
            "first_invite_id",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


class AccountObservabilityAccountMetadata(Base):
    """One-to-one, non-auth observability metadata for a canonical user."""

    __tablename__ = "account_observability_account_metadata"

    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    registered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    acquisition_invite_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "account_observability_invite_links.invite_id",
            ondelete="RESTRICT",
        ),
    )
    prior_guest_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "account_observability_guest_identities.guest_id",
            ondelete="SET NULL",
        ),
    )
    attribution_method: Mapped[str | None] = mapped_column(String(64))
    attribution_confidence: Mapped[str | None] = mapped_column(String(32))
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
            f"attribution_method IS NULL OR attribution_method IN ('{ACCOUNT_OBSERVABILITY_ATTRIBUTION_METHOD_VALUES_SQL}')",
            name="account_observability_attribution_method_check",
        ),
        CheckConstraint(
            f"attribution_confidence IS NULL OR attribution_confidence IN ('{ACCOUNT_OBSERVABILITY_ATTRIBUTION_CONFIDENCE_VALUES_SQL}')",
            name="account_observability_attribution_confidence_check",
        ),
        CheckConstraint(
            "((acquisition_invite_id IS NULL AND attribution_method IS NULL AND attribution_confidence IS NULL) "
            "OR (acquisition_invite_id IS NOT NULL "
            "AND attribution_method = 'first_party_first_touch' "
            "AND attribution_confidence = 'verified'))",
            name="account_observability_attribution_consistency_check",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}


class AccountObservabilityPresenceSession(Base):
    """Content-free foreground presence lease for one account or guest."""

    __tablename__ = "account_observability_presence_sessions"

    presence_session_id: Mapped[str] = mapped_column(
        String(36), primary_key=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE")
    )
    guest_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "account_observability_guest_identities.guest_id",
            ondelete="CASCADE",
        ),
    )
    invite_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "account_observability_invite_links.invite_id",
            ondelete="RESTRICT",
        ),
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    country_code: Mapped[str | None] = mapped_column(String(2))
    region_code: Mapped[str | None] = mapped_column(String(64))
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
            "((user_id IS NOT NULL) <> (guest_id IS NOT NULL))",
            name="account_observability_presence_exactly_one_subject_check",
        ),
        CheckConstraint(
            "last_seen_at >= started_at",
            name="account_observability_presence_last_seen_order_check",
        ),
        CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="account_observability_presence_ended_order_check",
        ),
        CheckConstraint(
            "region_code IS NULL OR country_code IS NOT NULL",
            name="account_observability_presence_region_country_check",
        ),
        CheckConstraint(
            "country_code IS NULL OR (length(country_code) = 2 AND country_code = upper(country_code))",
            name="account_observability_presence_country_code_check",
        ),
        Index(
            "ix_account_observability_presence_sessions_user_last_seen_at",
            "user_id",
            "last_seen_at",
        ),
        Index(
            "ix_account_observability_presence_sessions_guest_last_seen_at",
            "guest_id",
            "last_seen_at",
        ),
        Index(
            "ix_account_observability_presence_sessions_invite_started_at",
            "invite_id",
            "started_at",
        ),
        Index(
            "ix_acct_obs_presence_last_seen_country_region",
            "last_seen_at",
            "country_code",
            "region_code",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}
