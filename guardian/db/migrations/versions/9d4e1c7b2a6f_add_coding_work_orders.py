"""add durable coding work orders table

Revision ID: 9d4e1c7b2a6f
Revises: 8c9d0e1f2a3b
Create Date: 2026-05-10 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9d4e1c7b2a6f"
down_revision: str | Sequence[str] | None = "8c9d0e1f2a3b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "coding_work_orders",
        sa.Column("work_order_id", sa.String(length=64), nullable=False),
        sa.Column("campaign_id", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="ready",
        ),
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("assigned_worker_id", sa.String(length=255), nullable=True),
        sa.Column("source_thread_id", sa.String(length=128), nullable=True),
        sa.Column("source_message_id", sa.String(length=128), nullable=True),
        sa.Column(
            "dependency_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "file_scope",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("validation_command", sa.Text(), nullable=True),
        sa.Column("adapter_kind", sa.String(length=64), nullable=True),
        sa.Column(
            "max_validation_attempts",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "require_worktree_lease",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "commit_after_validation",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "require_human_review_before_merge",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("latest_run_id", sa.String(length=64), nullable=True),
        sa.Column("latest_lease_id", sa.String(length=64), nullable=True),
        sa.Column("latest_receipt_id", sa.String(length=64), nullable=True),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column(
            "extra_meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("archived_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft','ready','leased','running','validating','retrying','passed','failed','blocked','escalated','merge_ready','merged','archived','cancelled')",
            name="coding_work_orders_status_check",
        ),
        sa.PrimaryKeyConstraint("work_order_id"),
    )

    op.create_index(
        "ix_coding_work_orders_campaign_id",
        "coding_work_orders",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        "ix_coding_work_orders_status",
        "coding_work_orders",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_coding_work_orders_priority",
        "coding_work_orders",
        ["priority"],
        unique=False,
    )
    op.create_index(
        "ix_coding_work_orders_assigned_worker_id",
        "coding_work_orders",
        ["assigned_worker_id"],
        unique=False,
    )
    op.create_index(
        "ix_coding_work_orders_source_thread_id",
        "coding_work_orders",
        ["source_thread_id"],
        unique=False,
    )
    op.create_index(
        "ix_coding_work_orders_latest_run_id",
        "coding_work_orders",
        ["latest_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_coding_work_orders_latest_lease_id",
        "coding_work_orders",
        ["latest_lease_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_coding_work_orders_latest_lease_id",
        table_name="coding_work_orders",
    )
    op.drop_index(
        "ix_coding_work_orders_latest_run_id",
        table_name="coding_work_orders",
    )
    op.drop_index(
        "ix_coding_work_orders_source_thread_id",
        table_name="coding_work_orders",
    )
    op.drop_index(
        "ix_coding_work_orders_assigned_worker_id",
        table_name="coding_work_orders",
    )
    op.drop_index(
        "ix_coding_work_orders_priority",
        table_name="coding_work_orders",
    )
    op.drop_index(
        "ix_coding_work_orders_status",
        table_name="coding_work_orders",
    )
    op.drop_index(
        "ix_coding_work_orders_campaign_id",
        table_name="coding_work_orders",
    )
    op.drop_table("coding_work_orders")
