"""Add canonical UMS memory persistence substrate.

Revision ID: f6b0d3e8c5a2
Revises: e5a9c2f7b4d1

Additive schema only. Creates ``memory_records``,
``memory_persona_links``, and ``memory_provenance`` empty, exactly as
frozen by §4.16 of ``docs/architecture/unified-memory-store-contract.md``
(amended by UMS-03C-A). No legacy memory-bearing row is read, mutated,
or migrated. No runtime writer or reader is redirected. The legacy
``memory_entries`` and ``personal_facts`` stores remain the durable
authority for existing records.

The CHECK string literals in this migration are revision-local and
immutable. They must not depend on the future mutable contents of
``guardian.protocol_tokens``.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "f6b0d3e8c5a2"
down_revision = "e5a9c2f7b4d1"
branch_labels = None
depends_on = None


# Revision-local immutable snapshot of the canonical token values.
# These are the strings frozen by §4.16 (amended) and §4.16.8 of the
# Unified Memory Store Contract. They must not import from
# ``guardian.protocol_tokens``; historical Alembic replay must remain
# deterministic regardless of future application-token mutations.
_UMS_MIGRATION_SEMANTIC_SPECIES = (
    "episodic_semantic_memory",
    "verified_personal_fact",
    "candidate_unreviewed_fact",
)
_UMS_MIGRATION_PERSONA_LINK_KINDS = (
    "captured_under",
    "suggested_by",
    "associated_with",
)
_UMS_MIGRATION_PROVENANCE_SOURCE_SYSTEMS = (
    "codexify",
    "openai",
    "anthropic",
    "future_registered",
)
_UMS_MIGRATION_PROVENANCE_SOURCE_SUBJECT_KINDS = (
    "chat",
    "vault",
    "importer",
    "classifier",
    "future_registered",
)


def _semantic_species_check_sql() -> str:
    values = ", ".join(f"'{value}'" for value in _UMS_MIGRATION_SEMANTIC_SPECIES)
    return f"semantic_species IN ({values})"


def _persona_link_kind_check_sql() -> str:
    values = ", ".join(f"'{value}'" for value in _UMS_MIGRATION_PERSONA_LINK_KINDS)
    return f"link_kind IN ({values})"


def _provenance_source_system_check_sql() -> str:
    values = ", ".join(
        f"'{value}'" for value in _UMS_MIGRATION_PROVENANCE_SOURCE_SYSTEMS
    )
    return f"source_system IN ({values})"


def _provenance_source_subject_kind_check_sql() -> str:
    values = ", ".join(
        f"'{value}'" for value in _UMS_MIGRATION_PROVENANCE_SOURCE_SUBJECT_KINDS
    )
    return f"source_subject_kind IS NULL OR source_subject_kind IN ({values})"


def _review_activation_order_check_sql() -> str:
    # Frozen by UMS-03C-A §4.16.2a of the Unified Memory Store Contract.
    return (
        "activated_at IS NULL OR "
        "(reviewed_at IS NOT NULL AND activated_at >= reviewed_at)"
    )


def _seed_legacy_snapshot_rows() -> Sequence[dict[str, object]]:
    """No legacy backfill is performed by this migration.

    The function returns an empty list deliberately; legacy
    ``memory_entries`` and ``personal_facts`` rows are not read,
    copied, or migrated. The function exists so the upgrade body stays
    symmetric with the additive-create shape and so any future
    migration author is forced to make the additive-only decision
    explicit.
    """

    return ()


def upgrade() -> None:
    # UMS-03C-B enabling relational target for the same-account Project
    # composite FK. The constraint is mathematically non-destructive:
    # projects.id is already a primary key, so no existing row can violate
    # UNIQUE (id, user_id). This step must succeed before any FK that
    # references projects(id, user_id) is created below.
    op.create_unique_constraint(
        "uq_projects_id_user_id",
        "projects",
        ["id", "user_id"],
    )

    op.create_table(
        "memory_records",
        sa.Column("memory_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("semantic_species", sa.String(length=32), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("fact_key", sa.String(length=255), nullable=True),
        sa.Column("fact_value", sa.Text(), nullable=True),
        sa.Column("fact_confidence", sa.Float(), nullable=True),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("activated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "held",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("extensions", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("memory_id", name="pk_memory_records"),
        sa.UniqueConstraint(
            "memory_id", "user_id", name="uq_memory_records_memory_user"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_memory_records_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_memory_records_project",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["projects.id", "projects.user_id"],
            name="fk_memory_records_project_account",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            _semantic_species_check_sql(),
            name="memory_records_semantic_species_check",
        ),
        sa.CheckConstraint(
            "fact_confidence IS NULL OR "
            "(fact_confidence >= 0.0 AND fact_confidence <= 1.0)",
            name="memory_records_fact_confidence_check",
        ),
        sa.CheckConstraint(
            "project_id IS NULL OR " "text_content IS NOT NULL OR fact_key IS NOT NULL",
            name="memory_records_payload_present_check",
        ),
        sa.CheckConstraint(
            "NOT (semantic_species = 'episodic_semantic_memory') "
            "OR (text_content IS NOT NULL "
            "AND fact_key IS NULL "
            "AND fact_value IS NULL "
            "AND fact_confidence IS NULL)",
            name="memory_records_episodic_payload_shape_check",
        ),
        sa.CheckConstraint(
            "NOT (semantic_species IN "
            "('verified_personal_fact', 'candidate_unreviewed_fact')) "
            "OR (fact_key IS NOT NULL "
            "AND fact_value IS NOT NULL "
            "AND text_content IS NULL)",
            name="memory_records_fact_payload_shape_check",
        ),
        sa.CheckConstraint(
            _review_activation_order_check_sql(),
            name="memory_records_review_activation_order_check",
        ),
    )
    op.create_index("ix_memory_records_user_id", "memory_records", ["user_id"])
    op.create_index(
        "ix_memory_records_user_project",
        "memory_records",
        ["user_id", "project_id"],
    )
    op.create_index(
        "ix_memory_records_user_species",
        "memory_records",
        ["user_id", "semantic_species"],
    )
    op.create_index(
        "ix_memory_records_user_activated_at",
        "memory_records",
        ["user_id", "activated_at"],
    )

    op.create_table(
        "memory_persona_links",
        sa.Column("link_id", sa.String(length=36), nullable=False),
        sa.Column("memory_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("persona_subject_id", sa.String(length=36), nullable=False),
        sa.Column("persona_user_id", sa.String(length=255), nullable=False),
        sa.Column("link_kind", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("link_id", name="pk_memory_persona_links"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_memory_persona_links_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["persona_user_id"],
            ["users.id"],
            name="fk_memory_persona_links_persona_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["memory_id", "user_id"],
            ["memory_records.memory_id", "memory_records.user_id"],
            name="fk_memory_persona_links_memory_account",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["persona_subject_id", "persona_user_id"],
            [
                "persona_subjects.persona_subject_id",
                "persona_subjects.user_id",
            ],
            name="fk_memory_persona_links_persona_account",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "user_id = persona_user_id",
            name="memory_persona_links_same_account_check",
        ),
        sa.CheckConstraint(
            _persona_link_kind_check_sql(),
            name="memory_persona_links_link_kind_check",
        ),
        sa.UniqueConstraint(
            "memory_id",
            "persona_subject_id",
            "link_kind",
            name="uq_memory_persona_links_memory_persona_kind",
        ),
    )
    op.create_index(
        "ix_memory_persona_links_user_id",
        "memory_persona_links",
        ["user_id"],
    )
    op.create_index(
        "ix_memory_persona_links_persona_subject_id",
        "memory_persona_links",
        ["persona_subject_id"],
    )

    op.create_table(
        "memory_provenance",
        sa.Column("provenance_id", sa.String(length=36), nullable=False),
        sa.Column("memory_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("source_system", sa.String(length=32), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=True),
        sa.Column("source_thread_id", sa.BigInteger(), nullable=True),
        sa.Column("source_message_id", sa.BigInteger(), nullable=True),
        sa.Column("source_import_job_id", sa.String(length=36), nullable=True),
        sa.Column("source_export_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("source_subject_kind", sa.String(length=32), nullable=True),
        sa.Column("source_subject_id", sa.String(length=255), nullable=True),
        sa.Column(
            "is_imported",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("extensions", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("provenance_id", name="pk_memory_provenance"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_memory_provenance_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_thread_id"],
            ["chat_threads.id"],
            name="fk_memory_provenance_source_thread",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id"],
            ["chat_messages.id"],
            name="fk_memory_provenance_source_message",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["memory_id", "user_id"],
            ["memory_records.memory_id", "memory_records.user_id"],
            name="fk_memory_provenance_memory_account",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            _provenance_source_system_check_sql(),
            name="memory_provenance_source_system_check",
        ),
        sa.CheckConstraint(
            _provenance_source_subject_kind_check_sql(),
            name="memory_provenance_source_subject_kind_check",
        ),
    )
    op.create_index(
        "ix_memory_provenance_memory_id", "memory_provenance", ["memory_id"]
    )
    op.create_index(
        "ix_memory_provenance_user_source_system",
        "memory_provenance",
        ["user_id", "source_system"],
    )
    op.create_index(
        "ix_memory_provenance_source_thread_id",
        "memory_provenance",
        ["source_thread_id"],
        postgresql_where=sa.text("source_thread_id IS NOT NULL"),
    )

    # No-op placeholder: this migration is additive only. The function
    # exists so the symmetry between ``upgrade()`` and the
    # additive-only decision is preserved.
    legacy_snapshot_rows = _seed_legacy_snapshot_rows()
    if legacy_snapshot_rows:
        raise RuntimeError(
            "UMS-03D must remain additive only; legacy rows must not be migrated"
        )


def downgrade() -> None:
    # Drop child tables before the parent table.
    op.drop_index(
        "ix_memory_provenance_source_thread_id",
        table_name="memory_provenance",
    )
    op.drop_index(
        "ix_memory_provenance_user_source_system",
        table_name="memory_provenance",
    )
    op.drop_index("ix_memory_provenance_memory_id", table_name="memory_provenance")
    op.drop_table("memory_provenance")

    op.drop_index(
        "ix_memory_persona_links_persona_subject_id",
        table_name="memory_persona_links",
    )
    op.drop_index(
        "ix_memory_persona_links_user_id",
        table_name="memory_persona_links",
    )
    op.drop_table("memory_persona_links")

    op.drop_index("ix_memory_records_user_activated_at", table_name="memory_records")
    op.drop_index("ix_memory_records_user_species", table_name="memory_records")
    op.drop_index("ix_memory_records_user_project", table_name="memory_records")
    op.drop_index("ix_memory_records_user_id", table_name="memory_records")
    op.drop_table("memory_records")

    # UMS-03C-B: drop the enabling Project relational target last, after
    # all UMS-03D canonical-memory dependents have been removed. The
    # memory_records composite FK references projects(id, user_id);
    # dropping the unique target first would leave the FK pointing at
    # an unsupported target during the gap.
    op.drop_constraint(
        "uq_projects_id_user_id",
        "projects",
        type_="unique",
    )
