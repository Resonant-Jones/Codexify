"""add GitHub Watchdog review attempts

Revision ID: 3b7c8d9e0f1a
Revises: 2a6b7c8d9e0f
Create Date: 2026-08-23 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "3b7c8d9e0f1a"
down_revision: Union[str, Sequence[str], None] = "2a6b7c8d9e0f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "github_watchdog_review_attempts",
        sa.Column("review_attempt_id", sa.String(length=36), nullable=False),
        sa.Column("trigger_receipt_id", sa.String(length=36), nullable=False),
        sa.Column("github_delivery_id", sa.String(length=255), nullable=False),
        sa.Column("installation_id", sa.String(length=64), nullable=True),
        sa.Column("repository_id", sa.String(length=64), nullable=True),
        sa.Column("repository_full_name", sa.String(length=512), nullable=True),
        sa.Column("pull_request_number", sa.Integer(), nullable=True),
        sa.Column("head_sha", sa.String(length=64), nullable=True),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("attempt_state", sa.String(length=32), nullable=False),
        sa.Column("policy_resolution_state", sa.String(length=32), nullable=False),
        sa.Column("provider_id", sa.String(length=64), nullable=True),
        sa.Column("model_id", sa.String(length=512), nullable=True),
        sa.Column("inference_mode", sa.String(length=64), nullable=True),
        sa.Column("model_selection_source", sa.String(length=64), nullable=False),
        sa.Column("policy_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("escalation_mode", sa.String(length=32), nullable=False),
        sa.Column("escalation_provider_id", sa.String(length=64), nullable=True),
        sa.Column("escalation_model_id", sa.String(length=512), nullable=True),
        sa.Column("policy_reason_code", sa.String(length=64), nullable=True),
        sa.Column("superseded_by_attempt_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "operation = 'automated_review'",
            name="ck_github_watchdog_review_attempts_operation",
        ),
        sa.CheckConstraint(
            "attempt_state IN ('blocked_policy','prepared','superseded')",
            name="ck_github_watchdog_review_attempts_state",
        ),
        sa.CheckConstraint(
            "policy_resolution_state IN ('blocked','resolved')",
            name="ck_github_watchdog_review_attempts_policy_resolution_state",
        ),
        sa.CheckConstraint(
            "escalation_mode IN ('disabled','explicit_only')",
            name="ck_github_watchdog_review_attempts_escalation_mode",
        ),
        sa.CheckConstraint(
            "model_selection_source IN ('system_default')",
            name="ck_github_watchdog_review_attempts_model_selection_source",
        ),
        sa.CheckConstraint(
            "policy_reason_code IS NULL OR policy_reason_code IN "
            "('cloud_providers_disabled','configuration_missing',"
            "'egress_policy_forbids_provider','head_sha_missing',"
            "'local_only_mode_forbids_cloud','model_missing',"
            "'provider_governance_disabled','provider_unknown')",
            name="ck_github_watchdog_review_attempts_policy_reason_code",
        ),
        sa.ForeignKeyConstraint(
            ["trigger_receipt_id"],
            ["github_watchdog_delivery_receipts.receipt_id"],
            name="fk_github_watchdog_review_attempts_trigger_receipt_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_attempt_id"],
            ["github_watchdog_review_attempts.review_attempt_id"],
            name="fk_github_watchdog_review_attempts_superseded_by_attempt_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("review_attempt_id"),
        sa.UniqueConstraint(
            "trigger_receipt_id",
            name="uq_github_watchdog_review_attempts_trigger_receipt_id",
        ),
    )
    op.create_index(
        "ix_github_watchdog_review_attempts_repository_pr",
        "github_watchdog_review_attempts",
        ["repository_id", "pull_request_number"],
        unique=False,
    )
    op.create_index(
        "ix_github_watchdog_review_attempts_state",
        "github_watchdog_review_attempts",
        ["attempt_state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_github_watchdog_review_attempts_state",
        table_name="github_watchdog_review_attempts",
    )
    op.drop_index(
        "ix_github_watchdog_review_attempts_repository_pr",
        table_name="github_watchdog_review_attempts",
    )
    op.drop_table("github_watchdog_review_attempts")
