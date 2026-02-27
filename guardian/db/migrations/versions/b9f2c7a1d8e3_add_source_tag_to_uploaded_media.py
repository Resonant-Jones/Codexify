"""Add source_tag to uploaded media tables.

Revision ID: b9f2c7a1d8e3
Revises: 3a85478c70e4
Create Date: 2026-02-02 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9f2c7a1d8e3"
down_revision: Union[str, Sequence[str], None] = "3a85478c70e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column_name in {
        col["name"] for col in inspector.get_columns(table_name)
    }


def _has_index(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return index_name in {
        idx["name"] for idx in inspector.get_indexes(table_name)
    }


def upgrade() -> None:
    """Upgrade schema."""
    if not _has_column("uploaded_images", "source_tag"):
        op.add_column(
            "uploaded_images",
            sa.Column("source_tag", sa.String(length=64), nullable=True),
        )
    if not _has_column("uploaded_documents", "source_tag"):
        op.add_column(
            "uploaded_documents",
            sa.Column("source_tag", sa.String(length=64), nullable=True),
        )
    if not _has_index("uploaded_images", "ix_uploaded_images_source_tag"):
        op.create_index(
            "ix_uploaded_images_source_tag",
            "uploaded_images",
            ["source_tag"],
            unique=False,
        )
    if not _has_index("uploaded_documents", "ix_uploaded_documents_source_tag"):
        op.create_index(
            "ix_uploaded_documents_source_tag",
            "uploaded_documents",
            ["source_tag"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    if _has_index("uploaded_documents", "ix_uploaded_documents_source_tag"):
        op.drop_index(
            "ix_uploaded_documents_source_tag",
            table_name="uploaded_documents",
        )
    if _has_index("uploaded_images", "ix_uploaded_images_source_tag"):
        op.drop_index(
            "ix_uploaded_images_source_tag", table_name="uploaded_images"
        )
    if _has_column("uploaded_documents", "source_tag"):
        op.drop_column("uploaded_documents", "source_tag")
    if _has_column("uploaded_images", "source_tag"):
        op.drop_column("uploaded_images", "source_tag")
