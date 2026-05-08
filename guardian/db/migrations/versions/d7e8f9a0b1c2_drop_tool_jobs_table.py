"""drop legacy tool_jobs table

Revision ID: d7e8f9a0b1c2
Revises: b3c4d5e6f7a8
Create Date: 2026-04-27 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tool_jobs" not in inspector.get_table_names():
        return

    index_names = {
        index["name"] for index in inspector.get_indexes("tool_jobs")
    }
    check_constraint_names = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("tool_jobs")
    }

    if "ix_tool_jobs_status" in index_names:
        op.drop_index("ix_tool_jobs_status", table_name="tool_jobs")
    if "ix_tool_jobs_created_at" in index_names:
        op.drop_index("ix_tool_jobs_created_at", table_name="tool_jobs")
    if "tool_jobs_status_check" in check_constraint_names:
        op.drop_constraint(
            "tool_jobs_status_check",
            "tool_jobs",
            type_="check",
        )
    op.drop_table("tool_jobs")


def downgrade() -> None:
    """Downgrade schema."""
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
