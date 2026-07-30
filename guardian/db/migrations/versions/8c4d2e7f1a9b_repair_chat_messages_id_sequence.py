"""Repair stale PostgreSQL identity allocation for chat messages.

Explicit-ID restore and legacy setup paths can leave the sequence behind the
persisted maximum message ID.  Repair only raises the sequence to the minimum
safe value; it never rewinds an existing allocation position.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "8c4d2e7f1a9b"
down_revision: Union[str, Sequence[str], None] = "8b02d5f3a7c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Raise the chat-message sequence when persisted IDs are ahead of it."""
    op.execute(
        """
        DO $$
        DECLARE
            sequence_name text;
            max_message_id bigint;
            sequence_value bigint;
            sequence_called boolean;
        BEGIN
            IF to_regclass('public.chat_messages') IS NULL THEN
                RETURN;
            END IF;

            SELECT pg_get_serial_sequence('public.chat_messages', 'id')
            INTO sequence_name;

            IF sequence_name IS NULL THEN
                RETURN;
            END IF;

            SELECT COALESCE(MAX(id), 0)
            INTO max_message_id
            FROM public.chat_messages;

            IF max_message_id <= 0 THEN
                RETURN;
            END IF;

            EXECUTE format(
                'SELECT last_value, is_called FROM %s',
                sequence_name::regclass
            )
            INTO sequence_value, sequence_called;

            IF sequence_value < max_message_id
               OR (sequence_value = max_message_id AND NOT sequence_called)
            THEN
                PERFORM setval(sequence_name::regclass, max_message_id, true);
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Identity repair is monotonic and has no safe downgrade operation."""
    pass
