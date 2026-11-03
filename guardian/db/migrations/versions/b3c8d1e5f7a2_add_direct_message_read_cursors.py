"""Add recipient-local direct message read cursors.

Revision ID: b3c8d1e5f7a2
Revises: a6b9d2e4f701

Introduces one participant-local cursor row per (conversation, reading
profile).  The cursor stores only the id of the last message the reading
profile has read; unread counts are derived from the durable message store
and this cursor, so no second message store and no counters are introduced.

The cursor is not a read receipt: it is keyed by the reading profile, and
the other participant can never observe or advance it.  No existing IDs,
messages, relationships, consents, or request lineage are rewritten.

Integration note (2026-10-27, post-rebase integration): this revision was
authored against ``f0d7c4b2a198``, which was the single head at the time.
After local ``main`` was reconciled with ``origin/main``, that revision is a
branch point with two existing heads, and keeping it here would have
introduced a third independent head.  The revision therefore extends
``a6b9d2e4f701`` — the lineage the reconciled mainline most recently
advanced — so this additive migration extends an existing branch rather than
creating an independent one.  No existing revision was rewritten, and the
schema effect of this migration is unchanged.  The reconciled mainline head
count (a6b9d2e4f701, c59e4d1a28f0) is preserved: the read cursor replaces
the a6b9d2e4f701 head in the integrated tree rather than adding to it.
"""
from alembic import op
import sqlalchemy as sa

revision = "b3c8d1e5f7a2"
down_revision = "a6b9d2e4f701"
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
