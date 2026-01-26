"""merge heads

Revision ID: 83c2f0bb0dfa
Revises: 7c2a8e6d1f4b, c7a253a50757
Create Date: 2026-01-26 15:19:32.980809

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "83c2f0bb0dfa"
down_revision: Union[str, Sequence[str], None] = (
    "7c2a8e6d1f4b",
    "c7a253a50757",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
