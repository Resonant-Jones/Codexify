"""Add account-owned onboarding state.

Revision ID: 8d41a0c2b7ef
Revises: c9f3e2a7b601
"""

from alembic import op
import sqlalchemy as sa

revision = "8d41a0c2b7ef"
down_revision = "c9f3e2a7b601"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_onboarding_state",
        sa.Column(
            "user_id",
            sa.String(255),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "onboarding_version", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column(
            "status", sa.String(16), nullable=False, server_default="not_started"
        ),
        sa.Column("last_step_key", sa.String(32), nullable=True),
        sa.Column(
            "desktop_tour_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "mobile_tour_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "contextual_tips_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('not_started', 'in_progress', 'skipped', 'completed')",
            name="user_onboarding_status_check",
        ),
        sa.CheckConstraint(
            "onboarding_version = 1", name="user_onboarding_version_check"
        ),
    )


def downgrade():
    op.drop_table("user_onboarding_state")
