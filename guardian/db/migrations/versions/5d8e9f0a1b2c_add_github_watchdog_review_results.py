"""add GitHub Watchdog review results

Revision ID: 5d8e9f0a1b2c
Revises: 4c7d8e9f0a1b
Create Date: 2026-08-24 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "5d8e9f0a1b2c"
down_revision: Union[str, Sequence[str], None] = "4c7d8e9f0a1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_github_watchdog_review_attempts_state",
        "github_watchdog_review_attempts",
        type_="check",
    )
    op.create_check_constraint(
        "ck_github_watchdog_review_attempts_state",
        "github_watchdog_review_attempts",
        "attempt_state IN "
        "('blocked_policy','blocked_runtime_policy','completed','failed',"
        "'prepared','running','superseded')",
    )
    op.create_table(
        "github_watchdog_review_results",
        sa.Column("result_id", sa.String(length=36), nullable=False),
        sa.Column("review_attempt_id", sa.String(length=36), nullable=False),
        sa.Column("review_input_snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("result_state", sa.String(length=32), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_sha256", sa.String(length=64), nullable=False),
        sa.Column("invoked_provider_id", sa.String(length=64), nullable=False),
        sa.Column("invoked_model_id", sa.String(length=512), nullable=False),
        sa.Column("inference_mode", sa.String(length=64), nullable=True),
        sa.Column("requested_max_output_tokens", sa.Integer(), nullable=False),
        sa.Column("raw_output_text", sa.Text(), nullable=True),
        sa.Column("raw_output_sha256", sa.String(length=64), nullable=True),
        sa.Column("raw_output_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "structured_review_json",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()),
                "postgresql",
            ),
            nullable=True,
        ),
        sa.Column("provider_input_tokens", sa.Integer(), nullable=True),
        sa.Column("provider_output_tokens", sa.Integer(), nullable=True),
        sa.Column("provider_total_tokens", sa.Integer(), nullable=True),
        sa.Column("provider_request_id", sa.String(length=128), nullable=True),
        sa.Column("terminal_error_code", sa.String(length=64), nullable=True),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "result_state IN "
            "('blocked_runtime_policy','completed','discarded_superseded',"
            "'failed_output_contract','failed_provider','running')",
            name="ck_github_watchdog_review_results_state",
        ),
        sa.CheckConstraint(
            "terminal_error_code IS NULL OR terminal_error_code IN "
            "('attempt_not_eligible','attempt_not_found','attempt_superseded',"
            "'empty_response','output_not_json','output_schema_invalid',"
            "'provider_authentication_failed','provider_failed','provider_rate_limited',"
            "'provider_timeout','provider_transport_failed','provider_unavailable',"
            "'provider_or_model_missing','raw_output_limit_exceeded',"
            "'result_persistence_failed','runtime_cloud_disabled',"
            "'runtime_credentials_unavailable','runtime_egress_denied',"
            "'runtime_local_only_blocked','runtime_provider_governance_disabled',"
            "'runtime_provider_unknown','snapshot_digest_missing',"
            "'snapshot_identity_mismatch','snapshot_missing','snapshot_not_captured')",
            name="ck_github_watchdog_review_results_terminal_error_code",
        ),
        sa.CheckConstraint(
            "(result_state = 'running' AND completed_at IS NULL) OR "
            "(result_state != 'running' AND completed_at IS NOT NULL)",
            name="ck_github_watchdog_review_results_terminal_shape",
        ),
        sa.ForeignKeyConstraint(
            ["review_attempt_id"],
            ["github_watchdog_review_attempts.review_attempt_id"],
            name="fk_github_watchdog_review_results_review_attempt_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["review_input_snapshot_id"],
            ["github_watchdog_review_input_snapshots.snapshot_id"],
            name="fk_github_watchdog_review_results_review_input_snapshot_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("result_id"),
        sa.UniqueConstraint(
            "review_attempt_id",
            name="uq_github_watchdog_review_results_review_attempt_id",
        ),
    )
    op.create_index(
        "ix_github_watchdog_review_results_state",
        "github_watchdog_review_results",
        ["result_state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_github_watchdog_review_results_state",
        table_name="github_watchdog_review_results",
    )
    op.drop_table("github_watchdog_review_results")
    op.drop_constraint(
        "ck_github_watchdog_review_attempts_state",
        "github_watchdog_review_attempts",
        type_="check",
    )
    op.create_check_constraint(
        "ck_github_watchdog_review_attempts_state",
        "github_watchdog_review_attempts",
        "attempt_state IN ('blocked_policy','prepared','superseded')",
    )
