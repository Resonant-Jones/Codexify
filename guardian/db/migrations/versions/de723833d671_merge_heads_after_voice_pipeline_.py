"""merge heads after voice pipeline integration

Revision ID: de723833d671
Revises: 0b6d1f3981ad, c2f4a8e1b9d0
Create Date: 2026-02-25 20:47:21.881465

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "de723833d671"
down_revision: Union[str, Sequence[str], None] = (
    "0b6d1f3981ad",
    "c2f4a8e1b9d0",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
