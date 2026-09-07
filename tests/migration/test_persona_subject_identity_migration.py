"""Real PostgreSQL/Alembic proof for stable Persona-subject persistence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from tests.migration import (
    test_persona_profile_manifest_binding_migration as persona_profile_migration,
)
from tests.migration.test_persona_profile_manifest_binding_migration import (
    _insert_user,
    _upgrade,
)

PARENT_REVISION = "d4e8f1a2b6c9"
PERSONA_SUBJECT_REVISION = "e5a9c2f7b4d1"
PERSONA_SUBJECT_TABLES = {"persona_subjects", "persona_subject_bindings"}
NOW = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def temporary_postgres(monkeypatch):
    """Reuse the repository's disposable PostgreSQL fixture unchanged."""

    yield from persona_profile_migration.temporary_postgres.__wrapped__(monkeypatch)


def _insert_legacy_persona(
    connection,
    account_id: str,
    *,
    created_at: datetime,
    is_active: bool,
) -> int:
    return int(
        connection.execute(
            sa.text("""
                INSERT INTO personas (user_id, body, source, is_active, created_at)
                VALUES (:account_id, 'Stable subject source', 'user', :is_active, :created_at)
                RETURNING id
                """),
            {
                "account_id": account_id,
                "created_at": created_at,
                "is_active": is_active,
            },
        ).scalar_one()
    )


def _insert_legacy_profile(
    connection,
    profile_id: str,
    account_id: str,
    *,
    name: str,
    binding_created_at: datetime | None,
) -> None:
    connection.execute(
        sa.text("""
            INSERT INTO persona_profiles
                (
                    id, name, system_prompt, model_provider, model_id,
                    temperature, current_revision
                )
            VALUES
                (
                    :profile_id, :name, 'Stable subject source', 'local', 'model',
                    0.0, 1
                )
            """),
        {"profile_id": profile_id, "name": name},
    )
    _insert_profile_revision(
        connection,
        profile_id,
        revision=1,
        created_at=binding_created_at or NOW,
    )
    if binding_created_at is not None:
        connection.execute(
            sa.text("""
                INSERT INTO persona_profile_bindings
                    (profile_id, owner_account_id, created_at)
                VALUES (:profile_id, :account_id, :created_at)
                """),
            {
                "profile_id": profile_id,
                "account_id": account_id,
                "created_at": binding_created_at,
            },
        )


def _insert_profile_revision(
    connection,
    profile_id: str,
    *,
    revision: int,
    created_at: datetime,
) -> None:
    connection.execute(
        sa.text("""
            INSERT INTO persona_profile_revisions (
                profile_id, revision, api_version, manifest_json, created_at
            ) VALUES (
                CAST(:profile_id AS TEXT), :revision, 'codexify.persona/v1',
                jsonb_build_object(
                    'apiVersion', 'codexify.persona/v1',
                    'profileIdentity', :profile_id,
                    'revision', :revision,
                    'identity', jsonb_build_object('name', 'Stable subject source'),
                    'prompt', jsonb_build_object('systemPrompt', 'Stable subject source'),
                    'model', jsonb_build_object(
                        'provider', 'local', 'model', 'model', 'temperature', 0.0
                    )
                ),
                :created_at
            )
            """),
        {
            "profile_id": profile_id,
            "revision": revision,
            "created_at": created_at,
        },
    )


def _downgrade(config, revision: str) -> None:
    from alembic import command

    command.downgrade(config, revision)


