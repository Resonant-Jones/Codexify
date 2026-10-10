"""Merge chat deadline and Campaign Continuation Authority lineages.

Revision ID: 2e865c4a9b10
Revises: f1a6d83b9024, 17b23052da6a

Both branches retain their existing schema operations. This merge only joins
revision history so upgrading either installed lineage reaches one head.
"""

revision = "2e865c4a9b10"
down_revision = ("f1a6d83b9024", "17b23052da6a")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
