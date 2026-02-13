"""add media assets and aliases identity layer

Revision ID: c9e1f7a6b3d2
Revises: b8f7c2d1e4a9
Create Date: 2026-02-12 18:55:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9e1f7a6b3d2"
down_revision: Union[str, Sequence[str], None] = "b8f7c2d1e4a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "media_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.String(length=255), nullable=True),
        sa.Column("media_kind", sa.String(length=32), nullable=False),
        sa.Column("provenance", sa.String(length=32), nullable=False),
        sa.Column(
            "source_tag",
            sa.String(length=64),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("deterministic_id", sa.String(length=32), nullable=False),
        sa.Column("normalized_slug", sa.String(length=255), nullable=False),
        sa.Column("system_name", sa.String(length=512), nullable=False),
        sa.Column("storage_prefix", sa.String(length=255), nullable=False),
        sa.Column("src_url", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("filesize", sa.BigInteger(), nullable=True),
        sa.Column(
            "ingested_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "media_kind IN ('document', 'image', 'audio', 'video', 'other')",
            name="media_assets_media_kind_check",
        ),
        sa.CheckConstraint(
            "provenance IN ('uploaded', 'generated', 'imported', 'system')",
            name="media_assets_provenance_check",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["chat_threads.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_media_assets_project", "media_assets", ["project_id"], unique=False
    )
    op.create_index(
        "ix_media_assets_thread", "media_assets", ["thread_id"], unique=False
    )
    op.create_index(
        "ix_media_assets_content_hash",
        "media_assets",
        ["content_hash"],
        unique=False,
    )
    op.create_index(
        "ix_media_assets_deterministic_id",
        "media_assets",
        ["deterministic_id"],
        unique=False,
    )
    op.create_index(
        "ix_media_assets_ingested",
        "media_assets",
        [sa.literal_column("ingested_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_media_assets_kind_provenance",
        "media_assets",
        ["media_kind", "provenance"],
        unique=False,
    )
    op.create_index(
        "uq_media_assets_active_identity",
        "media_assets",
        ["project_id", "media_kind", "provenance", "content_hash"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "media_aliases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column("alias_normalized", sa.String(length=512), nullable=False),
        sa.Column("alias_type", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "alias_type IN ('original_name', 'prompt', 'user_alias', 'system_generated')",
            name="media_aliases_alias_type_check",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["media_assets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_media_aliases_asset_id", "media_aliases", ["asset_id"], unique=False
    )
    op.create_index(
        "ix_media_aliases_alias_normalized",
        "media_aliases",
        ["alias_normalized"],
        unique=False,
    )
    op.create_index(
        "ix_media_aliases_alias_type",
        "media_aliases",
        ["alias_type"],
        unique=False,
    )

    op.add_column(
        "generated_images",
        sa.Column("asset_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "uploaded_images",
        sa.Column("asset_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "uploaded_documents",
        sa.Column("asset_id", sa.String(length=36), nullable=True),
    )

    op.create_foreign_key(
        "fk_generated_images_asset_id",
        "generated_images",
        "media_assets",
        ["asset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_uploaded_images_asset_id",
        "uploaded_images",
        "media_assets",
        ["asset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_uploaded_documents_asset_id",
        "uploaded_documents",
        "media_assets",
        ["asset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_generated_images_asset_id",
        "generated_images",
        ["asset_id"],
        unique=False,
    )
    op.create_index(
        "ix_uploaded_images_asset_id",
        "uploaded_images",
        ["asset_id"],
        unique=False,
    )
    op.create_index(
        "ix_uploaded_documents_asset_id",
        "uploaded_documents",
        ["asset_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_uploaded_documents_asset_id", table_name="uploaded_documents"
    )
    op.drop_index("ix_uploaded_images_asset_id", table_name="uploaded_images")
    op.drop_index("ix_generated_images_asset_id", table_name="generated_images")

    op.drop_constraint(
        "fk_uploaded_documents_asset_id",
        "uploaded_documents",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_uploaded_images_asset_id", "uploaded_images", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_generated_images_asset_id", "generated_images", type_="foreignkey"
    )

    op.drop_column("uploaded_documents", "asset_id")
    op.drop_column("uploaded_images", "asset_id")
    op.drop_column("generated_images", "asset_id")

    op.drop_index("ix_media_aliases_alias_type", table_name="media_aliases")
    op.drop_index(
        "ix_media_aliases_alias_normalized", table_name="media_aliases"
    )
    op.drop_index("ix_media_aliases_asset_id", table_name="media_aliases")
    op.drop_table("media_aliases")

    op.drop_index("uq_media_assets_active_identity", table_name="media_assets")
    op.drop_index("ix_media_assets_kind_provenance", table_name="media_assets")
    op.drop_index("ix_media_assets_ingested", table_name="media_assets")
    op.drop_index("ix_media_assets_deterministic_id", table_name="media_assets")
    op.drop_index("ix_media_assets_content_hash", table_name="media_assets")
    op.drop_index("ix_media_assets_thread", table_name="media_assets")
    op.drop_index("ix_media_assets_project", table_name="media_assets")
    op.drop_table("media_assets")
