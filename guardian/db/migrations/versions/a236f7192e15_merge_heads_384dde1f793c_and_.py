"""merge heads 384dde1f793c and 62127ee9a537

Revision ID: a236f7192e15
Revises: 384dde1f793c, 62127ee9a537
Create Date: 2026-02-19 18:40:34.485508

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a236f7192e15"
down_revision: Union[str, Sequence[str], None] = (
    "384dde1f793c",
    "62127ee9a537",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
