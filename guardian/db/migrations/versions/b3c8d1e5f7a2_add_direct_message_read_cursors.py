"""Add recipient-local direct message read cursors.

Revision ID: b3c8d1e5f7a2
Revises: f0d7c4b2a198

Introduces one participant-local cursor row per (conversation, reading
profile).  The cursor stores only the id of the last message the reading
profile has read; unread counts are derived from the durable message store
and this cursor, so no second message store and no counters are introduced.

The cursor is not a read receipt: it is keyed by the reading profile, and
the other participant can never observe or advance it.  No existing IDs,
messages, relationships, consents, or request lineage are rewritten.
"""
from alembic import op
import sqlalchemy as sa

revision = "b3c8d1e5f7a2"
down_revision = "f0d7c4b2a198"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "direct_message_read_cursors",
        sa.Column(
            "conversation_id",
            sa.String(36),
            sa.ForeignKey("direct_message_conversations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "profile_id",
            sa.String(36),
            sa.ForeignKey("user_profiles.profile_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "last_read_message_id",
            sa.String(36),
            sa.ForeignKey("direct_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_direct_message_read_cursors_profile",
        "direct_message_read_cursors",
        ["profile_id"],
    )


def downgrade():
    op.drop_index(
        "ix_direct_message_read_cursors_profile",
        table_name="direct_message_read_cursors",
    )
    op.drop_table("direct_message_read_cursors")
