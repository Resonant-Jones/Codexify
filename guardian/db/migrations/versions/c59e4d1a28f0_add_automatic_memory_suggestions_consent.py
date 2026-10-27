"""add automatic memory suggestions consent to user_settings

Adds the durable, account-owned consent preference that gates automatic
Personal Fact collection.  The default is ``unset`` so every existing and
future account denies automatic collection until it explicitly opts in.

Revision ID: c59e4d1a28f0
Revises: f0d7c4b2a198
Create Date: 2026-10-27 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c59e4d1a28f0"
down_revision: Union[str, Sequence[str], None] = "f0d7c4b2a198"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {c["name"] for c in inspector.get_columns(table_name)}


def _constraint_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {
        c["name"]
        for c in inspector.get_check_constraints(table_name)
        if c.get("name")
    }


def upgrade() -> None:
    user_settings_cols = _column_names("user_settings")

    # Existing rows are preserved: every added column is either nullable or
    # carries a server default, so no historical settings row is rewritten.
    if "automatic_memory_suggestions" not in user_settings_cols:
        op.add_column(
            "user_settings",
            sa.Column(
                "automatic_memory_suggestions",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'unset'"),
            ),
        )
    if "consent_policy_version" not in user_settings_cols:
        op.add_column(
            "user_settings",
            sa.Column(
                "consent_policy_version",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'1'"),
            ),
        )
    if "consent_recorded_by_user_id" not in user_settings_cols:
        op.add_column(
            "user_settings",
            sa.Column(
                "consent_recorded_by_user_id",
                sa.String(length=255),
                nullable=True,
            ),
        )
    if "consent_recorded_at" not in user_settings_cols:
        op.add_column(
            "user_settings",
            sa.Column(
                "consent_recorded_at",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
            ),
        )
    if "consent_updated_at" not in user_settings_cols:
        op.add_column(
            "user_settings",
            sa.Column(
                "consent_updated_at",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
            ),
        )

    user_settings_constraints = _constraint_names("user_settings")
    if (
        "user_settings_automatic_memory_suggestions_check"
        not in user_settings_constraints
    ):
        op.create_check_constraint(
            "user_settings_automatic_memory_suggestions_check",
            "user_settings",
            "automatic_memory_suggestions IN "
            "('unset','enabled','paused','declined')",
        )


def downgrade() -> None:
    user_settings_constraints = _constraint_names("user_settings")
    if (
        "user_settings_automatic_memory_suggestions_check"
        in user_settings_constraints
    ):
        op.drop_constraint(
            "user_settings_automatic_memory_suggestions_check",
            "user_settings",
            type_="check",
        )

    user_settings_cols = _column_names("user_settings")
    for column in (
        "consent_updated_at",
        "consent_recorded_at",
        "consent_recorded_by_user_id",
        "consent_policy_version",
        "automatic_memory_suggestions",
    ):
        if column in user_settings_cols:
            op.drop_column("user_settings", column)
