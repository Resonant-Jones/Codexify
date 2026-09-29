"""Add durable chat completion attempt authority.

Revision ID: c9f3e2a7b601
Revises: a8d4c2f6b1e9
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c9f3e2a7b601"
down_revision: str | Sequence[str] | None = "a8d4c2f6b1e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_completion_attempts",
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("backend_task_id", sa.String(length=128), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("turn_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("accepted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["chat_threads.id"],
            name="fk_chat_completion_attempts_thread",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("request_id", name="pk_chat_completion_attempts"),
        sa.UniqueConstraint(
            "backend_task_id", name="uq_chat_completion_attempts_backend_task_id"
        ),
    )
    op.create_index(
        "ix_chat_completion_attempts_thread_id",
        "chat_completion_attempts",
        ["thread_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_chat_completion_attempts_thread_id",
        table_name="chat_completion_attempts",
    )
    op.drop_table("chat_completion_attempts")
