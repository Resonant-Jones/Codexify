"""add embedding status fields to uploaded_documents

Revision ID: 7c2a8e6d1f4b
Revises: c6b2fdd401a9
Create Date: 2026-01-23 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c2a8e6d1f4b"
down_revision: Union[str, Sequence[str], None] = "c6b2fdd401a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column_name in {
        col["name"] for col in inspector.get_columns(table_name)
    }


def _has_check_constraint(table_name: str, constraint_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return constraint_name in {
        c["name"] for c in inspector.get_check_constraints(table_name)
    }


def upgrade() -> None:
    """Upgrade schema."""
    if not _has_column("uploaded_documents", "embedding_status"):
        op.add_column(
            "uploaded_documents",
            sa.Column(
                "embedding_status",
                sa.String(length=32),
                nullable=False,
                server_default="pending",
            ),
        )
    if not _has_column("uploaded_documents", "embedding_error"):
        op.add_column(
            "uploaded_documents",
            sa.Column("embedding_error", sa.Text(), nullable=True),
        )
    if not _has_column("uploaded_documents", "embedding_started_at"):
        op.add_column(
            "uploaded_documents",
            sa.Column(
                "embedding_started_at",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
            ),
        )
    if not _has_column("uploaded_documents", "embedding_completed_at"):
        op.add_column(
            "uploaded_documents",
            sa.Column(
                "embedding_completed_at",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
            ),
        )
    if not _has_check_constraint(
        "uploaded_documents", "uploaded_documents_embedding_status_check"
    ):
        op.create_check_constraint(
            "uploaded_documents_embedding_status_check",
            "uploaded_documents",
            "embedding_status IN ('pending','processing','ready','failed')",
        )


def downgrade() -> None:
    """Downgrade schema."""
    if _has_check_constraint(
        "uploaded_documents", "uploaded_documents_embedding_status_check"
    ):
        op.drop_constraint(
            "uploaded_documents_embedding_status_check",
            "uploaded_documents",
            type_="check",
        )
    if _has_column("uploaded_documents", "embedding_completed_at"):
        op.drop_column("uploaded_documents", "embedding_completed_at")
    if _has_column("uploaded_documents", "embedding_started_at"):
        op.drop_column("uploaded_documents", "embedding_started_at")
    if _has_column("uploaded_documents", "embedding_error"):
        op.drop_column("uploaded_documents", "embedding_error")
    if _has_column("uploaded_documents", "embedding_status"):
        op.drop_column("uploaded_documents", "embedding_status")
