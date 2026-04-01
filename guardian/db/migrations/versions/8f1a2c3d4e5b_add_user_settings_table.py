"""add durable user_settings table

Revision ID: 8f1a2c3d4e5b
Revises: e9a4c1b8d2f7
Create Date: 2026-04-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f1a2c3d4e5b"
down_revision: Union[str, Sequence[str], None] = "e9a4c1b8d2f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.String(length=255), primary_key=True),
        sa.Column(
            "memory_mode",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'deep'"),
        ),
        sa.Column(
            "diary_requires_unlock",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "allow_sensitive_modeling",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
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
            "memory_mode IN ('none','light','deep')",
            name="user_settings_memory_mode_check",
        ),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
