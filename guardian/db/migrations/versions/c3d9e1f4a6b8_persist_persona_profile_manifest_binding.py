"""persist Persona Profile manifests, revisions, and account bindings

Revision ID: c3d9e1f4a6b8
Revises: b2c8d0e3f5a7
Create Date: 2026-09-04 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "c3d9e1f4a6b8"
down_revision: str | Sequence[str] | None = "b2c8d0e3f5a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

API_VERSION = "codexify.persona/v1"
PROFILES_TABLE = "persona_profiles"
REVISIONS_TABLE = "persona_profile_revisions"
BINDINGS_TABLE = "persona_profile_bindings"


def _legacy_manifest(row: dict[str, Any]) -> dict[str, Any]:
    """Build a sparse revision-1 manifest from only persisted legacy data."""
    return {
        "apiVersion": API_VERSION,
        "profileIdentity": row["id"],
        "revision": 1,
        "identity": {"name": row["name"]},
        "prompt": {"systemPrompt": row["system_prompt"]},
        "model": {
            "provider": row["model_provider"],
            "model": row["model_id"],
            "temperature": float(row["temperature"]),
        },
    }


def upgrade() -> None:
    connection = op.get_bind()

    op.add_column(
        PROFILES_TABLE,
        sa.Column("current_revision", sa.Integer(), nullable=True),
    )

    op.create_table(
        REVISIONS_TABLE,
        sa.Column("profile_id", sa.String(length=128), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("api_version", sa.String(length=64), nullable=False),
        sa.Column(
            "manifest_json",
            sa.JSON().with_variant(JSONB, "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint(
            "profile_id",
            "revision",
            name="pk_persona_profile_revisions",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            [f"{PROFILES_TABLE}.id"],
            name="fk_persona_profile_revisions_profile",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "revision > 0",
            name="persona_profile_revisions_revision_check",
        ),
    )
    op.create_index(
        "ix_persona_profile_revisions_profile_created_at",
        REVISIONS_TABLE,
        ["profile_id", "created_at"],
    )

    op.create_table(
        BINDINGS_TABLE,
        sa.Column("profile_id", sa.String(length=128), nullable=False),
        sa.Column("owner_account_id", sa.String(length=255), nullable=False),
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
        sa.PrimaryKeyConstraint("profile_id"),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            [f"{PROFILES_TABLE}.id"],
            name="fk_persona_profile_bindings_profile",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_account_id"],
            ["users.id"],
            name="fk_persona_profile_bindings_owner_account",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_persona_profile_bindings_owner_account_id",
        BINDINGS_TABLE,
        ["owner_account_id"],
    )

    profiles = sa.table(
        PROFILES_TABLE,
        sa.column("id", sa.String(length=128)),
        sa.column("name", sa.String(length=255)),
        sa.column("system_prompt", sa.Text()),
        sa.column("model_provider", sa.String(length=64)),
        sa.column("model_id", sa.String(length=255)),
        sa.column("temperature", sa.Float()),
        sa.column("current_revision", sa.Integer()),
        sa.column("created_at", sa.TIMESTAMP(timezone=True)),
        sa.column("updated_at", sa.TIMESTAMP(timezone=True)),
    )
    revisions = sa.table(
        REVISIONS_TABLE,
        sa.column("profile_id", sa.String(length=128)),
        sa.column("revision", sa.Integer()),
        sa.column("api_version", sa.String(length=64)),
        sa.column(
            "manifest_json",
            sa.JSON().with_variant(JSONB, "postgresql"),
        ),
        sa.column("created_at", sa.TIMESTAMP(timezone=True)),
    )
    bindings = sa.table(
        BINDINGS_TABLE,
        sa.column("profile_id", sa.String(length=128)),
        sa.column("owner_account_id", sa.String(length=255)),
        sa.column("created_at", sa.TIMESTAMP(timezone=True)),
        sa.column("updated_at", sa.TIMESTAMP(timezone=True)),
    )

    profile_rows = list(
        connection.execute(
            sa.select(
                profiles.c.id,
                profiles.c.name,
                profiles.c.system_prompt,
                profiles.c.model_provider,
                profiles.c.model_id,
                profiles.c.temperature,
                profiles.c.created_at,
                profiles.c.updated_at,
            )
        ).mappings()
    )
    if profile_rows:
        connection.execute(
            revisions.insert(),
            [
                {
                    "profile_id": row["id"],
                    "revision": 1,
                    "api_version": API_VERSION,
                    "manifest_json": _legacy_manifest(dict(row)),
                    "created_at": row["created_at"],
                }
                for row in profile_rows
            ],
        )
        connection.execute(profiles.update().values(current_revision=1))

    users = sa.table("users", sa.column("id", sa.String(length=255)))
    user_ids = list(
        connection.execute(
            sa.select(users.c.id).order_by(users.c.id.asc()).limit(2)
        ).scalars()
    )
    if len(user_ids) == 1 and profile_rows:
        owner_account_id = user_ids[0]
        connection.execute(
            bindings.insert(),
            [
                {
                    "profile_id": row["id"],
                    "owner_account_id": owner_account_id,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in profile_rows
            ],
        )

    op.alter_column(
        PROFILES_TABLE,
        "current_revision",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_check_constraint(
        "persona_profiles_current_revision_check",
        PROFILES_TABLE,
        "current_revision > 0",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_persona_profile_bindings_owner_account_id",
        table_name=BINDINGS_TABLE,
    )
    op.drop_table(BINDINGS_TABLE)

    op.drop_index(
        "ix_persona_profile_revisions_profile_created_at",
        table_name=REVISIONS_TABLE,
    )
    op.drop_table(REVISIONS_TABLE)

    op.drop_constraint(
        "persona_profiles_current_revision_check",
        PROFILES_TABLE,
        type_="check",
    )
    op.drop_column(PROFILES_TABLE, "current_revision")
