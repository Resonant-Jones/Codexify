"""add cron_jobs and cron_runs tables

Revision ID: e5d6f4a2190c
Revises: 90d9b9177a0e
Create Date: 2026-02-07 00:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5d6f4a2190c"
down_revision: Union[str, Sequence[str], None] = "90d9b9177a0e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "cron_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("schedule", sa.String(length=128), nullable=False),
        sa.Column(
            "job_type",
            sa.String(length=32),
            nullable=False,
            server_default="noop",
        ),
        sa.Column(
            "payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cron_jobs_is_enabled", "cron_jobs", ["is_enabled"], unique=False
    )
    op.create_index(
        "ix_cron_jobs_updated_at", "cron_jobs", ["updated_at"], unique=False
    )

    op.create_table(
        "cron_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="cron_runs_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["cron_jobs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cron_runs_job_id", "cron_runs", ["job_id"], unique=False)
    op.create_index("ix_cron_runs_status", "cron_runs", ["status"], unique=False)
    op.create_index(
        "ix_cron_runs_created_at", "cron_runs", ["created_at"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index("ix_cron_runs_created_at", table_name="cron_runs")
    op.drop_index("ix_cron_runs_status", table_name="cron_runs")
    op.drop_index("ix_cron_runs_job_id", table_name="cron_runs")
    op.drop_table("cron_runs")

    op.drop_index("ix_cron_jobs_updated_at", table_name="cron_jobs")
    op.drop_index("ix_cron_jobs_is_enabled", table_name="cron_jobs")
    op.drop_table("cron_jobs")
