"""Add the ThreadSpace node-membership persistence foundation.

Revision ID: d6f7a8b9c0d1
Revises: c1a2b3c4d5e6
Create Date: 2026-08-03 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from guardian.threadspace.membership_tokens import (
    INVITATION_STATES,
    MEMBERSHIP_LIFECYCLE_STATES,
    NODE_MEMBERSHIP_ROLES,
    NODE_STATUSES,
)

revision: str = "d6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "c1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _sql_values(values: frozenset[str]) -> str:
    return ",".join(repr(value) for value in sorted(values))


def upgrade() -> None:
    """Create durable node, invitation, and membership-grant records."""
    op.create_table(
        "threadspace_nodes",
        sa.Column("node_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'active'"),
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
        sa.PrimaryKeyConstraint("node_id"),
        sa.CheckConstraint(
            f"status IN ({_sql_values(NODE_STATUSES)})",
            name="threadspace_nodes_status_check",
        ),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name="threadspace_nodes_name_check",
        ),
    )

    op.create_table(
        "threadspace_membership_invitations",
        sa.Column("invitation_id", sa.String(length=64), nullable=False),
        sa.Column("node_id", sa.String(length=64), nullable=False),
        sa.Column("intended_account_id", sa.String(length=255), nullable=False),
        sa.Column("proposed_role", sa.String(length=32), nullable=False),
        sa.Column(
            "state",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("issuer_account_id", sa.String(length=255), nullable=False),
        sa.Column(
            "issued_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("declined_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "accepted_by_account_id", sa.String(length=255), nullable=True
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
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
        sa.PrimaryKeyConstraint("invitation_id"),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["threadspace_nodes.node_id"],
            name="fk_threadspace_membership_invitations_node",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["intended_account_id"],
            ["users.id"],
            name="fk_threadspace_membership_invitations_intended_account",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["issuer_account_id"],
            ["users.id"],
            name="fk_threadspace_membership_invitations_issuer_account",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_by_account_id"],
            ["users.id"],
            name="fk_threadspace_membership_invitations_accepted_by_account",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "node_id",
            "issuer_account_id",
            "idempotency_key",
            name="uq_threadspace_membership_invitations_idempotency",
        ),
        sa.CheckConstraint(
            f"proposed_role IN ({_sql_values(NODE_MEMBERSHIP_ROLES)})",
            name="threadspace_membership_invitations_role_check",
        ),
        sa.CheckConstraint(
            f"state IN ({_sql_values(INVITATION_STATES)})",
            name="threadspace_membership_invitations_state_check",
        ),
        sa.CheckConstraint(
            """
            (
                (state = 'pending'
                    AND accepted_at IS NULL
                    AND declined_at IS NULL
                    AND revoked_at IS NULL)
                OR
                (state = 'accepted'
                    AND accepted_at IS NOT NULL
                    AND accepted_by_account_id IS NOT NULL
                    AND declined_at IS NULL
                    AND revoked_at IS NULL)
                OR
                (state = 'declined'
                    AND accepted_at IS NULL
                    AND accepted_by_account_id IS NULL
                    AND declined_at IS NOT NULL
                    AND revoked_at IS NULL)
                OR
                (state = 'revoked'
                    AND accepted_at IS NULL
                    AND accepted_by_account_id IS NULL
                    AND declined_at IS NULL
                    AND revoked_at IS NOT NULL)
                OR
                (state = 'expired'
                    AND accepted_at IS NULL
                    AND accepted_by_account_id IS NULL
                    AND declined_at IS NULL
                    AND revoked_at IS NULL
                    AND expires_at IS NOT NULL)
            )
            """,
            name="threadspace_membership_invitations_lifecycle_check",
        ),
        sa.CheckConstraint(
            "length(idempotency_key) > 0",
            name="threadspace_membership_invitations_idempotency_key_check",
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at >= issued_at",
            name="threadspace_membership_invitations_expiry_check",
        ),
        sa.CheckConstraint(
            "accepted_at IS NULL OR accepted_at >= issued_at",
            name="threadspace_membership_invitations_accepted_order_check",
        ),
        sa.CheckConstraint(
            "declined_at IS NULL OR declined_at >= issued_at",
            name="threadspace_membership_invitations_declined_order_check",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= issued_at",
            name="threadspace_membership_invitations_revoked_order_check",
        ),
    )
    op.create_index(
        "ix_threadspace_membership_invitations_node_id",
        "threadspace_membership_invitations",
        ["node_id"],
    )
    op.create_index(
        "ix_threadspace_membership_invitations_intended_account_id",
        "threadspace_membership_invitations",
        ["intended_account_id"],
    )
    op.create_index(
        "ix_threadspace_membership_invitations_state",
        "threadspace_membership_invitations",
        ["state"],
    )

    op.create_table(
        "threadspace_membership_grants",
        sa.Column("membership_id", sa.String(length=64), nullable=False),
        sa.Column("node_id", sa.String(length=64), nullable=False),
        sa.Column("subject_account_id", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "lifecycle_state",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("source_invitation_id", sa.String(length=64), nullable=True),
        sa.Column("issuer_account_id", sa.String(length=255), nullable=False),
        sa.Column(
            "accepted_by_account_id", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "record_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "effective_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("suspended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "suspended_by_account_id", sa.String(length=255), nullable=True
        ),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "revoked_by_account_id", sa.String(length=255), nullable=True
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.String(length=512), nullable=True),
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
        sa.PrimaryKeyConstraint("membership_id"),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["threadspace_nodes.node_id"],
            name="fk_threadspace_membership_grants_node",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["subject_account_id"],
            ["users.id"],
            name="fk_threadspace_membership_grants_subject_account",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_invitation_id"],
            ["threadspace_membership_invitations.invitation_id"],
            name="fk_threadspace_membership_grants_source_invitation",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["issuer_account_id"],
            ["users.id"],
            name="fk_threadspace_membership_grants_issuer_account",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_by_account_id"],
            ["users.id"],
            name="fk_threadspace_membership_grants_accepted_by_account",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["suspended_by_account_id"],
            ["users.id"],
            name="fk_threadspace_membership_grants_suspended_by_account",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by_account_id"],
            ["users.id"],
            name="fk_threadspace_membership_grants_revoked_by_account",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "source_invitation_id",
            name="uq_threadspace_membership_grants_source_invitation",
        ),
        sa.CheckConstraint(
            f"role IN ({_sql_values(NODE_MEMBERSHIP_ROLES)})",
            name="threadspace_membership_grants_role_check",
        ),
        sa.CheckConstraint(
            f"lifecycle_state IN ({_sql_values(MEMBERSHIP_LIFECYCLE_STATES)})",
            name="threadspace_membership_grants_lifecycle_state_check",
        ),
        sa.CheckConstraint(
            """
            (
                (
                    source_invitation_id IS NULL
                    AND role IN ('node_owner', 'node_operator')
                    AND accepted_by_account_id IS NULL
                )
                OR
                (
                    source_invitation_id IS NOT NULL
                    AND accepted_by_account_id IS NOT NULL
                )
            )
            """,
            name="threadspace_membership_grants_source_check",
        ),
        sa.CheckConstraint(
            """
            (
                (lifecycle_state = 'invited' AND revoked_at IS NULL)
                OR (lifecycle_state = 'active' AND revoked_at IS NULL)
                OR (
                    lifecycle_state = 'suspended'
                    AND suspended_at IS NOT NULL
                    AND suspended_by_account_id IS NOT NULL
                    AND revoked_at IS NULL
                )
                OR (
                    lifecycle_state = 'revoked'
                    AND revoked_at IS NOT NULL
                    AND revoked_by_account_id IS NOT NULL
                )
                OR (
                    lifecycle_state = 'expired'
                    AND expires_at IS NOT NULL
                    AND revoked_at IS NULL
                )
            )
            """,
            name="threadspace_membership_grants_lifecycle_check",
        ),
        sa.CheckConstraint(
            "record_version > 0",
            name="threadspace_membership_grants_record_version_check",
        ),
        sa.CheckConstraint(
            "suspended_at IS NULL OR suspended_at >= effective_at",
            name="threadspace_membership_grants_suspended_order_check",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= effective_at",
            name="threadspace_membership_grants_revoked_order_check",
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at >= effective_at",
            name="threadspace_membership_grants_expiry_check",
        ),
        sa.CheckConstraint(
            "revocation_reason IS NULL OR revoked_at IS NOT NULL",
            name="threadspace_membership_grants_revocation_reason_check",
        ),
    )
    op.create_index(
        "ix_threadspace_membership_grants_node_id",
        "threadspace_membership_grants",
        ["node_id"],
    )
    op.create_index(
        "ix_threadspace_membership_grants_subject_account_id",
        "threadspace_membership_grants",
        ["subject_account_id"],
    )
    op.create_index(
        "ix_threadspace_membership_grants_lifecycle_state",
        "threadspace_membership_grants",
        ["lifecycle_state"],
    )
    op.create_index(
        "uq_threadspace_membership_grants_node_subject_non_revoked",
        "threadspace_membership_grants",
        ["node_id", "subject_account_id"],
        unique=True,
        postgresql_where=sa.text("lifecycle_state <> 'revoked'"),
    )


def downgrade() -> None:
    """Remove only the ThreadSpace membership structures from this revision."""
    op.drop_index(
        "uq_threadspace_membership_grants_node_subject_non_revoked",
        table_name="threadspace_membership_grants",
    )
    op.drop_index(
        "ix_threadspace_membership_grants_lifecycle_state",
        table_name="threadspace_membership_grants",
    )
    op.drop_index(
        "ix_threadspace_membership_grants_subject_account_id",
        table_name="threadspace_membership_grants",
    )
    op.drop_index(
        "ix_threadspace_membership_grants_node_id",
        table_name="threadspace_membership_grants",
    )
    op.drop_table("threadspace_membership_grants")

    op.drop_index(
        "ix_threadspace_membership_invitations_state",
        table_name="threadspace_membership_invitations",
    )
    op.drop_index(
        "ix_threadspace_membership_invitations_intended_account_id",
        table_name="threadspace_membership_invitations",
    )
    op.drop_index(
        "ix_threadspace_membership_invitations_node_id",
        table_name="threadspace_membership_invitations",
    )
    op.drop_table("threadspace_membership_invitations")
    op.drop_table("threadspace_nodes")
