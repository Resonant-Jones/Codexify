"""Persist worker-owned chat failure and cancellation outcomes.

Revision ID: d4c69e03a712
Revises: b7e6d42c91af
"""

from alembic import op
import sqlalchemy as sa


revision = "d4c69e03a712"
down_revision = "b7e6d42c91af"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_completion_attempts",
        sa.Column("terminal_event_type", sa.String(length=32), nullable=True),
    )
    op.create_check_constraint(
        "ck_chat_completion_attempts_terminal_event",
        "chat_completion_attempts",
        "terminal_event_type IS NULL OR terminal_event_type IN "
        "('task.failed', 'task.cancelled')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_chat_completion_attempts_terminal_event",
        "chat_completion_attempts",
        type_="check",
    )
    op.drop_column("chat_completion_attempts", "terminal_event_type")
