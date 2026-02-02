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


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "chat_messages",
        sa.Column("embedded_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("embedding_model", sa.Text(), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("embedding_backend", sa.Text(), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("embedding_schema_version", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("chat_messages", "embedding_schema_version")
    op.drop_column("chat_messages", "embedding_backend")
    op.drop_column("chat_messages", "embedding_model")
    op.drop_column("chat_messages", "embedded_at")
