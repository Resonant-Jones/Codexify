"""add event graph events table for lineage emission

Revision ID: a7c9d1e2f3b4
Revises: f8ab1c2d3e4f
Create Date: 2026-02-16 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a7c9d1e2f3b4"
down_revision: Union[str, Sequence[str], None] = "f8ab1c2d3e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_graph_events",
        sa.Column(
            "event_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "occurred_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor_user_id", sa.String(length=255), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("thread_id", sa.Integer(), nullable=True),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("parent_event_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "payload_json",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()),
                "postgresql",
            ),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_event_graph_events_idempotency_key"
        ),
    )
    op.create_index(
        "ix_event_graph_event_type_occurred",
        "event_graph_events",
        ["event_type", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_event_graph_thread_occurred",
        "event_graph_events",
        ["thread_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_event_graph_entity",
        "event_graph_events",
        ["entity_type", "entity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_event_graph_entity", table_name="event_graph_events")
    op.drop_index(
        "ix_event_graph_thread_occurred", table_name="event_graph_events"
    )
    op.drop_index(
        "ix_event_graph_event_type_occurred", table_name="event_graph_events"
    )
    op.drop_table("event_graph_events")
