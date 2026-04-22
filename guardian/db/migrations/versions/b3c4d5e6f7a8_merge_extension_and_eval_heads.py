"""merge extension and eval heads

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7, e4f5a6b7c8d9
Create Date: 2026-04-22 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa  # noqa: F401
from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: str | Sequence[str] | None = (
    "a2b3c4d5e6f7",
    "e4f5a6b7c8d9",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge the extension and eval branches without changing schema."""
    pass


def downgrade() -> None:
    """Downgrade the merge point without altering branch contents."""
    pass
