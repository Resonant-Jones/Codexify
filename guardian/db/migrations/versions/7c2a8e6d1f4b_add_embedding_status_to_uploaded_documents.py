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


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "uploaded_documents",
        sa.Column(
            "embedding_status",
            sa.String(length=32),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "uploaded_documents",
        sa.Column("embedding_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "uploaded_documents",
        sa.Column(
            "embedding_started_at", sa.TIMESTAMP(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "uploaded_documents",
        sa.Column(
            "embedding_completed_at", sa.TIMESTAMP(timezone=True), nullable=True
        ),
    )
    op.create_check_constraint(
        "uploaded_documents_embedding_status_check",
        "uploaded_documents",
        "embedding_status IN ('pending','processing','ready','failed')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uploaded_documents_embedding_status_check",
        "uploaded_documents",
        type_="check",
    )
    op.drop_column("uploaded_documents", "embedding_completed_at")
    op.drop_column("uploaded_documents", "embedding_started_at")
    op.drop_column("uploaded_documents", "embedding_error")
    op.drop_column("uploaded_documents", "embedding_status")
