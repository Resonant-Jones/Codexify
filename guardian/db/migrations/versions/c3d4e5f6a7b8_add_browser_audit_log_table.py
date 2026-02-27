"""add browser_audit_log table

Revision ID: c3d4e5f6a7b8
Revises: b1a2c3d4e5f7
Create Date: 2026-02-07 02:06:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b1a2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return index_name in {
        idx["name"] for idx in inspector.get_indexes(table_name)
    }


def upgrade() -> None:
    if not _has_table("browser_audit_log"):
        op.create_table(
            "browser_audit_log",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("approval_id", sa.Integer(), nullable=True),
            sa.Column("operation", sa.String(length=64), nullable=False),
            sa.Column("target", sa.String(length=512), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("actor", sa.String(length=255), nullable=True),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["approval_id"],
                ["browser_approvals.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("browser_audit_log", "ix_browser_audit_log_created_at"):
        op.create_index(
            "ix_browser_audit_log_created_at",
            "browser_audit_log",
            ["created_at"],
            unique=False,
        )
    if not _has_index("browser_audit_log", "ix_browser_audit_log_status"):
        op.create_index(
            "ix_browser_audit_log_status",
            "browser_audit_log",
            ["status"],
            unique=False,
        )


def downgrade() -> None:
    if _has_index("browser_audit_log", "ix_browser_audit_log_status"):
        op.drop_index(
            "ix_browser_audit_log_status", table_name="browser_audit_log"
        )
    if _has_index("browser_audit_log", "ix_browser_audit_log_created_at"):
        op.drop_index(
            "ix_browser_audit_log_created_at",
            table_name="browser_audit_log",
        )
    if _has_table("browser_audit_log"):
        op.drop_table("browser_audit_log")
