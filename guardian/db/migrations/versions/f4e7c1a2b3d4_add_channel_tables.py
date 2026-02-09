"""add channel config/pairing/allowlist/message tables

Revision ID: f4e7c1a2b3d4
Revises: c3d4e5f6a7b8
Create Date: 2026-02-07 02:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4e7c1a2b3d4"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "channel_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column(
            "config_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
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
            "user_id",
            "channel",
            name="uq_channel_configs_user_channel",
        ),
    )
    op.create_index(
        "ix_channel_configs_user_id",
        "channel_configs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_channel_configs_channel",
        "channel_configs",
        ["channel"],
        unique=False,
    )

    op.create_table(
        "channel_allowlists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "channel",
            "external_id",
            name="uq_channel_allowlists_user_channel_external",
        ),
    )
    op.create_index(
        "ix_channel_allowlists_user_channel",
        "channel_allowlists",
        ["user_id", "channel"],
        unique=False,
    )

    op.create_table(
        "channel_pairings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
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
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'revoked')",
            name="channel_pairings_status_check",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "channel",
            "external_id",
            name="uq_channel_pairings_user_channel_external",
        ),
    )
    op.create_index(
        "ix_channel_pairings_user_channel",
        "channel_pairings",
        ["user_id", "channel"],
        unique=False,
    )
    op.create_index(
        "ix_channel_pairings_status",
        "channel_pairings",
        ["status"],
        unique=False,
    )

    op.create_table(
        "channel_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("thread_id", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="channel_messages_direction_check",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_channel_messages_user_channel",
        "channel_messages",
        ["user_id", "channel"],
        unique=False,
    )
    op.create_index(
        "ix_channel_messages_created_at",
        "channel_messages",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_channel_messages_created_at", table_name="channel_messages"
    )
    op.drop_index(
        "ix_channel_messages_user_channel", table_name="channel_messages"
    )
    op.drop_table("channel_messages")

    op.drop_index("ix_channel_pairings_status", table_name="channel_pairings")
    op.drop_index(
        "ix_channel_pairings_user_channel", table_name="channel_pairings"
    )
    op.drop_table("channel_pairings")

    op.drop_index(
        "ix_channel_allowlists_user_channel", table_name="channel_allowlists"
    )
    op.drop_table("channel_allowlists")

    op.drop_index("ix_channel_configs_channel", table_name="channel_configs")
    op.drop_index("ix_channel_configs_user_id", table_name="channel_configs")
    op.drop_table("channel_configs")
