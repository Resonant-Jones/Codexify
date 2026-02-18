"""add project_document_links

Revision ID: 384dde1f793c
Revises: 62127ee9a537
Create Date: 2026-02-17 19:29:38.016277

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "384dde1f793c"
down_revision = "62127ee9a537"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "project_document_links",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "attached_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("attached_by", sa.String(length=255), nullable=True),
        sa.CheckConstraint(
            "document_type IN ('generated', 'uploaded')",
            name="project_document_links_type_check",
        ),
        sa.UniqueConstraint(
            "project_id",
            "document_id",
            "document_type",
            name="uq_project_document_links_scope",
        ),
    )

    op.create_index(
        "ix_project_document_links_project_enabled",
        "project_document_links",
        ["project_id", "is_enabled"],
    )
    op.create_index(
        "ix_project_document_links_document",
        "project_document_links",
        ["document_type", "document_id"],
    )
    # DESC index on attached_at (matches models.py)
    op.create_index(
        "ix_project_document_links_attached",
        "project_document_links",
        [sa.text("attached_at DESC")],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Be defensive: earlier attempts may have stamped the revision without creating the table.
    # Using IF EXISTS avoids failing the downgrade in that scenario.
    op.execute("DROP INDEX IF EXISTS ix_project_document_links_attached")
    op.execute("DROP INDEX IF EXISTS ix_project_document_links_document")
    op.execute("DROP INDEX IF EXISTS ix_project_document_links_project_enabled")
    op.execute("DROP TABLE IF EXISTS project_document_links CASCADE")
