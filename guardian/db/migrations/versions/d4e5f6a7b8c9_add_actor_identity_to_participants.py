"""add actor identity to hosted_room_participants

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-28 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add nullable actor identity columns
    op.add_column(
        "hosted_room_participants",
        sa.Column("actor_source", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "hosted_room_participants",
        sa.Column("actor_ref", sa.String(length=128), nullable=True),
    )

    # Human participants must have null actor fields;
    # agent participants must have non-null actor fields.
    op.create_check_constraint(
        "hosted_room_participants_actor_check",
        "hosted_room_participants",
        (
            "("
            "kind = 'agent' AND role = 'agent' "
            "AND actor_source IS NOT NULL AND actor_ref IS NOT NULL"
            ") OR ("
            "kind = 'human' "
            "AND actor_source IS NULL AND actor_ref IS NULL"
            ")"
        ),
    )

    # One participant per room per actor binding
    op.create_unique_constraint(
        "uq_hosted_room_participants_room_actor",
        "hosted_room_participants",
        ["room_id", "actor_source", "actor_ref"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_hosted_room_participants_room_actor",
        "hosted_room_participants",
        type_="unique",
    )
    op.drop_constraint(
        "hosted_room_participants_actor_check",
        "hosted_room_participants",
        type_="check",
    )
    op.drop_column("hosted_room_participants", "actor_ref")
    op.drop_column("hosted_room_participants", "actor_source")
