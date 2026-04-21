"""add agent extension proposals table

Revision ID: f9a1b2c3d4e5
Revises: a5b6c7d8e9f0
Create Date: 2026-04-20 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from guardian.extensions.tokens import (
    EXTENSION_PROPOSAL_SCOPES,
    EXTENSION_PROPOSAL_STATUSES,
    EXTENSION_TARGET_SURFACES,
)

EXTENSION_TARGET_SURFACE_VALUES_SQL = "','".join(
    sorted(EXTENSION_TARGET_SURFACES)
)
EXTENSION_PROPOSAL_SCOPE_VALUES_SQL = "','".join(
    sorted(EXTENSION_PROPOSAL_SCOPES)
)
EXTENSION_PROPOSAL_STATUS_VALUES_SQL = "','".join(
    sorted(EXTENSION_PROPOSAL_STATUSES)
)

# revision identifiers, used by Alembic.
revision: str = "f9a1b2c3d4e5"
down_revision: str | Sequence[str] | None = "a5b6c7d8e9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agent_extension_proposals",
        sa.Column(
            "proposal_id",
            sa.String(length=64),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("account_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("profile_id", sa.String(length=128), nullable=True),
        sa.Column("source_thread_id", sa.Integer(), nullable=True),
        sa.Column("source_message_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "target_surface_token",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "scope_token",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'project_scoped'"),
        ),
        sa.Column(
            "status_token",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column(
            "requested_permissions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "declared_dependencies_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "rollback_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "test_evidence_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "manifest_json",
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
            name="agent_extension_proposals_target_surface_check",
        ),
        sa.CheckConstraint(
            f"scope_token IN ('{EXTENSION_PROPOSAL_SCOPE_VALUES_SQL}')",
            name="agent_extension_proposals_scope_check",
        ),
        sa.CheckConstraint(
            f"status_token IN ('{EXTENSION_PROPOSAL_STATUS_VALUES_SQL}')",
            name="agent_extension_proposals_status_check",
        ),
    )
    op.create_index(
        "ix_agent_extension_proposals_account_created_at",
        "agent_extension_proposals",
        ["account_id", "created_at"],
    )
    op.create_index(
        "ix_agent_extension_proposals_project_created_at",
        "agent_extension_proposals",
        ["project_id", "created_at"],
    )
    op.create_index(
        "ix_agent_extension_proposals_profile_created_at",
        "agent_extension_proposals",
        ["profile_id", "created_at"],
    )
    op.create_index(
        "ix_agent_extension_proposals_status_created_at",
        "agent_extension_proposals",
        ["status_token", "created_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_agent_extension_proposals_status_created_at",
        table_name="agent_extension_proposals",
    )
    op.drop_index(
        "ix_agent_extension_proposals_profile_created_at",
        table_name="agent_extension_proposals",
    )
    op.drop_index(
        "ix_agent_extension_proposals_project_created_at",
        table_name="agent_extension_proposals",
    )
    op.drop_index(
        "ix_agent_extension_proposals_account_created_at",
        table_name="agent_extension_proposals",
    )
    op.drop_table("agent_extension_proposals")
