"""Promote direct-message pairs into Relationships with multi-Conversation cardinality and origin provenance.

Creates ``direct_message_relationships`` (canonical one-per-address-pair
authority), ``direct_message_relationship_participants`` (canonical
membership), and ``direct_message_conversation_placements``
(participant-local Project organization).  Existing Conversations keep
their IDs and Message IDs; every Conversation is backfilled onto exactly
one Relationship derived from its existing pair key, origin provenance
remains NULL/unknown (never fabricated), and the obsolete conversation-
participant membership table is removed only after all backfills land.

Revision ID: b2c8d0e3f5a7
Revises: a1b7c9d2e4f6
Create Date: 2026-08-31 00:00:00.000000
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c8d0e3f5a7"
down_revision: Union[str, Sequence[str], None] = "a1b7c9d2e4f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RELATIONSHIPS_TABLE = "direct_message_relationships"
RELATIONSHIP_PARTICIPANTS_TABLE = "direct_message_relationship_participants"
CONVERSATIONS_TABLE = "direct_message_conversations"
CONVERSATION_PARTICIPANTS_TABLE = "direct_message_conversation_participants"
PLACEMENTS_TABLE = "direct_message_conversation_placements"

CONVERSATION_PAIR_UNIQUE = "uq_direct_message_conversations_participant_pair_key"


def _pair_key_parts(pair_key: str) -> list[tuple[str, str]]:
    """Split a ``node:profile|node:profile`` pair key into addresses."""
    addresses: list[tuple[str, str]] = []
    for part in pair_key.split("|"):
        node_id, profile_id = part.split(":", 1)
        addresses.append((node_id, profile_id))
    return addresses


def _backfill_relationships(connection) -> None:
    """One Relationship per distinct existing conversation pair key."""
    pair_keys = connection.execute(
        sa.text(f"SELECT DISTINCT participant_pair_key FROM {CONVERSATIONS_TABLE}")
    ).fetchall()
    for (pair_key,) in pair_keys:
        relationship_id = uuid.uuid4().hex
        connection.execute(
            sa.text(
                f"INSERT INTO {RELATIONSHIPS_TABLE} "
                "(id, participant_pair_key) VALUES (:id, :pair_key)"
            ),
            {"id": relationship_id, "pair_key": pair_key},
        )
        for node_id, profile_id in _pair_key_parts(pair_key):
            connection.execute(
                sa.text(
                    f"INSERT INTO {RELATIONSHIP_PARTICIPANTS_TABLE} "
                    "(id, relationship_id, node_id, profile_id) "
                    "VALUES (:id, :relationship_id, :node_id, :profile_id)"
                ),
                {
                    "id": uuid.uuid4().hex,
                    "relationship_id": relationship_id,
                    "node_id": node_id,
                    "profile_id": profile_id,
                },
            )


def _backfill_conversation_relationships(connection) -> None:
    connection.execute(
        sa.text(
            f"UPDATE {CONVERSATIONS_TABLE} AS c "
            f"SET relationship_id = r.id "
            f"FROM {RELATIONSHIPS_TABLE} AS r "
            "WHERE r.participant_pair_key = c.participant_pair_key"
        )
    )


def _backfill_placements(connection) -> None:
    """Unscoped (NULL Project) placement rows for every existing member."""
    conversations = connection.execute(
        sa.text(f"SELECT id, relationship_id FROM {CONVERSATIONS_TABLE}")
    ).fetchall()
    for conversation_id, relationship_id in conversations:
        members = connection.execute(
            sa.text(
                f"SELECT profile_id FROM {RELATIONSHIP_PARTICIPANTS_TABLE} "
                "WHERE relationship_id = :relationship_id"
            ),
            {"relationship_id": relationship_id},
        ).fetchall()
        for (profile_id,) in members:
            connection.execute(
                sa.text(
                    f"INSERT INTO {PLACEMENTS_TABLE} "
                    "(id, conversation_id, profile_id, project_id) "
                    "VALUES (:id, :conversation_id, :profile_id, NULL)"
                ),
                {
                    "id": uuid.uuid4().hex,
                    "conversation_id": conversation_id,
                    "profile_id": profile_id,
                },
            )


def upgrade() -> None:
    """Create Relationships, migrate pair authority, add origin/placement."""
    connection = op.get_bind()

    # ── Relationship domain ────────────────────────────────────────────────
    op.create_table(
        RELATIONSHIPS_TABLE,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("participant_pair_key", sa.String(length=256), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "participant_pair_key",
            name="uq_direct_message_relationships_participant_pair_key",
        ),
    )

    op.create_table(
        RELATIONSHIP_PARTICIPANTS_TABLE,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("relationship_id", sa.String(length=36), nullable=False),
        sa.Column("node_id", sa.String(length=64), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["relationship_id"],
            [f"{RELATIONSHIPS_TABLE}.id"],
            name="fk_direct_message_relationship_participants_relationship",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["user_profiles.profile_id"],
            name="fk_direct_message_relationship_participants_profile",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "relationship_id",
            "profile_id",
            name="uq_direct_message_relationship_participants_member",
        ),
    )
    op.create_index(
        "ix_direct_message_relationship_participants_profile",
        RELATIONSHIP_PARTICIPANTS_TABLE,
        ["profile_id"],
    )
    op.create_index(
        "ix_direct_message_relationship_participants_relationship",
        RELATIONSHIP_PARTICIPANTS_TABLE,
        ["relationship_id"],
    )

    _backfill_relationships(connection)

    # ── Conversations: relationship + origin columns ───────────────────────
    op.add_column(
        CONVERSATIONS_TABLE,
        sa.Column("relationship_id", sa.String(length=36), nullable=True),
    )
    _backfill_conversation_relationships(connection)
    op.alter_column(CONVERSATIONS_TABLE, "relationship_id", nullable=False)
    op.create_foreign_key(
        "fk_direct_message_conversations_relationship",
        CONVERSATIONS_TABLE,
        RELATIONSHIPS_TABLE,
        ["relationship_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_direct_message_conversations_relationship_activity",
        CONVERSATIONS_TABLE,
        ["relationship_id", "latest_activity_at", "id"],
    )

    op.add_column(
        CONVERSATIONS_TABLE,
        sa.Column("created_by_profile_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        CONVERSATIONS_TABLE,
        sa.Column("origin_project_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        CONVERSATIONS_TABLE,
        sa.Column("origin_thread_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_direct_message_conversations_created_by_profile",
        CONVERSATIONS_TABLE,
        "user_profiles",
        ["created_by_profile_id"],
        ["profile_id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_direct_message_conversations_origin_project",
        CONVERSATIONS_TABLE,
        "projects",
        ["origin_project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_direct_message_conversations_origin_thread",
        CONVERSATIONS_TABLE,
        "chat_threads",
        ["origin_thread_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_direct_message_conversations_origin_project",
        CONVERSATIONS_TABLE,
        ["origin_project_id"],
    )
    op.create_index(
        "ix_direct_message_conversations_origin_thread",
        CONVERSATIONS_TABLE,
        ["origin_thread_id"],
    )

    # ── Placement domain ───────────────────────────────────────────────────
    op.create_table(
        PLACEMENTS_TABLE,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            [f"{CONVERSATIONS_TABLE}.id"],
            name="fk_direct_message_conversation_placements_conversation",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["user_profiles.profile_id"],
            name="fk_direct_message_conversation_placements_profile",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_direct_message_conversation_placements_project",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "profile_id",
            name="uq_direct_message_conversation_placements_member",
        ),
    )
    op.create_index(
        "ix_direct_message_conversation_placements_profile",
        PLACEMENTS_TABLE,
        ["profile_id"],
    )
    op.create_index(
        "ix_direct_message_conversation_placements_project",
        PLACEMENTS_TABLE,
        ["project_id"],
    )
    _backfill_placements(connection)

    # ── Retire the old pair-key authority after all backfills ──────────────
    op.drop_constraint(
        CONVERSATION_PAIR_UNIQUE,
        CONVERSATIONS_TABLE,
        type_="unique",
    )
    op.drop_column(CONVERSATIONS_TABLE, "participant_pair_key")

    op.drop_index(
        "ix_direct_message_conversation_participants_conversation",
        table_name=CONVERSATION_PARTICIPANTS_TABLE,
    )
    op.drop_index(
        "ix_direct_message_conversation_participants_profile",
        table_name=CONVERSATION_PARTICIPANTS_TABLE,
    )
    op.drop_table(CONVERSATION_PARTICIPANTS_TABLE)


def downgrade() -> None:
    """Restore the one-pair-one-conversation shape from ADR-077."""
    connection = op.get_bind()

    # Recreate the old conversation-participant membership table.
    op.create_table(
        CONVERSATION_PARTICIPANTS_TABLE,
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
            [f"{CONVERSATIONS_TABLE}.id"],
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
        CONVERSATION_PARTICIPANTS_TABLE,
        ["profile_id"],
    )
    op.create_index(
        "ix_direct_message_conversation_participants_conversation",
        CONVERSATION_PARTICIPANTS_TABLE,
        ["conversation_id"],
    )

    conversations = connection.execute(
        sa.text(f"SELECT id, relationship_id FROM {CONVERSATIONS_TABLE}")
    ).fetchall()
    for conversation_id, relationship_id in conversations:
        members = connection.execute(
            sa.text(
                f"SELECT node_id, profile_id FROM {RELATIONSHIP_PARTICIPANTS_TABLE} "
                "WHERE relationship_id = :relationship_id"
            ),
            {"relationship_id": relationship_id},
        ).fetchall()
        for node_id, profile_id in members:
            connection.execute(
                sa.text(
                    f"INSERT INTO {CONVERSATION_PARTICIPANTS_TABLE} "
                    "(id, conversation_id, node_id, profile_id) "
                    "VALUES (:id, :conversation_id, :node_id, :profile_id)"
                ),
                {
                    "id": uuid.uuid4().hex,
                    "conversation_id": conversation_id,
                    "node_id": node_id,
                    "profile_id": profile_id,
                },
            )

    # Restore the conversation-level pair key.
    op.add_column(
        CONVERSATIONS_TABLE,
        sa.Column("participant_pair_key", sa.String(length=256), nullable=True),
    )
    connection.execute(
        sa.text(
            f"UPDATE {CONVERSATIONS_TABLE} AS c "
            f"SET participant_pair_key = r.participant_pair_key "
            f"FROM {RELATIONSHIPS_TABLE} AS r "
            "WHERE r.id = c.relationship_id"
        )
    )
    op.alter_column(CONVERSATIONS_TABLE, "participant_pair_key", nullable=False)
    op.create_unique_constraint(
        CONVERSATION_PAIR_UNIQUE,
        CONVERSATIONS_TABLE,
        ["participant_pair_key"],
    )

    # Remove placement, origin, and relationship structures.
    op.drop_index(
        "ix_direct_message_conversation_placements_project",
        table_name=PLACEMENTS_TABLE,
    )
    op.drop_index(
        "ix_direct_message_conversation_placements_profile",
        table_name=PLACEMENTS_TABLE,
    )
    op.drop_table(PLACEMENTS_TABLE)

    op.drop_index(
        "ix_direct_message_conversations_origin_thread",
        table_name=CONVERSATIONS_TABLE,
    )
    op.drop_index(
        "ix_direct_message_conversations_origin_project",
        table_name=CONVERSATIONS_TABLE,
    )
    op.drop_constraint(
        "fk_direct_message_conversations_origin_thread",
        CONVERSATIONS_TABLE,
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_direct_message_conversations_origin_project",
        CONVERSATIONS_TABLE,
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_direct_message_conversations_created_by_profile",
        CONVERSATIONS_TABLE,
        type_="foreignkey",
    )
    op.drop_column(CONVERSATIONS_TABLE, "origin_thread_id")
    op.drop_column(CONVERSATIONS_TABLE, "origin_project_id")
    op.drop_column(CONVERSATIONS_TABLE, "created_by_profile_id")

    op.drop_index(
        "ix_direct_message_conversations_relationship_activity",
        table_name=CONVERSATIONS_TABLE,
    )
    op.drop_constraint(
        "fk_direct_message_conversations_relationship",
        CONVERSATIONS_TABLE,
        type_="foreignkey",
    )
    op.drop_column(CONVERSATIONS_TABLE, "relationship_id")

    op.drop_index(
        "ix_direct_message_relationship_participants_relationship",
        table_name=RELATIONSHIP_PARTICIPANTS_TABLE,
    )
    op.drop_index(
        "ix_direct_message_relationship_participants_profile",
        table_name=RELATIONSHIP_PARTICIPANTS_TABLE,
    )
    op.drop_table(RELATIONSHIP_PARTICIPANTS_TABLE)
    op.drop_table(RELATIONSHIPS_TABLE)
