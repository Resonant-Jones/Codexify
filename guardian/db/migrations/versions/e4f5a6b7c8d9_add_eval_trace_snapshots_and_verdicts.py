"""add eval trace snapshots and verdict tables

Revision ID: e4f5a6b7c8d9
Revises: a1b2c3d4e5f6, c1d2e3f4a5b6, f2b3c4d5e6f8
Create Date: 2026-04-22 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: str | Sequence[str] | None = (
    "a1b2c3d4e5f6",
    "c1d2e3f4a5b6",
    "f2b3c4d5e6f8",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "eval_trace_snapshots",
        sa.Column(
            "trace_snapshot_id",
            sa.String(length=64),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=255), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("user_message_id", sa.BigInteger(), nullable=True),
        sa.Column("assistant_message_id", sa.BigInteger(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("source_mode", sa.String(length=64), nullable=True),
        sa.Column("widen_reason", sa.String(length=128), nullable=True),
        sa.Column(
            "retrieval_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("assistant_output_text", sa.Text(), nullable=False),
        sa.Column(
            "trace",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "payload_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "timestamps",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["chat_threads.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_message_id"],
            ["chat_messages.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assistant_message_id"],
            ["chat_messages.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("task_id", name="uq_eval_trace_snapshots_task_id"),
    )
    op.create_index(
        "ix_eval_trace_snapshots_thread_created",
        "eval_trace_snapshots",
        ["thread_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "eval_verdicts",
        sa.Column(
            "id",
            sa.BigInteger(),
            nullable=False,
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("eval_run_id", sa.String(length=64), nullable=False),
        sa.Column(
            "trace_snapshot_id",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(length=255), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("user_message_id", sa.BigInteger(), nullable=True),
        sa.Column("assistant_message_id", sa.BigInteger(), nullable=True),
        sa.Column("evaluator_kind", sa.String(length=32), nullable=False),
        sa.Column("evaluator_name", sa.String(length=128), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "structured_findings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "evaluator_kind IN ('code', 'llm_judge')",
            name="eval_verdicts_evaluator_kind_check",
        ),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed')",
            name="eval_verdicts_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["trace_snapshot_id"],
            ["eval_trace_snapshots.trace_snapshot_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["chat_threads.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_message_id"],
            ["chat_messages.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assistant_message_id"],
            ["chat_messages.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "eval_run_id",
            "evaluator_name",
            name="uq_eval_verdicts_run_evaluator",
        ),
    )
    op.create_index(
        "ix_eval_verdicts_thread_created",
        "eval_verdicts",
        ["thread_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_eval_verdicts_thread_created", table_name="eval_verdicts")
    op.drop_table("eval_verdicts")
    op.drop_index(
        "ix_eval_trace_snapshots_thread_created",
        table_name="eval_trace_snapshots",
    )
    op.drop_table("eval_trace_snapshots")
