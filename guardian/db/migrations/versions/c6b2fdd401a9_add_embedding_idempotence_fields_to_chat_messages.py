"""add embedding idempotence fields to chat_messages

Revision ID: c6b2fdd401a9
Revises: f2564d429cda
Create Date: 2025-01-02 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c6b2fdd401a9"
down_revision: Union[str, Sequence[str], None] = "f2564d429cda"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column_name in {
        col["name"] for col in inspector.get_columns(table_name)
    }


def upgrade() -> None:
    """Upgrade schema."""
    if not _has_column("chat_messages", "embedded_at"):
        op.add_column(
            "chat_messages",
            sa.Column(
                "embedded_at", sa.TIMESTAMP(timezone=True), nullable=True
            ),
        )
    if not _has_column("chat_messages", "embedding_model"):
        op.add_column(
            "chat_messages",
            sa.Column("embedding_model", sa.Text(), nullable=True),
        )
    if not _has_column("chat_messages", "embedding_backend"):
        op.add_column(
            "chat_messages",
            sa.Column("embedding_backend", sa.Text(), nullable=True),
        )
    if not _has_column("chat_messages", "embedding_schema_version"):
        op.add_column(
            "chat_messages",
            sa.Column("embedding_schema_version", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    if _has_column("chat_messages", "embedding_schema_version"):
        op.drop_column("chat_messages", "embedding_schema_version")
    if _has_column("chat_messages", "embedding_backend"):
        op.drop_column("chat_messages", "embedding_backend")
    if _has_column("chat_messages", "embedding_model"):
        op.drop_column("chat_messages", "embedding_model")
    if _has_column("chat_messages", "embedded_at"):
        op.drop_column("chat_messages", "embedded_at")
