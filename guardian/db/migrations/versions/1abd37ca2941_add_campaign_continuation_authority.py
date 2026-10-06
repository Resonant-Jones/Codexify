"""add durable Campaign Continuation Authority envelopes

Revision ID: 1abd37ca2941
Revises: 1760875e3c3b
Create Date: 2026-10-05 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "1abd37ca2941"
down_revision: str | Sequence[str] | None = "1760875e3c3b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "campaign_continuation_authorities",
        sa.Column("authority_id", sa.String(length=64), nullable=False),
        sa.Column("campaign_id", sa.String(length=128), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "is_latest",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("approval_event_id", sa.String(length=128), nullable=False),
        sa.Column("approved_by_actor_id", sa.String(length=255), nullable=False),
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "allowed_task_classes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "allowed_execution_lanes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "repository_scope",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "workspace_scope",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "validation_classes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "proof_classes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("spend_posture", sa.String(length=64), nullable=False),
        sa.Column(
            "spend_limits",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "retry_permitted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "retry_ceiling",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "downstream_dispatch_permitted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "stop_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_by_actor_id", sa.String(length=255), nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "revision > 0",
            name="campaign_continuation_revision_check",
        ),
        sa.CheckConstraint(
            "(retry_permitted AND retry_ceiling > 0) OR "
            "(NOT retry_permitted AND retry_ceiling = 0)",
            name="campaign_continuation_retry_check",
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at > approved_at",
            name="campaign_continuation_expiry_check",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= approved_at",
            name="campaign_continuation_revoked_at_check",
        ),
        sa.CheckConstraint(
            "superseded_at IS NULL OR superseded_at >= approved_at",
            name="campaign_continuation_superseded_at_check",
        ),
        sa.CheckConstraint(
            "(revoked_at IS NULL AND revoked_by_actor_id IS NULL "
            "AND revocation_reason IS NULL) OR "
            "(revoked_at IS NOT NULL AND revoked_by_actor_id IS NOT NULL "
            "AND revocation_reason IS NOT NULL)",
            name="campaign_continuation_revocation_check",
        ),
        sa.CheckConstraint(
            "is_latest OR superseded_at IS NOT NULL OR revoked_at IS NOT NULL",
            name="campaign_continuation_history_check",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.campaign_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("authority_id"),
        sa.UniqueConstraint(
            "campaign_id",
            "revision",
            name="uq_campaign_continuation_authorities_revision",
        ),
        sa.UniqueConstraint(
            "approval_event_id",
            name="uq_campaign_continuation_authorities_approval_event",
        ),
    )
    op.create_index(
        "uq_campaign_continuation_authorities_latest_campaign",
        "campaign_continuation_authorities",
        ["campaign_id"],
        unique=True,
        postgresql_where=sa.text("is_latest = true"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_campaign_continuation_authorities_latest_campaign",
        table_name="campaign_continuation_authorities",
    )
    op.drop_table("campaign_continuation_authorities")
