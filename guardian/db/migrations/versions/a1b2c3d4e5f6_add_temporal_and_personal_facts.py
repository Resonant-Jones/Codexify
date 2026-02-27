"""add temporal fields and personal facts tables

Revision ID: a1b2c3d4e5f6
Revises: c6b2fdd401a9
Create Date: 2026-01-12 00:00:00.000000

This migration adds:
1. event_at, kind, extra_meta columns to chat_messages for temporal ordering
2. personal_facts table for correctable facts about users
3. personal_fact_evidence table for multi-evidence support
4. personal_fact_revisions table for audit trail
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "c6b2fdd401a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return column_name in {
        col["name"] for col in inspector.get_columns(table_name)
    }


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return index_name in {
        idx["name"] for idx in inspector.get_indexes(table_name)
    }


def upgrade() -> None:
    """Upgrade schema."""
    # =========================================================================
    # 1. Add temporal columns to chat_messages
    # =========================================================================

    # Add event_at column (when the event actually happened)
    if not _has_column("chat_messages", "event_at"):
        op.add_column(
            "chat_messages",
            sa.Column(
                "event_at",
                sa.TIMESTAMP(timezone=True),
                nullable=True,  # Initially nullable for backfill
            ),
        )

    # Backfill event_at from created_at
    if _has_column("chat_messages", "event_at"):
        op.execute(
            "UPDATE chat_messages SET event_at = created_at WHERE event_at IS NULL"
        )

    # Now make it NOT NULL with default
    if _has_column("chat_messages", "event_at"):
        op.alter_column(
            "chat_messages",
            "event_at",
            nullable=False,
            server_default=sa.text("NOW()"),
        )

    # Add kind column (message type discriminator)
    if not _has_column("chat_messages", "kind"):
        op.add_column(
            "chat_messages",
            sa.Column(
                "kind",
                sa.String(32),
                nullable=False,
                server_default="chat",
            ),
        )

    # Add extra_meta column (JSONB for extensible metadata)
    if not _has_column("chat_messages", "extra_meta"):
        op.add_column(
            "chat_messages",
            sa.Column(
                "extra_meta",
                JSONB,
                nullable=False,
                server_default="{}",
            ),
        )

    # Add composite index for temporal ordering queries
    if not _has_index("chat_messages", "ix_chat_messages_thread_event"):
        op.create_index(
            "ix_chat_messages_thread_event",
            "chat_messages",
            ["thread_id", "event_at", "id"],
        )

    # Add index for kind filtering
    if not _has_index("chat_messages", "ix_chat_messages_kind"):
        op.create_index(
            "ix_chat_messages_kind",
            "chat_messages",
            ["thread_id", "kind"],
        )

    # =========================================================================
    # 2. Create personal_facts table
    # =========================================================================
    if not _has_table("personal_facts"):
        op.create_table(
            "personal_facts",
            sa.Column(
                "id", sa.BigInteger, primary_key=True, autoincrement=True
            ),
            sa.Column("user_id", sa.String(255), nullable=False),
            sa.Column("key", sa.String(255), nullable=False),
            sa.Column("value", sa.Text, nullable=False),
            sa.Column(
                "status",
                sa.String(32),
                nullable=False,
                server_default="candidate",
            ),
            sa.Column(
                "confidence", sa.Float, nullable=False, server_default="0.5"
            ),
            sa.Column(
                "is_active", sa.Boolean, nullable=False, server_default="true"
            ),
            sa.Column(
                "last_confirmed_at", sa.TIMESTAMP(timezone=True), nullable=True
            ),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.CheckConstraint(
                "status IN ('candidate', 'verified', 'disputed', 'archived')",
                name="personal_facts_status_check",
            ),
            sa.CheckConstraint(
                "confidence >= 0.0 AND confidence <= 1.0",
                name="personal_facts_confidence_check",
            ),
        )

    # Unique index: only ONE active fact per user+key
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_personal_facts_active_key
        ON personal_facts (user_id, key)
        WHERE is_active = TRUE
    """
    )

    # Index for retrieval by status
    if not _has_index("personal_facts", "ix_personal_facts_user_status"):
        op.create_index(
            "ix_personal_facts_user_status",
            "personal_facts",
            ["user_id", "status", "is_active"],
        )

    # =========================================================================
    # 3. Create personal_fact_evidence table
    # =========================================================================
    if not _has_table("personal_fact_evidence"):
        op.create_table(
            "personal_fact_evidence",
            sa.Column(
                "id", sa.BigInteger, primary_key=True, autoincrement=True
            ),
            sa.Column(
                "fact_id",
                sa.BigInteger,
                sa.ForeignKey("personal_facts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "source_message_id",
                sa.BigInteger,
                sa.ForeignKey("chat_messages.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("excerpt", sa.Text, nullable=True),
            sa.Column(
                "modality",
                sa.String(64),
                nullable=False,
                server_default="text",
            ),
            sa.Column(
                "confidence", sa.Float, nullable=False, server_default="0.5"
            ),
            sa.Column("source_type", sa.String(64), nullable=False),
            sa.Column(
                "evidence_meta", JSONB, nullable=False, server_default="{}"
            ),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.CheckConstraint(
                "modality IN ('text', 'voice', 'image', 'inferred')",
                name="fact_evidence_modality_check",
            ),
            sa.CheckConstraint(
                "source_type IN ('chatgpt_import', 'runtime_extraction', 'user_stated', 'user_corrected')",
                name="fact_evidence_source_type_check",
            ),
        )

    if not _has_index("personal_fact_evidence", "ix_fact_evidence_fact_id"):
        op.create_index(
            "ix_fact_evidence_fact_id",
            "personal_fact_evidence",
            ["fact_id"],
        )

    if not _has_index(
        "personal_fact_evidence", "ix_fact_evidence_source_message"
    ):
        op.create_index(
            "ix_fact_evidence_source_message",
            "personal_fact_evidence",
            ["source_message_id"],
        )

    # =========================================================================
    # 4. Create personal_fact_revisions table
    # =========================================================================
    if not _has_table("personal_fact_revisions"):
        op.create_table(
            "personal_fact_revisions",
            sa.Column(
                "id", sa.BigInteger, primary_key=True, autoincrement=True
            ),
            sa.Column(
                "fact_id",
                sa.BigInteger,
                sa.ForeignKey("personal_facts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("actor", sa.String(64), nullable=False),
            sa.Column("action", sa.String(32), nullable=False),
            sa.Column("field_changed", sa.String(64), nullable=True),
            sa.Column("old_value", sa.Text, nullable=True),
            sa.Column("new_value", sa.Text, nullable=True),
            sa.Column("reason", sa.Text, nullable=True),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
        )

    if not _has_index("personal_fact_revisions", "ix_fact_revisions_fact_id"):
        op.create_index(
            "ix_fact_revisions_fact_id",
            "personal_fact_revisions",
            ["fact_id", "created_at"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop revision tables
    if _has_index("personal_fact_revisions", "ix_fact_revisions_fact_id"):
        op.drop_index(
            "ix_fact_revisions_fact_id",
            table_name="personal_fact_revisions",
        )
    if _has_table("personal_fact_revisions"):
        op.drop_table("personal_fact_revisions")

    # Drop evidence tables
    if _has_index("personal_fact_evidence", "ix_fact_evidence_source_message"):
        op.drop_index(
            "ix_fact_evidence_source_message",
            table_name="personal_fact_evidence",
        )
    if _has_index("personal_fact_evidence", "ix_fact_evidence_fact_id"):
        op.drop_index(
            "ix_fact_evidence_fact_id",
            table_name="personal_fact_evidence",
        )
    if _has_table("personal_fact_evidence"):
        op.drop_table("personal_fact_evidence")

    # Drop facts tables
    if _has_index("personal_facts", "ix_personal_facts_user_status"):
        op.drop_index(
            "ix_personal_facts_user_status", table_name="personal_facts"
        )
    op.execute("DROP INDEX IF EXISTS ix_personal_facts_active_key")
    if _has_table("personal_facts"):
        op.drop_table("personal_facts")

    # Remove chat_messages columns
    if _has_index("chat_messages", "ix_chat_messages_kind"):
        op.drop_index("ix_chat_messages_kind", table_name="chat_messages")
    if _has_index("chat_messages", "ix_chat_messages_thread_event"):
        op.drop_index(
            "ix_chat_messages_thread_event", table_name="chat_messages"
        )
    if _has_column("chat_messages", "extra_meta"):
        op.drop_column("chat_messages", "extra_meta")
    if _has_column("chat_messages", "kind"):
        op.drop_column("chat_messages", "kind")
    if _has_column("chat_messages", "event_at"):
        op.drop_column("chat_messages", "event_at")
