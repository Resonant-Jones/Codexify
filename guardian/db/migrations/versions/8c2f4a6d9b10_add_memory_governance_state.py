"""Add canonical ordinary-memory governance state to memory_records.

Revision ID: 8c2f4a6d9b10
Revises: f6b0d3e8c5a2

Materializes the canonical review_state and lifecycle_state authority on
``memory_records`` per UMS-05C8 (ordinary-memory governance persistence
prerequisite). The new columns become the sole canonical review and
lifecycle authority; the legacy ``reviewed_at`` / ``activated_at``
timestamps are preserved as durable historical metadata but no longer
substitute for typed state authority.

Backfill is deterministic and refuses to invent history. No legacy
row becomes ``rejected``, ``disputed``, or ``retired``; the only
post-backfill states are ``pending``/``approved`` and
``dormant``/``active`` derived from the existing timestamp
semantics.

Additive CHECK constraints match the closed ``MemoryReviewState`` and
``MemoryLifecycleState`` vocabularies registered in
``guardian.protocol_tokens``. The CHECK string literals are
revision-local and immutable; they do not import from the runtime
protocol module.

The downgrade is fail-closed: it refuses to remove the new columns if
the existing data contains a typed state combination whose meaning
cannot be reconstructed by the old timestamp-only model. This preserves
``rejected``, ``disputed``, and ``retired`` rows from being silently
erased.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "8c2f4a6d9b10"
down_revision = "7e5a5fccf253"
branch_labels = None
depends_on = None


# Revision-local immutable snapshot of the canonical token values.
# These are the strings frozen by UMS-05C8 from the protocol tokens
# ``MemoryReviewState`` and ``MemoryLifecycleState``. They must not
# import from ``guardian.protocol_tokens``; historical Alembic replay
# must remain reproducible without runtime access.
_REVIEW_STATES: tuple[str, ...] = (
    "pending",
    "approved",
    "rejected",
    "disputed",
)
_LIFECYCLE_STATES: tuple[str, ...] = (
    "active",
    "dormant",
    "retired",
)


def upgrade() -> None:
    # 1. Add the two columns in a safely backfillable posture. Use
    # nullable=True initially so the backfill can write typed values
    # without a server-default that would silently invent a different
    # lifecycle meaning.
    with op.batch_alter_table("memory_records") as batch_op:
        batch_op.add_column(
            sa.Column(
                "review_state",
                sa.String(32),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "lifecycle_state",
                sa.String(32),
                nullable=True,
            )
        )

    # 2. Backfill every existing row from the legacy timestamp-only
    # model. No row becomes rejected/disputed/retired.
    op.execute(
        sa.text(
            "UPDATE memory_records SET review_state = "
            "CASE WHEN reviewed_at IS NULL THEN 'pending' ELSE 'approved' END"
        )
    )
    op.execute(
        sa.text(
            "UPDATE memory_records SET lifecycle_state = "
            "CASE WHEN activated_at IS NULL THEN 'dormant' ELSE 'active' END"
        )
    )

    # 3. Add CHECK constraints and enforce non-null posture.
    with op.batch_alter_table("memory_records") as batch_op:
        batch_op.alter_column(
            "review_state",
            existing_type=sa.String(32),
            nullable=False,
            server_default=sa.text("'pending'"),
        )
        batch_op.alter_column(
            "lifecycle_state",
            existing_type=sa.String(32),
            nullable=False,
            server_default=sa.text("'dormant'"),
        )
        batch_op.create_check_constraint(
            "memory_records_review_state_check",
            "review_state IN ("
            + ", ".join("'" + s + "'" for s in _REVIEW_STATES)
            + ")",
        )
        batch_op.create_check_constraint(
            "memory_records_lifecycle_state_check",
            "lifecycle_state IN ("
            + ", ".join("'" + s + "'" for s in _LIFECYCLE_STATES)
            + ")",
        )


def downgrade() -> None:
    # Fail-closed downgrade. The legacy timestamp-only model cannot
    # faithfully represent ``rejected``, ``disputed``, or ``retired``
    # rows. Refuse to drop the typed columns if any such row exists.
    bind = op.get_bind()
    review_blocking = (
        "SELECT 1 FROM memory_records "
        "WHERE review_state IN ('rejected', 'disputed') LIMIT 1"
    )
    lifecycle_blocking = (
        "SELECT 1 FROM memory_records " "WHERE lifecycle_state = 'retired' LIMIT 1"
    )
    review_blocked = bind.execute(sa.text(review_blocking)).first() is not None
    lifecycle_blocked = bind.execute(sa.text(lifecycle_blocking)).first() is not None
    if review_blocked or lifecycle_blocked:
        raise RuntimeError(
            "memory_records governance downgrade refused: "
            "rejected/disputed/retired rows would lose meaning. "
            "Resolve governance state before downgrading."
        )

    with op.batch_alter_table("memory_records") as batch_op:
        batch_op.drop_constraint(
            "memory_records_lifecycle_state_check",
            type_="check",
        )
        batch_op.drop_constraint(
            "memory_records_review_state_check",
            type_="check",
        )
        batch_op.alter_column(
            "lifecycle_state",
            existing_type=sa.String(32),
            nullable=True,
        )
        batch_op.alter_column(
            "review_state",
            existing_type=sa.String(32),
            nullable=True,
        )
        batch_op.drop_column("lifecycle_state")
        batch_op.drop_column("review_state")
