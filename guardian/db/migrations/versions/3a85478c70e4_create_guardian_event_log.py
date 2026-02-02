"""Create guardian_event_log.

Revision ID: 3a85478c70e4
Revises: 13a4a6dc5ba1
Create Date: 2026-01-26 18:17:08.937218

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3a85478c70e4"
down_revision: Union[str, Sequence[str], None] = "13a4a6dc5ba1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind, table_name: str, schema: str = "public") -> bool:
    insp = sa.inspect(bind)
    return table_name in insp.get_table_names(schema=schema)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if _table_exists(bind, "guardian_event_log"):
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.create_table(
        "guardian_event_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "ts",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("persona_tag", sa.Text(), nullable=False),
        sa.Column("thread_id", sa.Text(), nullable=True),
        sa.Column("message_id", sa.Text(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if not _table_exists(bind, "guardian_event_log"):
        return

    op.drop_table("guardian_event_log", schema="public")
