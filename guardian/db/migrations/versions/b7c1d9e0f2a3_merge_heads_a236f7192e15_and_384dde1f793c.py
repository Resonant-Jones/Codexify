"""merge heads a236f7192e15 and 384dde1f793c

Revision ID: b7c1d9e0f2a3
Revises: a236f7192e15, 384dde1f793c
Create Date: 2026-02-20

"""
from typing import Sequence, Union

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "b7c1d9e0f2a3"
down_revision: Union[str, Sequence[str], None] = (
    "a236f7192e15",
    "384dde1f793c",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
