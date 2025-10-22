"""baseline schema

Revision ID: 1eb6836bb10e
Revises: 984a47e3bc2c
Create Date: 2025-09-26 15:52:43.228072

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1eb6836bb10e'
down_revision: Union[str, Sequence[str], None] = '984a47e3bc2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
