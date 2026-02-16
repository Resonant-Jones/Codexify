"""add control-plane identity depth and thread modeling flags

Revision ID: f8ab1c2d3e4f
Revises: 7f6e5d4c3b2a, c9e1f7a6b3d2
Create Date: 2026-02-16 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8ab1c2d3e4f"
down_revision: Union[str, Sequence[str], None] = (
    "7f6e5d4c3b2a",
    "c9e1f7a6b3d2",
)
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
    chat_thread_cols = _column_names("chat_threads")
    if "diary_mode" not in chat_thread_cols:
        op.add_column(
            "chat_threads",
            sa.Column(
                "diary_mode",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )
    if "modeling_excluded" not in chat_thread_cols:
        op.add_column(
            "chat_threads",
            sa.Column(
                "modeling_excluded",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    project_cols = _column_names("projects")
    if "identity_depth" not in project_cols:
        op.add_column(
            "projects",
            sa.Column(
                "identity_depth",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'light'"),
            ),
        )

    project_constraints = _constraint_names("projects")
    if "projects_identity_depth_check" not in project_constraints:
        op.create_check_constraint(
            "projects_identity_depth_check",
            "projects",
            "identity_depth IN ('light','deep')",
        )


def downgrade() -> None:
    project_constraints = _constraint_names("projects")
    if "projects_identity_depth_check" in project_constraints:
        op.drop_constraint(
            "projects_identity_depth_check",
            "projects",
            type_="check",
        )

    project_cols = _column_names("projects")
    if "identity_depth" in project_cols:
        op.drop_column("projects", "identity_depth")

    chat_thread_cols = _column_names("chat_threads")
    if "modeling_excluded" in chat_thread_cols:
        op.drop_column("chat_threads", "modeling_excluded")
    if "diary_mode" in chat_thread_cols:
        op.drop_column("chat_threads", "diary_mode")
