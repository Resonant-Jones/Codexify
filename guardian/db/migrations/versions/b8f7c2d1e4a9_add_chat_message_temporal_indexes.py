"""add chat message temporal indexes

Revision ID: b8f7c2d1e4a9
Revises: f4e7c1a2b3d4
Create Date: 2026-02-08 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8f7c2d1e4a9"
down_revision: Union[str, Sequence[str], None] = "f4e7c1a2b3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Composite chronological index for turn-window stitching:
    # (source_thread_id, turn_index)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_chat_messages_source_thread_turn_index
        ON chat_messages (
            (extra_meta->>'source_thread_id'),
            ((extra_meta->>'turn_index')::integer)
        )
        WHERE extra_meta ? 'source_thread_id'
          AND extra_meta ? 'turn_index'
          AND (extra_meta->>'turn_index') ~ '^[0-9]+$'
        """
    )

    # Composite chronological index for timestamp scans:
    # (source_thread_id, source_created_at)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_chat_messages_source_thread_created_at
        ON chat_messages (
            (extra_meta->>'source_thread_id'),
            ((extra_meta->>'source_created_at')::timestamptz)
        )
        WHERE extra_meta ? 'source_thread_id'
          AND extra_meta ? 'source_created_at'
          AND (extra_meta->>'source_created_at') <> ''
        """
    )

    # Safe idempotency uniqueness for imports:
    # (source_thread_id, source_message_id) where both are present.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_chat_messages_source_thread_message
        ON chat_messages (
            (extra_meta->>'source_thread_id'),
            (extra_meta->>'source_message_id')
        )
        WHERE extra_meta ? 'source_thread_id'
          AND extra_meta ? 'source_message_id'
          AND (extra_meta->>'source_message_id') <> ''
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS uq_chat_messages_source_thread_message")
    op.execute("DROP INDEX IF EXISTS ix_chat_messages_source_thread_created_at")
    op.execute("DROP INDEX IF EXISTS ix_chat_messages_source_thread_turn_index")
