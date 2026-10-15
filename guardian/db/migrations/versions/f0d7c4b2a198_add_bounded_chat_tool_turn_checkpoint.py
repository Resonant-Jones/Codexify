"""Add the bounded chat tool decision checkpoint to accepted attempts.

Revision ID: f0d7c4b2a198
Revises: 17b23052da6a
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f0d7c4b2a198"
down_revision: str | Sequence[str] | None = "17b23052da6a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chat_completion_attempts", sa.Column("tool_turn_id", sa.String(128)))
    op.add_column("chat_completion_attempts", sa.Column("tool_command_id", sa.String(512)))
    op.add_column("chat_completion_attempts", sa.Column("tool_args_hash", sa.String(64)))
    op.add_column(
        "chat_completion_attempts",
        sa.Column("tool_checkpoint_at", sa.TIMESTAMP(timezone=True)),
    )
    op.create_check_constraint(
        "ck_chat_completion_attempt_tool_checkpoint_complete",
        "chat_completion_attempts",
        "(tool_turn_id IS NULL AND tool_command_id IS NULL AND "
        "tool_args_hash IS NULL AND tool_checkpoint_at IS NULL) OR "
        "(tool_turn_id IS NOT NULL AND tool_command_id IS NOT NULL AND "
        "tool_args_hash IS NOT NULL AND tool_checkpoint_at IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_chat_completion_attempt_tool_checkpoint_complete",
        "chat_completion_attempts",
        type_="check",
    )
    for name in ("tool_checkpoint_at", "tool_args_hash", "tool_command_id", "tool_turn_id"):
        op.drop_column("chat_completion_attempts", name)
