"""Account appearance and explicitly unique client workspaces; no backfill."""

import sqlalchemy as sa
from alembic import op

revision = "f3a9c7d2b8e1"
down_revision = "d2e7a9b4c1f6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_presentation",
        sa.Column(
            "user_id",
            sa.String(255),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("workspace_id", sa.String(36), primary_key=True),
        sa.Column("is_unique", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("wallpaper_data", sa.LargeBinary()),
        sa.Column("wallpaper_mime", sa.String(32)),
        sa.CheckConstraint(
            "workspace_id != 'account' OR is_unique = false",
            name="ck_user_presentation_account_scope",
        ),
        sa.CheckConstraint(
            "(wallpaper_data IS NULL AND wallpaper_mime IS NULL) OR "
            "(wallpaper_data IS NOT NULL AND wallpaper_mime IS NOT NULL AND wallpaper_mime IN ('image/png','image/jpeg','image/webp') "
            "AND length(wallpaper_data) <= 5242880)",
            name="ck_user_presentation_wallpaper",
        ),
    )


def downgrade():
    op.drop_table("user_presentation")
