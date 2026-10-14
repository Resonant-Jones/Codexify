"""Merge agent run provenance and message request heads

Revision ID: 1760875e3c3b
Revises: 7fcd8ca51401, 9e52b1d3c8fa
Create Date: 2026-10-03 20:43:14.724125

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '1760875e3c3b'
down_revision: Union[str, Sequence[str], None] = ('7fcd8ca51401', '9e52b1d3c8fa')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
