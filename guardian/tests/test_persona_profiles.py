from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.cognition.system_profiles import store as persona_profile_store
from guardian.core.dependencies import RequestUserScope
from guardian.db import models as db_models
from guardian.routes import persona_profiles


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@contextmanager
def _build_client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    db_models.Base.metadata.create_all(
        engine,
        tables=[
            db_models.User.__table__,
            db_models.PersonaProfile.__table__,
            db_models.PersonaProfileRevision.__table__,
            db_models.PersonaProfileBinding.__table__,
        ],
    )
    session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    with session_factory.begin() as session:
        session.add_all(
            [
                db_models.User(
                    id="account-a",
                    username="account-a",
                    password_hash="not-a-real-hash",
                    role="guest",
                ),
                db_models.User(
                    id="account-b",
                    username="account-b",
                    password_hash="not-a-real-hash",
                    role="guest",
                ),
            ]
        )
    persona_profile_store._set_session_factory(session_factory)

    current_account = {"id": "account-a"}

    def _request_scope() -> RequestUserScope:
        account_id = current_account["id"]
        return RequestUserScope(
            user_id=account_id,
            subject_id=f"subject-{account_id}",
            account_id=account_id,
            multi_user_enabled=True,
        )

    app = FastAPI()
    app.include_router(persona_profiles.router)
    app.dependency_overrides[persona_profiles.require_api_key] = lambda: "test-api-key"
    app.dependency_overrides[persona_profiles.get_request_user_scope] = _request_scope

    client = TestClient(app)
    try:
        yield client, session_factory, current_account
    finally:
        client.close()
        persona_profile_store._set_session_factory(None)
        event.remove(engine, "connect", _enable_sqlite_foreign_keys)
        engine.dispose()


def _canonical_manifest(profile_id: str) -> dict:
    return {
        "apiVersion": "codexify.persona/v1",
        "profileIdentity": profile_id,
        "identity": {
            "name": "Canonical Persona",
            "description": "Persist every authored field.",
        },
        "prompt": {
            "systemPrompt": "Use the canonical prompt.",
            "styleNotes": "Be concise.",
            "directives": "Never infer authority.",
        },
        "model": {
            "provider": "OpenAI",
            "model": "gpt-4o",
            "temperature": 0.4,
            "topK": 32,
            "topP": 0.9,
            "maxTokens": 4096,
        },
        "voice": {
            "enabled": True,
            "provider": "elevenlabs",
            "voicePreset": "rachel",
            "speed": 1.0,
            "wakeWord": "Hey Guardian",
            "interruptible": True,
        },
        "capabilities": {
            "pinnedTools": ["web-search"],
            "allowedTools": ["web-search", "calculator"],
            "skills": ["critical-thinking"],
            "permissions": {
                "web": True,
                "email": False,
                "calendar": False,
                "cli": False,
                "filesystem": True,
            },
        },
        "retrieval": {
            "enabled": True,
            "mode": "hybrid",
            "topK": 10,
            "rerank": True,
        },
    }


def test_legacy_routes_persist_revision_and_enforce_account_scope():
    with _build_client() as (client, session_factory, current_account):
        create_response = client.post(
            "/api/persona-profiles",
            json={
                "id": "profile-runtime",
                "name": "Runtime Persona",
                "system_prompt": "You are a runtime persona.",
                "model_provider": "OpenAI",
                "model_id": "gpt-4o",
                "temperature": 0.4,
            },
        )
        assert create_response.status_code == 200, create_response.text
        created = create_response.json()["profile"]
        assert created["id"] == "profile-runtime"
        assert created["model_provider"] == "openai"
        assert created["api_version"] == "codexify.persona/v1"
        assert created["current_revision"] == 1
        assert created["manifest"] == {
            "apiVersion": "codexify.persona/v1",
            "profileIdentity": "profile-runtime",
            "identity": {"name": "Runtime Persona"},
            "prompt": {"systemPrompt": "You are a runtime persona."},
            "model": {
                "provider": "openai",
                "model": "gpt-4o",
                "temperature": 0.4,
            },
            "revision": 1,
        }
        assert "owner_account_id" not in created

        list_response = client.get("/api/persona-profiles")
        assert list_response.status_code == 200, list_response.text
        assert [profile["id"] for profile in list_response.json()["profiles"]] == [
            "profile-runtime"
        ]

        update_response = client.patch(
            "/api/persona-profiles/profile-runtime",
            json={
                "name": "Runtime Persona Updated",
                "system_prompt": "Updated system prompt.",
                "model_provider": "Anthropic",
                "model_id": "claude-sonnet-4-20250514",
                "temperature": 0.2,
            },
        )
        assert update_response.status_code == 200, update_response.text
        updated = update_response.json()["profile"]
        assert updated["current_revision"] == 2
        assert updated["model_provider"] == "anthropic"

        no_op_response = client.patch(
            "/api/persona-profiles/profile-runtime",
            json={"temperature": 0.2},
        )
        assert no_op_response.status_code == 200, no_op_response.text
        assert no_op_response.json()["profile"]["current_revision"] == 2

        with session_factory() as session:
            binding = session.get(
                db_models.PersonaProfileBinding,
                "profile-runtime",
            )
            assert binding is not None
            assert binding.owner_account_id == "account-a"
            revisions = list(
                session.scalars(
                    select(db_models.PersonaProfileRevision)
                    .where(
                        db_models.PersonaProfileRevision.profile_id == "profile-runtime"
                    )
                    .order_by(db_models.PersonaProfileRevision.revision)
                )
            )
            assert [row.revision for row in revisions] == [1, 2]

        current_account["id"] = "account-b"
        assert client.get("/api/persona-profiles").json()["profiles"] == []
        assert client.get("/api/persona-profiles/profile-runtime").status_code == 404
        assert (
            client.patch(
                "/api/persona-profiles/profile-runtime",
                json={"temperature": 0.8},
            ).status_code
            == 404
        )
        collision = client.post(
            "/api/persona-profiles",
            json={
                "id": "profile-runtime",
                "name": "Attempted adoption",
                "system_prompt": "Do not adopt.",
                "model_provider": "openai",
                "model_id": "gpt-4o",
                "temperature": 0.8,
            },
        )
        assert collision.status_code == 409

        current_account["id"] = "account-a"
        assert client.get("/api/persona-profiles/profile-runtime").status_code == 200


