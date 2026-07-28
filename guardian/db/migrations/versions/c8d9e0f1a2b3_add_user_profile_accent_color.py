"""add accent_color to user_profiles for account-owned presentation preference

Revision ID: c8d9e0f1a2b3
Revises: e5f6a7b8c9d0
Create Date: 2026-07-22 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

from guardian.user_profile_tokens import (
    DEFAULT_USER_ACCENT_COLOR,
    USER_ACCENT_COLORS,
)

# revision identifiers, used by Alembic.
revision: str = "c8d9e0f1a2b3"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACCENT_COLOR_VALUES_SQL = "','".join(sorted(USER_ACCENT_COLORS))


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column(
            "accent_color",
            sa.String(length=16),
            nullable=True,
        ),
    )

    # Backfill existing rows to the canonical default.
    op.execute(
        f"UPDATE user_profiles SET accent_color = '{DEFAULT_USER_ACCENT_COLOR}'"
        " WHERE accent_color IS NULL"
    )

    # Make the column non-null after backfill.
    op.alter_column("user_profiles", "accent_color", nullable=False)

    # Add the named check constraint limiting values to the canonical set.
    op.create_check_constraint(
        "ck_user_profiles_accent_color",
        "user_profiles",
        f"accent_color IN ('{_ACCENT_COLOR_VALUES_SQL}')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_user_profiles_accent_color",
        "user_profiles",
        type_="check",
    )
    op.drop_column("user_profiles", "accent_color")
