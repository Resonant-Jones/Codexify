"""add durable Campaign Continuation Authority records

Revision ID: 17b23052da6a
Revises: 1760875e3c3b
Create Date: 2026-10-05 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "17b23052da6a"
down_revision: str | Sequence[str] | None = "1760875e3c3b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "campaign_continuation_authorities",
        sa.Column("authority_id", sa.String(length=64), nullable=False),
        sa.Column("campaign_id", sa.String(length=128), nullable=False),
        sa.Column(
            "envelope_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("approved_by_actor_id", sa.String(length=255), nullable=False),
        sa.Column(
            "approved_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_by_actor_id", sa.String(length=255), nullable=True),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at > approved_at",
            name="campaign_continuation_authorities_expiry_check",
        ),
        sa.CheckConstraint(
            "(revoked_at IS NULL AND revoked_by_actor_id IS NULL "
            "AND revocation_reason IS NULL) OR "
            "(revoked_at IS NOT NULL AND revoked_by_actor_id IS NOT NULL "
            "AND revocation_reason IS NOT NULL)",
            name="campaign_continuation_authorities_revocation_check",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.campaign_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("authority_id"),
    )
    op.create_index(
        "uq_campaign_continuation_authorities_unrevoked_campaign",
        "campaign_continuation_authorities",
        ["campaign_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_index(
        "ix_campaign_continuation_authorities_campaign_approved_at",
        "campaign_continuation_authorities",
        ["campaign_id", "approved_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_campaign_continuation_authorities_campaign_approved_at",
        table_name="campaign_continuation_authorities",
    )
    op.drop_index(
        "uq_campaign_continuation_authorities_unrevoked_campaign",
        table_name="campaign_continuation_authorities",
    )
    op.drop_table("campaign_continuation_authorities")
