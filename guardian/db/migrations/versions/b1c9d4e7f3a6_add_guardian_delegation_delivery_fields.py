"""add guardian delegation delivery fields

Revision ID: b1c9d4e7f3a6
Revises: 7c21f0a4b8de
Create Date: 2026-05-26 22:15:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c9d4e7f3a6"
down_revision: str | Sequence[str] | None = "7c21f0a4b8de"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "guardian_delegation_intents",
        sa.Column(
            "visibility_status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'not_posted'"),
        ),
    )
    op.add_column(
        "guardian_delegation_intents",
        sa.Column("result_message_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "guardian_delegation_intents",
        sa.Column("result_delivered_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "guardian_delegation_intents",
        sa.Column("result_delivery_key", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "guardian_delegation_intents",
        sa.Column("delivery_error", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "guardian_delegation_intents_visibility_status_check",
        "guardian_delegation_intents",
        "visibility_status IN ('delivery_degraded','interrupt_posted','not_posted','result_posted','stale_suppressed')",
    )
    op.create_index(
        "ix_guardian_delegation_intents_result_message_id",
        "guardian_delegation_intents",
        ["result_message_id"],
    )
    op.create_index(
        "ix_guardian_delegation_intents_result_delivery_key",
        "guardian_delegation_intents",
        ["result_delivery_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_guardian_delegation_intents_result_delivery_key",
        table_name="guardian_delegation_intents",
    )
    op.drop_index(
        "ix_guardian_delegation_intents_result_message_id",
        table_name="guardian_delegation_intents",
    )
    op.drop_constraint(
        "guardian_delegation_intents_visibility_status_check",
        "guardian_delegation_intents",
        type_="check",
    )
    op.drop_column("guardian_delegation_intents", "delivery_error")
    op.drop_column("guardian_delegation_intents", "result_delivery_key")
    op.drop_column("guardian_delegation_intents", "result_delivered_at")
    op.drop_column("guardian_delegation_intents", "result_message_id")
    op.drop_column("guardian_delegation_intents", "visibility_status")
