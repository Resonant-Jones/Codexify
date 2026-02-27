"""compatibility head after voice pipeline integration

Revision ID: de723833d671
Revises: 0b6d1f3981ad
Create Date: 2026-02-26 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa  # noqa: F401
from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "de723833d671"
down_revision: Union[str, Sequence[str], None] = "0b6d1f3981ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
