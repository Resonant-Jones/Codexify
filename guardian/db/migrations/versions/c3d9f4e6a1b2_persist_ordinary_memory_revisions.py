"""Add ordinary-memory content revision history.

Revision ID: c3d9f4e6a1b2
Revises: 8c2f4a6d9b10

Creates ``memory_revisions``, the canonical append-only text-revision
family for ordinary canonical memory (UMS-05C9).

``memory_records.text_content`` remains the current content authority.
This table preserves the exact prior and resulting authored text for one
transition, so a direct content correction can be reconstructed.

It is deliberately distinct from:

* ``memory_provenance`` — source identity plus non-authoritative receipt
  extensions; audit evidence, not content history.
* ``personal_fact_revisions`` — the specialized Personal Facts revision
  authority, which is untouched here.

Additive only:

* zero changes to existing ``memory_records`` rows;
* zero synthetic historical revision rows (no existing memory is given
  invented history);
* zero changes to Personal Facts.

The CHECK string literals in this migration are revision-local and
immutable. They must not import from ``guardian.protocol_tokens``; historical
Alembic replay must remain reproducible without runtime access.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "c3d9f4e6a1b2"
down_revision = "8c2f4a6d9b10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_revisions",
        sa.Column("revision_id", sa.String(36), nullable=False),
        sa.Column("memory_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("old_text_content", sa.Text(), nullable=False),
        sa.Column("new_text_content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Revision account identity is bound to canonical-memory account
        # identity. CASCADE ties revision lifetime to legitimate permanent
        # erasure of the parent memory.
        sa.ForeignKeyConstraint(
            ["memory_id", "user_id"],
            ["memory_records.memory_id", "memory_records.user_id"],
            name="fk_memory_revisions_memory_account",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("revision_id", name="pk_memory_revisions"),
        # Per-memory ordering is explicit and duplicate sequence numbers are
        # impossible. memory_id is globally unique (PK of memory_records), so
        # this is strictly per-memory unique without weakening that.
        sa.UniqueConstraint(
            "memory_id",
            "revision_number",
            name="uq_memory_revisions_memory_number",
        ),
        sa.CheckConstraint(
            "revision_number >= 1",
            name="memory_revisions_number_check",
        ),
        # Exact byte comparison: a row with identical prior and resulting text
        # is not a semantic revision. No trimming, no collation.
        sa.CheckConstraint(
            "old_text_content <> new_text_content",
            name="memory_revisions_change_check",
        ),
    )
    op.create_index(
        "ix_memory_revisions_memory_id",
        "memory_revisions",
        ["memory_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_memory_revisions_memory_id", table_name="memory_revisions")
    op.drop_table("memory_revisions")
