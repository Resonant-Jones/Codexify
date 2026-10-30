"""Merge the campaign provenance branch into the unified main head.

Revision ID: e2a7f3c1b9d4
Revises: b7e2c4a1d903, c8e42a91d307

This graph-only merge changes no schema.  It joins the branch that carries
the Campaign Continuation Authority provenance discriminator to the branch
that carries the Guardian coding-worker claim schema, leaving a single
Alembic head.

``c8e42a91d307`` is the graph-only merge of the Guardian coding-worker claim
schema (``d86f2a4b1c90``) with the unified main head (``3a91d7c4e8b2``).
``b7e2c4a1d903`` adds the Campaign Continuation Authority provenance
discriminator.  Both are additive, both are already applied by the time this
revision runs, and neither is changed or replaced here.

Why this revision exists: ``b7e2c4a1d903`` was rooted at ``3a91d7c4e8b2``
rather than at ``c8e42a91d307``, so it forked a second head below the merge
instead of joining it.  The graph then carried two heads,
``b7e2c4a1d903`` and ``c8e42a91d307``, and ``alembic upgrade head`` failed
with "Multiple head revisions are present".  This revision restores the
single-head invariant that the rest of the graph, and
``tests/migration/test_read_state_main_head_merge.py``, already assume.
"""

from __future__ import annotations

from typing import Sequence

revision: str = "e2a7f3c1b9d4"
down_revision: str | Sequence[str] | None = ("b7e2c4a1d903", "c8e42a91d307")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
