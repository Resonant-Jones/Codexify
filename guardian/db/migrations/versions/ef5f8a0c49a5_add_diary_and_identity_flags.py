"""add diary and identity exclusion flags to chat_threads

Revision ID: ef5f8a0c49a5
Revises: d3b3e9f5d5ab
Create Date: 2025-11-21 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ef5f8a0c49a5"
down_revision: Union[str, Sequence[str], None] = "d3b3e9f5d5ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_threads",
        sa.Column(
            "is_diary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "chat_threads",
        sa.Column(
            "exclude_from_identity",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("chat_threads", "exclude_from_identity")
    op.drop_column("chat_threads", "is_diary")
