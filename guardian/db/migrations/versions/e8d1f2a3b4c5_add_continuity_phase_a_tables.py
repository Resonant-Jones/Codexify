"""add continuity Phase A tables: context_packets, reality_states,
reality_commits, and state_packet_links

Revision ID: e8d1f2a3b4c5
Revises: b6a7c8d9e0f1
Create Date: 2026-06-25 00:00:00.000000

This migration creates the four Phase A continuity tables only.  Phase B
normalisation tables (open_loops, rejected_paths, decisions, compiler_runs,
project_pulse_snapshots) are explicitly excluded.

No runtime writes, compiler persistence, routes, workers, graph writes,
browser capture, sync, export/restore, or provider-routing behaviour is
introduced by this migration.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "e8d1f2a3b4c5"
down_revision: str | Sequence[str] | None = "b6a7c8d9e0f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ── continuity_context_packets ──────────────────────────────────────────────

_CONTEXT_PACKET_INDEXES: list[tuple[str, list[str] | str, dict]] = [
    ("ix_cty_packets_project_created", ["project_id", "created_at"], {}),
    ("ix_cty_packets_thread_created", ["thread_id", "created_at"], {}),
    ("ix_cty_packets_user_created", ["user_id", "created_at"], {}),
    ("ix_cty_packets_kind_created", ["kind", "created_at"], {}),
    ("ix_cty_packets_retention", ["retention"], {}),
    ("ix_cty_packets_sensitivity", ["sensitivity"], {}),
]

# ── continuity_reality_states ───────────────────────────────────────────────

_REALITY_STATE_INDEXES: list[tuple[str, list[str] | str, dict]] = [
    ("ix_cty_states_scope_compiled", ["scope", "compiled_at"], {}),
    ("ix_cty_states_project_compiled", ["project_id", "compiled_at"], {}),
    ("ix_cty_states_thread_compiled", ["thread_id", "compiled_at"], {}),
    ("ix_cty_states_user_compiled", ["user_id", "compiled_at"], {}),
    ("ix_cty_states_expires", ["expires_or_decays_at"], {}),
]

# ── continuity_reality_commits ──────────────────────────────────────────────

_REALITY_COMMIT_INDEXES: list[tuple[str, list[str] | str, dict]] = [
    ("ix_cty_commits_project_created", ["project_id", "created_at"], {}),
    ("ix_cty_commits_thread_created", ["thread_id", "created_at"], {}),
    ("ix_cty_commits_scope_created", ["scope", "created_at"], {}),
    ("ix_cty_commits_kind_created", ["kind", "created_at"], {}),
    ("ix_cty_commits_trigger_created", ["trigger", "created_at"], {}),
    ("ix_cty_commits_new_state", ["new_state_id"], {}),
]


def _partial_active_ix(table: str, col: str) -> None:
    """Create a partial index for non-deleted rows on *table*."""
    op.create_index(
        f"ix_{table}_active",
        table,
        [col],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def _drop_indexes(
    table: str,
    name_col_tuples: list[tuple[str, list[str] | str]],
) -> None:
    for name, _cols in name_col_tuples:
        op.drop_index(name, table_name=table)


# ─────────────────────────────────────────────────────────────────────────────


def upgrade() -> None:
    # ── continuity_context_packets ──────────────────────────────────────────

    op.create_table(
        "continuity_context_packets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("project_id", sa.String(128), nullable=True),
        sa.Column("thread_id", sa.String(128), nullable=True),
        sa.Column("task_id", sa.String(128), nullable=True),
        sa.Column("tab_id", sa.String(128), nullable=True),
        sa.Column("persona_id", sa.String(128), nullable=True),
        sa.Column("node_id", sa.String(128), nullable=True),
        sa.Column("team_id", sa.String(128), nullable=True),
        sa.Column("dyad_id", sa.String(128), nullable=True),
        sa.Column("source_system", sa.String(128), nullable=False),
        sa.Column("source_plugin", sa.String(128), nullable=True),
        sa.Column("source_provider", sa.String(128), nullable=True),
        sa.Column("origin_ref", sa.String(256), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload_json", JSONB, nullable=False),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column("provenance_json", JSONB, nullable=False),
        sa.Column("sensitivity", sa.String(32), nullable=False),
        sa.Column("retention", sa.String(32), nullable=False),
        sa.Column("integrity_json", JSONB, nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    for name, cols, kwargs in _CONTEXT_PACKET_INDEXES:
        op.create_index(name, "continuity_context_packets", cols, **kwargs)
    _partial_active_ix("continuity_context_packets", "created_at")

    # ── continuity_reality_states ───────────────────────────────────────────

    op.create_table(
        "continuity_reality_states",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(32), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("project_id", sa.String(128), nullable=True),
        sa.Column("thread_id", sa.String(128), nullable=True),
        sa.Column("task_id", sa.String(128), nullable=True),
        sa.Column("node_id", sa.String(128), nullable=True),
        sa.Column("team_id", sa.String(128), nullable=True),
        sa.Column("dyad_id", sa.String(128), nullable=True),
        sa.Column("compiled_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("active_branch", sa.String(256), nullable=True),
        sa.Column("source_packet_ids_json", JSONB, nullable=False),
        sa.Column("state_json", JSONB, nullable=False),
        sa.Column("accepted_decisions_json", JSONB, nullable=True),
        sa.Column("open_loops_json", JSONB, nullable=True),
        sa.Column("rejected_paths_json", JSONB, nullable=True),
        sa.Column("active_artifacts_json", JSONB, nullable=True),
        sa.Column("assumptions_json", JSONB, nullable=True),
        sa.Column("risks_json", JSONB, nullable=True),
        sa.Column("next_actions_json", JSONB, nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("provenance_json", JSONB, nullable=False),
        sa.Column("expires_or_decays_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    for name, cols, kwargs in _REALITY_STATE_INDEXES:
        op.create_index(name, "continuity_reality_states", cols, **kwargs)
    _partial_active_ix("continuity_reality_states", "compiled_at")

    # ── continuity_reality_commits ──────────────────────────────────────────

    op.create_table(
        "continuity_reality_commits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("trigger", sa.String(64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("project_id", sa.String(128), nullable=True),
        sa.Column("thread_id", sa.String(128), nullable=True),
        sa.Column("task_id", sa.String(128), nullable=True),
        sa.Column("node_id", sa.String(128), nullable=True),
        sa.Column("team_id", sa.String(128), nullable=True),
        sa.Column("dyad_id", sa.String(128), nullable=True),
        sa.Column("source_packet_ids_json", JSONB, nullable=False),
        sa.Column("previous_state_id", sa.String(36), nullable=True),
        sa.Column("new_state_id", sa.String(36), nullable=True),
        sa.Column("provenance_json", JSONB, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    for name, cols, kwargs in _REALITY_COMMIT_INDEXES:
        op.create_index(name, "continuity_reality_commits", cols, **kwargs)
    _partial_active_ix("continuity_reality_commits", "created_at")

    # ── continuity_state_packet_links ───────────────────────────────────────

    op.create_table(
        "continuity_state_packet_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("state_id", sa.String(36), nullable=False),
        sa.Column("packet_id", sa.String(36), nullable=False),
        sa.Column("relationship", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False
        ),
        sa.UniqueConstraint(
            "state_id",
            "packet_id",
            "relationship",
            name="uq_cty_state_packet_link",
        ),
    )

    op.create_index(
        "ix_cty_links_state_id",
        "continuity_state_packet_links",
        ["state_id"],
    )
    op.create_index(
        "ix_cty_links_packet_id",
        "continuity_state_packet_links",
        ["packet_id"],
    )
    op.create_index(
        "ix_cty_links_relationship",
        "continuity_state_packet_links",
        ["relationship"],
    )

    # NOTE: Foreign-key constraints to continuity_reality_states.id and
    # continuity_context_packets.id are intentionally deferred.  Delete
    # semantics (cascade vs. restrict vs. set-null) have not been decided.
    # A future migration will add FKs when delete policy is explicit.


def downgrade() -> None:
    op.drop_table("continuity_state_packet_links")
    op.drop_table("continuity_reality_commits")
    op.drop_table("continuity_reality_states")
    op.drop_table("continuity_context_packets")
