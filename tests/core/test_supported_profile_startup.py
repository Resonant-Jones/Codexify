import importlib
import os
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

_GUARDIAN_API_ENV_KEYS = (
    "GUARDIAN_API_KEY",
    "ENABLE_CONNECTOR_WORKER",
    "CODEXIFY_SUPPORTED_PROFILE",
    "CODEXIFY_SINGLE_USER_ID",
    "CODEXIFY_CHATGPT_IMPORT_STARTUP_RETRY_CAP",
    "LLM_PROVIDER",
    "ALLOW_CLOUD_PROVIDERS",
    "CODEXIFY_LOCAL_ONLY_MODE",
    "CODEXIFY_EGRESS_ALLOWLIST",
    "LOCAL_BASE_URL",
    "LOCAL_API_KEY",
    "LOCAL_LLM_MODEL",
    "LOCAL_CHAT_MODEL",
)


def _fake_db() -> MagicMock:
    db = MagicMock()
    db.ensure_sync_job_support.return_value = None
    db.sync_inference_provider_rows_from_catalog.return_value = {
        "provider_rows": 0,
        "providers_created": 0,
        "providers_updated": 0,
        "runtime_created": 0,
    }
    return db


def _load_guardian_api(monkeypatch, **env_overrides):
    fake_db = _fake_db()
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv(
        "CODEXIFY_BETA_CORE_ONLY",
        env_overrides.pop("CODEXIFY_BETA_CORE_ONLY", "false"),
    )
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    monkeypatch.setenv(
        "LLM_PROVIDER", env_overrides.pop("LLM_PROVIDER", "local")
    )
    monkeypatch.setenv(
        "ALLOW_CLOUD_PROVIDERS",
        env_overrides.pop("ALLOW_CLOUD_PROVIDERS", "false"),
    )
    monkeypatch.setenv(
        "CODEXIFY_LOCAL_ONLY_MODE",
        env_overrides.pop("CODEXIFY_LOCAL_ONLY_MODE", "true"),
    )
    monkeypatch.setenv(
        "CODEXIFY_EGRESS_ALLOWLIST",
        env_overrides.pop("CODEXIFY_EGRESS_ALLOWLIST", ""),
    )
    monkeypatch.setenv(
        "LOCAL_BASE_URL",
        env_overrides.pop(
            "LOCAL_BASE_URL", "http://host.docker.internal:11434/v1"
        ),
    )
    monkeypatch.setenv(
        "LOCAL_API_KEY", env_overrides.pop("LOCAL_API_KEY", "local")
    )
    monkeypatch.setenv(
        "LOCAL_LLM_MODEL",
        env_overrides.pop("LOCAL_LLM_MODEL", "library2/ministral-3:8b"),
    )
    monkeypatch.setenv(
        "LOCAL_CHAT_MODEL",
        env_overrides.pop("LOCAL_CHAT_MODEL", "library2/ministral-3:8b"),
    )
    for key, value in env_overrides.items():
        monkeypatch.setenv(key, value)

    import guardian.core.dependencies as dependencies

    monkeypatch.setattr(dependencies, "init_database", lambda: fake_db)

    import guardian.guardian_api as guardian_api

    guardian_api = importlib.reload(guardian_api)
    monkeypatch.setattr(
        guardian_api, "assert_config_coherence", lambda _settings: None
    )
    monkeypatch.setattr(
        guardian_api.dependencies, "init_database", lambda: fake_db
    )
    monkeypatch.setattr(guardian_api, "chatlog_db", fake_db)
    monkeypatch.setattr(guardian_api, "ensure_default_project", lambda: None)
    monkeypatch.setattr(guardian_api, "init_services", lambda _db: None)
    monkeypatch.setattr(
        guardian_api.memory, "bind_dependencies", lambda **_: None
    )
    monkeypatch.setattr(guardian_api, "load_guardian_db_from_env", lambda: None)
    monkeypatch.setattr(guardian_api.metrics, "set_db_backend", lambda *_: None)
    monkeypatch.setattr(
        guardian_api.task_events, "publish", lambda *_a, **_k: None
    )
    monkeypatch.setattr(guardian_api, "enqueue", lambda *_a, **_k: None)
    settings = guardian_api.get_settings()
    settings.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local")
    settings.ALLOW_CLOUD_PROVIDERS = (
        os.getenv("ALLOW_CLOUD_PROVIDERS", "false").strip().lower() == "true"
    )
    settings.CODEXIFY_LOCAL_ONLY_MODE = (
        os.getenv("CODEXIFY_LOCAL_ONLY_MODE", "true").strip().lower() == "true"
    )
    settings.CODEXIFY_EGRESS_ALLOWLIST = os.getenv(
        "CODEXIFY_EGRESS_ALLOWLIST", ""
    )
    settings.LOCAL_BASE_URL = os.getenv(
        "LOCAL_BASE_URL", "http://host.docker.internal:11434/v1"
    )
    settings.LOCAL_API_KEY = os.getenv("LOCAL_API_KEY", "local")
    settings.LOCAL_LLM_MODEL = os.getenv(
        "LOCAL_LLM_MODEL", "library2/ministral-3:8b"
    )
    settings.LOCAL_CHAT_MODEL = os.getenv(
        "LOCAL_CHAT_MODEL", "library2/ministral-3:8b"
    )
    return guardian_api


