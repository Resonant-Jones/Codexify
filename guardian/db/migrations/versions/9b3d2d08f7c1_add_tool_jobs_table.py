"""add tool_jobs table for durable tools orchestration

Revision ID: 9b3d2d08f7c1
Revises: f2564d429cda
Create Date: 2026-02-21 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9b3d2d08f7c1"
down_revision: Union[str, Sequence[str], None] = "f2564d429cda"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "tool_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tool_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "request_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "result_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "error_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "tool_jobs_status_check",
        "tool_jobs",
        "status IN ('queued','running','succeeded','failed')",
    )
    op.create_index("ix_tool_jobs_created_at", "tool_jobs", ["created_at"])
    op.create_index("ix_tool_jobs_status", "tool_jobs", ["status"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_tool_jobs_status", table_name="tool_jobs")
    op.drop_index("ix_tool_jobs_created_at", table_name="tool_jobs")
    op.drop_constraint("tool_jobs_status_check", "tool_jobs", type_="check")
    op.drop_table("tool_jobs")
