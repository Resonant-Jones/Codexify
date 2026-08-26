"""merge Watchdog and Connections migration heads

Revision ID: 9c66e490a42b
Revises: 6e9f0a1b2c3, d2e3f4a5b6c7
Create Date: 2026-08-24 22:00:22.570673

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '9c66e490a42b'
down_revision: Union[str, Sequence[str], None] = ('6e9f0a1b2c3', 'd2e3f4a5b6c7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
