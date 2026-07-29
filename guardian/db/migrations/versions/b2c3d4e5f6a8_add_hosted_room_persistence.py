"""add Hosted Room persistence foundation

Revision ID: b2c3d4e5f6a8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-27 18:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROOM_STATUSES = ("active", "closed")
INVITE_STATUSES = ("accepted", "expired", "pending", "revoked")
PARTICIPANT_KINDS = ("agent", "human")
PARTICIPANT_ROLES = ("agent", "member", "owner")
PARTICIPANT_STATES = ("active", "removed")


def _domain_check(column: str, values: tuple[str, ...]) -> str:
    quoted_values = ",".join(repr(value) for value in values)
    return f"{column} IN ({quoted_values})"


def upgrade() -> None:
    op.create_table(
        "hosted_rooms",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_account_id", sa.String(length=255), nullable=False),
        sa.Column("backing_thread_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "enabled_agent_ids",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()),
                "postgresql",
            ),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
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
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True)),
        sa.CheckConstraint(
            _domain_check("status", ROOM_STATUSES),
            name="hosted_rooms_status_check",
        ),
        sa.CheckConstraint(
            "(status = 'active' AND closed_at IS NULL) "
            "OR (status = 'closed' AND closed_at IS NOT NULL)",
            name="hosted_rooms_lifecycle_check",
        ),
        sa.CheckConstraint(
            "slug <> '' AND slug NOT LIKE '% %'",
            name="hosted_rooms_slug_check",
        ),
        sa.CheckConstraint(
            "length(CAST(enabled_agent_ids AS TEXT)) <= 4096",
            name="hosted_rooms_enabled_agent_ids_size_check",
        ),
        sa.ForeignKeyConstraint(
            ["owner_account_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["backing_thread_id"],
            ["chat_threads.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "backing_thread_id",
            name="uq_hosted_rooms_backing_thread_id",
        ),
        sa.UniqueConstraint("slug", name="uq_hosted_rooms_slug"),
    )
    op.create_index(
        "ix_hosted_rooms_owner_account_id",
        "hosted_rooms",
        ["owner_account_id"],
    )

    op.create_table(
        "hosted_room_invites",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("room_id", sa.String(length=36), nullable=False),
        sa.Column(
            "intended_display_name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("accepted_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("expired_at", sa.TIMESTAMP(timezone=True)),
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
            _domain_check("status", INVITE_STATUSES),
            name="hosted_room_invites_status_check",
        ),
        sa.CheckConstraint(
            "("
            "status = 'pending' "
            "AND accepted_at IS NULL "
            "AND revoked_at IS NULL "
            "AND expired_at IS NULL"
            ") OR ("
            "status = 'accepted' "
            "AND accepted_at IS NOT NULL "
            "AND revoked_at IS NULL "
            "AND expired_at IS NULL"
            ") OR ("
            "status = 'revoked' "
            "AND revoked_at IS NOT NULL "
            "AND expired_at IS NULL"
            ") OR ("
            "status = 'expired' "
            "AND expired_at IS NOT NULL "
            "AND accepted_at IS NULL "
            "AND revoked_at IS NULL"
            ")",
            name="hosted_room_invites_lifecycle_check",
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["hosted_rooms.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "token_hash",
            name="uq_hosted_room_invites_token_hash",
        ),
    )
    op.create_index(
        "ix_hosted_room_invites_room_id",
        "hosted_room_invites",
        ["room_id"],
    )

    op.create_table(
        "hosted_room_participants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("room_id", sa.String(length=36), nullable=False),
        sa.Column("invitation_id", sa.String(length=36)),
        sa.Column("bound_account_id", sa.String(length=255)),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column(
            "state",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "joined_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("removed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            _domain_check("kind", PARTICIPANT_KINDS),
            name="hosted_room_participants_kind_check",
        ),
        sa.CheckConstraint(
            _domain_check("role", PARTICIPANT_ROLES),
            name="hosted_room_participants_role_check",
        ),
        sa.CheckConstraint(
            _domain_check("state", PARTICIPANT_STATES),
            name="hosted_room_participants_state_check",
        ),
        sa.CheckConstraint(
            "("
            "kind = 'human' "
            "AND role = 'owner' "
            "AND bound_account_id IS NOT NULL"
            ") OR ("
            "kind = 'human' "
            "AND role = 'member'"
            ") OR ("
            "kind = 'agent' "
            "AND role = 'agent' "
            "AND bound_account_id IS NULL"
            ")",
            name="hosted_room_participants_kind_role_check",
        ),
        sa.CheckConstraint(
            "(state = 'active' AND removed_at IS NULL) "
            "OR (state = 'removed' AND removed_at IS NOT NULL)",
            name="hosted_room_participants_lifecycle_check",
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["hosted_rooms.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invitation_id"],
            ["hosted_room_invites.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["bound_account_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "invitation_id",
            name="uq_hosted_room_participants_invitation_id",
        ),
    )
    op.create_index(
        "ix_hosted_room_participants_room_id",
        "hosted_room_participants",
        ["room_id"],
    )
    op.create_index(
        "ix_hosted_room_participants_room_state",
        "hosted_room_participants",
        ["room_id", "state"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_hosted_room_participants_room_state",
        table_name="hosted_room_participants",
    )
    op.drop_index(
        "ix_hosted_room_participants_room_id",
        table_name="hosted_room_participants",
    )
    op.drop_table("hosted_room_participants")

    op.drop_index(
        "ix_hosted_room_invites_room_id",
        table_name="hosted_room_invites",
    )
    op.drop_table("hosted_room_invites")

    op.drop_index(
        "ix_hosted_rooms_owner_account_id",
        table_name="hosted_rooms",
    )
    op.drop_table("hosted_rooms")
