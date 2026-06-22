"""Add guardrail_metadata JSONB column to personal_facts.

Revision ID: a3b4c5d6e7f8
Revises: 3cdd66742226
Create Date: 2026-06-22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f8"
down_revision: str | Sequence[str] | None = "3cdd66742226"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "personal_facts",
        sa.Column(
            "guardrail_metadata",
            postgresql.JSONB,
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("personal_facts", "guardrail_metadata")
