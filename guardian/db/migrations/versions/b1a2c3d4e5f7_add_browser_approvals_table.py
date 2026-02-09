"""add browser_approvals table

Revision ID: b1a2c3d4e5f7
Revises: e5d6f4a2190c
Create Date: 2026-02-07 02:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1a2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "e5d6f4a2190c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "browser_approvals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("target", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("requested_by", sa.String(length=255), nullable=True),
        sa.Column("request_reason", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.String(length=255), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'DENIED')",
            name="browser_approvals_status_check",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_browser_approvals_status",
        "browser_approvals",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_browser_approvals_created_at",
        "browser_approvals",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_browser_approvals_created_at", table_name="browser_approvals"
    )
    op.drop_index("ix_browser_approvals_status", table_name="browser_approvals")
    op.drop_table("browser_approvals")
