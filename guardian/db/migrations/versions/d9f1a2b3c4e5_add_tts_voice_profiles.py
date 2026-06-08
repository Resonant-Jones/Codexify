"""add tts voice profiles

Revision ID: d9f1a2b3c4e5
Revises: aa4c2e7f91b3, c6d7e8f9a0b1
Create Date: 2026-06-08 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d9f1a2b3c4e5"
down_revision: str | Sequence[str] | None = (
    "aa4c2e7f91b3",
    "c6d7e8f9a0b1",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tts_voice_profiles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("backend_id", sa.String(length=64), nullable=False),
        sa.Column(
            "is_default",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "voice_mode",
            sa.String(length=32),
            server_default=sa.text("'preset'"),
            nullable=False,
        ),
        sa.Column("speaker", sa.String(length=128), nullable=True),
        sa.Column("voice_prompt", sa.Text(), nullable=True),
        sa.Column("style_instructions", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=64), nullable=True),
        sa.Column("speed", sa.Float(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("top_k", sa.Integer(), nullable=True),
        sa.Column("top_p", sa.Float(), nullable=True),
        sa.Column("repetition_penalty", sa.Float(), nullable=True),
        sa.Column("max_new_tokens", sa.Integer(), nullable=True),
        sa.Column("do_sample", sa.Boolean(), nullable=True),
        sa.Column(
            "backend_params",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("reference_audio_asset_id", sa.String(length=128), nullable=True),
        sa.Column("reference_text", sa.Text(), nullable=True),
        sa.Column("x_vector_only_mode", sa.Boolean(), nullable=True),
        sa.Column("sample_rate", sa.Integer(), nullable=True),
        sa.Column(
            "output_format",
            sa.String(length=16),
            server_default=sa.text("'wav'"),
            nullable=True,
        ),
        sa.Column("loudness_normalization", sa.Boolean(), nullable=True),
        sa.Column(
            "pause_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "backend_id IN ('qwen3_tts','local_openai_compatible','local')",
            name="tts_voice_profiles_backend_id_check",
        ),
        sa.CheckConstraint(
            "voice_mode IN ('preset','prompt','reference_audio','custom')",
            name="tts_voice_profiles_voice_mode_check",
        ),
        sa.CheckConstraint(
            "output_format IN ('wav','mp3')",
            name="tts_voice_profiles_output_format_check",
        ),
        sa.CheckConstraint(
            "speed IS NULL OR (speed > 0.0 AND speed <= 4.0)",
            name="tts_voice_profiles_speed_check",
        ),
        sa.CheckConstraint(
            "temperature IS NULL OR (temperature >= 0.0 AND temperature <= 2.0)",
            name="tts_voice_profiles_temperature_check",
        ),
        sa.CheckConstraint(
            "top_k IS NULL OR top_k >= 0",
            name="tts_voice_profiles_top_k_check",
        ),
        sa.CheckConstraint(
            "top_p IS NULL OR (top_p >= 0.0 AND top_p <= 1.0)",
            name="tts_voice_profiles_top_p_check",
        ),
        sa.CheckConstraint(
            "repetition_penalty IS NULL OR repetition_penalty > 0.0",
            name="tts_voice_profiles_repetition_penalty_check",
        ),
        sa.CheckConstraint(
            "max_new_tokens IS NULL OR max_new_tokens > 0",
            name="tts_voice_profiles_max_new_tokens_check",
        ),
        sa.CheckConstraint(
            "sample_rate IS NULL OR sample_rate > 0",
            name="tts_voice_profiles_sample_rate_check",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tts_voice_profiles_backend",
        "tts_voice_profiles",
        ["backend_id"],
        unique=False,
    )
    op.create_index(
        "ix_tts_voice_profiles_default",
        "tts_voice_profiles",
        ["is_default"],
        unique=False,
    )
    op.create_index(
        "ix_tts_voice_profiles_updated",
        "tts_voice_profiles",
        [sa.literal_column("updated_at DESC")],
        unique=False,
    )
    op.create_index(
        "uq_tts_voice_profiles_single_default",
        "tts_voice_profiles",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default IS TRUE"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_tts_voice_profiles_single_default",
        table_name="tts_voice_profiles",
        postgresql_where=sa.text("is_default IS TRUE"),
    )
    op.drop_index("ix_tts_voice_profiles_updated", table_name="tts_voice_profiles")
    op.drop_index("ix_tts_voice_profiles_default", table_name="tts_voice_profiles")
    op.drop_index("ix_tts_voice_profiles_backend", table_name="tts_voice_profiles")
    op.drop_table("tts_voice_profiles")
