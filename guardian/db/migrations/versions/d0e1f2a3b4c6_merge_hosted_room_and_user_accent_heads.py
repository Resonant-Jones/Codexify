"""merge Hosted Room and user accent heads

Revision ID: d0e1f2a3b4c6
Revises: 8c4d2e7f1a9b, c8d9e0f1a2b3
Create Date: 2026-07-29 15:10:00.000000
"""

from typing import Sequence, Union

revision: str = "d0e1f2a3b4c6"
down_revision: Union[str, Sequence[str], None] = (
    "8c4d2e7f1a9b",
    "c8d9e0f1a2b3",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
