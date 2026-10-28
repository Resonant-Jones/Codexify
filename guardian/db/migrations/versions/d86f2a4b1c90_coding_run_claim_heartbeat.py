"""Add a claim-scoped heartbeat to accepted coding runs.

Revision ID: d86f2a4b1c90
Revises: e42c7d0b9135

Adds one nullable column to ``agent_runs``:

* ``coding_worker_last_heartbeat_at`` -- the last durable liveness
  observation recorded by the owning worker instance.

The column is subordinate execution *evidence*. It never grants execution,
retry, or recovery authority, and an absent or stale heartbeat is not proof
that the worker died.

The migration is additive. It does not backfill: runs accepted before this
revision have no recorded heartbeat and remain heartbeat-unknown. It does not
alter the run-status vocabulary, and it does not touch credential or account
data.
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "d86f2a4b1c90"
down_revision: str | Sequence[str] | None = "e42c7d0b9135"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_runs",
        sa.Column(
            "coding_worker_last_heartbeat_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    # A heartbeat is evidence about an owner, so it may only exist when the
    # owner and its claim are both recorded.
    op.create_check_constraint(
        "agent_runs_coding_worker_heartbeat_ownership_check",
        "agent_runs",
        "coding_worker_last_heartbeat_at IS NULL OR "
        "(coding_worker_instance_id IS NOT NULL AND "
        "coding_worker_claim_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "agent_runs_coding_worker_heartbeat_ownership_check",
        "agent_runs",
        type_="check",
    )
    op.drop_column("agent_runs", "coding_worker_last_heartbeat_at")
