"""Add Guardian-owned one-time account activation capabilities.

Revision ID: a8d4c2f6b1e9
Revises: 7e5a5fccf253
Create Date: 2026-09-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a8d4c2f6b1e9"
down_revision: str | Sequence[str] | None = "7e5a5fccf253"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "account_activation_capabilities",
        sa.Column("activation_id", sa.String(length=36), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("intended_role", sa.String(length=16), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False
        ),
        sa.Column(
            "expires_at", sa.TIMESTAMP(timezone=True), nullable=False
        ),
        sa.Column(
            "consumed_at", sa.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("resulting_user_id", sa.String(length=255), nullable=True),
        sa.CheckConstraint(
            "intended_role IN ('admin', 'guest')",
            name="account_activation_capabilities_role_check",
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="account_activation_capabilities_expiry_check",
        ),
        sa.CheckConstraint(
            "((consumed_at IS NULL AND resulting_user_id IS NULL) OR "
            "(consumed_at IS NOT NULL AND resulting_user_id IS NOT NULL))",
            name="account_activation_capabilities_consumption_check",
        ),
        sa.CheckConstraint(
            "NOT (consumed_at IS NOT NULL AND revoked_at IS NOT NULL)",
            name="account_activation_capabilities_terminal_state_check",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_account_activation_capabilities_creator",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_user_id"],
            ["users.id"],
            name="fk_account_activation_capabilities_resulting_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "activation_id",
            name="pk_account_activation_capabilities",
        ),
        sa.UniqueConstraint(
            "token_digest",
            name="uq_account_activation_capabilities_token_digest",
        ),
    )
    op.create_index(
        "ix_account_activation_capabilities_recipient_lifecycle",
        "account_activation_capabilities",
        ["recipient_email", "consumed_at", "revoked_at", "expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_account_activation_capabilities_recipient_lifecycle",
        table_name="account_activation_capabilities",
    )
    op.drop_table("account_activation_capabilities")
