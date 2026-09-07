"""Persist stable account-owned Persona subjects and source bindings.

Revision ID: e5a9c2f7b4d1
Revises: d4e8f1a2b6c9
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "e5a9c2f7b4d1"
down_revision = "d4e8f1a2b6c9"
branch_labels = None
depends_on = None

PERSONA_SUBJECTS_TABLE = "persona_subjects"
PERSONA_SUBJECT_BINDINGS_TABLE = "persona_subject_bindings"
PERSONA_SUBJECT_NAMESPACE = uuid.UUID("19e873bc-d52f-5a63-b75a-69347655b302")
PERSONA_SUBJECT_BINDING_NAMESPACE = uuid.UUID("5cc4cab5-85c8-5e9f-8f0c-c51106845b6a")


def _required_account_id(value: object, source_label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{source_label} has no canonical account owner")
    return value.strip()


def _required_timestamp(value: object, source_label: str) -> datetime:
    if not isinstance(value, datetime):
        raise RuntimeError(f"{source_label} has no durable authoritative timestamp")
    return value


def _assert_accounts_exist(connection, account_ids: Sequence[str]) -> None:
    users = sa.table("users", sa.column("id", sa.String(length=255)))
    for account_id in sorted(set(account_ids)):
        exists = connection.execute(
            sa.select(users.c.id).where(users.c.id == account_id)
        ).scalar_one_or_none()
        if exists is None:
            raise RuntimeError(
                "Persona-subject source ownership references a missing account"
            )


def _subject_id(ref_kind: str, ref_id: str) -> str:
    return str(
        uuid.uuid5(PERSONA_SUBJECT_NAMESPACE, f"persona-subject:{ref_kind}:{ref_id}")
    )


def _binding_id(ref_kind: str, ref_id: str) -> str:
    return str(
        uuid.uuid5(
            PERSONA_SUBJECT_BINDING_NAMESPACE,
            f"persona-subject-binding:{ref_kind}:{ref_id}",
        )
    )


def _classify_legacy_sources(connection) -> list[dict[str, object]]:
    persona_rows = list(
        connection.execute(
            sa.text("SELECT id, user_id, created_at FROM personas ORDER BY id")
        ).mappings()
    )
    profile_rows = list(connection.execute(sa.text("""
                SELECT
                    p.id AS profile_id,
                    p.name AS profile_name,
                    b.owner_account_id AS owner_account_id,
                    b.created_at AS binding_created_at
                FROM persona_profiles AS p
                LEFT JOIN persona_profile_bindings AS b ON b.profile_id = p.id
                ORDER BY p.id, b.owner_account_id
                """)).mappings())

    classified: list[dict[str, object]] = []
    account_ids: list[str] = []
    seen_profile_ids: set[str] = set()

    for row in persona_rows:
        ref_id = str(row["id"])
        account_id = _required_account_id(row["user_id"], f"Persona {ref_id}")
        account_ids.append(account_id)
        classified.append(
            {
                "ref_kind": "persona",
                "ref_id": ref_id,
                "account_id": account_id,
                "display_name_snapshot": None,
                "valid_from": _required_timestamp(
                    row["created_at"], f"Persona {ref_id}"
                ),
            }
        )

    for row in profile_rows:
        profile_id = str(row["profile_id"])
        if profile_id in seen_profile_ids:
            raise RuntimeError(
                "PersonaProfile source has contradictory canonical account bindings"
            )
        seen_profile_ids.add(profile_id)
        account_id = _required_account_id(
            row["owner_account_id"],
            f"PersonaProfile {profile_id}",
        )
        account_ids.append(account_id)
        classified.append(
            {
                "ref_kind": "persona_profile",
                "ref_id": profile_id,
                "account_id": account_id,
                "display_name_snapshot": row["profile_name"],
                "valid_from": _required_timestamp(
                    row["binding_created_at"], f"PersonaProfile {profile_id}"
                ),
            }
        )

    _assert_accounts_exist(connection, account_ids)
    return classified


def upgrade() -> None:
    connection = op.get_bind()
    # Classify every source before adding any subject or binding data. An
    # unbound/contradictory source aborts the full migration rather than
    # partially backfilling the sources that happened to be unambiguous.
    classified_sources = _classify_legacy_sources(connection)

    op.create_table(
        PERSONA_SUBJECTS_TABLE,
        sa.Column("persona_subject_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("display_name_snapshot", sa.String(length=255), nullable=True),
        sa.Column(
            "lifecycle",
            sa.String(length=16),
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
        sa.PrimaryKeyConstraint("persona_subject_id", name="pk_persona_subjects"),
        sa.UniqueConstraint(
            "persona_subject_id",
            "user_id",
            name="uq_persona_subjects_subject_user",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_persona_subjects_user",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "lifecycle IN ('active', 'retired')",
            name="persona_subjects_lifecycle_check",
        ),
    )

    op.create_table(
        PERSONA_SUBJECT_BINDINGS_TABLE,
        sa.Column("binding_id", sa.String(length=36), nullable=False),
        sa.Column("persona_subject_id", sa.String(length=36), nullable=False),
        sa.Column("subject_user_id", sa.String(length=255), nullable=False),
        sa.Column("source_account_id", sa.String(length=255), nullable=False),
        sa.Column("ref_kind", sa.String(length=32), nullable=False),
        sa.Column("ref_id", sa.String(length=128), nullable=False),
        sa.Column("valid_from", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("valid_until", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("binding_id", name="pk_persona_subject_bindings"),
        sa.ForeignKeyConstraint(
            ["subject_user_id"],
            ["users.id"],
            name="fk_persona_subject_bindings_subject_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_account_id"],
            ["users.id"],
            name="fk_persona_subject_bindings_source_account",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["persona_subject_id", "subject_user_id"],
            ["persona_subjects.persona_subject_id", "persona_subjects.user_id"],
            name="fk_persona_subject_bindings_subject_account",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "ref_kind IN ('persona', 'persona_profile')",
            name="persona_subject_bindings_ref_kind_check",
        ),
        sa.CheckConstraint(
            "source_account_id = subject_user_id",
            name="persona_subject_bindings_source_account_check",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="persona_subject_bindings_validity_check",
        ),
    )
    op.create_index(
        "uq_persona_subject_bindings_active_ref",
        PERSONA_SUBJECT_BINDINGS_TABLE,
        ["ref_kind", "ref_id"],
        unique=True,
        postgresql_where=sa.text("valid_until IS NULL"),
    )

    subjects = sa.table(
        PERSONA_SUBJECTS_TABLE,
        sa.column("persona_subject_id", sa.String(length=36)),
        sa.column("user_id", sa.String(length=255)),
        sa.column("display_name_snapshot", sa.String(length=255)),
        sa.column("lifecycle", sa.String(length=16)),
    )
    bindings = sa.table(
        PERSONA_SUBJECT_BINDINGS_TABLE,
        sa.column("binding_id", sa.String(length=36)),
        sa.column("persona_subject_id", sa.String(length=36)),
        sa.column("subject_user_id", sa.String(length=255)),
        sa.column("source_account_id", sa.String(length=255)),
        sa.column("ref_kind", sa.String(length=32)),
        sa.column("ref_id", sa.String(length=128)),
        sa.column("valid_from", sa.TIMESTAMP(timezone=True)),
        sa.column("valid_until", sa.TIMESTAMP(timezone=True)),
    )

    subject_rows: list[dict[str, object]] = []
    binding_rows: list[dict[str, object]] = []
    for source in classified_sources:
        ref_kind = str(source["ref_kind"])
        ref_id = str(source["ref_id"])
        account_id = str(source["account_id"])
        subject_id = _subject_id(ref_kind, ref_id)
        subject_rows.append(
            {
                "persona_subject_id": subject_id,
                "user_id": account_id,
                "display_name_snapshot": source["display_name_snapshot"],
                "lifecycle": "active",
            }
        )
        binding_rows.append(
            {
                "binding_id": _binding_id(ref_kind, ref_id),
                "persona_subject_id": subject_id,
                "subject_user_id": account_id,
                "source_account_id": account_id,
                "ref_kind": ref_kind,
                "ref_id": ref_id,
                "valid_from": source["valid_from"],
                "valid_until": None,
            }
        )

    if subject_rows:
        connection.execute(subjects.insert(), subject_rows)
        connection.execute(bindings.insert(), binding_rows)


def downgrade() -> None:
    op.drop_index(
        "uq_persona_subject_bindings_active_ref",
        table_name=PERSONA_SUBJECT_BINDINGS_TABLE,
    )
    op.drop_table(PERSONA_SUBJECT_BINDINGS_TABLE)
    op.drop_table(PERSONA_SUBJECTS_TABLE)
