"""Add observe-only, account-owned inference attempt metering.

Revision ID: d91e4fa6702b
Revises: a3115f64dda8
Create Date: 2026-11-01
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "d91e4fa6702b"
down_revision = "a3115f64dda8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inference_usage_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "account_id", sa.String(length=255),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "thread_id", sa.Integer(),
            sa.ForeignKey("chat_threads.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("request_id", sa.String(length=255), nullable=False),
        sa.Column("provider_attempt_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("provider_request_id", sa.String(length=128)),
        sa.Column("input_tokens", sa.BigInteger()),
        sa.Column("output_tokens", sa.BigInteger()),
        sa.Column("cached_input_tokens", sa.BigInteger()),
        sa.Column("total_tokens", sa.BigInteger()),
        sa.Column("usage_source", sa.String(length=32), nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(18, 9)),
        sa.Column("cost_source", sa.String(length=32), nullable=False),
        sa.Column(
            "price_snapshot", JSONB(), nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "recorded_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.UniqueConstraint(
            "account_id", "provider_attempt_id",
            name="uq_inference_usage_account_attempt",
        ),
        sa.CheckConstraint(
            "usage_source IN ('provider_reported','partial','unavailable')",
            name="inference_usage_source_check",
        ),
        sa.CheckConstraint(
            "cost_source IN ('rate_snapshot_estimate','unavailable')",
            name="inference_cost_source_check",
        ),
        sa.CheckConstraint(
            "(estimated_cost_usd IS NULL AND cost_source = 'unavailable') OR "
            "(estimated_cost_usd IS NOT NULL AND cost_source = 'rate_snapshot_estimate' "
            "AND estimated_cost_usd >= 0)",
            name="inference_cost_presence_check",
        ),
        sa.CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0",
            name="inference_input_tokens_nonnegative",
        ),
        sa.CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0",
            name="inference_output_tokens_nonnegative",
        ),
        sa.CheckConstraint(
            "cached_input_tokens IS NULL OR cached_input_tokens >= 0",
            name="inference_cached_tokens_nonnegative",
        ),
        sa.CheckConstraint(
            "total_tokens IS NULL OR total_tokens >= 0",
            name="inference_total_tokens_nonnegative",
        ),
    )
    op.create_index(
        "ix_inference_usage_account_time",
        "inference_usage_events", ["account_id", "recorded_at"],
    )
    op.create_index(
        "ix_inference_usage_request",
        "inference_usage_events", ["request_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_inference_usage_request", table_name="inference_usage_events")
    op.drop_index("ix_inference_usage_account_time", table_name="inference_usage_events")
    op.drop_table("inference_usage_events")
