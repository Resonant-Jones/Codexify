"""merge d6f7a8b9c0d1 compatibility

Revision ID: 8f3c1a7d2e6b
Revises: d6f7a8b9c0d1, 6e2b9c4a7d1f
Create Date: 2026-08-13 00:00:00.000000
"""

from typing import Sequence, Union

revision: str = "8f3c1a7d2e6b"
down_revision: Union[str, Sequence[str], None] = (
    "d6f7a8b9c0d1",
    "6e2b9c4a7d1f",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
