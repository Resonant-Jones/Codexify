"""Join published account presentation and OpenAI import source histories.

Both parents are already published. Their DDL is disjoint; this mergepoint
only records convergence, without reparenting, stamps, backfills or data writes.
"""

revision = "b7e6c4a29013"
down_revision = ("a3f8c2d6e901", "a64c358e2241")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
