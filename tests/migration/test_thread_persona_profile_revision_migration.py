"""Real PostgreSQL/Alembic proof of thread revision pins and atomic writes."""

from __future__ import annotations

import psycopg
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from tests.migration.test_persona_profile_manifest_binding_migration import (
    _insert_user,
    _upgrade,
)
from tests.migration.test_persona_profile_manifest_binding_migration import (
    temporary_postgres as temporary_postgres,  # noqa: PLC0414
)

PREVIOUS_REVISION = "c3d9e1f4a6b8"
PIN_REVISION = "d4e0f2a5b7c9"


@pytest.mark.integration
def test_backfill_pins_only_proven_account_revisions(temporary_postgres):
    config, database_url = temporary_postgres
    _upgrade(config, PREVIOUS_REVISION)
    engine = sa.create_engine(database_url)
    try:
        with engine.begin() as conn:
            owner = conn.execute(sa.text("SELECT id FROM users")).scalar_one()
            _insert_user(conn, "foreign-account")
            # Reuse the canonical revision written by the real parent migration.
            for profile_id in (
                "owned",
                "unbound",
                "foreign",
                "missing",
                "corrupt",
                "invalid-manifest",
                "flow",
            ):
                conn.execute(
                    sa.text("""
                    INSERT INTO persona_profiles
                        (id, name, system_prompt, model_provider, model_id, temperature, current_revision)
                    SELECT :id, name, system_prompt, model_provider, model_id, temperature, 1
                    FROM persona_profiles WHERE id = 'profile-1'
                """),
                    {"id": profile_id},
                )
                if profile_id != "missing":
                    conn.execute(
                        sa.text("""
                        INSERT INTO persona_profile_revisions
                            (profile_id, revision, api_version, manifest_json)
                        SELECT :id, 1, api_version,
                            jsonb_set(manifest_json::jsonb, '{profileIdentity}', to_jsonb(CAST(:identity AS text)))
                        FROM persona_profile_revisions WHERE profile_id = 'profile-1' AND revision = 1
                    """),
                        {
                            "id": profile_id,
                            "identity": "wrong"
                            if profile_id == "corrupt"
                            else profile_id,
                        },
                    )
                if profile_id == "owned":
                    conn.execute(
                        sa.text("""
                        INSERT INTO persona_profile_revisions (profile_id, revision, api_version, manifest_json)
                        SELECT profile_id, 2, api_version, jsonb_set(manifest_json::jsonb, '{revision}', '2'::jsonb)
                        FROM persona_profile_revisions WHERE profile_id = 'owned' AND revision = 1
                    """)
                    )
                    conn.execute(
                        sa.text(
                            "UPDATE persona_profiles SET current_revision = 2 WHERE id = 'owned'"
                        )
                    )
                if profile_id == "invalid-manifest":
                    conn.execute(
                        sa.text(
                            "UPDATE persona_profile_revisions SET manifest_json = manifest_json::jsonb - 'prompt' WHERE profile_id = :id"
                        ),
                        {"id": profile_id},
                    )
                if profile_id != "unbound":
                    conn.execute(
                        sa.text("""
                        INSERT INTO persona_profile_bindings (profile_id, owner_account_id)
                        VALUES (:id, :owner)
                    """),
                        {
                            "id": profile_id,
                            "owner": "foreign-account"
                            if profile_id == "foreign"
                            else owner,
                        },
                    )
            for profile_id in (
                "owned",
                "unbound",
                "foreign",
                "missing",
                "corrupt",
                "invalid-manifest",
                "flow",
                "local_mode",
                "env-profile",
            ):
                conn.execute(
                    sa.text("""
                    INSERT INTO chat_threads (user_id, title, active_profile_id, metadata)
                    VALUES (:owner, :id, :id, CAST(:metadata AS jsonb))
                """),
                    {
                        "owner": owner,
                        "id": profile_id,
                        "metadata": '{"profile_overrides":{"flow":{"profile_id":"flow"}}}'
                        if profile_id == "flow"
                        else "{}",
                    },
                )
        _upgrade(config, PIN_REVISION)
        with engine.connect() as conn:
            pins = dict(
                conn.execute(
                    sa.text("SELECT title, active_profile_revision FROM chat_threads")
                ).all()
            )
            assert pins["owned"] == 2
            for profile_id in (
                "unbound",
                "foreign",
                "missing",
                "corrupt",
                "invalid-manifest",
                "flow",
                "local_mode",
                "env-profile",
            ):
                assert pins[profile_id] is None
            assert (
                conn.execute(
                    sa.text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                == PIN_REVISION
            )
        inspector = sa.inspect(engine)
        fk = next(
            row
            for row in inspector.get_foreign_keys("chat_threads")
            if row["name"] == "fk_chat_threads_persona_profile_revision"
        )
        assert fk["constrained_columns"] == [
            "active_profile_id",
            "active_profile_revision",
        ]
        assert fk["referred_columns"] == ["profile_id", "revision"]
        for assignment in (
            "active_profile_revision = 0",
            "active_profile_revision = -1",
            "active_profile_id = NULL",
            "active_profile_revision = 99",
        ):
            with pytest.raises(IntegrityError), engine.begin() as conn:
                conn.execute(
                    sa.text(
                        f"UPDATE chat_threads SET {assignment} WHERE title = 'owned'"
                    )
                )
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(sa.text("DELETE FROM persona_profiles WHERE id = 'owned'"))
        with engine.begin() as conn:
            conn.execute(
                sa.text("DELETE FROM users WHERE id = :owner"), {"owner": owner}
            )
            assert (
                conn.execute(sa.text("SELECT count(*) FROM chat_threads")).scalar_one()
                == 0
            )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_real_chat_adapters_atomically_write_and_clear_pins(temporary_postgres):
    from guardian.core.db import GuardianDB
    from guardian.core.pgdb import PgDB

    config, database_url = temporary_postgres
    _upgrade(config, PIN_REVISION)
    engine = sa.create_engine(database_url)
    try:
        with engine.begin() as conn:
            owner = conn.execute(sa.text("SELECT id FROM users")).scalar_one()
            thread_id = conn.execute(
                sa.text("""
                INSERT INTO chat_threads (user_id, title) VALUES (:owner, 'pin proof') RETURNING id
            """),
                {"owner": owner},
            ).scalar_one()
        # Both adapters use their production transaction and readback paths.
        for db in (
            GuardianDB(database_url),
            PgDB(database_url.replace("postgresql+psycopg://", "postgresql://")),
        ):
            assert db.set_thread_active_profile_id(
                thread_id, "profile-1", profile_revision=1
            )
            state = db.get_chat_thread(thread_id)
            assert (state["active_profile_id"], state["active_profile_revision"]) == (
                "profile-1",
                1,
            )
            with pytest.raises((IntegrityError, psycopg.errors.ForeignKeyViolation)):
                db.set_thread_active_profile_id(
                    thread_id, "missing", profile_revision=1
                )
            state = db.get_chat_thread(thread_id)
            assert (state["active_profile_id"], state["active_profile_revision"]) == (
                "profile-1",
                1,
            )
            assert db.set_thread_active_profile_id(thread_id, "local_mode")
            assert db.get_chat_thread(thread_id)["active_profile_revision"] is None
            db.set_thread_active_profile_id(thread_id, "profile-1", profile_revision=1)
            db.update_thread(
                thread_id, active_profile_id="default", active_profile_id_set=True
            )
            assert db.get_chat_thread(thread_id)["active_profile_revision"] is None
    finally:
        engine.dispose()
