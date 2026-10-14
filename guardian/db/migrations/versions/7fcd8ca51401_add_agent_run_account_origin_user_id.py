"""Persist account coding-intake provenance on agent runs.

Revision ID: 7fcd8ca51401
Revises: 8d41a0c2b7ef
Create Date: 2026-10-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7fcd8ca51401"
down_revision: Union[str, Sequence[str], None] = "8d41a0c2b7ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_runs",
        sa.Column("account_origin_user_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_runs", "account_origin_user_id")
