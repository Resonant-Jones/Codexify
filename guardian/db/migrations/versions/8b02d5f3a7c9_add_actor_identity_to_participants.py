"""add actor identity to hosted_room_participants

Revision ID: 8b02d5f3a7c9
Revises: 7a91c4e2f6b8
Create Date: 2026-07-28 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "8b02d5f3a7c9"
down_revision: Union[str, Sequence[str], None] = "7a91c4e2f6b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_column(column_name: str) -> bool:
    return column_name in {
        column["name"]
        for column in _inspector().get_columns("hosted_room_participants")
    }


def _has_constraint(constraint_name: str, constraint_type: str) -> bool:
    inspector = _inspector()
    if constraint_type == "check":
        constraints = inspector.get_check_constraints("hosted_room_participants")
    else:
        constraints = inspector.get_unique_constraints("hosted_room_participants")
    return constraint_name in {
        constraint.get("name") for constraint in constraints
    }


def upgrade() -> None:
    # Add nullable actor identity columns
    if not _has_column("actor_source"):
        op.add_column(
            "hosted_room_participants",
            sa.Column("actor_source", sa.String(length=32), nullable=True),
        )
    if not _has_column("actor_ref"):
        op.add_column(
            "hosted_room_participants",
            sa.Column("actor_ref", sa.String(length=128), nullable=True),
        )

    # Human participants must have null actor fields;
    # agent participants must have non-null actor fields.
    if not _has_constraint("hosted_room_participants_actor_check", "check"):
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
    if not _has_constraint(
        "uq_hosted_room_participants_room_actor", "unique"
    ):
        op.create_unique_constraint(
            "uq_hosted_room_participants_room_actor",
            "hosted_room_participants",
            ["room_id", "actor_source", "actor_ref"],
        )


def downgrade() -> None:
    if _has_constraint("uq_hosted_room_participants_room_actor", "unique"):
        op.drop_constraint(
            "uq_hosted_room_participants_room_actor",
            "hosted_room_participants",
            type_="unique",
        )
    if _has_constraint("hosted_room_participants_actor_check", "check"):
        op.drop_constraint(
            "hosted_room_participants_actor_check",
            "hosted_room_participants",
            type_="check",
        )
    if _has_column("actor_ref"):
        op.drop_column("hosted_room_participants", "actor_ref")
    if _has_column("actor_source"):
        op.drop_column("hosted_room_participants", "actor_source")
