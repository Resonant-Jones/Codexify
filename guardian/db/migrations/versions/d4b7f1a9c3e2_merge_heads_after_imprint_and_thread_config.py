"""merge heads after imprint observations and thread_config

Revision ID: d4b7f1a9c3e2
Revises: 4f6c8d1a2b3c, b0c1d2e3f4a5
Create Date: 2026-04-02 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa  # noqa: F401
from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "d4b7f1a9c3e2"
down_revision: Union[str, Sequence[str], None] = (
    "4f6c8d1a2b3c",
    "b0c1d2e3f4a5",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
