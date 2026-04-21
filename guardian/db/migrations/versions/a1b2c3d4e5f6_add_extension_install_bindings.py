"""add extension install bindings table

Revision ID: a1b2c3d4e5f6
Revises: c1d2e3f4a5b6
Create Date: 2026-04-21 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from guardian.extensions.tokens import (
    EXTENSION_INSTALL_BINDING_SCOPES,
    EXTENSION_INSTALL_BINDING_STATUSES,
)

EXTENSION_INSTALL_BINDING_SCOPE_VALUES_SQL = "','".join(
    sorted(EXTENSION_INSTALL_BINDING_SCOPES)
)
EXTENSION_INSTALL_BINDING_STATUS_VALUES_SQL = "','".join(
    sorted(EXTENSION_INSTALL_BINDING_STATUSES)
)

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_extension_install_bindings",
        sa.Column(
            "binding_id",
            sa.String(length=64),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("account_id", sa.String(length=255), nullable=False),
        sa.Column(
            "registry_entry_id",
            sa.String(length=64),
            sa.ForeignKey(
                "agent_extension_registry_entries.registry_id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "proposal_id",
            sa.String(length=64),
            sa.ForeignKey(
                "agent_extension_proposals.proposal_id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "scope_token",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'project_scoped'"),
        ),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("profile_id", sa.String(length=128), nullable=True),
        sa.Column(
            "account_scope_target_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "binding_status_token",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("bind_reason", sa.Text(), nullable=True),
        sa.Column(
            "bind_notes_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "bind_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "unbind_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("source_thread_id", sa.Integer(), nullable=True),
        sa.Column("source_message_id", sa.BigInteger(), nullable=True),
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
        sa.Column(
            "unbound_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            f"scope_token IN ('{EXTENSION_INSTALL_BINDING_SCOPE_VALUES_SQL}')",
            name="agent_extension_install_bindings_scope_check",
        ),
        sa.CheckConstraint(
            f"binding_status_token IN ('{EXTENSION_INSTALL_BINDING_STATUS_VALUES_SQL}')",
            name="agent_extension_install_bindings_status_check",
        ),
        sa.CheckConstraint(
            """
            (
                scope_token <> 'project_scoped'
                OR (
                    project_id IS NOT NULL
                    AND profile_id IS NULL
                    AND account_scope_target_id IS NULL
                )
            )
            AND (
                scope_token <> 'profile_scoped'
                OR (
                    profile_id IS NOT NULL
                    AND project_id IS NULL
                    AND account_scope_target_id IS NULL
                )
            )
            AND (
                scope_token <> 'account_scoped'
                OR (
                    account_scope_target_id IS NOT NULL
                    AND project_id IS NULL
                    AND profile_id IS NULL
                )
            )
            """.strip(),
            name="agent_extension_install_bindings_scope_target_check",
        ),
    )
    op.create_index(
        "ix_agent_extension_install_bindings_account_created_at",
        "agent_extension_install_bindings",
        ["account_id", "created_at"],
    )
    op.create_index(
        "ix_agent_extension_install_bindings_registry_created_at",
        "agent_extension_install_bindings",
        ["registry_entry_id", "created_at"],
    )
    op.create_index(
        "ix_agent_extension_install_bindings_scope_created_at",
        "agent_extension_install_bindings",
        ["scope_token", "created_at"],
    )
    op.create_index(
        "ix_agent_extension_install_bindings_project_created_at",
        "agent_extension_install_bindings",
        ["project_id", "created_at"],
    )
    op.create_index(
        "ix_agent_extension_install_bindings_profile_created_at",
        "agent_extension_install_bindings",
        ["profile_id", "created_at"],
    )
    op.create_index(
        "ix_agent_extension_install_bindings_account_target_created_at",
        "agent_extension_install_bindings",
        ["account_scope_target_id", "created_at"],
    )
    op.create_index(
        "ix_agent_extension_install_bindings_status_created_at",
        "agent_extension_install_bindings",
        ["binding_status_token", "created_at"],
    )
    op.create_index(
        "uq_agent_extension_install_bindings_active_tuple",
        "agent_extension_install_bindings",
        [
            "account_id",
            "registry_entry_id",
            "scope_token",
            "project_id",
            "profile_id",
            "account_scope_target_id",
        ],
        unique=True,
        postgresql_where=sa.text("binding_status_token = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_agent_extension_install_bindings_active_tuple",
        table_name="agent_extension_install_bindings",
    )
    op.drop_index(
        "ix_agent_extension_install_bindings_status_created_at",
        table_name="agent_extension_install_bindings",
    )
    op.drop_index(
        "ix_agent_extension_install_bindings_account_target_created_at",
        table_name="agent_extension_install_bindings",
    )
    op.drop_index(
        "ix_agent_extension_install_bindings_profile_created_at",
        table_name="agent_extension_install_bindings",
    )
    op.drop_index(
        "ix_agent_extension_install_bindings_project_created_at",
        table_name="agent_extension_install_bindings",
    )
    op.drop_index(
        "ix_agent_extension_install_bindings_scope_created_at",
        table_name="agent_extension_install_bindings",
    )
    op.drop_index(
        "ix_agent_extension_install_bindings_registry_created_at",
        table_name="agent_extension_install_bindings",
    )
    op.drop_index(
        "ix_agent_extension_install_bindings_account_created_at",
        table_name="agent_extension_install_bindings",
    )
    op.drop_table("agent_extension_install_bindings")
