"""add music_jobs table

Revision ID: c4f7a9e2b810
Revises: a7d4c9e2f1b3
Create Date: 2026-11-07 12:20:00.000000

The host's own record of which project a music job belongs to.

The route used to read the project and thread out of the context the
Agent-DAW service echoes back on a finished job.  That made the host's
attribution depend on the engine's age:  an engine that predates the
echo returns files the host cannot place, and the host reports success
anyway --  files produced, none registered.  The host sent the context,
so it can keep its own copy and stop depending on what the engine
happens to remember.

The row is written when the job handle is minted and is never rewritten.
The first write wins, so a job belongs to exactly one project.

``thread_id`` is nullable and set to null on delete:  a thread that goes
away leaves the job attributed to its project alone, because losing the
attribution to a thread is not a reason to lose the project.  The
project is the hard requirement and cascades.

There is deliberately no ``user_id`` column:  the asset row already
carries one, and it comes from the scope of the request that registers
the files rather than from the job that produced them.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4f7a9e2b810"
down_revision: str | Sequence[str] | None = "a7d4c9e2f1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "music_jobs",
        sa.Column(
            "job_id",
            sa.String(length=128),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "thread_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["chat_threads.id"],
            ondelete="SET NULL",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("music_jobs")