@pytest.mark.integration
def test_empty_parent_replay_creates_no_subject_rows(temporary_postgres) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PARENT_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "UPDATE chat_threads SET active_profile_id = NULL, "
                    "active_profile_revision = NULL"
                )
            )
            connection.execute(sa.text("DELETE FROM persona_profile_bindings"))
            connection.execute(sa.text("DELETE FROM persona_profile_revisions"))
            connection.execute(sa.text("DELETE FROM persona_profiles"))
            connection.execute(sa.text("DELETE FROM personas"))

        _upgrade(config, PERSONA_SUBJECT_REVISION)

        with engine.connect() as connection:
            assert (
                connection.execute(
                    sa.text("SELECT count(*) FROM persona_subjects")
                ).scalar_one()
                == 0
            )
            assert (
                connection.execute(
                    sa.text("SELECT count(*) FROM persona_subject_bindings")
                ).scalar_one()
                == 0
            )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_upgrade_backfills_one_active_subject_per_legacy_source_and_constraints(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PARENT_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            account_a = connection.execute(
                sa.text("SELECT id FROM users ORDER BY id LIMIT 1")
            ).scalar_one()
            _insert_user(connection, "account-b")
            persona_a = _insert_legacy_persona(
                connection,
                account_a,
                created_at=NOW,
                is_active=False,
            )
            persona_b = _insert_legacy_persona(
                connection,
                "account-b",
                created_at=NOW + timedelta(seconds=1),
                is_active=True,
            )
            _insert_legacy_profile(
                connection,
                "profile-a",
                account_a,
                name="Same name is not an identity key",
                binding_created_at=NOW + timedelta(seconds=2),
            )
            _insert_legacy_profile(
                connection,
                "profile-b",
                "account-b",
                name="Same name is not an identity key",
                binding_created_at=NOW + timedelta(seconds=3),
            )
            _insert_profile_revision(
                connection,
                "profile-a",
                revision=2,
                created_at=NOW + timedelta(seconds=4),
            )
            connection.execute(
                sa.text(
                    "UPDATE persona_profiles SET current_revision = 2 "
                    "WHERE id = 'profile-a'"
                )
            )

        _upgrade(config, PERSONA_SUBJECT_REVISION)

        with engine.connect() as connection:
            rows = connection.execute(
                sa.text("""
                    SELECT
                        s.persona_subject_id,
                        s.user_id,
                        s.display_name_snapshot,
                        s.lifecycle,
                        b.binding_id,
                        b.subject_user_id,
                        b.source_account_id,
                        b.ref_kind,
                        b.ref_id,
                        b.valid_from,
                        b.valid_until
                    FROM persona_subjects AS s
                    JOIN persona_subject_bindings AS b
                      ON b.persona_subject_id = s.persona_subject_id
                     AND b.subject_user_id = s.user_id
                    WHERE (b.ref_kind, b.ref_id) IN (
                        ('persona', :persona_a),
                        ('persona', :persona_b),
                        ('persona_profile', 'profile-a'),
                        ('persona_profile', 'profile-b')
                    )
                    ORDER BY b.ref_kind, b.ref_id
                    """),
                {"persona_a": str(persona_a), "persona_b": str(persona_b)},
            ).mappings()
            by_source = {(row["ref_kind"], row["ref_id"]): row for row in rows}

            expected_sources = {
                ("persona", str(persona_a)): (account_a, None, NOW),
                ("persona", str(persona_b)): (
                    "account-b",
                    None,
                    NOW + timedelta(seconds=1),
                ),
                ("persona_profile", "profile-a"): (
                    account_a,
                    "Same name is not an identity key",
                    NOW + timedelta(seconds=2),
                ),
                ("persona_profile", "profile-b"): (
                    "account-b",
                    "Same name is not an identity key",
                    NOW + timedelta(seconds=3),
                ),
            }
            assert set(by_source) == set(expected_sources)
            assert len({row["persona_subject_id"] for row in by_source.values()}) == 4
            for source, (account_id, snapshot, valid_from) in expected_sources.items():
                row = by_source[source]
                assert row["user_id"] == account_id
                assert row["subject_user_id"] == account_id
                assert row["source_account_id"] == account_id
                assert row["display_name_snapshot"] == snapshot
                assert row["lifecycle"] == "active"
                assert row["valid_from"] == valid_from
                assert row["valid_until"] is None
            assert (
                connection.execute(
                    sa.text(
                        "SELECT count(*) FROM persona_profile_revisions "
                        "WHERE profile_id = 'profile-a'"
                    )
                ).scalar_one()
                == 2
            )
            assert (
                connection.execute(
                    sa.text(
                        "SELECT count(*) FROM persona_subject_bindings "
                        "WHERE ref_kind = 'persona_profile' AND ref_id = 'profile-a'"
                    )
                ).scalar_one()
                == 1
            )
            source_count = (
                connection.execute(
                    sa.text(
                        "SELECT count(*) FROM personas "
                        "UNION ALL SELECT count(*) FROM persona_profiles"
                    )
                )
                .scalars()
                .all()
            )
            assert connection.execute(
                sa.text("SELECT count(*) FROM persona_subjects")
            ).scalar_one() == sum(source_count)
            assert connection.execute(
                sa.text("SELECT count(*) FROM persona_subject_bindings")
            ).scalar_one() == sum(source_count)

            assert (
                connection.execute(
                    sa.text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                == PERSONA_SUBJECT_REVISION
            )

        inspector = sa.inspect(engine)
        assert PERSONA_SUBJECT_TABLES <= set(inspector.get_table_names())
        assert {
            column["name"] for column in inspector.get_columns("persona_subjects")
        } == {
            "persona_subject_id",
            "user_id",
            "display_name_snapshot",
            "lifecycle",
            "created_at",
            "updated_at",
        }
        assert {
            column["name"]
            for column in inspector.get_columns("persona_subject_bindings")
        } == {
            "binding_id",
            "persona_subject_id",
            "subject_user_id",
            "source_account_id",
            "ref_kind",
            "ref_id",
            "valid_from",
            "valid_until",
            "created_at",
        }
        assert {
            check["name"]
            for check in inspector.get_check_constraints("persona_subjects")
        } == {"persona_subjects_lifecycle_check"}
        assert {
            check["name"]
            for check in inspector.get_check_constraints("persona_subject_bindings")
        } == {
            "persona_subject_bindings_ref_kind_check",
            "persona_subject_bindings_source_account_check",
            "persona_subject_bindings_validity_check",
        }
        binding_foreign_keys = {
            foreign_key["name"]: (
                foreign_key["constrained_columns"],
                foreign_key["referred_table"],
                foreign_key["referred_columns"],
                foreign_key["options"].get("ondelete"),
            )
            for foreign_key in inspector.get_foreign_keys("persona_subject_bindings")
        }
        assert binding_foreign_keys == {
            "fk_persona_subject_bindings_subject_user": (
                ["subject_user_id"],
                "users",
                ["id"],
                "CASCADE",
            ),
            "fk_persona_subject_bindings_source_account": (
                ["source_account_id"],
                "users",
                ["id"],
                "CASCADE",
            ),
            "fk_persona_subject_bindings_subject_account": (
                ["persona_subject_id", "subject_user_id"],
                "persona_subjects",
                ["persona_subject_id", "user_id"],
                "CASCADE",
            ),
        }
        active_ref_index = next(
            index
            for index in inspector.get_indexes("persona_subject_bindings")
            if index["name"] == "uq_persona_subject_bindings_active_ref"
        )
        assert active_ref_index["column_names"] == ["ref_kind", "ref_id"]
        assert active_ref_index["unique"]

        current_binding = by_source[("persona", str(persona_a))]
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                sa.text("""
                    INSERT INTO persona_subject_bindings (
                        binding_id, persona_subject_id, subject_user_id,
                        source_account_id, ref_kind, ref_id, valid_from
                    ) VALUES (
                        'invalid-ref-kind', :subject_id, :account_id, :account_id,
                        'thread_profile', 'invalid-ref-kind', now()
                    )
                    """),
                {
                    "subject_id": current_binding["persona_subject_id"],
                    "account_id": current_binding["user_id"],
                },
            )
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                sa.text("""
                    INSERT INTO persona_subject_bindings (
                        binding_id, persona_subject_id, subject_user_id,
                        source_account_id, ref_kind, ref_id, valid_from
                    ) VALUES (
                        'source-account-check-failure', :subject_id, :account_id,
                        'account-b', 'persona', 'source-account-check-failure', now()
                    )
                    """),
                {
                    "subject_id": current_binding["persona_subject_id"],
                    "account_id": current_binding["user_id"],
                },
            )
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                sa.text("""
                    INSERT INTO persona_subject_bindings (
                        binding_id, persona_subject_id, subject_user_id,
                        source_account_id, ref_kind, ref_id, valid_from
                    ) VALUES (
                        'account-integrity-failure', :subject_id, 'account-b',
                        'account-b', 'persona', 'account-integrity-failure', now()
                    )
                    """),
                {"subject_id": current_binding["persona_subject_id"]},
            )
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                sa.text("""
                    INSERT INTO persona_subject_bindings (
                        binding_id, persona_subject_id, subject_user_id,
                        source_account_id, ref_kind, ref_id, valid_from, valid_until
                    ) VALUES (
                        'invalid-interval', :subject_id, :account_id, :account_id,
                        'persona', 'invalid-interval', now(), now()
                    )
                    """),
                {
                    "subject_id": current_binding["persona_subject_id"],
                    "account_id": current_binding["user_id"],
                },
            )
        with engine.begin() as connection:
            connection.execute(
                sa.text("""
                    INSERT INTO persona_subject_bindings (
                        binding_id, persona_subject_id, subject_user_id,
                        source_account_id, ref_kind, ref_id, valid_from
                    ) VALUES (
                        'first-current-binding', :subject_id, :account_id, :account_id,
                        'persona', 'partial-unique-test', now()
                    )
                    """),
                {
                    "subject_id": current_binding["persona_subject_id"],
                    "account_id": current_binding["user_id"],
                },
            )
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                sa.text("""
                    INSERT INTO persona_subject_bindings (
                        binding_id, persona_subject_id, subject_user_id,
                        source_account_id, ref_kind, ref_id, valid_from
                    ) VALUES (
                        'second-current-binding', :subject_id, :account_id, :account_id,
                        'persona', 'partial-unique-test', now()
                    )
                    """),
                {
                    "subject_id": current_binding["persona_subject_id"],
                    "account_id": current_binding["user_id"],
                },
            )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_replacement_history_and_downgrade_preserve_legacy_sources(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PARENT_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            account_a = connection.execute(
                sa.text("SELECT id FROM users ORDER BY id LIMIT 1")
            ).scalar_one()
            persona_id = _insert_legacy_persona(
                connection,
                account_a,
                created_at=NOW,
                is_active=True,
            )
            _insert_legacy_profile(
                connection,
                "explicit-successor-profile",
                account_a,
                name="Explicit successor source",
                binding_created_at=NOW + timedelta(seconds=1),
            )

        _upgrade(config, PERSONA_SUBJECT_REVISION)

        with engine.connect() as connection:
            old_binding = (
                connection.execute(
                    sa.text("""
                    SELECT binding_id, persona_subject_id, subject_user_id
                    FROM persona_subject_bindings
                    WHERE ref_kind = 'persona' AND ref_id = :ref_id
                    """),
                    {"ref_id": str(persona_id)},
                )
                .mappings()
                .one()
            )
            successor_binding = connection.execute(sa.text("""
                    SELECT binding_id
                    FROM persona_subject_bindings
                    WHERE ref_kind = 'persona_profile'
                      AND ref_id = 'explicit-successor-profile'
                    """)).mappings().one()

        replacement_at = NOW + timedelta(days=1)
        with engine.begin() as connection:
            connection.execute(
                sa.text("""
                    UPDATE persona_subject_bindings
                    SET valid_until = :replacement_at
                    WHERE binding_id = :binding_id
                    """),
                {
                    "binding_id": old_binding["binding_id"],
                    "replacement_at": replacement_at,
                },
            )
            connection.execute(
                sa.text(
                    "DELETE FROM persona_subject_bindings WHERE binding_id = :binding_id"
                ),
                {"binding_id": successor_binding["binding_id"]},
            )
            connection.execute(
                sa.text("""
                    INSERT INTO persona_subject_bindings (
                        binding_id, persona_subject_id, subject_user_id,
                        source_account_id, ref_kind, ref_id, valid_from, valid_until
                    ) VALUES (
                        'explicit-successor-binding', :subject_id, :account_id,
                        :account_id, 'persona_profile', 'explicit-successor-profile',
                        :replacement_at, NULL
                    )
                    """),
                {
                    "subject_id": old_binding["persona_subject_id"],
                    "account_id": old_binding["subject_user_id"],
                    "replacement_at": replacement_at,
                },
            )

        with engine.connect() as connection:
            history = (
                connection.execute(
                    sa.text("""
                    SELECT persona_subject_id, ref_kind, ref_id, valid_from, valid_until
                    FROM persona_subject_bindings
                    WHERE (ref_kind = 'persona' AND ref_id = :persona_ref_id)
                       OR (
                            ref_kind = 'persona_profile'
                        AND ref_id = 'explicit-successor-profile'
                       )
                    ORDER BY valid_from
                    """),
                    {"persona_ref_id": str(persona_id)},
                )
                .mappings()
                .all()
            )
            selected_history = [
                row
                for row in history
                if row["ref_id"] in {str(persona_id), "explicit-successor-profile"}
            ]
            assert len(selected_history) == 2
            assert {row["persona_subject_id"] for row in selected_history} == {
                old_binding["persona_subject_id"]
            }
            assert selected_history[0]["valid_until"] == replacement_at
            assert selected_history[1]["valid_from"] == replacement_at
            assert selected_history[1]["valid_until"] is None

        _downgrade(config, PARENT_REVISION)

        inspector = sa.inspect(engine)
        assert not (PERSONA_SUBJECT_TABLES & set(inspector.get_table_names()))
        with engine.connect() as connection:
            assert (
                connection.execute(
                    sa.text("SELECT count(*) FROM personas WHERE id = :id"),
                    {"id": persona_id},
                ).scalar_one()
                == 1
            )
            assert (
                connection.execute(
                    sa.text(
                        "SELECT count(*) FROM persona_profiles "
                        "WHERE id = 'explicit-successor-profile'"
                    )
                ).scalar_one()
                == 1
            )
            assert (
                connection.execute(
                    sa.text(
                        "SELECT count(*) FROM persona_profile_bindings "
                        "WHERE profile_id = 'explicit-successor-profile'"
                    )
                ).scalar_one()
                == 1
            )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_upgrade_aborts_before_backfill_when_a_profile_has_no_canonical_owner(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PARENT_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            account_a = connection.execute(
                sa.text("SELECT id FROM users ORDER BY id LIMIT 1")
            ).scalar_one()
            _insert_legacy_profile(
                connection,
                "unbound-profile",
                account_a,
                name="Unbound source must stop the migration",
                binding_created_at=None,
            )

        with pytest.raises(RuntimeError, match="has no canonical account owner"):
            _upgrade(config, PERSONA_SUBJECT_REVISION)

        inspector = sa.inspect(engine)
        assert not (PERSONA_SUBJECT_TABLES & set(inspector.get_table_names()))
        with engine.connect() as connection:
            assert (
                connection.execute(
                    sa.text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                == PARENT_REVISION
            )
    finally:
        engine.dispose()
