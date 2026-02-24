"""add idempotency key unique constraint for command runs

Revision ID: c2f4a8e1b9d0
Revises: f1a2b3c4d5e6
Create Date: 2026-02-24

"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2f4a8e1b9d0"
down_revision: str | Sequence[str] | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "command_runs",
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
    )
    op.create_unique_constraint(
        "uq_command_idempotency_key",
        "command_runs",
        ["command_id", "idempotency_key"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_command_idempotency_key",
        "command_runs",
        type_="unique",
    )
    op.drop_column("command_runs", "idempotency_key")
