"""add delegation packets, jobs, and summaries

Revision ID: d4e5f6a7b8c9
Revises: b0c1d2e3f4a5
Create Date: 2026-04-04 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "b0c1d2e3f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_DELEGATION_STATUS_CHECK = "status IN ('draft', 'approved', 'queued', 'running', 'completed', 'failed', 'cancelled')"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "delegation_packets",
        sa.Column("packet_id", sa.String(length=64), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=True),
        sa.Column("conversation_id", sa.String(length=255), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("repo_path", sa.String(length=1024), nullable=False),
        sa.Column("executor", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("task_prompt", sa.Text(), nullable=False),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "context_json",
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
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            _DELEGATION_STATUS_CHECK,
            name="delegation_packets_status_check",
        ),
        sa.PrimaryKeyConstraint("packet_id"),
    )
    op.create_index(
        "ix_delegation_packets_status",
        "delegation_packets",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_delegation_packets_created_at",
        "delegation_packets",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "delegation_jobs",
        sa.Column("delegation_id", sa.String(length=64), nullable=False),
        sa.Column("packet_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=True),
        sa.Column("conversation_id", sa.String(length=255), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("repo_path", sa.String(length=1024), nullable=False),
        sa.Column("executor", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="approved",
        ),
        sa.Column("task_prompt", sa.Text(), nullable=False),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("queued_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            _DELEGATION_STATUS_CHECK,
            name="delegation_jobs_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["packet_id"],
            ["delegation_packets.packet_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("delegation_id"),
        sa.UniqueConstraint("packet_id", name="uq_delegation_jobs_packet_id"),
        sa.UniqueConstraint("task_id", name="uq_delegation_jobs_task_id"),
    )
    op.create_index(
        "ix_delegation_jobs_status",
        "delegation_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_delegation_jobs_created_at",
        "delegation_jobs",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "delegation_summaries",
        sa.Column("delegation_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="completed",
        ),
        sa.Column(
            "summary_json",
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
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            _DELEGATION_STATUS_CHECK,
            name="delegation_summaries_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["delegation_id"],
            ["delegation_jobs.delegation_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("delegation_id"),
    )
    op.create_index(
        "ix_delegation_summaries_status",
        "delegation_summaries",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_delegation_summaries_created_at",
        "delegation_summaries",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_delegation_summaries_created_at",
        table_name="delegation_summaries",
    )
    op.drop_index(
        "ix_delegation_summaries_status",
        table_name="delegation_summaries",
    )
    op.drop_table("delegation_summaries")

    op.drop_index("ix_delegation_jobs_created_at", table_name="delegation_jobs")
    op.drop_index("ix_delegation_jobs_status", table_name="delegation_jobs")
    op.drop_table("delegation_jobs")

    op.drop_index(
        "ix_delegation_packets_created_at",
        table_name="delegation_packets",
    )
    op.drop_index(
        "ix_delegation_packets_status",
        table_name="delegation_packets",
    )
    op.drop_table("delegation_packets")
