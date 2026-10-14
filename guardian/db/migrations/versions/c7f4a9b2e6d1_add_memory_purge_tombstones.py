"""Add audited permanent-erasure tombstones.

Revision: c7f4a9b2e6d1
Revises: b8e2f4a6c901

Creates ``memory_purge_tombstones``, the minimal non-content suppression
authority that survives ordinary-memory permanent erasure (UMS-11).

Campaign revalidation established the gap this migration closes: ADR-084
holds supported user-facing release until permanent erasure and re-import
suppression are proven, contract §12 makes purge mandatory before that
release, and no persistence, service, route, or proof existed for either.
Contract §12 twice deferred its own implementation to UMS-11, so the
capability had no owner. This relation is that ownership.

This is *not* an ordinary canonical memory family. It deliberately has no
composite foreign key to ``memory_records`` and stores no canonical
``memory_id``: the parent row is deleted by the purge that writes the
tombstone, so a foreign key would be unsatisfiable by construction. Identity
is instead carried by a versioned, domain-separated, non-reversible digest of
the erased record identity. That digest is what makes an idempotent retry
detectable after the canonical row is gone, and it reveals nothing about the
erased content.

What is retained is the minimum needed to stop a future import from
resurrecting the same source atom:

* an account boundary;
* an opaque purged-record fingerprint (retry detection);
* the *kind* of source that produced the atom, not its plaintext identity;
* a versioned source-atom fingerprint (replay detection);
* a purge receipt identity; and
* the purge time.

``suppress_reimport`` is stored but structurally cannot become false: a
CHECK constraint pins it true. A suppression flag that can be unset is not a
suppression authority, and no model, Operator, importer, or internal service
may clear it.

Additive only:

* zero changes to existing ``memory_records`` rows;
* zero synthetic tombstones -- no pre-existing memory is given invented
  suppression history, because no pre-existing memory was purged;
* zero changes to ``memory_revisions``, ``memory_review_revisions``, or
  ``memory_lifecycle_revisions``;
* zero changes to ``memory_provenance`` or ``memory_persona_links``;
* zero changes to Personal Facts. ``personal_facts`` and its evidence /
  revision families keep their own specialized authority; ordinary-memory
  purge has no schema path to them and no generic FK to ``memory_records``.
* zero changes to any existing account export schema meaning.

The CHECK string literals in this migration are revision-local and
immutable. They must not import from ``guardian.protocol_tokens``; historical
Alembic replay must remain reproducible without runtime access.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "c7f4a9b2e6d1"
down_revision = "b8e2f4a6c901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_purge_tombstones",
        # Server-authored stable purge receipt identity. This doubles as the
        # durable non-content purge receipt required by contract §12: it
        # proves purge occurred, within which account boundary, and when --
        # without preserving any deleted memory semantics.
        sa.Column("purge_receipt_id", sa.String(36), nullable=False),
        # Non-null account authority. CASCADE removes suppression when the
        # owning account itself is legitimately erased.
        sa.Column("user_id", sa.String(255), nullable=False),
        # Versioned opaque digest of the erased canonical record identity.
        # NOT NULL: every tombstone is retry-detectable.
        sa.Column("purged_record_fingerprint", sa.String(128), nullable=False),
        # Source *kind* is retained; source plaintext identity is not. A
        # direct/manual record has no import source and leaves these NULL.
        sa.Column("source_system", sa.String(32), nullable=True),
        sa.Column("source_entity_kind", sa.String(32), nullable=True),
        # Versioned non-reversible digest of the minimum stable source-atom
        # identity, used to suppress replay of the same imported atom.
        # NULL is legitimate for direct/manual memory. It is NOT legitimate
        # for an import-origin record, and the purge service fails closed
        # before deletion rather than writing NULL there.
        sa.Column("source_atom_fingerprint", sa.String(128), nullable=True),
        sa.Column(
            "purged_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Stored explicitly so the suppression posture is legible, but the
        # CHECK below makes it structurally impossible to set false.
        sa.Column(
            "suppress_reimport",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_memory_purge_tombstones_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("purge_receipt_id", name="pk_memory_purge_tombstones"),
        # One suppression entry per erased record per account. This is what
        # makes an idempotent retry provable without creating a second
        # tombstone or a second receipt identity.
        sa.UniqueConstraint(
            "user_id",
            "purged_record_fingerprint",
            name="uq_memory_purge_tombstones_account_record",
        ),
        # Typed source vocabulary, revision-local and immutable.
        sa.CheckConstraint(
            "source_system IS NULL OR source_system IN "
            "('codexify', 'openai', 'anthropic', 'future_registered')",
            name="memory_purge_tombstones_source_system_check",
        ),
        sa.CheckConstraint(
            "source_entity_kind IS NULL OR source_entity_kind IN "
            "('chat', 'vault', 'importer', 'classifier', 'future_registered')",
            name="memory_purge_tombstones_source_entity_kind_check",
        ),
        # The suppression posture cannot be relaxed. This is a structural
        # guarantee, not a service convention.
        sa.CheckConstraint(
            "suppress_reimport",
            name="memory_purge_tombstones_suppress_reimport_check",
        ),
    )
    op.create_index(
        "ix_memory_purge_tombstones_user_id",
        "memory_purge_tombstones",
        ["user_id"],
    )
    # Partial unique index: a given source atom may be suppressed at most
    # once per account, while leaving the NULL case unconstrained so any
    # number of direct/manual purges coexist.
    op.create_index(
        "uq_memory_purge_tombstones_account_source_atom",
        "memory_purge_tombstones",
        ["user_id", "source_atom_fingerprint"],
        unique=True,
        postgresql_where=sa.text("source_atom_fingerprint IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_memory_purge_tombstones_account_source_atom",
        table_name="memory_purge_tombstones",
    )
    op.drop_index(
        "ix_memory_purge_tombstones_user_id",
        table_name="memory_purge_tombstones",
    )
    op.drop_table("memory_purge_tombstones")
