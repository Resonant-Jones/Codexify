"""add inference provider state tables

Revision ID: 62127ee9a537
Revises: a7c9d1e2f3b4
Create Date: 2026-02-17 12:49:18.828898

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "62127ee9a537"
down_revision: Union[str, Sequence[str], None] = "a7c9d1e2f3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "inference_providers",
        sa.Column("provider_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("provider_type", sa.Text(), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("100"),
        ),
        sa.Column("default_model_id", sa.Text(), nullable=True),
        sa.Column(
            "capabilities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True
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
            "priority >= 0",
            name="ck_inference_providers_priority_nonnegative",
        ),
    )
    op.create_index(
        "ix_inference_providers_enabled",
        "inference_providers",
        ["enabled"],
        unique=False,
    )
    op.create_index(
        "ix_inference_providers_priority",
        "inference_providers",
        ["priority"],
        unique=False,
    )

    op.create_table(
        "inference_provider_runtime",
        sa.Column(
            "provider_id",
            sa.Text(),
            sa.ForeignKey(
                "inference_providers.provider_id",
                ondelete="CASCADE",
            ),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "health_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'unknown'"),
        ),
        sa.Column(
            "consecutive_failures",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "last_success_at", sa.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column(
            "last_failure_at", sa.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("cooldown_until", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("avg_latency_ms", sa.Float(), nullable=True),
        sa.Column("error_rate", sa.Float(), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "health_status IN ('unknown','healthy','degraded','unavailable')",
            name="ck_inference_provider_runtime_health_status",
        ),
        sa.CheckConstraint(
            "consecutive_failures >= 0",
            name="ck_inference_provider_runtime_consecutive_failures_nonnegative",
        ),
        sa.CheckConstraint(
            "error_rate IS NULL OR (error_rate >= 0 AND error_rate <= 1)",
            name="ck_inference_provider_runtime_error_rate_bounds",
        ),
    )
    op.create_index(
        "ix_inference_provider_runtime_health_status",
        "inference_provider_runtime",
        ["health_status"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_inference_provider_runtime_health_status",
        table_name="inference_provider_runtime",
    )
    op.drop_table("inference_provider_runtime")
    op.drop_index(
        "ix_inference_providers_priority",
        table_name="inference_providers",
    )
    op.drop_index(
        "ix_inference_providers_enabled",
        table_name="inference_providers",
    )
    op.drop_table("inference_providers")
