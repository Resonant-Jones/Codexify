"""Add durable coding-worker ownership to accepted runs.

Revision ID: e42c7d0b9135
Revises: f0d7c4b2a198

Adds the two nullable ownership columns that the atomic Guardian coding-run
acceptance transition writes alongside ``status`` and ``started_at``:

* ``coding_worker_instance_id`` -- the coding-worker instance that accepted
  the run.
* ``coding_worker_claim_id`` -- the unique ownership claim made at acceptance.

The columns are executor metadata, subordinate to the existing ``agent_runs``
authority. They are deliberately *not* a liveness signal, a lease, an expiry,
or a takeover mechanism; a persisted owner records that an instance took the
claim, not that it still holds it.

This migration is additive. It does not backfill historical rows: runs accepted
before this revision have no recorded owner and remain ownership-unknown. It
does not alter the run-status vocabulary, and it does not touch credential or
account data.
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e42c7d0b9135"
down_revision: str | Sequence[str] | None = "f0d7c4b2a198"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_runs",
        sa.Column("coding_worker_instance_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "agent_runs",
        sa.Column("coding_worker_claim_id", sa.String(length=64), nullable=True),
    )
    # Ownership is paired: either both fields are present or neither is.
    op.create_check_constraint(
        "agent_runs_coding_worker_ownership_check",
        "agent_runs",
        "(coding_worker_instance_id IS NULL AND coding_worker_claim_id IS NULL) OR "
        "(coding_worker_instance_id IS NOT NULL AND "
        "coding_worker_claim_id IS NOT NULL)",
    )
    # A claim id identifies exactly one acceptance. NULLs stay distinct, so
    # historical ownership-unknown rows are unaffected.
    op.create_unique_constraint(
        "uq_agent_runs_coding_worker_claim_id",
        "agent_runs",
        ["coding_worker_claim_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_agent_runs_coding_worker_claim_id",
        "agent_runs",
        type_="unique",
    )
    op.drop_constraint(
        "agent_runs_coding_worker_ownership_check",
        "agent_runs",
        type_="check",
    )
    op.drop_column("agent_runs", "coding_worker_claim_id")
    op.drop_column("agent_runs", "coding_worker_instance_id")
