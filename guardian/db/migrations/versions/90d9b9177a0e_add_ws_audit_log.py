"""add ws_audit_log table

Revision ID: 90d9b9177a0e
Revises: b9f2c7a1d8e3
Create Date: 2026-02-07 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "90d9b9177a0e"
down_revision: Union[str, Sequence[str], None] = "b9f2c7a1d8e3"
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
    """Upgrade schema."""
    if not _has_table("ws_audit_log"):
        op.create_table(
            "ws_audit_log",
            sa.Column(
                "id", sa.BigInteger(), autoincrement=True, nullable=False
            ),
            sa.Column("connection_id", sa.String(length=128), nullable=False),
            sa.Column("identity", sa.String(length=255), nullable=True),
            sa.Column("method", sa.String(length=128), nullable=False),
            sa.Column("params_hash", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("duration_ms", sa.Integer(), nullable=False),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("ws_audit_log", "ix_ws_audit_connection_id"):
        op.create_index(
            "ix_ws_audit_connection_id",
            "ws_audit_log",
            ["connection_id"],
            unique=False,
        )
    if not _has_index("ws_audit_log", "ix_ws_audit_identity"):
        op.create_index(
            "ix_ws_audit_identity",
            "ws_audit_log",
            ["identity"],
            unique=False,
        )
    if not _has_index("ws_audit_log", "ix_ws_audit_created_at"):
        op.create_index(
            "ix_ws_audit_created_at",
            "ws_audit_log",
            ["created_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    if _has_index("ws_audit_log", "ix_ws_audit_created_at"):
        op.drop_index("ix_ws_audit_created_at", table_name="ws_audit_log")
    if _has_index("ws_audit_log", "ix_ws_audit_identity"):
        op.drop_index("ix_ws_audit_identity", table_name="ws_audit_log")
    if _has_index("ws_audit_log", "ix_ws_audit_connection_id"):
        op.drop_index("ix_ws_audit_connection_id", table_name="ws_audit_log")
    if _has_table("ws_audit_log"):
        op.drop_table("ws_audit_log")
