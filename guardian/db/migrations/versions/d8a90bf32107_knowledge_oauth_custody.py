"""Durable account-bound Knowledge OAuth custody, no credential backfill.

Revision ID: d8a90bf32107
Revises: c13f0713a901
"""

from alembic import op
import sqlalchemy as sa

revision = "d8a90bf32107"
down_revision = "c13f0713a901"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "knowledge_oauth_credentials",
        sa.CheckConstraint(
            "provider IN ('notion', 'github')", name="ck_knowledge_oauth_provider"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'connected', 'disconnected', 'reconnect_required')",
            name="ck_knowledge_oauth_status",
        ),
        sa.Column("user_id", sa.String(255), primary_key=True),
        sa.Column("provider", sa.String(16), primary_key=True),
        sa.Column("generation", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("encrypted_access_token", sa.Text()),
        sa.Column("encrypted_refresh_token", sa.Text()),
        sa.Column("expires_at", sa.Float()),
        sa.Column("refresh_claim", sa.String(64)),
        sa.Column("provider_metadata", sa.JSON(), nullable=False),
        sa.Column("repositories", sa.JSON(), nullable=False),
    )
    op.create_table(
        "knowledge_oauth_flows",
        sa.CheckConstraint(
            "provider IN ('notion', 'github')", name="ck_knowledge_oauth_flow_provider"
        ),
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("generation", sa.String(64), nullable=False),
        sa.Column("browser_binding_hash", sa.String(64), nullable=False),
        sa.Column("encrypted_verifier", sa.Text(), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
        sa.Column("consumed", sa.Boolean(), nullable=False),
        sa.Column("repositories", sa.JSON(), nullable=False),
    )


def downgrade():
    op.drop_table("knowledge_oauth_flows")
    op.drop_table("knowledge_oauth_credentials")
