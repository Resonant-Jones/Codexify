"""add guardian delegation manual approval mode

Revision ID: c6d7e8f9a0b1
Revises: b1c9d4e7f3a6
Create Date: 2026-05-27 11:15:00.000000
"""

from __future__ import annotations

from typing import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c6d7e8f9a0b1"
down_revision: str | Sequence[str] | None = "b1c9d4e7f3a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "guardian_delegation_intents_approval_mode_check",
        "guardian_delegation_intents",
        type_="check",
    )
    op.create_check_constraint(
        "guardian_delegation_intents_approval_mode_check",
        "guardian_delegation_intents",
        "approval_mode IN ('human_required','scoped_auto')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "guardian_delegation_intents_approval_mode_check",
        "guardian_delegation_intents",
        type_="check",
    )
    op.create_check_constraint(
        "guardian_delegation_intents_approval_mode_check",
        "guardian_delegation_intents",
        "approval_mode IN ('scoped_auto')",
    )
