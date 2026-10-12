"""Add ordinary-memory lifecycle-transition revision history.

Revision: b8e2f4a6c901
Revises: a7c3e91d4b60

Creates ``memory_lifecycle_revisions``, the canonical append-only
lifecycle-state transition family for ordinary canonical memory
(UMS-05C10B-P).

UMS-05C10B-R proved this family must exist and must be distinct. Nothing in
current canonical storage could record that a record retired from ``active``
and a record retired from ``dormant`` are different histories, yet the
governing contract requires restore to return a retired record to its
*pre-retirement governed posture*. The pre-retirement posture is preserved
in ``old_lifecycle_state``; no parallel mutable ``pre_retirement_state``
column is added.

This is the fourth independent truth surface:

* ``memory_records.lifecycle_state`` -- present lifecycle authority;
* ``memory_revisions`` -- authored content history (untouched here);
* ``memory_review_revisions`` -- review-authority history (untouched here);
* ``memory_provenance`` -- intent / source / audit evidence, whose
  ``extensions`` are explicitly non-authority (untouched here); and
* ``personal_fact_revisions`` -- specialized Personal Facts revision
  authority (untouched here).

No legal transition graph is encoded. The table accepts any *unequal* pair
of valid lifecycle tokens and forbids no source-to-target combination, so
this migration cannot smuggle an unaccepted mutation policy into the schema.
Which transitions a writer may legally perform remains unresolved and is
owned by UMS-05C10B-C; the retire / restore writer stays frozen.

Actor, reason, request reference, and action identity are deliberately
absent: those are intent/source evidence belonging to the receipt layer.

Additive only:

* zero changes to existing ``memory_records`` rows, including
  ``lifecycle_state``;
* zero synthetic historical rows -- no existing memory is given invented
  lifecycle history, and a record retired from a posture that was never
  canonically recorded is not back-filled with a guess;
* zero changes to content or review revision families;
* zero changes to provenance and Personal Facts.

The CHECK string literals in this migration are revision-local and
immutable. They must not import from ``guardian.protocol_tokens``; historical
Alembic replay must remain reproducible without runtime access.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "b8e2f4a6c901"
down_revision = "a7c3e91d4b60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_lifecycle_revisions",
        sa.Column("lifecycle_revision_id", sa.String(36), nullable=False),
        sa.Column("memory_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("old_lifecycle_state", sa.String(32), nullable=False),
        sa.Column("new_lifecycle_state", sa.String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Lifecycle-revision account identity is bound to canonical-memory
        # account identity. CASCADE ties lifecycle history to legitimate
        # permanent erasure of the parent memory.
        sa.ForeignKeyConstraint(
            ["memory_id", "user_id"],
            ["memory_records.memory_id", "memory_records.user_id"],
            name="fk_memory_lifecycle_revisions_memory_account",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "lifecycle_revision_id", name="pk_memory_lifecycle_revisions"
        ),
        # Per-memory ordering is explicit and duplicate sequence numbers are
        # impossible. This sequence is scoped to the lifecycle-history family
        # and is NOT shared with content or review revision numbering.
        sa.UniqueConstraint(
            "memory_id",
            "revision_number",
            name="uq_memory_lifecycle_revisions_memory_number",
        ),
        sa.CheckConstraint(
            "revision_number >= 1",
            name="memory_lifecycle_revisions_number_check",
        ),
        # Typed canonical lifecycle vocabulary only. No source->target pair
        # is privileged or forbidden: transition legality is unresolved and
        # is owned by UMS-05C10B-C, not by this schema.
        sa.CheckConstraint(
            "old_lifecycle_state IN ('active', 'dormant', 'retired')",
            name="memory_lifecycle_revisions_old_state_check",
        ),
        sa.CheckConstraint(
            "new_lifecycle_state IN ('active', 'dormant', 'retired')",
            name="memory_lifecycle_revisions_new_state_check",
        ),
        sa.CheckConstraint(
            "old_lifecycle_state <> new_lifecycle_state",
            name="memory_lifecycle_revisions_change_check",
        ),
    )
    op.create_index(
        "ix_memory_lifecycle_revisions_memory_id",
        "memory_lifecycle_revisions",
        ["memory_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_memory_lifecycle_revisions_memory_id",
        table_name="memory_lifecycle_revisions",
    )
    op.drop_table("memory_lifecycle_revisions")
