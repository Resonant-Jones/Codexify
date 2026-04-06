"""add thread_moves and last_interaction_at to chat_threads

Revision ID: 4c9d1e2f3a5b
Revises: 62127ee9a537
Create Date: 2026-04-06 17:45:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c9d1e2f3a5b"
down_revision: Union[str, Sequence[str], None] = "62127ee9a537"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {c["name"] for c in inspector.get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    chat_thread_cols = _column_names("chat_threads")
    if "last_interaction_at" not in chat_thread_cols:
        op.add_column(
            "chat_threads",
            sa.Column(
                "last_interaction_at",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
            ),
        )

    if "ix_chat_threads_last_interaction_at" not in _index_names(
        "chat_threads"
    ):
        op.create_index(
            "ix_chat_threads_last_interaction_at",
            "chat_threads",
            [sa.literal_column("last_interaction_at DESC")],
            unique=False,
        )

    if "thread_moves" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "thread_moves",
            sa.Column(
                "id", sa.BigInteger(), autoincrement=True, nullable=False
            ),
            sa.Column("thread_id", sa.Integer(), nullable=False),
            sa.Column("from_project_id", sa.Integer(), nullable=True),
            sa.Column("to_project_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.String(length=255), nullable=False),
            sa.Column(
                "timestamp",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["thread_id"], ["chat_threads.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["from_project_id"], ["projects.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["to_project_id"], ["projects.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_thread_moves_thread_id",
            "thread_moves",
            ["thread_id"],
            unique=False,
        )
        op.create_index(
            "ix_thread_moves_timestamp",
            "thread_moves",
            [sa.literal_column("timestamp DESC")],
            unique=False,
        )


def downgrade() -> None:
    if "thread_moves" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_index("ix_thread_moves_timestamp", table_name="thread_moves")
        op.drop_index("ix_thread_moves_thread_id", table_name="thread_moves")
        op.drop_table("thread_moves")

    chat_thread_indexes = _index_names("chat_threads")
    if "ix_chat_threads_last_interaction_at" in chat_thread_indexes:
        op.drop_index(
            "ix_chat_threads_last_interaction_at",
            table_name="chat_threads",
        )

    chat_thread_cols = _column_names("chat_threads")
    if "last_interaction_at" in chat_thread_cols:
        op.drop_column("chat_threads", "last_interaction_at")
