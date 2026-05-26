"""add guardian_delegation_intents

Revision ID: 7c21f0a4b8de
Revises: 384dde1f793c
Create Date: 2026-05-26 15:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "7c21f0a4b8de"
down_revision = "384dde1f793c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "guardian_delegation_intents",
        sa.Column("intent_id", sa.String(length=64), nullable=False),
        sa.Column(
            "thread_id",
            sa.Integer(),
            sa.ForeignKey("chat_threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_message_id",
            sa.BigInteger(),
            sa.ForeignKey("chat_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "interaction_mode",
            sa.String(length=32),
            server_default=sa.text("'non_blocking'"),
            nullable=False,
        ),
        sa.Column(
            "approval_mode",
            sa.String(length=32),
            server_default=sa.text("'scoped_auto'"),
            nullable=False,
        ),
        sa.Column("approval_state", sa.String(length=32), nullable=False),
        sa.Column("approval_source", sa.String(length=32), nullable=False),
        sa.Column("acceptance_status", sa.String(length=32), nullable=False),
        sa.Column("intent_status", sa.String(length=32), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column(
            "plan_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "context_basis",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
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
            "interaction_mode IN ('non_blocking')",
            name="guardian_delegation_intents_interaction_mode_check",
        ),
        sa.CheckConstraint(
            "approval_mode IN ('scoped_auto')",
            name="guardian_delegation_intents_approval_mode_check",
        ),
        sa.CheckConstraint(
            "approval_state IN ('approved','blocked','pending')",
            name="guardian_delegation_intents_approval_state_check",
        ),
        sa.CheckConstraint(
            "approval_source IN ('auto','human','none')",
            name="guardian_delegation_intents_approval_source_check",
        ),
        sa.CheckConstraint(
            "acceptance_status IN ('accepted','accepted_degraded')",
            name="guardian_delegation_intents_acceptance_status_check",
        ),
        sa.CheckConstraint(
            "intent_status IN ('accepted','awaiting_approval','awaiting_clarification','cancelled','draft','failed','planning','superseded')",
            name="guardian_delegation_intents_intent_status_check",
        ),
        sa.PrimaryKeyConstraint("intent_id"),
    )
    op.create_index(
        "ix_guardian_delegation_intents_run_id",
        "guardian_delegation_intents",
        ["run_id"],
    )
    op.create_index(
        "ix_guardian_delegation_intents_thread_source",
        "guardian_delegation_intents",
        ["thread_id", "source_message_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_guardian_delegation_intents_thread_source",
        table_name="guardian_delegation_intents",
    )
    op.drop_index(
        "ix_guardian_delegation_intents_run_id",
        table_name="guardian_delegation_intents",
    )
    op.drop_table("guardian_delegation_intents")
