"""add music_projects table

Revision ID: a7d4c9e2f1b3
Revises: d91e4fa6702b
Create Date: 2026-10-30 16:10:00.000000

A Music Project is an ordinary Codexify ``Project`` whose musical state
lives in this side table, mirroring how ``media_assets`` already hangs
off ``projects`` by ``project_id``.

``projects.system_role`` cannot carry this.  It means "system-owned", its
CHECK constraint allows only ``'general'`` and ``'imports'``, and the
partial unique index ``uq_projects_user_id_system_role`` is unique over
``(user_id, system_role)`` where ``system_role IS NOT NULL`` -- so a
user could have exactly one music project under it.  It is a column for
"the system made this", not for "this has a domain".

The table is 1:1 with ``projects``: ``project_id`` is both the primary
key and the foreign key, so attaching a Music Project to a Project and
detaching it are the same operation.

``current_spec`` is the complete session state as the Producer produced
it, and it is a *record* of that state rather than a second truth about
it.  The Producer owns the specification; this column is what this side
keeps of it.  It is written whole and never field-patched, so a revision
replaces the whole state rather than merging into it.

The scalar columns beside it are a queryable projection of the same
values -- "every project at 120 BPM" is a question worth asking, and
asking it should not mean parsing JSON.  They are not indexed because
the table is small and is almost always reached by ``project_id``.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a7d4c9e2f1b3"
down_revision: str | Sequence[str] | None = "d91e4fa6702b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "music_projects",
        sa.Column(
            "project_id",
            sa.Integer(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("bpm", sa.Float(), nullable=True),
        sa.Column("musical_key", sa.String(length=16), nullable=True),
        sa.Column("musical_mode", sa.String(length=32), nullable=True),
        sa.Column("bars", sa.Integer(), nullable=True),
        sa.Column("time_signature", sa.String(length=16), nullable=True),
        sa.Column("length_seconds", sa.Float(), nullable=True),
        sa.Column(
            "library_path",
            sa.String(length=512),
            nullable=True,
        ),
        sa.Column(
            "current_spec",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("music_projects")
