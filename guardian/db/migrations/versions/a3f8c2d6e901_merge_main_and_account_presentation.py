"""Join published main custody and Preview account presentation histories.

No reparenting, stamp, backfill or data operations. Either installed lineage
applies only the missing sibling before Alembic records this mergepoint.
"""

revision = "a3f8c2d6e901"
down_revision = ("e723ba9046cd", "f3a9c7d2b8e1")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
