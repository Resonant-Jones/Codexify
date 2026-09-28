"""Add ordinary-memory review-transition revision history.

Revision: a7c3e91d4b60
Revises: c3d9f4e6a1b2

Creates ``memory_review_revisions``, the canonical append-only review-state
transition family for ordinary canonical memory (UMS-05C10A-P).

UMS-05C10A-R classified ordinary review-transition history as
``REVIEW_HISTORY_NEW_CANONICAL_PERSISTENCE_REQUIRED``: the current contract
requires every authority-changing transition to produce a revision *and* an
intent receipt, but no canonical family could represent old/new review state.

Three truth surfaces remain strictly separate:

* ``memory_records.review_state`` -- current review authority (untouched here);
* ``memory_revisions`` -- content history only (untouched here);
* ``memory_provenance`` -- intent / source / audit evidence, whose
  ``extensions`` are explicitly non-authority (untouched here);
* ``personal_fact_revisions`` -- specialized Personal Facts revision
  authority (untouched here).

This table records *that* a typed review state changed. It deliberately does
**not** encode a legal-transition graph: the database accepts any unequal
pair of valid review tokens. Persistence capability is not mutation
authorization. The review writer remains frozen and unimplemented.

Additive only:

* zero changes to existing ``memory_records`` rows, including
  ``review_state`` and ``lifecycle_state``;
* zero synthetic historical rows (no existing memory is given invented
  history);
* zero changes to content ``memory_revisions``;
* zero changes to ``memory_provenance``;
* zero changes to Personal Facts.

The CHECK string literals in this migration are revision-local and
immutable. They must not import from ``guardian.protocol_tokens``; historical
Alembic replay must remain reproducible without runtime access.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "a7c3e91d4b60"
down_revision = "c3d9f4e6a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_review_revisions",
        sa.Column("review_revision_id", sa.String(36), nullable=False),
        sa.Column("memory_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("old_review_state", sa.String(32), nullable=False),
        sa.Column("new_review_state", sa.String(32), nullable=False),
        sa.Column("actor_account_id", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Review-revision account identity is bound to canonical-memory
        # account identity. CASCADE ties review-revision lifetime to
        # legitimate permanent erasure of the parent memory.
        sa.ForeignKeyConstraint(
            ["memory_id", "user_id"],
            ["memory_records.memory_id", "memory_records.user_id"],
            name="fk_memory_review_revisions_memory_account",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "review_revision_id", name="pk_memory_review_revisions"
        ),
        # Per-memory ordering is explicit and duplicate sequence numbers are
        # impossible. This sequence is scoped to the review-history family
        # and is NOT shared with content `memory_revisions`.
        sa.UniqueConstraint(
            "memory_id",
            "revision_number",
            name="uq_memory_review_revisions_memory_number",
        ),
        sa.CheckConstraint(
            "revision_number >= 1",
            name="memory_review_revisions_number_check",
        ),
        # Typed review vocabulary only. No source->target pair is privileged
        # or forbidden: the legal transition graph is unresolved.
        sa.CheckConstraint(
            "old_review_state IN ('pending', 'approved', 'rejected', 'disputed')",
            name="memory_review_revisions_old_state_check",
        ),
        sa.CheckConstraint(
            "new_review_state IN ('pending', 'approved', 'rejected', 'disputed')",
            name="memory_review_revisions_new_state_check",
        ),
        sa.CheckConstraint(
            "old_review_state <> new_review_state",
            name="memory_review_revisions_change_check",
        ),
        sa.CheckConstraint(
            "actor_account_id = user_id",
            name="memory_review_revisions_actor_account_check",
        ),
    )
    op.create_index(
        "ix_memory_review_revisions_memory_id",
        "memory_review_revisions",
        ["memory_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_memory_review_revisions_memory_id",
        table_name="memory_review_revisions",
    )
    op.drop_table("memory_review_revisions")
