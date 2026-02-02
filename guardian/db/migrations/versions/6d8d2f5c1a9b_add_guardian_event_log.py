"""add guardian_event_log table

Revision ID: 6d8d2f5c1a9b
Revises: c6b2fdd401a9
Create Date: 2025-11-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6d8d2f5c1a9b"
down_revision: Union[str, Sequence[str], None] = "c6b2fdd401a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
        CREATE TABLE IF NOT EXISTS public.guardian_event_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            ts TIMESTAMPTZ NOT NULL DEFAULT now(),
            persona_tag TEXT NOT NULL,
            thread_id TEXT,
            message_id TEXT,
            event_type TEXT NOT NULL,
            origin TEXT NOT NULL,
            summary TEXT NOT NULL,
            payload JSONB
        );
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS public.guardian_event_log;")
