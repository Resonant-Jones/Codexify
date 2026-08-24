"""add GitHub Watchdog review-input snapshots

Revision ID: 4c7d8e9f0a1b
Revises: 3b7c8d9e0f1a
Create Date: 2026-08-23 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "4c7d8e9f0a1b"
down_revision: Union[str, Sequence[str], None] = "3b7c8d9e0f1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "github_watchdog_review_input_snapshots",
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("review_attempt_id", sa.String(length=36), nullable=False),
        sa.Column("installation_id", sa.String(length=64), nullable=False),
        sa.Column("repository_id", sa.String(length=64), nullable=False),
        sa.Column("repository_full_name", sa.String(length=512), nullable=False),
        sa.Column("pull_request_number", sa.Integer(), nullable=False),
        sa.Column("capture_state", sa.String(length=32), nullable=False),
        sa.Column("expected_head_sha", sa.String(length=64), nullable=False),
        sa.Column("observed_head_sha", sa.String(length=64), nullable=True),
        sa.Column("base_sha", sa.String(length=64), nullable=True),
        sa.Column("observed_base_sha", sa.String(length=64), nullable=True),
        sa.Column("pull_request_title", sa.Text(), nullable=True),
        sa.Column("pull_request_body", sa.Text(), nullable=True),
        sa.Column("author_id", sa.String(length=64), nullable=True),
        sa.Column("author_login", sa.String(length=255), nullable=True),
        sa.Column("draft", sa.Boolean(), nullable=True),
        sa.Column("changed_file_count", sa.Integer(), nullable=True),
        sa.Column("files_without_patch_count", sa.Integer(), nullable=True),
        sa.Column("aggregate_additions", sa.Integer(), nullable=True),
        sa.Column("aggregate_deletions", sa.Integer(), nullable=True),
        sa.Column("aggregate_changes", sa.Integer(), nullable=True),
        sa.Column(
            "changed_files_json",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()),
                "postgresql",
            ),
            nullable=True,
        ),
        sa.Column("captured_patch_bytes", sa.Integer(), nullable=True),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=True),
        sa.Column("block_error_code", sa.String(length=64), nullable=True),
        sa.Column(
            "captured_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "capture_state IN ('blocked_limits','blocked_stale','captured')",
            name="ck_github_watchdog_review_input_snapshots_state",
        ),
        sa.CheckConstraint(
            "block_error_code IS NULL OR block_error_code IN "
            "('attempt_not_eligible','attempt_not_found','attempt_superseded',"
            "'capture_file_limit_exceeded','capture_patch_byte_limit_exceeded',"
            "'expected_head_missing','github_read_failure','installation_id_missing',"
            "'live_head_mismatch','malformed_github_response',"
            "'pull_request_identity_missing','repository_identity_missing',"
            "'snapshot_persistence_failed','source_changed_during_capture')",
            name="ck_github_watchdog_review_input_snapshots_block_error_code",
        ),
        sa.CheckConstraint(
            "(capture_state = 'captured' AND snapshot_sha256 IS NOT NULL "
            "AND block_error_code IS NULL) OR "
            "(capture_state != 'captured' AND snapshot_sha256 IS NULL "
            "AND block_error_code IS NOT NULL)",
            name="ck_github_watchdog_review_input_snapshots_terminal_shape",
        ),
        sa.ForeignKeyConstraint(
            ["review_attempt_id"],
            ["github_watchdog_review_attempts.review_attempt_id"],
            name="fk_github_watchdog_review_input_snapshots_review_attempt_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("snapshot_id"),
        sa.UniqueConstraint(
            "review_attempt_id",
            name="uq_github_watchdog_review_input_snapshots_review_attempt_id",
        ),
    )
    op.create_index(
        "ix_github_watchdog_review_input_snapshots_capture_state",
        "github_watchdog_review_input_snapshots",
        ["capture_state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_github_watchdog_review_input_snapshots_capture_state",
        table_name="github_watchdog_review_input_snapshots",
    )
    op.drop_table("github_watchdog_review_input_snapshots")
