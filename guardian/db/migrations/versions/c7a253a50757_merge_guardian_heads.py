"""merge guardian heads

Revision ID: c7a253a50757
Revises: 6d8d2f5c1a9b, a1b2c3d4e5f6
Create Date: 2026-01-12 20:26:26.159951

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7a253a50757"
down_revision: Union[str, Sequence[str], None] = (
    "6d8d2f5c1a9b",
    "a1b2c3d4e5f6",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
