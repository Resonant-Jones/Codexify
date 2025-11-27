"""add audit_log table

Revision ID: 2fa2ab3faac6
Revises: 1eb6836bb10e
Create Date: 2025-10-24 22:35:58.174725

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2fa2ab3faac6"
down_revision: Union[str, Sequence[str], None] = "1eb6836bb10e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS public;
        CREATE TABLE IF NOT EXISTS public.audit_log (
            id BIGSERIAL PRIMARY KEY,
            event TEXT NOT NULL,
            entity TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            "timestamp" TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_audit_log_ts ON public.audit_log ("timestamp" DESC);'
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON public.audit_log (entity, entity_id);"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS public.idx_audit_log_entity;")
    op.execute("DROP INDEX IF EXISTS public.idx_audit_log_ts;")
    op.execute("DROP TABLE IF EXISTS public.audit_log;")
