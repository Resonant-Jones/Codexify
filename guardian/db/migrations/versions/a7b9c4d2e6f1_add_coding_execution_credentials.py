"""add scoped coding execution credentials and lease receipts

Revision ID: a7b9c4d2e6f1
Revises: c9f3e2a7b601
Create Date: 2026-09-29
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a7b9c4d2e6f1"
down_revision: str | Sequence[str] | None = "c9f3e2a7b601"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "coding_execution_credentials",
        sa.Column("credential_ref", sa.String(length=64), primary_key=True),
        sa.Column("owner_scope", sa.String(length=16), nullable=False),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column(
            "credential_type",
            sa.String(length=32),
            nullable=False,
            server_default="api_key",
        ),
        sa.Column("funding_route", sa.String(length=32), nullable=False),
        sa.Column("encrypted_secret", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="active"
        ),
        sa.Column(
            "allowed_account_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "allowed_model_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("usage_policy_ref", sa.String(length=128), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
            "owner_scope IN ('account', 'service', 'operator')",
            name="ck_coding_execution_credentials_owner_scope",
        ),
        sa.CheckConstraint(
            "credential_type = 'api_key'",
            name="ck_coding_execution_credentials_type",
        ),
        sa.CheckConstraint(
            "funding_route IN ('user_byok', 'codexify_included', "
            "'codexify_metered', 'local_self_hosted')",
            name="ck_coding_execution_credentials_funding_route",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'revoked')",
            name="ck_coding_execution_credentials_status",
        ),
        sa.CheckConstraint(
            "(status = 'active' AND encrypted_secret IS NOT NULL) OR "
            "(status = 'revoked' AND encrypted_secret IS NULL)",
            name="ck_coding_execution_credentials_secret_status",
        ),
    )
    op.create_index(
        "ix_coding_execution_credentials_owner_provider",
        "coding_execution_credentials",
        ["owner_scope", "owner_id", "provider_id"],
    )
    op.create_table(
        "coding_execution_credential_leases",
        sa.Column("lease_id", sa.String(length=64), primary_key=True),
        sa.Column("binding_id", sa.String(length=64), nullable=False),
        sa.Column("attempt_id", sa.String(length=255), nullable=False),
        sa.Column("attempt_index", sa.Integer(), nullable=False),
        sa.Column("credential_ref", sa.String(length=64), nullable=False),
        sa.Column("owner_scope", sa.String(length=16), nullable=False),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column("account_id", sa.String(length=255), nullable=False),
        sa.Column(
            "issued_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint(
            "attempt_index > 0",
            name="ck_coding_execution_credential_leases_attempt_index_positive",
        ),
        sa.ForeignKeyConstraint(
            ["credential_ref"],
            ["coding_execution_credentials.credential_ref"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "binding_id",
            "attempt_index",
            name="uq_coding_execution_credential_lease_binding_attempt",
        ),
    )
    op.create_index(
        "ix_coding_execution_credential_leases_credential_ref",
        "coding_execution_credential_leases",
        ["credential_ref"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_coding_execution_credential_leases_credential_ref",
        table_name="coding_execution_credential_leases",
    )
    op.drop_table("coding_execution_credential_leases")
    op.drop_index(
        "ix_coding_execution_credentials_owner_provider",
        table_name="coding_execution_credentials",
    )
    op.drop_table("coding_execution_credentials")
