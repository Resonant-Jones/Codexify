from __future__ import annotations

import importlib
import os
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from guardian.core.config import (
    VECTOR_STORE_PROOF_STATUS_READY,
    resolve_vector_store_runtime,
)

_GUARDIAN_API_ENV_KEYS = (
    "GUARDIAN_API_KEY",
    "GUARDIAN_AUTH_MODE",
    "ENABLE_CONNECTOR_WORKER",
    "GUARDIAN_EXPOSURE_MODE",
    "CODEXIFY_SUPPORTED_PROFILE",
    "CODEXIFY_EMBEDDINGS_BACKEND",
    "CODEXIFY_VECTOR_STORE",
    "CODEXIFY_CHROMA_PATH",
    "CODEXIFY_COLLECTION",
)


class _FakeVectorStore:
    def __init__(self) -> None:
        self.runtime = resolve_vector_store_runtime()
        self.search_calls: list[dict[str, object]] = []

    def search(self, query: str, k: int = 5, namespace: str | None = None):
        self.search_calls.append(
            {"query": query, "k": k, "namespace": namespace}
        )
        if "fresh-sentinel" not in query:
            return []
        return [
            {
                "text": "fresh-sentinel from backend search",
                "meta": {"doc_id": "doc-1", "namespace": "thread:9"},
                "metadata": {"doc_id": "doc-1", "namespace": "thread:9"},
                "score": 0.99,
            }
        ]


class _FakePersonalFactsDB:
    def list_facts(
        self,
        user_id: str,
        *,
        status: str | None = None,
        active_only: bool = True,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        return []


def _snapshot_guardian_api_env() -> dict[str, str | None]:
    return {key: os.environ.get(key) for key in _GUARDIAN_API_ENV_KEYS}


def _restore_guardian_api_env(snapshot: dict[str, str | None]) -> None:
    for key, value in snapshot.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@contextmanager
def _supported_profile_client(monkeypatch, tmp_path):
    snapshot = _snapshot_guardian_api_env()
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "chroma")
    monkeypatch.setenv("CODEXIFY_CHROMA_PATH", str(tmp_path / "supported"))
    monkeypatch.setenv("CODEXIFY_COLLECTION", "supported_retrieval_health")

    import guardian.guardian_api as guardian_api

    guardian_api = importlib.reload(guardian_api)
    fake_store = _FakeVectorStore()

    def _init_services(_db):
        guardian_api.dependencies._vector_store = fake_store
        return fake_store, object()

    monkeypatch.setattr(guardian_api, "init_services", _init_services)
    client = TestClient(guardian_api.app, headers={"X-API-Key": ""})
    try:
        guardian_api.dependencies._vector_store = fake_store
        yield client, fake_store
    finally:
        client.close()
        from guardian.core import event_bus

        event_bus.reset()
        _restore_guardian_api_env(snapshot)
        if not os.environ.get("GUARDIAN_API_KEY"):
            os.environ["GUARDIAN_API_KEY"] = "test-api-key"
            try:
                importlib.reload(guardian_api)
            finally:
                _restore_guardian_api_env(snapshot)
        else:
            importlib.reload(guardian_api)


def test_supported_path_exposes_truthful_retrieval_health_surface(
    monkeypatch,
    tmp_path,
) -> None:
    with _supported_profile_client(monkeypatch, tmp_path) as (
        client,
        fake_store,
    ):
        response = client.get(
            "/api/health/retrieval",
            headers={"X-API-Key": "test-api-key"},
            params={"q": "fresh-sentinel", "k": 2, "namespace": "thread:9"},
        )

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        payload = response.json()
        assert payload["status"] == VECTOR_STORE_PROOF_STATUS_READY
        assert payload["ok"] is True
        assert payload["proof_capable"] is True
        assert payload["same_runtime_as_worker"] is True
        assert (
            payload["worker_write_runtime"] == payload["backend_search_runtime"]
        )
        assert payload["backend_store_source"] == "shared"
        assert payload["search"]["executed"] is True
        assert payload["search"]["match_count"] == 1
        assert (
            payload["search"]["matches"][0]["text"]
            == "fresh-sentinel from backend search"
        )
        assert fake_store.search_calls == [
            {"query": "fresh-sentinel", "k": 2, "namespace": "thread:9"}
        ]

        headers = {"X-API-Key": "test-api-key"}
        assert (
            client.get("/api/tools/manifest", headers=headers).status_code
            == 404
        )

        from guardian.routes import personal_facts

        monkeypatch.setattr(
            personal_facts,
            "chatlog_db",
            _FakePersonalFactsDB(),
            raising=False,
        )
        client.app.dependency_overrides[
            personal_facts.get_current_user
        ] = lambda: "local"

        personal_facts_response = client.get(
            "/api/personal-facts",
            headers=headers,
        )
        assert personal_facts_response.status_code == 200
        assert personal_facts_response.json() == {"ok": True, "facts": []}


