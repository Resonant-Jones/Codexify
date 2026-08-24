"""add GitHub Watchdog review dispatches

Revision ID: 6e9f0a1b2c3
Revises: 5d8e9f0a1b2c
Create Date: 2026-08-24 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "6e9f0a1b2c3"
down_revision: Union[str, Sequence[str], None] = "5d8e9f0a1b2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "github_watchdog_review_dispatches",
        sa.Column("dispatch_id", sa.String(length=36), nullable=False),
        sa.Column("review_attempt_id", sa.String(length=36), nullable=False),
        sa.Column("review_input_snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("head_sha", sa.String(length=64), nullable=False),
        sa.Column("dispatch_state", sa.String(length=32), nullable=False),
        sa.Column("queue_task_id", sa.String(length=64), nullable=False),
        sa.Column(
            "enqueue_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("last_enqueue_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("worker_id", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("review_result_id", sa.String(length=36), nullable=True),
        sa.Column("terminal_error_code", sa.String(length=64), nullable=True),
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
            "dispatch_state IN "
            "('blocked','completed','discarded_superseded','enqueue_failed',"
            "'failed','pending_enqueue','queued','running')",
            name="ck_github_watchdog_review_dispatches_state",
        ),
        sa.CheckConstraint(
            "terminal_error_code IS NULL OR terminal_error_code IN "
            "('attempt_not_eligible','attempt_not_found','attempt_superseded',"
            "'dispatch_persistence_failed','empty_response','invalid_queue_envelope',"
            "'output_not_json','output_schema_invalid','provider_authentication_failed',"
            "'provider_failed','provider_rate_limited','provider_timeout',"
            "'provider_transport_failed','provider_unavailable',"
            "'provider_or_model_missing','queue_enqueue_failed',"
            "'queue_identity_mismatch','raw_output_limit_exceeded',"
            "'result_persistence_failed','review_result_exists',"
            "'runtime_cloud_disabled','runtime_credentials_unavailable',"
            "'runtime_egress_denied','runtime_local_only_blocked',"
            "'runtime_provider_governance_disabled','runtime_provider_unknown',"
            "'snapshot_digest_missing','snapshot_identity_mismatch',"
            "'snapshot_missing','snapshot_not_captured','worker_pre_inference_failed')",
            name="ck_github_watchdog_review_dispatches_terminal_error_code",
        ),
        sa.CheckConstraint(
            "(dispatch_state IN ('completed','failed','blocked',"
            "'discarded_superseded','enqueue_failed') AND completed_at IS NOT NULL) "
            "OR (dispatch_state IN ('pending_enqueue','queued','running') "
            "AND completed_at IS NULL)",
            name="ck_github_watchdog_review_dispatches_terminal_shape",
        ),
        sa.ForeignKeyConstraint(
            ["review_attempt_id"],
            ["github_watchdog_review_attempts.review_attempt_id"],
            name="fk_github_watchdog_review_dispatches_review_attempt_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["review_input_snapshot_id"],
            ["github_watchdog_review_input_snapshots.snapshot_id"],
            name="fk_github_watchdog_review_dispatches_review_input_snapshot_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["review_result_id"],
            ["github_watchdog_review_results.result_id"],
            name="fk_github_watchdog_review_dispatches_review_result_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("dispatch_id"),
        sa.UniqueConstraint(
            "review_attempt_id",
            name="uq_github_watchdog_review_dispatches_review_attempt_id",
        ),
    )
    op.create_index(
        "ix_github_watchdog_review_dispatches_state",
        "github_watchdog_review_dispatches",
        ["dispatch_state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_github_watchdog_review_dispatches_state",
        table_name="github_watchdog_review_dispatches",
    )
    op.drop_table("github_watchdog_review_dispatches")