def _snapshot_guardian_api_env() -> dict[str, str | None]:
    return {key: os.environ.get(key) for key in _GUARDIAN_API_ENV_KEYS}


def _restore_guardian_api_env(snapshot: dict[str, str | None]) -> None:
    for key, value in snapshot.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@contextmanager
def _loaded_guardian_api(monkeypatch, **env_overrides):
    snapshot = _snapshot_guardian_api_env()
    guardian_api = _load_guardian_api(monkeypatch, **env_overrides)
    try:
        yield guardian_api
    finally:
        _restore_guardian_api_env(snapshot)
        from guardian.core import event_bus

        event_bus.reset()
        importlib.reload(guardian_api)


def test_supported_profile_health_reports_active_profile(monkeypatch) -> None:
    with _loaded_guardian_api(monkeypatch) as guardian_api:
        guardian_api._refresh_supported_profile_state(
            guardian_api.app, guardian_api.get_settings()
        )

        client = TestClient(guardian_api.app)
        try:
            response = client.get("/health")
            assert response.status_code == 200
            payload = response.json()
            assert payload["status"] == "ok"
            assert (
                payload["supported_profile"]["name"] == "v1-local-core-web-mcp"
            )
            assert payload["supported_profile"]["valid"] is True
        finally:
            client.close()


def test_supported_profile_startup_fails_on_provider_drift(monkeypatch) -> None:
    with _loaded_guardian_api(monkeypatch, LLM_PROVIDER="groq") as guardian_api:
        with pytest.raises(RuntimeError, match="supported profile drift"):
            guardian_api._refresh_supported_profile_state(
                guardian_api.app, guardian_api.get_settings()
            )


def test_startup_chatgpt_import_sweep_uses_single_user_cap(monkeypatch) -> None:
    captured: dict[str, object] = {}

    with _loaded_guardian_api(
        monkeypatch,
        CODEXIFY_SINGLE_USER_ID="single-user",
        CODEXIFY_CHATGPT_IMPORT_STARTUP_RETRY_CAP="7",
    ) as guardian_api:

        def fake_retry(*, user_id, limit=5000):
            captured["user_id"] = user_id
            captured["limit"] = limit
            return {
                "embedding_candidates": 0,
                "embeddings_persisted": 0,
                "embeddings_failed": 0,
                "embedding_coverage_degraded": False,
            }

        monkeypatch.setattr(
            "backend.rag.chatgpt_migration.retry_chatgpt_import_embeddings",
            fake_retry,
        )

        with TestClient(guardian_api.app):
            pass

    assert captured["user_id"] == "single-user"
    assert captured["limit"] == 7


def test_startup_chatgpt_import_sweep_uses_default_cap(monkeypatch) -> None:
    captured: dict[str, object] = {}

    with _loaded_guardian_api(
        monkeypatch,
        CODEXIFY_SINGLE_USER_ID="single-user",
    ) as guardian_api:

        def fake_retry(*, user_id, limit=5000):
            captured["user_id"] = user_id
            captured["limit"] = limit
            return {
                "embedding_candidates": 0,
                "embeddings_persisted": 0,
                "embeddings_failed": 0,
                "embedding_coverage_degraded": False,
            }

        monkeypatch.setattr(
            "backend.rag.chatgpt_migration.retry_chatgpt_import_embeddings",
            fake_retry,
        )

        with TestClient(guardian_api.app):
            pass

    assert captured["user_id"] == "single-user"
    assert captured["limit"] == 128
