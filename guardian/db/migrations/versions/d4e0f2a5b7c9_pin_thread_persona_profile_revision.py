"""Pin account-owned thread Persona selections to immutable revisions.

Revision ID: d4e0f2a5b7c9
Revises: c3d9e1f4a6b8
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pydantic import ValidationError

from guardian.cognition.system_profiles.manifest import PersonaProfileManifest

revision = "d4e0f2a5b7c9"
down_revision = "c3d9e1f4a6b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_threads",
        sa.Column("active_profile_revision", sa.Integer(), nullable=True),
    )
    # This establishes a deterministic pin at migration time, not a claim
    # about the profile's historical revision when the thread was created.
    # Thread-local overrides remain revisionless even when their ID collides.
    connection = op.get_bind()
    candidates = connection.execute(
        sa.text(
            """
            SELECT t.id AS thread_id, p.current_revision, r.manifest_json
            FROM chat_threads AS t
            JOIN persona_profiles AS p ON t.active_profile_id = p.id
            JOIN persona_profile_bindings AS b ON b.profile_id = p.id
            JOIN persona_profile_revisions AS r
              ON r.profile_id = p.id AND r.revision = p.current_revision
            WHERE t.active_profile_id = p.id
              AND t.user_id = b.owner_account_id
              AND NOT COALESCE(
                  (t.metadata::jsonb -> 'profile_overrides') ? t.active_profile_id,
                  false
              )
              AND r.manifest_json ->> 'profileIdentity' = p.id
              AND r.manifest_json ->> 'revision' = p.current_revision::text
              AND r.manifest_json ->> 'apiVersion' = r.api_version
            """
        )
    )
    for row in candidates.mappings():
        try:
            PersonaProfileManifest.model_validate(row["manifest_json"])
        except ValidationError:
            continue
        connection.execute(
            sa.text(
                "UPDATE chat_threads SET active_profile_revision = :revision WHERE id = :thread_id"
            ),
            {"revision": row["current_revision"], "thread_id": row["thread_id"]},
        )
    op.create_check_constraint(
        "ck_chat_threads_active_profile_revision_positive",
        "chat_threads",
        "active_profile_revision IS NULL OR active_profile_revision > 0",
    )
    op.create_check_constraint(
        "ck_chat_threads_active_profile_revision_requires_id",
        "chat_threads",
        "active_profile_revision IS NULL OR active_profile_id IS NOT NULL",
    )
    # MATCH SIMPLE permits built-in/flow IDs when the revision is NULL.
    # No cascade or pin-clearing deletion behavior is introduced.
    op.create_foreign_key(
        "fk_chat_threads_persona_profile_revision",
        "chat_threads",
        "persona_profile_revisions",
        ["active_profile_id", "active_profile_revision"],
        ["profile_id", "revision"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_chat_threads_persona_profile_revision", "chat_threads", type_="foreignkey"
    )
    op.drop_constraint(
        "ck_chat_threads_active_profile_revision_requires_id",
        "chat_threads",
        type_="check",
    )
    op.drop_constraint(
        "ck_chat_threads_active_profile_revision_positive",
        "chat_threads",
        type_="check",
    )
    op.drop_column("chat_threads", "active_profile_revision")
