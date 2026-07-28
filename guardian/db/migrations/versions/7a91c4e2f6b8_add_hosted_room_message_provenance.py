"""add Hosted Room participant provenance to chat_messages

Revision ID: 7a91c4e2f6b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-28 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7a91c4e2f6b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Maximum display-name snapshot length (matches participant display_name)
_SNAPSHOT_MAX_LENGTH = 255


def upgrade() -> None:
    # Add nullable participant foreign key to chat_messages
    op.add_column(
        "chat_messages",
        sa.Column(
            "hosted_room_participant_id",
            sa.String(length=36),
            nullable=True,
        ),
    )
    # Add nullable sender display-name snapshot
    op.add_column(
        "chat_messages",
        sa.Column(
            "sender_display_name_snapshot",
            sa.String(length=_SNAPSHOT_MAX_LENGTH),
            nullable=True,
        ),
    )

    # Paired-provenance constraint:
    # Either both fields are NULL, or both are non-NULL and the snapshot is non-blank.
    op.create_check_constraint(
        "ck_chat_messages_paired_provenance",
        "chat_messages",
        (
            "("
            "hosted_room_participant_id IS NULL "
            "AND sender_display_name_snapshot IS NULL"
            ") OR ("
            "hosted_room_participant_id IS NOT NULL "
            "AND sender_display_name_snapshot IS NOT NULL "
            "AND sender_display_name_snapshot <> ''"
            ")"
        ),
    )

    # Foreign key from participant ID to hosted_room_participants
    op.create_foreign_key(
        "fk_chat_messages_hosted_room_participant_id",
        "chat_messages",
        "hosted_room_participants",
        ["hosted_room_participant_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Index for room transcript rendering and provenance inspection
    op.create_index(
        "ix_chat_messages_hosted_room_participant_id",
        "chat_messages",
        ["hosted_room_participant_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_chat_messages_hosted_room_participant_id",
        table_name="chat_messages",
    )
    op.drop_constraint(
        "fk_chat_messages_hosted_room_participant_id",
        "chat_messages",
        type_="foreignkey",
    )
    op.drop_constraint(
        "ck_chat_messages_paired_provenance",
        "chat_messages",
        type_="check",
    )
    op.drop_column("chat_messages", "sender_display_name_snapshot")
    op.drop_column("chat_messages", "hosted_room_participant_id")
