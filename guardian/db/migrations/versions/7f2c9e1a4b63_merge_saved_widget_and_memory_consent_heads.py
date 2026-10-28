"""merge saved widget and memory consent heads

Revision ID: 7f2c9e1a4b63
Revises: a6b9d2e4f701, c59e4d1a28f0
Create Date: 2026-10-27 20:16:57.476470

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f2c9e1a4b63'
down_revision: Union[str, Sequence[str], None] = ('a6b9d2e4f701', 'c59e4d1a28f0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
