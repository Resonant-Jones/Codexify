"""Add server-side admin and guest roles to user accounts.

Revision ID: e5f6a7b8c9d0
Revises: e8d1f2a3b4c5
"""

from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "e8d1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=16), nullable=False, server_default="guest"),
    )
    op.create_check_constraint("users_role_check", "users", "role IN ('admin', 'guest')")


def downgrade() -> None:
    op.drop_constraint("users_role_check", "users", type_="check")
    op.drop_column("users", "role")
