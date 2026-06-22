"""add work order result receipts table

Revision ID: a1b2c3d4e5f6
Revises: f9a1b2c3d4e5
Create Date: 2026-06-18 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "3cdd66742226"
down_revision: str | Sequence[str] | None = "f9a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_order_result_receipts",
        sa.Column("receipt_id", sa.String(length=64), nullable=False),
        sa.Column("work_order_id", sa.String(length=64), nullable=False),
        sa.Column("command_run_id", sa.String(length=64), nullable=False),
        sa.Column(
            "receipt_kind",
            sa.String(length=32),
            nullable=False,
            server_default="command_run_observation",
        ),
        sa.Column(
            "observed_command_id", sa.String(length=512), nullable=False
        ),
        sa.Column(
            "observed_run_status", sa.String(length=32), nullable=False
        ),
        sa.Column("observed_result_summary", sa.Text(), nullable=False),
        sa.Column("observed_error_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("source_thread_id", sa.String(length=128), nullable=True),
        sa.Column("source_message_id", sa.String(length=128), nullable=True),
        sa.Column(
            "provenance_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "redaction_summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("integrity_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "schema_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "artifact_ids_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("review_state", sa.String(length=32), nullable=True),
        sa.Column("operator_note", sa.Text(), nullable=True),
        sa.Column(
            "supersedes_receipt_id", sa.String(length=64), nullable=True
        ),
        sa.PrimaryKeyConstraint("receipt_id"),
        sa.UniqueConstraint(
            "work_order_id",
            "command_run_id",
            "receipt_kind",
            "schema_version",
            name="uq_receipt_work_order_source",
        ),
    )
    op.create_index(
        "ix_receipts_work_order_id",
        "work_order_result_receipts",
        ["work_order_id"],
    )
    op.create_index(
        "ix_receipts_command_run_id",
        "work_order_result_receipts",
        ["command_run_id"],
    )
    op.create_index(
        "ix_receipts_created_at",
        "work_order_result_receipts",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_receipts_created_at", table_name="work_order_result_receipts")
    op.drop_index("ix_receipts_command_run_id", table_name="work_order_result_receipts")
    op.drop_index("ix_receipts_work_order_id", table_name="work_order_result_receipts")
    op.drop_table("work_order_result_receipts")
