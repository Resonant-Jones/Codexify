"""add metadata to chat_threads

Revision ID: f2564d429cda
Revises: ef5f8a0c49a5
Create Date: 2025-12-17 21:25:28.133475

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2564d429cda"
down_revision: Union[str, Sequence[str], None] = "ef5f8a0c49a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Idempotent guard: some dev DBs may already have this column.
    op.execute(
        """
        ALTER TABLE public.chat_threads
        ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        ALTER TABLE public.chat_threads
        DROP COLUMN IF EXISTS metadata;
        """
    )
