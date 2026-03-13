import importlib
import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


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


def test_supported_profile_health_reports_active_profile(monkeypatch) -> None:
    guardian_api = _load_guardian_api(monkeypatch)
    guardian_api._refresh_supported_profile_state(
        guardian_api.app, guardian_api.get_settings()
    )

    client = TestClient(guardian_api.app)
    try:
        response = client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["supported_profile"]["name"] == "v1-local-core-web-mcp"
        assert payload["supported_profile"]["valid"] is True
    finally:
        client.close()


def test_supported_profile_startup_fails_on_provider_drift(monkeypatch) -> None:
    guardian_api = _load_guardian_api(monkeypatch, LLM_PROVIDER="groq")
    with pytest.raises(RuntimeError, match="supported profile drift"):
        guardian_api._refresh_supported_profile_state(
            guardian_api.app, guardian_api.get_settings()
        )
