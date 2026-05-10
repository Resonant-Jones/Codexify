"""add durable coding worktree leases table

Revision ID: 8c9d0e1f2a3b
Revises: 7a6b5c4d3e2f
Create Date: 2026-05-09 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8c9d0e1f2a3b"
down_revision: str | Sequence[str] | None = "7a6b5c4d3e2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "coding_worktree_leases",
        sa.Column("lease_id", sa.String(length=64), nullable=False),
        sa.Column("work_order_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("worker_id", sa.String(length=255), nullable=False),
        sa.Column("base_ref", sa.String(length=255), nullable=False),
        sa.Column("branch_name", sa.String(length=255), nullable=False),
        sa.Column("worktree_path", sa.String(length=1024), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "preserve_on_failure",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("cleanup_policy", sa.String(length=64), nullable=False),
        sa.Column(
            "last_heartbeat_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("released_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "cleanup_completed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("cleanup_error", sa.Text(), nullable=True),
        sa.Column(
            "extra_meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('active','expired','released','abandoned','cleanup_pending','cleaned','blocked','failed')",
            name="coding_worktree_leases_status_check",
        ),
        sa.CheckConstraint(
            "cleanup_policy IN ('cleanup_on_merge','preserve_on_fail','manual_cleanup_required')",
            name="coding_worktree_leases_cleanup_policy_check",
        ),
        sa.PrimaryKeyConstraint("lease_id"),
    )

    op.create_index(
        "ix_coding_worktree_leases_work_order_id",
        "coding_worktree_leases",
        ["work_order_id"],
        unique=False,
    )
    op.create_index(
        "ix_coding_worktree_leases_run_id",
        "coding_worktree_leases",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_coding_worktree_leases_worker_id",
        "coding_worktree_leases",
        ["worker_id"],
        unique=False,
    )
    op.create_index(
        "ix_coding_worktree_leases_status",
        "coding_worktree_leases",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_coding_worktree_leases_branch_name",
        "coding_worktree_leases",
        ["branch_name"],
        unique=False,
    )
    op.create_index(
        "ix_coding_worktree_leases_worktree_path",
        "coding_worktree_leases",
        ["worktree_path"],
        unique=False,
    )
    op.create_index(
        "uq_coding_worktree_leases_active_branch_name",
        "coding_worktree_leases",
        ["branch_name"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "uq_coding_worktree_leases_active_worktree_path",
        "coding_worktree_leases",
        ["worktree_path"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_coding_worktree_leases_active_worktree_path",
        table_name="coding_worktree_leases",
    )
    op.drop_index(
        "uq_coding_worktree_leases_active_branch_name",
        table_name="coding_worktree_leases",
    )
    op.drop_index(
        "ix_coding_worktree_leases_worktree_path",
        table_name="coding_worktree_leases",
    )
    op.drop_index(
        "ix_coding_worktree_leases_branch_name",
        table_name="coding_worktree_leases",
    )
    op.drop_index(
        "ix_coding_worktree_leases_status",
        table_name="coding_worktree_leases",
    )
    op.drop_index(
        "ix_coding_worktree_leases_worker_id",
        table_name="coding_worktree_leases",
    )
    op.drop_index(
        "ix_coding_worktree_leases_run_id",
        table_name="coding_worktree_leases",
    )
    op.drop_index(
        "ix_coding_worktree_leases_work_order_id",
        table_name="coding_worktree_leases",
    )
    op.drop_table("coding_worktree_leases")
