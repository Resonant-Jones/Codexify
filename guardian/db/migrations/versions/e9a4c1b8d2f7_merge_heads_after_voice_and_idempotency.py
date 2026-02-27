"""merge heads after voice pipeline and command idempotency

Revision ID: e9a4c1b8d2f7
Revises: de723833d671, c2f4a8e1b9d0
Create Date: 2026-02-26 00:00:01.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa  # noqa: F401
from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "e9a4c1b8d2f7"
down_revision: Union[str, Sequence[str], None] = (
    "de723833d671",
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
