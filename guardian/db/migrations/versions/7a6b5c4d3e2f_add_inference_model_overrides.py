"""add inference model overrides table

Revision ID: 7a6b5c4d3e2f
Revises: d7e8f9a0b1c2, f2b3c4d5e6f9
Create Date: 2026-05-03 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7a6b5c4d3e2f"
down_revision: Union[str, Sequence[str], None] = (
    "d7e8f9a0b1c2",
    "f2b3c4d5e6f9",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "inference_model_overrides",
        sa.Column(
            "provider_id",
            sa.Text(),
            sa.ForeignKey(
                "inference_providers.provider_id",
                ondelete="CASCADE",
            ),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("model_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("display_label", sa.Text(), nullable=True),
        sa.Column("picker_label", sa.Text(), nullable=True),
        sa.Column("supports_chat", sa.Boolean(), nullable=True),
        sa.Column("supports_vision", sa.Boolean(), nullable=True),
        sa.Column("supports_text_input", sa.Boolean(), nullable=True),
        sa.Column("model_kind", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "model_kind IS NULL OR model_kind IN ('chat','vision_chat','utility')",
            name="ck_inference_model_overrides_model_kind",
        ),
    )
    op.create_index(
        "ix_inference_model_overrides_provider_id",
        "inference_model_overrides",
        ["provider_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_inference_model_overrides_provider_id",
        table_name="inference_model_overrides",
    )
    op.drop_table("inference_model_overrides")