def test_canonical_manifest_revisions_preserve_broad_authored_fields():
    with _build_client() as (client, session_factory, _current_account):
        authored = _canonical_manifest("profile-canonical")
        response = client.post(
            "/api/persona-profiles",
            json={"manifest": authored},
        )
        assert response.status_code == 200, response.text
        created = response.json()["profile"]
        revision_one = deepcopy(created["manifest"])
        assert set(revision_one) == {
            "apiVersion",
            "profileIdentity",
            "identity",
            "prompt",
            "model",
            "voice",
            "capabilities",
            "retrieval",
            "revision",
        }
        assert revision_one["model"]["provider"] == "openai"

        legacy_patch = client.patch(
            "/api/persona-profiles/profile-canonical",
            json={"temperature": 0.6},
        )
        assert legacy_patch.status_code == 200, legacy_patch.text
        revision_two = legacy_patch.json()["profile"]["manifest"]
        assert revision_two["revision"] == 2
        assert revision_two["model"]["temperature"] == 0.6
        for field in ("voice", "capabilities", "retrieval"):
            assert revision_two[field] == revision_one[field]
        assert (
            revision_two["identity"]["description"]
            == (revision_one["identity"]["description"])
        )

        canonical_update = deepcopy(authored)
        canonical_update["identity"]["description"] = "Revision three."
        canonical_update["model"]["temperature"] = 0.6
        update_response = client.patch(
            "/api/persona-profiles/profile-canonical",
            json={"manifest": canonical_update},
        )
        assert update_response.status_code == 200, update_response.text
        assert update_response.json()["profile"]["current_revision"] == 3

        identity_mismatch = deepcopy(canonical_update)
        identity_mismatch["profileIdentity"] = "different-profile"
        mismatch_response = client.patch(
            "/api/persona-profiles/profile-canonical",
            json={"manifest": identity_mismatch},
        )
        assert mismatch_response.status_code == 400

        readback = client.get("/api/persona-profiles/profile-canonical")
        assert readback.status_code == 200, readback.text
        assert readback.json()["profile"]["manifest"]["revision"] == 3

        no_op = client.patch(
            "/api/persona-profiles/profile-canonical",
            json={"manifest": canonical_update},
        )
        assert no_op.status_code == 200, no_op.text
        assert no_op.json()["profile"]["current_revision"] == 3

        with session_factory() as session:
            rows = list(
                session.scalars(
                    select(db_models.PersonaProfileRevision)
                    .where(
                        db_models.PersonaProfileRevision.profile_id
                        == "profile-canonical"
                    )
                    .order_by(db_models.PersonaProfileRevision.revision)
                )
            )
            assert [row.revision for row in rows] == [1, 2, 3]
            assert rows[0].manifest_json == revision_one
            assert rows[1].manifest_json == revision_two


def test_manifest_contract_rejects_revision_authority_and_unknown_fields():
    with _build_client() as (client, _session_factory, _current_account):
        manifest = _canonical_manifest("profile-rejected")

        with_revision = deepcopy(manifest)
        with_revision["revision"] = 99
        assert (
            client.post(
                "/api/persona-profiles",
                json={"manifest": with_revision},
            ).status_code
            == 422
        )

        for field, value in (
            ("ownerAccountId", "account-b"),
            ("projectIds", [42]),
            ("participants", ["account-b"]),
        ):
            with_authority = deepcopy(manifest)
            with_authority[field] = value
            assert (
                client.post(
                    "/api/persona-profiles",
                    json={"manifest": with_authority},
                ).status_code
                == 422
            )

        with_secret = deepcopy(manifest)
        with_secret["credentials"] = {"apiKey": "must-not-persist"}
        assert (
            client.post(
                "/api/persona-profiles",
                json={"manifest": with_secret},
            ).status_code
            == 422
        )

        wrong_version = deepcopy(manifest)
        wrong_version["apiVersion"] = "codexify.persona/v2"
        assert (
            client.post(
                "/api/persona-profiles",
                json={"manifest": wrong_version},
            ).status_code
            == 422
        )

        internal_field_names = deepcopy(manifest)
        internal_field_names["api_version"] = internal_field_names.pop(
            "apiVersion"
        )
        assert (
            client.post(
                "/api/persona-profiles",
                json={"manifest": internal_field_names},
            ).status_code
            == 422
        )

        with_nested_unknown = deepcopy(manifest)
        with_nested_unknown["model"]["apiKey"] = "must-not-persist"
        assert (
            client.post(
                "/api/persona-profiles",
                json={"manifest": with_nested_unknown},
            ).status_code
            == 422
        )

        mixed = client.post(
            "/api/persona-profiles",
            json={"manifest": manifest, "name": "mixed"},
        )
        assert mixed.status_code == 422

        top_level_owner = client.post(
            "/api/persona-profiles",
            json={
                "manifest": manifest,
                "owner_account_id": "account-b",
            },
        )
        assert top_level_owner.status_code == 422
