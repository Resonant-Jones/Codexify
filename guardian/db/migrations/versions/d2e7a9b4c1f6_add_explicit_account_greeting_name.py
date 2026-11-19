"""Add an optional explicitly chosen greeting name, without backfilling."""

import sqlalchemy as sa
from alembic import op

revision = "d2e7a9b4c1f6"
down_revision = "ab71d5ce9604"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_profiles", sa.Column("greeting_name", sa.String(255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "greeting_name")
