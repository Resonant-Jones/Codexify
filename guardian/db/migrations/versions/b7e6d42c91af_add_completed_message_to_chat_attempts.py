"""Bind successful chat attempts to their persisted assistant message.

Revision ID: b7e6d42c91af
Revises: 9e52b1d3c8fa
"""

from alembic import op
import sqlalchemy as sa


revision = "b7e6d42c91af"
down_revision = "9e52b1d3c8fa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_completion_attempts",
        sa.Column("completed_message_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_chat_completion_attempts_completed_message",
        "chat_completion_attempts",
        "chat_messages",
        ["completed_message_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_chat_completion_attempts_completed_message",
        "chat_completion_attempts",
        type_="foreignkey",
    )
    op.drop_column("chat_completion_attempts", "completed_message_id")
