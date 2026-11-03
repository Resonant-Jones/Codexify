"""Merge the read-cursor branch into the unified Saved Widget / consent head.

Revision ID: 3a91d7c4e8b2
Revises: 7f2c9e1a4b63, b3c8d1e5f7a2

This graph-only merge changes no schema.  It joins the branch that carries the
recipient-local direct-message read cursor to the branch that carries the
unified Saved Widget and automatic-collection consent head, leaving a single
Alembic head.

``7f2c9e1a4b63`` is the graph-only merge of the Saved Widget storage head and
the automatic-collection consent head.  ``b3c8d1e5f7a2`` adds the
participant-local read cursor.  Both are additive, both are already applied by
the time this revision runs, and neither is changed or replaced here.
"""

from typing import Sequence

revision: str = "3a91d7c4e8b2"
down_revision: str | Sequence[str] | None = ("7f2c9e1a4b63", "b3c8d1e5f7a2")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
