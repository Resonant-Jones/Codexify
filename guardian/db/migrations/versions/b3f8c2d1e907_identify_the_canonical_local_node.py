"""identify the canonical local node explicitly

Revision ID: b3f8c2d1e907
Revises: c4f7a9e2b810
Create Date: 2026-11-07 13:05:00.000000

The local node was resolved by being the oldest row in
``threadspace_nodes``, with the node id as the tie-break.  That cannot
deliver what ADR-079 asks for -- one stable canonical local node row --
because the oldest row is the local node only while nothing else was
recorded earlier or in the same clock tick.

Two rows created within the same second tie, and the tie-break was the node
id, so a foreign row whose id sorted ahead was adopted as "local".  That is
what made ``tests/routes/test_people_search_discoverability.py`` fail about
one run in sixteen, and in production it would silently widen a search's
scope to a remote node.

The local node is now *identified* by an ``is_local`` flag rather than
inferred from the row's age, and a partial unique index admits at most one
local row so that two concurrent first-use requests cannot each mint one.

The backfill marks the oldest row local, which is exactly what the resolver
returned before this change.  No existing deployment changes behaviour: the
same row is canonical after the migration as before it.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f8c2d1e907"
down_revision: str | Sequence[str] | None = "c4f7a9e2b810"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_INDEX_NAME = "threadspace_nodes_one_local_idx"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "threadspace_nodes",
        sa.Column(
            "is_local",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # Behaviour-preserving backfill: mark the oldest row local, which is the
    # row the age-based resolver selected before this migration.
    op.execute(
        sa.text(
            "UPDATE threadspace_nodes "
            "SET is_local = true "
            "WHERE node_id = ("
            "  SELECT node_id FROM threadspace_nodes "
            "  ORDER BY created_at ASC, node_id ASC LIMIT 1"
            ")"
        )
    )

    # At most one local node, enforced by the database rather than by the
    # resolver's cooperation.
    op.create_index(
        _INDEX_NAME,
        "threadspace_nodes",
        ["is_local"],
        unique=True,
        sqlite_where=sa.text("is_local = 1"),
        postgresql_where=sa.text("is_local IS true"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(_INDEX_NAME, table_name="threadspace_nodes")
    op.drop_column("threadspace_nodes", "is_local")
