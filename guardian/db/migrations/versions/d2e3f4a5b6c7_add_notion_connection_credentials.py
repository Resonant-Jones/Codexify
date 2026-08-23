"""add user-scoped Notion connection credentials

Revision ID: d2e3f4a5b6c7
Revises: 1c0a2b3c4d5e
Create Date: 2026-08-23
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d2e3f4a5b6c7"
down_revision: str | Sequence[str] | None = "1c0a2b3c4d5e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the narrow non-OAuth token record for the Notion connection."""
    op.create_table(
        "notion_connection_credentials",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("encrypted_integration_token", sa.Text(), nullable=False),
        sa.Column(
            "validation_status",
            sa.String(length=32),
            nullable=False,
            server_default="unvalidated",
        ),
        sa.Column("last_validated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "validation_status IN "
            "('unvalidated', 'valid', 'authorization_error', "
            "'transport_error', 'provider_error')",
            name="ck_notion_connection_credentials_validation_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_notion_connection_credentials_user"),
    )


def downgrade() -> None:
    op.drop_table("notion_connection_credentials")
