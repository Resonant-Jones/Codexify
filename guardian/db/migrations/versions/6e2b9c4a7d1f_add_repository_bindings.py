"""Add repository_bindings table for Project-to-Git-working-tree authority.

Revision ID: 6e2b9c4a7d1f
Revises: c1a2b3c4d5e6
Create Date: 2026-08-12 00:00:00.000000

Stage 2K.1 (ADR-065): introduce durable Project-to-RepositoryBinding authority.
Cardinality is one active binding per Project. The binding resolves one
authorized working-tree root and is Guardian-owned durable authority state,
never model input or conversational context.

This migration introduces ONLY the new table, its columns, the Project FK,
the source-class check, the partial unique active-binding index, and one
narrowly justified lookup index. There is no backfill, no Project mutation,
no ``General`` binding creation, and no filesystem work.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6e2b9c4a7d1f"
down_revision: Union[str, Sequence[str], None] = "c1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLE_NAME = "repository_bindings"
_TABLE_SCHEMA = "public"
_FK_NAME = "fk_repository_bindings_project_id"
_CHECK_NAME = "ck_repository_bindings_source_class"
_LOOKUP_INDEX_NAME = "ix_repository_bindings_project_id"
_ACTIVE_UNIQUE_INDEX_NAME = "uq_repository_bindings_one_active_per_project"
_ACTIVE_UNIQUE_POSTGRES_WHERE = "is_active IS TRUE"
_SOURCE_CLASS_VALUES = ("'guardian_managed'", "'external_linked'")


def upgrade() -> None:
    """Add the repository_bindings table and its access invariants."""
    op.create_table(
        _TABLE_NAME,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("source_class", sa.String(length=32), nullable=False),
        sa.Column("canonical_root", sa.String(length=4096), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_class IN ("
            + ", ".join(_SOURCE_CLASS_VALUES)
            + ")",
            name=_CHECK_NAME,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=_FK_NAME,
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=_TABLE_SCHEMA,
    )
    op.create_index(
        _LOOKUP_INDEX_NAME,
        _TABLE_NAME,
        ["project_id"],
        unique=False,
        schema=_TABLE_SCHEMA,
    )
    op.create_index(
        _ACTIVE_UNIQUE_INDEX_NAME,
        _TABLE_NAME,
        ["project_id"],
        unique=True,
        postgresql_where=sa.text(_ACTIVE_UNIQUE_POSTGRES_WHERE),
        schema=_TABLE_SCHEMA,
    )


def downgrade() -> None:
    """Remove only the objects introduced by this migration."""
    op.drop_index(
        _ACTIVE_UNIQUE_INDEX_NAME,
        table_name=_TABLE_NAME,
        postgresql_where=sa.text(_ACTIVE_UNIQUE_POSTGRES_WHERE),
        schema=_TABLE_SCHEMA,
    )
    op.drop_index(
        _LOOKUP_INDEX_NAME,
        table_name=_TABLE_NAME,
        schema=_TABLE_SCHEMA,
    )
    op.drop_table(_TABLE_NAME, schema=_TABLE_SCHEMA)
