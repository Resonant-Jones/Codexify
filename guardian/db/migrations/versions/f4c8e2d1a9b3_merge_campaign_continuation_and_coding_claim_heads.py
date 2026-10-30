"""Merge the campaign-continuation branch into the Guardian coding-claim head.

Revision ID: f4c8e2d1a9b3
Revises: b7e2c4a1d903, c8e42a91d307

This graph-only merge changes no schema.  It joins the branch that carries the
Campaign Continuation Authority provenance discriminator to the branch that
carries the Guardian coding-worker ownership and claim-scoped heartbeat
schema, leaving a single Alembic head.

Both parents descend from the same pre-merge parent ``3a91d7c4e8b2``.  The
campaign-continuation branch (``b7e2c4a1d903``) and the coding-claim merge
(``c8e42a91d307``) were each opened against that shared parent before either
had landed, so integrating both left two sibling children and therefore two
Alembic heads on ``main``.  No single pull request could observe the conflict
on its own branch, and a push to ``main`` that touches no backend file does
not run the backend suite, so the two-head state was not detected by CI.

``b7e2c4a1d903`` adds the nullable provenance discriminator and its backfill.
``c8e42a91d307`` is itself the no-op merge that unified the coding-claim
branch with the main lineage.  Both are additive, both are applied before this
revision runs, and neither is changed or replaced here.
"""

from typing import Sequence

revision: str = "f4c8e2d1a9b3"
down_revision: str | Sequence[str] | None = ("b7e2c4a1d903", "c8e42a91d307")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
