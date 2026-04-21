"""add extension registry entries tables

Revision ID: c1d2e3f4a5b6
Revises: f9a1b2c3d4e5
Create Date: 2026-04-21 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from guardian.extensions.tokens import (
    CAPABILITY_ENTRY_PROVENANCE_CLASSES,
    CAPABILITY_REGISTRY_STATUSES,
    EXTENSION_PROPOSAL_SCOPES,
    EXTENSION_TARGET_SURFACES,
    INSTALL_GATE_DECISION_TOKENS,
)

INSTALL_GATE_DECISION_VALUES_SQL = "','".join(
    sorted(INSTALL_GATE_DECISION_TOKENS)
)
CAPABILITY_REGISTRY_STATUS_VALUES_SQL = "','".join(
    sorted(CAPABILITY_REGISTRY_STATUSES)
)
CAPABILITY_ENTRY_PROVENANCE_CLASS_VALUES_SQL = "','".join(
    sorted(CAPABILITY_ENTRY_PROVENANCE_CLASSES)
)
EXTENSION_TARGET_SURFACE_VALUES_SQL = "','".join(
    sorted(EXTENSION_TARGET_SURFACES)
)
EXTENSION_PROPOSAL_SCOPE_VALUES_SQL = "','".join(
    sorted(EXTENSION_PROPOSAL_SCOPES)
)

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: str | Sequence[str] | None = "f9a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agent_extension_install_gate_decisions",
        sa.Column(
            "decision_id",
            sa.String(length=64),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("account_id", sa.String(length=255), nullable=False),
        sa.Column(
            "proposal_id",
            sa.String(length=64),
            sa.ForeignKey(
                "agent_extension_proposals.proposal_id", ondelete="CASCADE"
            ),
            nullable=False,
        ),
        sa.Column(
            "decision_token",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'approved'"),
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "notes_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "requested_permissions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "approved_permissions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
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
        sa.CheckConstraint(
            f"decision_token IN ('{INSTALL_GATE_DECISION_VALUES_SQL}')",
            name="agent_extension_install_gate_decisions_decision_check",
        ),
    )
    op.create_index(
        "ix_agent_extension_install_gate_decisions_account_created_at",
        "agent_extension_install_gate_decisions",
        ["account_id", "created_at"],
    )
    op.create_index(
        "ix_agent_extension_install_gate_decisions_proposal_created_at",
        "agent_extension_install_gate_decisions",
        ["proposal_id", "created_at"],
    )
    op.create_index(
        "ix_agent_extension_install_gate_decisions_decision_created_at",
        "agent_extension_install_gate_decisions",
        ["decision_token", "created_at"],
    )

    op.create_table(
        "agent_extension_registry_entries",
        sa.Column(
            "registry_id",
            sa.String(length=64),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("account_id", sa.String(length=255), nullable=False),
        sa.Column(
            "proposal_id",
            sa.String(length=64),
            sa.ForeignKey(
                "agent_extension_proposals.proposal_id", ondelete="CASCADE"
            ),
            nullable=False,
        ),
        sa.Column(
            "decision_id",
            sa.String(length=64),
            sa.ForeignKey(
                "agent_extension_install_gate_decisions.decision_id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("profile_id", sa.String(length=128), nullable=True),
        sa.Column("source_thread_id", sa.Integer(), nullable=True),
        sa.Column("source_message_id", sa.BigInteger(), nullable=True),
        sa.Column("target_surface_token", sa.String(length=64), nullable=False),
        sa.Column(
            "scope_token",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'project_scoped'"),
        ),
        sa.Column(
            "status_token",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'registered'"),
        ),
        sa.Column(
            "requested_permissions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "approved_permissions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "manifest_snapshot_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "registration_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "provenance_class_token",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'proposal_approval'"),
        ),
        sa.Column(
            "provenance_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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
        sa.CheckConstraint(
            f"target_surface_token IN ('{EXTENSION_TARGET_SURFACE_VALUES_SQL}')",
            name="agent_extension_registry_entries_target_surface_check",
        ),
        sa.CheckConstraint(
            f"scope_token IN ('{EXTENSION_PROPOSAL_SCOPE_VALUES_SQL}')",
            name="agent_extension_registry_entries_scope_check",
        ),
        sa.CheckConstraint(
            f"status_token IN ('{CAPABILITY_REGISTRY_STATUS_VALUES_SQL}')",
            name="agent_extension_registry_entries_status_check",
        ),
        sa.CheckConstraint(
            f"provenance_class_token IN ('{CAPABILITY_ENTRY_PROVENANCE_CLASS_VALUES_SQL}')",
            name="agent_extension_registry_entries_provenance_class_check",
        ),
    )
    op.create_index(
        "ix_agent_extension_registry_entries_account_created_at",
        "agent_extension_registry_entries",
        ["account_id", "created_at"],
    )
    op.create_index(
        "ix_agent_extension_registry_entries_proposal_created_at",
        "agent_extension_registry_entries",
        ["proposal_id", "created_at"],
    )
    op.create_index(
        "ix_agent_extension_registry_entries_project_created_at",
        "agent_extension_registry_entries",
        ["project_id", "created_at"],
    )
    op.create_index(
        "ix_agent_extension_registry_entries_profile_created_at",
        "agent_extension_registry_entries",
        ["profile_id", "created_at"],
    )
    op.create_index(
        "ix_agent_extension_registry_entries_status_created_at",
        "agent_extension_registry_entries",
        ["status_token", "created_at"],
    )
    op.create_index(
        "ix_agent_extension_registry_entries_decision_created_at",
        "agent_extension_registry_entries",
        ["decision_id", "created_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_agent_extension_registry_entries_decision_created_at",
        table_name="agent_extension_registry_entries",
    )
    op.drop_index(
        "ix_agent_extension_registry_entries_status_created_at",
        table_name="agent_extension_registry_entries",
    )
    op.drop_index(
        "ix_agent_extension_registry_entries_profile_created_at",
        table_name="agent_extension_registry_entries",
    )
    op.drop_index(
        "ix_agent_extension_registry_entries_project_created_at",
        table_name="agent_extension_registry_entries",
    )
    op.drop_index(
        "ix_agent_extension_registry_entries_proposal_created_at",
        table_name="agent_extension_registry_entries",
    )
    op.drop_index(
        "ix_agent_extension_registry_entries_account_created_at",
        table_name="agent_extension_registry_entries",
    )
    op.drop_table("agent_extension_registry_entries")

    op.drop_index(
        "ix_agent_extension_install_gate_decisions_decision_created_at",
        table_name="agent_extension_install_gate_decisions",
    )
    op.drop_index(
        "ix_agent_extension_install_gate_decisions_proposal_created_at",
        table_name="agent_extension_install_gate_decisions",
    )
    op.drop_index(
        "ix_agent_extension_install_gate_decisions_account_created_at",
        table_name="agent_extension_install_gate_decisions",
    )
    op.drop_table("agent_extension_install_gate_decisions")
