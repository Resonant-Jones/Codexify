"""add command bus phase1 tables

Revision ID: e0f1a2b3c4d5
Revises: d1a6b9f2c4e7
Create Date: 2026-02-23

"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e0f1a2b3c4d5"
down_revision: str | Sequence[str] | None = "d1a6b9f2c4e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "command_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("command_id", sa.String(length=512), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("actor_kind", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=False),
        sa.Column("actor_session_id", sa.String(length=255), nullable=True),
        sa.Column("delegated_by", sa.String(length=255), nullable=True),
        sa.Column("auth_subject", sa.String(length=255), nullable=False),
        sa.Column("invoke_version", sa.String(length=32), nullable=False),
        sa.Column("args_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "args_redacted",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "result_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'blocked')",
            name="command_runs_status_check",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index(
        "ix_command_runs_command_id",
        "command_runs",
        ["command_id"],
        unique=False,
    )
    op.create_index(
        "ix_command_runs_status", "command_runs", ["status"], unique=False
    )
    op.create_index(
        "ix_command_runs_created_at",
        "command_runs",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "command_run_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "payload_json",
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
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["command_runs.run_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "sequence",
            name="uq_command_run_events_run_sequence",
        ),
    )
    op.create_index(
        "ix_command_run_events_run_id",
        "command_run_events",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_command_run_events_created_at",
        "command_run_events",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_command_run_events_created_at", table_name="command_run_events"
    )
    op.drop_index(
        "ix_command_run_events_run_id", table_name="command_run_events"
    )
    op.drop_table("command_run_events")

    op.drop_index("ix_command_runs_created_at", table_name="command_runs")
    op.drop_index("ix_command_runs_status", table_name="command_runs")
    op.drop_index("ix_command_runs_command_id", table_name="command_runs")
    op.drop_table("command_runs")
