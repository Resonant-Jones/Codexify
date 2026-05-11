"""add campaign runner MVP spine tables

Revision ID: aa4c2e7f91b3
Revises: 9d4e1c7b2a6f
Create Date: 2026-05-11 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "aa4c2e7f91b3"
down_revision: str | Sequence[str] | None = "9d4e1c7b2a6f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "campaign_goals",
        sa.Column("goal_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
        sa.Column("source_thread_id", sa.String(length=128), nullable=True),
        sa.Column("source_message_id", sa.String(length=128), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('draft','active','blocked','completed','archived')",
            name="campaign_goals_status_check",
        ),
        sa.PrimaryKeyConstraint("goal_id"),
    )
    op.create_index(
        "ix_campaign_goals_status",
        "campaign_goals",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_campaign_goals_source_thread_id",
        "campaign_goals",
        ["source_thread_id"],
        unique=False,
    )

    op.create_table(
        "campaigns",
        sa.Column("campaign_id", sa.String(length=128), nullable=False),
        sa.Column("goal_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
        sa.Column("source_thread_id", sa.String(length=128), nullable=True),
        sa.Column("source_message_id", sa.String(length=128), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('draft','planned','active','blocked','completed','archived')",
            name="campaigns_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["goal_id"],
            ["campaign_goals.goal_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("campaign_id"),
    )
    op.create_index(
        "ix_campaigns_goal_id",
        "campaigns",
        ["goal_id"],
        unique=False,
    )
    op.create_index(
        "ix_campaigns_status",
        "campaigns",
        ["status"],
        unique=False,
    )

    op.create_table(
        "campaign_execution_attempts",
        sa.Column(
            "attempt_record_id",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("campaign_id", sa.String(length=128), nullable=True),
        sa.Column("goal_id", sa.String(length=64), nullable=True),
        sa.Column("work_order_id", sa.String(length=64), nullable=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("attempt_id", sa.String(length=128), nullable=False),
        sa.Column("coding_task_id", sa.String(length=128), nullable=True),
        sa.Column("adapter_kind", sa.String(length=64), nullable=True),
        sa.Column("runtime_target", sa.String(length=32), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="running",
        ),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("failed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "validation_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("commit_hash", sa.String(length=64), nullable=True),
        sa.Column("delivery_ok", sa.Boolean(), nullable=True),
        sa.Column("delivered_message_id", sa.BigInteger(), nullable=True),
        sa.Column("delivery_reason", sa.String(length=255), nullable=True),
        sa.Column("source_thread_id", sa.Integer(), nullable=True),
        sa.Column("source_message_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "evidence_json",
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
        sa.CheckConstraint(
            "status IN ('running','succeeded','failed','cancelled')",
            name="campaign_execution_attempts_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.campaign_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["goal_id"],
            ["campaign_goals.goal_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["work_order_id"],
            ["coding_work_orders.work_order_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("attempt_record_id"),
        sa.UniqueConstraint(
            "run_id",
            "attempt_id",
            name="uq_campaign_execution_attempts_run_attempt",
        ),
    )
    op.create_index(
        "ix_campaign_execution_attempts_campaign_id",
        "campaign_execution_attempts",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        "ix_campaign_execution_attempts_goal_id",
        "campaign_execution_attempts",
        ["goal_id"],
        unique=False,
    )
    op.create_index(
        "ix_campaign_execution_attempts_work_order_id",
        "campaign_execution_attempts",
        ["work_order_id"],
        unique=False,
    )
    op.create_index(
        "ix_campaign_execution_attempts_status",
        "campaign_execution_attempts",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_campaign_execution_attempts_created_at",
        "campaign_execution_attempts",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_campaign_execution_attempts_created_at",
        table_name="campaign_execution_attempts",
    )
    op.drop_index(
        "ix_campaign_execution_attempts_status",
        table_name="campaign_execution_attempts",
    )
    op.drop_index(
        "ix_campaign_execution_attempts_work_order_id",
        table_name="campaign_execution_attempts",
    )
    op.drop_index(
        "ix_campaign_execution_attempts_goal_id",
        table_name="campaign_execution_attempts",
    )
    op.drop_index(
        "ix_campaign_execution_attempts_campaign_id",
        table_name="campaign_execution_attempts",
    )
    op.drop_table("campaign_execution_attempts")

    op.drop_index("ix_campaigns_status", table_name="campaigns")
    op.drop_index("ix_campaigns_goal_id", table_name="campaigns")
    op.drop_table("campaigns")

    op.drop_index(
        "ix_campaign_goals_source_thread_id",
        table_name="campaign_goals",
    )
    op.drop_index("ix_campaign_goals_status", table_name="campaign_goals")
    op.drop_table("campaign_goals")
