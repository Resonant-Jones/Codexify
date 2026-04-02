"""add persona profiles table for Persona Studio first-wave runtime fields

Revision ID: b7c8d9e0f1a2
Revises: e9a4c1b8d2f7
Create Date: 2026-04-02 00:00:00.000000
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: str | Sequence[str] | None = "e9a4c1b8d2f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_PERSONA_PROFILE_TABLE = sa.table(
    "persona_profiles",
    sa.column("id", sa.String(length=128)),
    sa.column("name", sa.String(length=255)),
    sa.column("system_prompt", sa.Text()),
    sa.column("model_provider", sa.String(length=64)),
    sa.column("model_id", sa.String(length=255)),
    sa.column("temperature", sa.Float()),
    sa.column("created_at", sa.TIMESTAMP(timezone=True)),
    sa.column("updated_at", sa.TIMESTAMP(timezone=True)),
)


def upgrade() -> None:
    op.create_table(
        "persona_profiles",
        sa.Column(
            "id", sa.String(length=128), primary_key=True, nullable=False
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("model_provider", sa.String(length=64), nullable=False),
        sa.Column("model_id", sa.String(length=255), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
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
            "temperature >= 0.0 AND temperature <= 2.0",
            name="persona_profiles_temperature_check",
        ),
    )

    seeded_at = datetime.now(timezone.utc)
    op.bulk_insert(
        _PERSONA_PROFILE_TABLE,
        [
            {
                "id": "profile-1",
                "name": "Guardian Default",
                "system_prompt": (
                    "You are a Guardian, a partner in thought. Your primary goal is to foster the user's autonomy and creativity."
                ),
                "model_provider": "openai",
                "model_id": "gpt-4o",
                "temperature": 0.7,
                "created_at": seeded_at,
                "updated_at": seeded_at,
            },
            {
                "id": "profile-2",
                "name": "Code Assistant",
                "system_prompt": (
                    "You are an expert code assistant. Provide clear, concise, and accurate code solutions with explanation."
                ),
                "model_provider": "anthropic",
                "model_id": "claude-sonnet-4-20250514",
                "temperature": 0.3,
                "created_at": seeded_at,
                "updated_at": seeded_at,
            },
            {
                "id": "profile-3",
                "name": "Research Partner",
                "system_prompt": (
                    "You are a research partner specializing in information synthesis and critical analysis."
                ),
                "model_provider": "openai",
                "model_id": "gpt-4-turbo",
                "temperature": 0.5,
                "created_at": seeded_at,
                "updated_at": seeded_at,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("persona_profiles")
