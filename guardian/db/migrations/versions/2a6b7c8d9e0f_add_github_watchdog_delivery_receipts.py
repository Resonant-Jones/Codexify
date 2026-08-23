"""add GitHub Watchdog delivery receipts

Revision ID: 2a6b7c8d9e0f
Revises: 1c0a2b3c4d5e
Create Date: 2026-08-23 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "2a6b7c8d9e0f"
down_revision: Union[str, Sequence[str], None] = "1c0a2b3c4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "github_watchdog_delivery_receipts",
        sa.Column("receipt_id", sa.String(length=36), nullable=False),
        sa.Column("github_delivery_id", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("event_name", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("installation_id", sa.String(length=64), nullable=True),
        sa.Column("repository_id", sa.String(length=64), nullable=True),
        sa.Column("repository_full_name", sa.String(length=512), nullable=True),
        sa.Column("trigger_actor_id", sa.String(length=64), nullable=True),
        sa.Column("trigger_actor_login", sa.String(length=255), nullable=True),
        sa.Column("pull_request_number", sa.Integer(), nullable=True),
        sa.Column("head_sha", sa.String(length=64), nullable=True),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "first_received_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_received_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "redelivery_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("receipt_id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_github_watchdog_delivery_receipts_idempotency_key",
        ),
    )
    op.create_index(
        "ix_github_watchdog_delivery_receipts_github_delivery_id",
        "github_watchdog_delivery_receipts",
        ["github_delivery_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_github_watchdog_delivery_receipts_github_delivery_id",
        table_name="github_watchdog_delivery_receipts",
    )
    op.drop_table("github_watchdog_delivery_receipts")
