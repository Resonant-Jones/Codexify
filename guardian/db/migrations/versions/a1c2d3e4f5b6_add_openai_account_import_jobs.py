"""add durable OpenAI account import jobs and media lineage

Revision ID: a1c2d3e4f5b6
Revises: e5f6a7b8c9d0
Create Date: 2026-07-21 20:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1c2d3e4f5b6"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "openai_account_import_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column(
            "source_system",
            sa.String(length=32),
            nullable=False,
            server_default="openai",
        ),
        sa.Column("source_export_fingerprint", sa.String(length=64)),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="receiving",
        ),
        sa.Column("staging_locator", sa.Text(), nullable=False),
        sa.Column("total_file_count", sa.Integer(), nullable=False),
        sa.Column("total_byte_count", sa.BigInteger(), nullable=False),
        sa.Column(
            "uploaded_file_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "uploaded_byte_count", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column(
            "imported_thread_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "imported_message_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "imported_media_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "warning_details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "error_details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "staged_manifest",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "checkpoint",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("queued_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True)),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.CheckConstraint(
            "status IN ('completed','completed_with_warnings','failed','queued','receiving','running')",
            name="openai_account_import_jobs_status_check",
        ),
        sa.CheckConstraint(
            "total_file_count > 0 AND total_byte_count >= 0",
            name="openai_account_import_jobs_declared_counts_check",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_openai_account_import_jobs_user",
        "openai_account_import_jobs",
        ["user_id"],
    )
    op.create_index(
        "ix_openai_account_import_jobs_status",
        "openai_account_import_jobs",
        ["status"],
    )
    op.create_index(
        "ix_openai_account_import_jobs_fingerprint",
        "openai_account_import_jobs",
        ["user_id", "source_export_fingerprint"],
    )

    op.add_column(
        "media_assets", sa.Column("import_job_id", sa.String(length=36))
    )
    op.add_column("media_assets", sa.Column("source_relative_path", sa.Text()))
    op.add_column(
        "media_assets", sa.Column("source_export_id", sa.String(length=255))
    )
    op.add_column(
        "media_assets", sa.Column("source_message_id", sa.String(length=255))
    )
    op.add_column(
        "media_assets", sa.Column("source_thread_id", sa.String(length=255))
    )
    op.add_column(
        "media_assets",
        sa.Column(
            "import_lineage",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_foreign_key(
        "fk_media_assets_import_job_id",
        "media_assets",
        "openai_account_import_jobs",
        ["import_job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_media_assets_import_job", "media_assets", ["import_job_id"]
    )

    op.alter_column(
        "uploaded_images",
        "thread_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "generated_images",
        "thread_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "generated_images",
        "thread_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "uploaded_images",
        "thread_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_index("ix_media_assets_import_job", table_name="media_assets")
    op.drop_constraint(
        "fk_media_assets_import_job_id", "media_assets", type_="foreignkey"
    )
    op.drop_column("media_assets", "import_lineage")
    op.drop_column("media_assets", "source_thread_id")
    op.drop_column("media_assets", "source_message_id")
    op.drop_column("media_assets", "source_export_id")
    op.drop_column("media_assets", "source_relative_path")
    op.drop_column("media_assets", "import_job_id")

    op.drop_index(
        "ix_openai_account_import_jobs_fingerprint",
        table_name="openai_account_import_jobs",
    )
    op.drop_index(
        "ix_openai_account_import_jobs_status",
        table_name="openai_account_import_jobs",
    )
    op.drop_index(
        "ix_openai_account_import_jobs_user",
        table_name="openai_account_import_jobs",
    )
    op.drop_table("openai_account_import_jobs")
