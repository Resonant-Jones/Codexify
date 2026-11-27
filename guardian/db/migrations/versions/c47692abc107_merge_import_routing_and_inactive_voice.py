"""Join logical OpenAI import routing and inactive voice accounting.

Revision ID: c47692abc107
Revises: a64c358e2241, 1b6c8d9e2f40
"""

revision = "c47692abc107"
down_revision = ("a64c358e2241", "1b6c8d9e2f40")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Join the unchanged parent schemas without DDL or funding seeds."""


def downgrade() -> None:
    """Split the parent revisions without dropping either schema."""
