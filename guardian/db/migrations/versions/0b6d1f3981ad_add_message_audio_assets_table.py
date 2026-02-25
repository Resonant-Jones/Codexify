"""add message_audio_assets table for voice playback cache

Revision ID: 0b6d1f3981ad
Revises: 9b3d2d08f7c1
Create Date: 2026-02-25 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0b6d1f3981ad"
down_revision: Union[str, Sequence[str], None] = "9b3d2d08f7c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "message_audio_assets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("voice", sa.String(length=128), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("src_url", sa.Text(), nullable=False),
        sa.Column(
            "internal_format",
            sa.String(length=16),
            server_default=sa.text("'wav'"),
            nullable=False,
        ),
        sa.Column(
            "delivery_variants_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("filesize_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["message_id"], ["chat_messages.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Handle historical branch variant if a 3-column unique exists.
    op.execute(
        "ALTER TABLE message_audio_assets DROP CONSTRAINT IF EXISTS uq_message_audio_assets_message_provider_voice"
    )
    op.execute(
        "ALTER TABLE message_audio_assets DROP CONSTRAINT IF EXISTS message_audio_assets_message_id_provider_voice_key"
    )

    op.create_unique_constraint(
        "uq_message_audio_assets_message_provider_voice_texthash",
        "message_audio_assets",
        ["message_id", "provider", "voice", "text_hash"],
    )

    op.create_index(
        "ix_message_audio_assets_message",
        "message_audio_assets",
        ["message_id"],
        unique=False,
    )
    op.create_index(
        "ix_message_audio_assets_provider_voice_created",
        "message_audio_assets",
        ["provider", "voice", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_message_audio_assets_provider_voice_created",
        table_name="message_audio_assets",
    )
    op.drop_index(
        "ix_message_audio_assets_message", table_name="message_audio_assets"
    )
    op.drop_constraint(
        "uq_message_audio_assets_message_provider_voice_texthash",
        "message_audio_assets",
        type_="unique",
    )
    op.drop_table("message_audio_assets")