@pytest.mark.parametrize("mode", ["local", "remote", "private_preview"])
def test_retrieval_rejects_non_operator_credentials_before_search(
    monkeypatch, tmp_path, mode
):
    from guardian.core.auth import ACCOUNT_SESSION_PURPOSE, issue_session_token
    from guardian.core.hosted_room_session import issue_guest_session_token

    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "retrieval-test-secret")
    with _supported_profile_client(monkeypatch, tmp_path) as (client, store):
        monkeypatch.setenv(
            "GUARDIAN_AUTH_MODE", "local" if mode == "local" else "remote"
        )
        monkeypatch.setenv(
            "GUARDIAN_EXPOSURE_MODE",
            "private_preview" if mode == "private_preview" else "local_safe",
        )
        account, _ = issue_session_token(
            subject="account-a", purpose=ACCOUNT_SESSION_PURPOSE
        )
        guest, _ = issue_guest_session_token(
            room_id="room-a",
            room_slug="room-a",
            participant_id="guest-a",
            invitation_id="invite-a",
        )
        credentials = [
            {},
            {"X-API-Key": "incorrect"},
            {"X-User-Id": "operator"},
            {"Authorization": f"Bearer {account}"},
            {"Authorization": f"Bearer {guest}"},
            {"Cookie": f"gc_session={account}"},
            {"Cookie": f"codexify_hosted_room_session={guest}"},
            {"X-Guardian-Account-Session": account},
        ]
        for headers in credentials:
            for path, params in [
                ("/api/health/retrieval", {}),
                (
                    "/api/health/retrieval",
                    {"q": "fresh-sentinel", "namespace": "thread:9"},
                ),
                ("/api/health/retrieval/", {"q": "fresh-sentinel"}),
                ("/api/health/%72etrieval", {"q": "fresh-sentinel", "k": "invalid"}),
            ]:
                response = client.get(path, params=params, headers=headers)
                assert response.status_code in (400, 401), (
                    mode,
                    path,
                    response.status_code,
                )
                assert "fresh-sentinel from backend search" not in response.text
                assert "matches" not in response.json()
        assert store.search_calls == []


def test_retrieval_accepts_operator_session_and_rejects_mixed_account(
    monkeypatch, tmp_path
):
    from guardian.core.auth import (
        ACCOUNT_SESSION_PURPOSE,
        OPERATOR_SESSION_PURPOSE,
        issue_session_token,
    )

    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "retrieval-test-secret")
    with _supported_profile_client(monkeypatch, tmp_path) as (client, store):
        monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
        operator, _ = issue_session_token(
            subject="operator", purpose=OPERATOR_SESSION_PURPOSE
        )
        account, _ = issue_session_token(
            subject="account", purpose=ACCOUNT_SESSION_PURPOSE
        )
        response = client.get(
            "/api/health/retrieval",
            params={"q": "fresh-sentinel"},
            headers={"Authorization": f"Bearer {operator}"},
        )
        assert response.status_code == 200
        assert response.json()["search"]["match_count"] == 1
        assert response.headers["cache-control"] == "no-store"
        response = client.get(
            "/api/health/retrieval",
            params={"q": "fresh-sentinel"},
            headers={"X-API-Key": "test-api-key", "Authorization": f"Bearer {account}"},
        )
        assert response.status_code == 400
        assert len(store.search_calls) == 1
