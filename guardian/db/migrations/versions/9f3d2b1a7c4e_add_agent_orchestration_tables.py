"""add agent orchestration tables

Revision ID: 9f3d2b1a7c4e
Revises: a7c9d1e2f3b4
Create Date: 2026-02-18 15:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9f3d2b1a7c4e"
down_revision: Union[str, Sequence[str], None] = "a7c9d1e2f3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agent_deployments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("deployment_id", sa.String(length=64), nullable=False),
        sa.Column("flow_id", sa.String(length=128), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=True),
        sa.Column(
            "spec_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("spec_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "trust_state",
            sa.String(length=32),
            server_default="supervised",
            nullable=False,
        ),
        sa.Column(
            "unlocked_for_unsupervised",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("unlocked_by", sa.String(length=255), nullable=True),
        sa.Column("unlocked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="active",
            nullable=False,
        ),
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
            "trust_state IN ('supervised', 'unlocked')",
            name="agent_deployments_trust_state_check",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'canceled', 'archived')",
            name="agent_deployments_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["chat_threads.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deployment_id"),
    )
    op.create_index(
        "ix_agent_deployments_thread_id",
        "agent_deployments",
        ["thread_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_deployments_spec_hash",
        "agent_deployments",
        ["spec_hash"],
        unique=False,
    )
    op.create_index(
        "ix_agent_deployments_status",
        "agent_deployments",
        ["status"],
        unique=False,
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("deployment_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="queued",
            nullable=False,
        ),
        sa.Column(
            "runtime_target",
            sa.String(length=32),
            server_default="container",
            nullable=False,
        ),
        sa.Column(
            "rollback_mode",
            sa.String(length=32),
            server_default="auto",
            nullable=False,
        ),
        sa.Column(
            "rollback_applied",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("rollback_reason", sa.Text(), nullable=True),
        sa.Column("worktree_id", sa.String(length=128), nullable=True),
        sa.Column("worktree_path", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'escalated', 'canceled', 'failed', 'succeeded')",
            name="agent_runs_status_check",
        ),
        sa.CheckConstraint(
            "runtime_target IN ('container', 'terminal')",
            name="agent_runs_runtime_target_check",
        ),
        sa.CheckConstraint(
            "rollback_mode IN ('auto', 'manual')",
            name="agent_runs_rollback_mode_check",
        ),
        sa.ForeignKeyConstraint(
            ["deployment_id"], ["agent_deployments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["chat_threads.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index(
        "ix_agent_runs_deployment_id",
        "agent_runs",
        ["deployment_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_runs_thread_id", "agent_runs", ["thread_id"], unique=False
    )
    op.create_index(
        "ix_agent_runs_status", "agent_runs", ["status"], unique=False
    )

    op.create_table(
        "agent_run_steps",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("step_id", sa.String(length=128), nullable=False),
        sa.Column("primitive", sa.String(length=64), nullable=False),
        sa.Column(
            "is_mutating",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("schema_valid", sa.Boolean(), nullable=True),
        sa.Column("spec_alignment_ok", sa.Boolean(), nullable=True),
        sa.Column("tests_passed", sa.Boolean(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'escalated', 'canceled')",
            name="agent_run_steps_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["agent_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id", "step_index", name="uq_agent_run_steps_run_step_index"
        ),
    )
    op.create_index(
        "ix_agent_run_steps_run_id", "agent_run_steps", ["run_id"], unique=False
    )
    op.create_index(
        "ix_agent_run_steps_status", "agent_run_steps", ["status"], unique=False
    )

    op.create_table(
        "agent_run_attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_step_id", sa.BigInteger(), nullable=False),
        sa.Column("attempt_index", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="running",
            nullable=False,
        ),
        sa.Column("fail_count", sa.Integer(), nullable=True),
        sa.Column("fail_signature", sa.String(length=128), nullable=True),
        sa.Column(
            "diff_added", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "diff_deleted", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("error_category", sa.String(length=64), nullable=True),
        sa.Column(
            "progress_made",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("stderr_excerpt", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('running', 'failed', 'succeeded', 'escalated')",
            name="agent_run_attempts_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["run_step_id"], ["agent_run_steps.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_step_id",
            "attempt_index",
            name="uq_agent_run_attempts_step_attempt_index",
        ),
    )
    op.create_index(
        "ix_agent_run_attempts_step_id",
        "agent_run_attempts",
        ["run_step_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_run_attempts_signature",
        "agent_run_attempts",
        ["fail_signature"],
        unique=False,
    )

    op.create_table(
        "agent_run_artifacts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("run_step_id", sa.BigInteger(), nullable=True),
        sa.Column("attempt_id", sa.BigInteger(), nullable=True),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("uri", sa.Text(), nullable=True),
        sa.Column(
            "content_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["agent_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["run_step_id"], ["agent_run_steps.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"], ["agent_run_attempts.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_run_artifacts_run_id",
        "agent_run_artifacts",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_run_artifacts_type",
        "agent_run_artifacts",
        ["artifact_type"],
        unique=False,
    )

    op.create_table(
        "agent_confidence_reports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("run_step_id", sa.BigInteger(), nullable=True),
        sa.Column("step_index", sa.Integer(), nullable=True),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("decision", sa.String(length=64), nullable=False),
        sa.Column(
            "factors",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("model_self_confidence", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "scope IN ('step', 'task')",
            name="agent_confidence_reports_scope_check",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["agent_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["run_step_id"], ["agent_run_steps.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_confidence_reports_run_id",
        "agent_confidence_reports",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_confidence_reports_scope_step",
        "agent_confidence_reports",
        ["scope", "step_index"],
        unique=False,
    )

    op.create_table(
        "agent_escalations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("run_step_id", sa.BigInteger(), nullable=True),
        sa.Column("step_index", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="open",
            nullable=False,
        ),
        sa.Column(
            "preserved_worktree",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
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
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "severity IN ('soft', 'hard')",
            name="agent_escalations_severity_check",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved', 'canceled')",
            name="agent_escalations_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["agent_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["run_step_id"], ["agent_run_steps.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_escalations_run_id",
        "agent_escalations",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_escalations_status",
        "agent_escalations",
        ["status"],
        unique=False,
    )

    op.create_table(
        "agent_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("run_step_id", sa.BigInteger(), nullable=True),
        sa.Column("attempt_id", sa.BigInteger(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["agent_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["run_step_id"], ["agent_run_steps.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"], ["agent_run_attempts.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_events_run_id", "agent_events", ["run_id"], unique=False
    )
    op.create_index(
        "ix_agent_events_type", "agent_events", ["event_type"], unique=False
    )

    op.create_table(
        "agent_reflections",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("run_step_id", sa.BigInteger(), nullable=True),
        sa.Column("reflection_kind", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("derived_from", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "reflection_kind IN ('step_note', 'session_summary')",
            name="agent_reflections_kind_check",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["agent_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["run_step_id"], ["agent_run_steps.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_reflections_run_id",
        "agent_reflections",
        ["run_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_agent_reflections_run_id", table_name="agent_reflections")
    op.drop_table("agent_reflections")

    op.drop_index("ix_agent_events_type", table_name="agent_events")
    op.drop_index("ix_agent_events_run_id", table_name="agent_events")
    op.drop_table("agent_events")

    op.drop_index("ix_agent_escalations_status", table_name="agent_escalations")
    op.drop_index("ix_agent_escalations_run_id", table_name="agent_escalations")
    op.drop_table("agent_escalations")

    op.drop_index(
        "ix_agent_confidence_reports_scope_step",
        table_name="agent_confidence_reports",
    )
    op.drop_index(
        "ix_agent_confidence_reports_run_id",
        table_name="agent_confidence_reports",
    )
    op.drop_table("agent_confidence_reports")

    op.drop_index(
        "ix_agent_run_artifacts_type", table_name="agent_run_artifacts"
    )
    op.drop_index(
        "ix_agent_run_artifacts_run_id", table_name="agent_run_artifacts"
    )
    op.drop_table("agent_run_artifacts")

    op.drop_index(
        "ix_agent_run_attempts_signature",
        table_name="agent_run_attempts",
    )
    op.drop_index(
        "ix_agent_run_attempts_step_id", table_name="agent_run_attempts"
    )
    op.drop_table("agent_run_attempts")

    op.drop_index("ix_agent_run_steps_status", table_name="agent_run_steps")
    op.drop_index("ix_agent_run_steps_run_id", table_name="agent_run_steps")
    op.drop_table("agent_run_steps")

    op.drop_index("ix_agent_runs_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_thread_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_deployment_id", table_name="agent_runs")
    op.drop_table("agent_runs")

    op.drop_index("ix_agent_deployments_status", table_name="agent_deployments")
    op.drop_index(
        "ix_agent_deployments_spec_hash", table_name="agent_deployments"
    )
    op.drop_index(
        "ix_agent_deployments_thread_id", table_name="agent_deployments"
    )
    op.drop_table("agent_deployments")
