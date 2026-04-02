"""add imprint observations and folded state tables

Revision ID: 4f6c8d1a2b3c
Revises: 8f1a2c3d4e5b
Create Date: 2026-04-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4f6c8d1a2b3c"
down_revision: Union[str, Sequence[str], None] = "8f1a2c3d4e5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "imprint_observations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column(
            "schema_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "provenance",
            sa.JSON(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column(
            "signal_payload",
            sa.JSON(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "schema_version >= 1",
            name="imprint_observations_schema_version_check",
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_imprint_observations_idempotency_key",
        ),
    )
    op.create_index(
        "ix_imprint_observations_user_project_created",
        "imprint_observations",
        ["user_id", "project_id", "created_at"],
    )
    op.create_index(
        "ix_imprint_observations_user_scope",
        "imprint_observations",
        ["user_id", "project_id"],
    )

    op.create_table(
        "imprint_fold_states",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope_key", sa.String(length=255), nullable=False),
        sa.Column("scope_kind", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column(
            "fold_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "source_observation_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "source_observation_max_id",
            sa.BigInteger(),
            nullable=True,
        ),
        sa.Column(
            "state_payload",
            sa.JSON(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "state_hash",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "scope_kind IN ('user_global','project_scoped')",
            name="imprint_fold_states_scope_kind_check",
        ),
        sa.UniqueConstraint(
            "scope_key", name="uq_imprint_fold_states_scope_key"
        ),
    )
    op.create_index(
        "ix_imprint_fold_states_user_scope",
        "imprint_fold_states",
        ["user_id", "scope_kind"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_imprint_fold_states_user_scope", table_name="imprint_fold_states"
    )
    op.drop_table("imprint_fold_states")
    op.drop_index(
        "ix_imprint_observations_user_scope", table_name="imprint_observations"
    )
    op.drop_index(
        "ix_imprint_observations_user_project_created",
        table_name="imprint_observations",
    )
    op.drop_table("imprint_observations")
