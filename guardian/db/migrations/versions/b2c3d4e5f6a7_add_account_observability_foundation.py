"""add account observability persistence foundation

Revision ID: b2c3d4e5f6a7
Revises: a1c2d3e4f5b6
Create Date: 2026-07-24 00:00:00.000000

This migration creates dormant Guardian-owned schema only. It does not add
runtime collection, routes, workers, seed rows, or backfills.
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1c2d3e4f5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the four account-observability foundation tables."""

    op.create_table(
        "account_observability_invite_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("campaign_label", sa.String(length=255), nullable=True),
        sa.Column("placement_label", sa.String(length=255), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_account_observability_invite_links_created_by_user_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('active', 'disabled', 'revoked')",
            name="ck_account_observability_invite_links_status",
        ),
        sa.CheckConstraint(
            "(status = 'active' AND disabled_at IS NULL AND revoked_at IS NULL) "
            "OR (status = 'disabled' AND disabled_at IS NOT NULL AND revoked_at IS NULL) "
            "OR (status = 'revoked' AND revoked_at IS NOT NULL AND disabled_at IS NULL)",
            name="ck_account_observability_invite_links_lifecycle_timestamps",
        ),
    )
    op.create_index(
        "uq_account_observability_invite_links_token_hash",
        "account_observability_invite_links",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_account_observability_invite_links_status_created_at",
        "account_observability_invite_links",
        ["status", "created_at"],
    )

    op.create_table(
        "account_observability_guest_identities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("first_invite_id", sa.String(length=36), nullable=True),
        sa.Column("converted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["first_invite_id"],
            ["account_observability_invite_links.id"],
            name="fk_account_observability_guest_identities_first_invite_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_account_observability_guest_identities_first_invite",
        "account_observability_guest_identities",
        ["first_invite_id"],
    )

    op.create_table(
        "account_observability_account_metadata",
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("registered_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("acquisition_invite_id", sa.String(length=36), nullable=True),
        sa.Column("prior_guest_id", sa.String(length=36), nullable=True),
        sa.Column("attribution_method", sa.String(length=64), nullable=True),
        sa.Column(
            "attribution_confidence", sa.String(length=32), nullable=True
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_account_observability_account_metadata_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["acquisition_invite_id"],
            ["account_observability_invite_links.id"],
            name="fk_account_observability_account_metadata_acquisition_invite_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prior_guest_id"],
            ["account_observability_guest_identities.id"],
            name="fk_account_observability_account_metadata_prior_guest_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("user_id"),
        sa.CheckConstraint(
            "(acquisition_invite_id IS NULL "
            "AND prior_guest_id IS NULL "
            "AND attribution_method IS NULL "
            "AND attribution_confidence IS NULL) "
            "OR (acquisition_invite_id IS NOT NULL "
            "AND attribution_method = 'first_party_first_touch' "
            "AND attribution_confidence = 'verified')",
            name="ck_account_observability_account_metadata_attribution",
        ),
    )
    op.create_index(
        "ix_account_observability_account_metadata_acquisition_invite",
        "account_observability_account_metadata",
        ["acquisition_invite_id"],
    )

    op.create_table(
        "account_observability_presence_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=True),
        sa.Column("guest_id", sa.String(length=36), nullable=True),
        sa.Column("invite_id", sa.String(length=36), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("region_code", sa.String(length=32), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_account_observability_presence_sessions_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["guest_id"],
            ["account_observability_guest_identities.id"],
            name="fk_account_observability_presence_sessions_guest_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invite_id"],
            ["account_observability_invite_links.id"],
            name="fk_account_observability_presence_sessions_invite_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "(user_id IS NOT NULL AND guest_id IS NULL) "
            "OR (user_id IS NULL AND guest_id IS NOT NULL)",
            name="ck_account_observability_presence_sessions_exactly_one_subject",
        ),
        sa.CheckConstraint(
            "last_seen_at >= started_at",
            name="ck_ao_presence_sessions_last_seen_after_start",
        ),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="ck_ao_presence_sessions_end_after_start",
        ),
        sa.CheckConstraint(
            "region_code IS NULL OR country_code IS NOT NULL",
            name="ck_ao_presence_sessions_region_requires_country",
        ),
        sa.CheckConstraint(
            "country_code IS NULL OR length(country_code) = 2",
            name="ck_ao_presence_sessions_country_code_length",
        ),
    )
    op.create_index(
        "ix_account_observability_presence_sessions_user_last_seen",
        "account_observability_presence_sessions",
        ["user_id", "last_seen_at"],
    )
    op.create_index(
        "ix_account_observability_presence_sessions_guest_last_seen",
        "account_observability_presence_sessions",
        ["guest_id", "last_seen_at"],
    )
    op.create_index(
        "ix_account_observability_presence_sessions_invite_started",
        "account_observability_presence_sessions",
        ["invite_id", "started_at"],
    )
    op.create_index(
        "ix_account_observability_presence_sessions_started_geo",
        "account_observability_presence_sessions",
        ["started_at", "country_code", "region_code"],
    )


def downgrade() -> None:
    """Remove only the four account-observability foundation tables."""

    for index_name in (
        "ix_account_observability_presence_sessions_started_geo",
        "ix_account_observability_presence_sessions_invite_started",
        "ix_account_observability_presence_sessions_guest_last_seen",
        "ix_account_observability_presence_sessions_user_last_seen",
    ):
        op.drop_index(
            index_name, table_name="account_observability_presence_sessions"
        )
    op.drop_index(
        "ix_account_observability_account_metadata_acquisition_invite",
        table_name="account_observability_account_metadata",
    )
    op.drop_index(
        "ix_account_observability_guest_identities_first_invite",
        table_name="account_observability_guest_identities",
    )
    op.drop_index(
        "ix_account_observability_invite_links_status_created_at",
        table_name="account_observability_invite_links",
    )
    op.drop_index(
        "uq_account_observability_invite_links_token_hash",
        table_name="account_observability_invite_links",
    )

    op.drop_table("account_observability_presence_sessions")
    op.drop_table("account_observability_account_metadata")
    op.drop_table("account_observability_guest_identities")
    op.drop_table("account_observability_invite_links")
