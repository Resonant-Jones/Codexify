"""add account observability persistence foundation

Revision ID: b2c3d4e5f6a7
Revises: a1c2d3e4f5b6
Create Date: 2026-07-25 18:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1c2d3e4f5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "account_observability_invite_links",
        sa.Column("invite_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("campaign_label", sa.String(length=255), nullable=True),
        sa.Column("placement_label", sa.String(length=255), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=255), nullable=False),
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
        sa.CheckConstraint(
            "status IN ('active','disabled','revoked')",
            name="account_observability_invite_status_check",
        ),
        sa.CheckConstraint(
            "((status = 'active' AND disabled_at IS NULL AND revoked_at IS NULL) "
            "OR (status = 'disabled' AND disabled_at IS NOT NULL AND revoked_at IS NULL) "
            "OR (status = 'revoked' AND revoked_at IS NOT NULL))",
            name="account_observability_invite_lifecycle_check",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_account_observability_invites_created_by_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("invite_id"),
        sa.UniqueConstraint(
            "token_hash",
            name="uq_account_observability_invite_links_token_hash",
        ),
    )
    op.create_index(
        "ix_account_observability_invite_links_status_created_at",
        "account_observability_invite_links",
        ["status", "created_at"],
    )

    op.create_table(
        "account_observability_guest_identities",
        sa.Column("guest_id", sa.String(length=36), nullable=False),
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
            ["account_observability_invite_links.invite_id"],
            name="fk_account_observability_guests_first_invite",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("guest_id"),
    )
    op.create_index(
        "ix_account_observability_guest_identities_first_invite_id",
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
        sa.CheckConstraint(
            "attribution_method IS NULL OR attribution_method IN ('first_party_first_touch')",
            name="account_observability_attribution_method_check",
        ),
        sa.CheckConstraint(
            "attribution_confidence IS NULL OR attribution_confidence IN ('verified')",
            name="account_observability_attribution_confidence_check",
        ),
        sa.CheckConstraint(
            "((acquisition_invite_id IS NULL AND attribution_method IS NULL AND attribution_confidence IS NULL) "
            "OR (acquisition_invite_id IS NOT NULL "
            "AND attribution_method = 'first_party_first_touch' "
            "AND attribution_confidence = 'verified'))",
            name="account_observability_attribution_consistency_check",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_account_observability_metadata_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["acquisition_invite_id"],
            ["account_observability_invite_links.invite_id"],
            name="fk_account_observability_metadata_acquisition_invite",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prior_guest_id"],
            ["account_observability_guest_identities.guest_id"],
            name="fk_account_observability_metadata_prior_guest",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "account_observability_presence_sessions",
        sa.Column("presence_session_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=True),
        sa.Column("guest_id", sa.String(length=36), nullable=True),
        sa.Column("invite_id", sa.String(length=36), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("region_code", sa.String(length=64), nullable=True),
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
            "((user_id IS NOT NULL) <> (guest_id IS NOT NULL))",
            name="account_observability_presence_exactly_one_subject_check",
        ),
        sa.CheckConstraint(
            "last_seen_at >= started_at",
            name="account_observability_presence_last_seen_order_check",
        ),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="account_observability_presence_ended_order_check",
        ),
        sa.CheckConstraint(
            "region_code IS NULL OR country_code IS NOT NULL",
            name="account_observability_presence_region_country_check",
        ),
        sa.CheckConstraint(
            "country_code IS NULL OR (length(country_code) = 2 "
            "AND country_code = upper(country_code))",
            name="account_observability_presence_country_code_check",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_account_observability_presence_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["guest_id"],
            ["account_observability_guest_identities.guest_id"],
            name="fk_account_observability_presence_guest",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invite_id"],
            ["account_observability_invite_links.invite_id"],
            name="fk_account_observability_presence_invite",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("presence_session_id"),
    )
    op.create_index(
        "ix_account_observability_presence_sessions_user_last_seen_at",
        "account_observability_presence_sessions",
        ["user_id", "last_seen_at"],
    )
    op.create_index(
        "ix_account_observability_presence_sessions_guest_last_seen_at",
        "account_observability_presence_sessions",
        ["guest_id", "last_seen_at"],
    )
    op.create_index(
        "ix_account_observability_presence_sessions_invite_started_at",
        "account_observability_presence_sessions",
        ["invite_id", "started_at"],
    )
    op.create_index(
        "ix_acct_obs_presence_last_seen_country_region",
        "account_observability_presence_sessions",
        ["last_seen_at", "country_code", "region_code"],
    )


def downgrade() -> None:
    op.drop_table("account_observability_presence_sessions")
    op.drop_table("account_observability_account_metadata")
    op.drop_table("account_observability_guest_identities")
    op.drop_table("account_observability_invite_links")
