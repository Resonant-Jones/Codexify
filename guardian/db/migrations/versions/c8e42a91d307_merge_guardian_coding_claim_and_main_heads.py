"""merge guardian coding claim and main heads

Revision ID: c8e42a91d307
Revises: 3a91d7c4e8b2, d86f2a4b1c90
Create Date: 2026-10-28 14:31:57.190357

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8e42a91d307'
down_revision: Union[str, Sequence[str], None] = ('3a91d7c4e8b2', 'd86f2a4b1c90')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
