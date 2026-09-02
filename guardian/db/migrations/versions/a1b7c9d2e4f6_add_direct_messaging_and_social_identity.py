"""Add social identity to profiles and the direct-messaging persistence domain.

Adds the Node-scoped social username surface to ``user_profiles`` and the
durable direct conversation / participant / message tables.  Existing users
remain valid with no username (state ``unset``); nothing is derived from
email; no existing chat or Hosted Room rows are rewritten.

Revision ID: a1b7c9d2e4f6
Revises: f41493d13761
Create Date: 2026-08-31 00:00:00.000000
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b7c9d2e4f6"
down_revision: Union[str, Sequence[str], None] = "f41493d13761"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


USERNAME_STATES_SQL = "'active', 'unset'"
USERNAME_GRAMMAR_SQL = "'^[a-z0-9][a-z0-9_-]{1,30}[a-z0-9]$'"


def _backfill_profile_identity(connection) -> None:
    """Mint durable social tokens for pre-existing profile rows.

    ``profile_id`` is a fresh random token (never derived from email or
    account metadata); ``username_state`` records that no username has been
    deliberately claimed yet.
    """
    rows = connection.execute(
        sa.text("SELECT id FROM user_profiles WHERE profile_id IS NULL")
    ).fetchall()
    for (profile_row_id,) in rows:
        connection.execute(
            sa.text(
                "UPDATE user_profiles SET profile_id = :profile_id, "
                "username_state = COALESCE(username_state, 'unset') "
                "WHERE id = :row_id"
            ),
            {"profile_id": uuid.uuid4().hex, "row_id": profile_row_id},
        )


def upgrade() -> None:
    """Create the social identity and direct-messaging persistence domain."""
    connection = op.get_bind()

    # ── user_profiles: social identity columns ────────────────────────────
    op.add_column(
        "user_profiles",
        sa.Column("profile_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("node_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("username", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("username_state", sa.String(length=16), nullable=True),
    )

    _backfill_profile_identity(connection)

    op.create_unique_constraint(
        "uq_user_profiles_profile_id",
        "user_profiles",
        ["profile_id"],
    )
    op.create_unique_constraint(
        "uq_user_profiles_node_username",
        "user_profiles",
        ["node_id", "username"],
    )
    op.create_check_constraint(
        "ck_user_profiles_username_grammar",
        "user_profiles",
        f"username IS NULL OR username ~ {USERNAME_GRAMMAR_SQL}",
    )
    op.create_check_constraint(
        "ck_user_profiles_username_state",
        "user_profiles",
        f"username_state IS NULL OR username_state IN ({USERNAME_STATES_SQL})",
    )
    op.create_check_constraint(
        "ck_user_profiles_username_state_consistency",
        "user_profiles",
        "(username_state = 'active') = (username IS NOT NULL)",
    )
    op.create_foreign_key(
        "fk_user_profiles_node_id",
        "user_profiles",
        "threadspace_nodes",
        ["node_id"],
        ["node_id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_user_profiles_node_id",
        "user_profiles",
        ["node_id"],
    )

    # ── Direct conversations ──────────────────────────────────────────────
    op.create_table(
        "direct_message_conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "kind",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'direct'"),
        ),
        sa.Column("participant_pair_key", sa.String(length=256), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "latest_activity_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "participant_pair_key",
            name="uq_direct_message_conversations_participant_pair_key",
        ),
        sa.CheckConstraint(
            "kind IN ('direct')",
            name="ck_direct_message_conversations_kind",
        ),
    )

    op.create_table(
        "direct_message_conversation_participants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("node_id", sa.String(length=64), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column(
            "joined_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["direct_message_conversations.id"],
            name="fk_direct_message_conversation_participants_conversation",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["user_profiles.profile_id"],
            name="fk_direct_message_conversation_participants_profile",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "profile_id",
            name="uq_direct_message_conversation_participants_member",
        ),
    )
    op.create_index(
        "ix_direct_message_conversation_participants_profile",
        "direct_message_conversation_participants",
        ["profile_id"],
    )
    op.create_index(
        "ix_direct_message_conversation_participants_conversation",
        "direct_message_conversation_participants",
        ["conversation_id"],
    )

    # ── Direct messages ───────────────────────────────────────────────────
    op.create_table(
        "direct_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("sender_node_id", sa.String(length=64), nullable=False),
        sa.Column("sender_profile_id", sa.String(length=36), nullable=False),
        sa.Column(
            "content_type",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'text/plain'"),
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("client_message_key", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["direct_message_conversations.id"],
            name="fk_direct_messages_conversation",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_profile_id"],
            ["user_profiles.profile_id"],
            name="fk_direct_messages_sender_profile",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "sender_profile_id",
            "client_message_key",
            name="uq_direct_messages_idempotency",
        ),
        sa.CheckConstraint(
            "content_type IN ('text/plain')",
            name="ck_direct_messages_content_type",
        ),
        sa.CheckConstraint(
            "length(trim(body)) > 0",
            name="ck_direct_messages_body_nonblank",
        ),
        sa.CheckConstraint(
            "client_message_key IS NULL OR length(trim(client_message_key)) > 0",
            name="ck_direct_messages_client_key_nonblank",
        ),
    )
    op.create_index(
        "ix_direct_messages_conversation_chronological",
        "direct_messages",
        ["conversation_id", "created_at", "id"],
    )
    op.create_index(
        "ix_direct_messages_sender_profile_id",
        "direct_messages",
        ["sender_profile_id"],
    )


def downgrade() -> None:
    """Remove only the structures added by this revision."""
    op.drop_index(
        "ix_direct_messages_sender_profile_id",
        table_name="direct_messages",
    )
    op.drop_index(
        "ix_direct_messages_conversation_chronological",
        table_name="direct_messages",
    )
    op.drop_table("direct_messages")

    op.drop_index(
        "ix_direct_message_conversation_participants_conversation",
        table_name="direct_message_conversation_participants",
    )
    op.drop_index(
        "ix_direct_message_conversation_participants_profile",
        table_name="direct_message_conversation_participants",
    )
    op.drop_table("direct_message_conversation_participants")
    op.drop_table("direct_message_conversations")

    op.drop_index("ix_user_profiles_node_id", table_name="user_profiles")
    op.drop_constraint("fk_user_profiles_node_id", "user_profiles", type_="foreignkey")
    op.drop_constraint(
        "ck_user_profiles_username_state_consistency",
        "user_profiles",
        type_="check",
    )
    op.drop_constraint(
        "ck_user_profiles_username_state",
        "user_profiles",
        type_="check",
    )
    op.drop_constraint(
        "ck_user_profiles_username_grammar",
        "user_profiles",
        type_="check",
    )
    op.drop_constraint(
        "uq_user_profiles_node_username", "user_profiles", type_="unique"
    )
    op.drop_constraint("uq_user_profiles_profile_id", "user_profiles", type_="unique")
    op.drop_column("user_profiles", "username_state")
    op.drop_column("user_profiles", "username")
    op.drop_column("user_profiles", "node_id")
    op.drop_column("user_profiles", "profile_id")
