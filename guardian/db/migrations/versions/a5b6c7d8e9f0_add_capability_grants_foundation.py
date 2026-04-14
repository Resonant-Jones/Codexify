"""add capability grants foundation

Revision ID: a5b6c7d8e9f0
Revises: e3f2a1b4c5d6
Create Date: 2026-04-13 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from guardian.core.capability_tokens import (
    CapabilityFamily,
    CapabilityGrantKind,
    CapabilityGrantScope,
    CapabilityGrantStatus,
)

CAPABILITY_FAMILY_VALUES_SQL = "','".join(
    family.value for family in CapabilityFamily
)
CAPABILITY_GRANT_SCOPE_VALUES_SQL = "','".join(
    scope.value for scope in CapabilityGrantScope
)
CAPABILITY_GRANT_KIND_VALUES_SQL = "','".join(
    kind.value for kind in CapabilityGrantKind
)
CAPABILITY_GRANT_STATUS_VALUES_SQL = "','".join(
    status.value for status in CapabilityGrantStatus
)

# revision identifiers, used by Alembic.
revision: str = "a5b6c7d8e9f0"
down_revision: str | Sequence[str] | None = "e3f2a1b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return index_name in {
        idx["name"] for idx in inspector.get_indexes(table_name)
    }


def upgrade() -> None:
    """Upgrade schema."""
    if not _has_table("capability_tiers"):
        op.create_table(
            "capability_tiers",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column(
                "capability_family",
                sa.String(length=64),
                nullable=False,
            ),
            sa.Column("tier_key", sa.String(length=128), nullable=False),
            sa.Column("display_name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "capabilities_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column(
                "limits_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "priority",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("100"),
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
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
                f"capability_family IN ('{CAPABILITY_FAMILY_VALUES_SQL}')",
                name="capability_tiers_capability_family_check",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "tier_key", name="uq_capability_tiers_tier_key"
            ),
        )
    if not _has_index("capability_tiers", "ix_capability_tiers_family_active"):
        op.create_index(
            "ix_capability_tiers_family_active",
            "capability_tiers",
            ["capability_family", "is_active"],
            unique=False,
        )
    if not _has_index("capability_tiers", "ix_capability_tiers_priority"):
        op.create_index(
            "ix_capability_tiers_priority",
            "capability_tiers",
            ["priority"],
            unique=False,
        )

    if not _has_table("capability_grants"):
        op.create_table(
            "capability_grants",
            sa.Column(
                "id", sa.BigInteger(), autoincrement=True, nullable=False
            ),
            sa.Column("account_id", sa.String(length=255), nullable=False),
            sa.Column("tier_id", sa.Integer(), nullable=False),
            sa.Column(
                "grant_scope",
                sa.String(length=32),
                nullable=False,
                server_default=CapabilityGrantScope.ACCOUNT.value,
            ),
            sa.Column(
                "grant_kind",
                sa.String(length=32),
                nullable=False,
                server_default=CapabilityGrantKind.PERMANENT.value,
            ),
            sa.Column(
                "grant_status",
                sa.String(length=32),
                nullable=False,
                server_default=CapabilityGrantStatus.ACTIVE.value,
            ),
            sa.Column(
                "starts_at",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "ends_at",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "issued_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "revoked_at",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "provenance_source",
                sa.String(length=64),
                nullable=True,
            ),
            sa.Column(
                "provenance_ref",
                sa.String(length=255),
                nullable=True,
            ),
            sa.Column(
                "provenance_reason",
                sa.Text(),
                nullable=True,
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
                f"grant_scope IN ('{CAPABILITY_GRANT_SCOPE_VALUES_SQL}')",
                name="capability_grants_scope_check",
            ),
            sa.CheckConstraint(
                f"grant_kind IN ('{CAPABILITY_GRANT_KIND_VALUES_SQL}')",
                name="capability_grants_kind_check",
            ),
            sa.CheckConstraint(
                f"grant_status IN ('{CAPABILITY_GRANT_STATUS_VALUES_SQL}')",
                name="capability_grants_status_check",
            ),
            sa.ForeignKeyConstraint(
                ["account_id"],
                ["authenticated_principals.account_id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["tier_id"], ["capability_tiers.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index(
        "capability_grants", "ix_capability_grants_account_status"
    ):
        op.create_index(
            "ix_capability_grants_account_status",
            "capability_grants",
            ["account_id", "grant_status"],
            unique=False,
        )
    if not _has_index(
        "capability_grants", "ix_capability_grants_account_ends_at"
    ):
        op.create_index(
            "ix_capability_grants_account_ends_at",
            "capability_grants",
            ["account_id", "ends_at"],
            unique=False,
        )
    if not _has_index("capability_grants", "ix_capability_grants_tier_id"):
        op.create_index(
            "ix_capability_grants_tier_id",
            "capability_grants",
            ["tier_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    if _has_table("capability_grants"):
        if _has_index("capability_grants", "ix_capability_grants_tier_id"):
            op.drop_index(
                "ix_capability_grants_tier_id",
                table_name="capability_grants",
            )
        if _has_index(
            "capability_grants", "ix_capability_grants_account_ends_at"
        ):
            op.drop_index(
                "ix_capability_grants_account_ends_at",
                table_name="capability_grants",
            )
        if _has_index(
            "capability_grants", "ix_capability_grants_account_status"
        ):
            op.drop_index(
                "ix_capability_grants_account_status",
                table_name="capability_grants",
            )
        op.drop_table("capability_grants")

    if _has_table("capability_tiers"):
        if _has_index("capability_tiers", "ix_capability_tiers_priority"):
            op.drop_index(
                "ix_capability_tiers_priority",
                table_name="capability_tiers",
            )
        if _has_index("capability_tiers", "ix_capability_tiers_family_active"):
            op.drop_index(
                "ix_capability_tiers_family_active",
                table_name="capability_tiers",
            )
        op.drop_table("capability_tiers")
