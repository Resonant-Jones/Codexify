"""add active_profile_id to chat_threads

Revision ID: 7f6e5d4c3b2a
Revises: c7a253a50757
Create Date: 2026-02-15 16:55:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7f6e5d4c3b2a"
down_revision: Union[str, Sequence[str], None] = "c7a253a50757"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        ALTER TABLE public.chat_threads
        ADD COLUMN IF NOT EXISTS active_profile_id VARCHAR(128);
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        ALTER TABLE public.chat_threads
        DROP COLUMN IF EXISTS active_profile_id;
        """
    )
