"""merge the guardian coding claim and campaign continuation heads

Revision ID: a3115f64dda8
Revises: b7e2c4a1d903, c8e42a91d307
Create Date: 2026-10-30 17:10:13.876922

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3115f64dda8'
down_revision: Union[str, Sequence[str], None] = ('b7e2c4a1d903', 'c8e42a91d307')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
