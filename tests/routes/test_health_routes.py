from __future__ import annotations

from guardian.core.config import get_settings
from guardian.routes import health as health_routes


def _healthy_completion_service() -> dict[str, object]:
    return {
        "ok": True,
        "redis_reachable": True,
        "enqueue_test_ok": True,
        "worker_heartbeat_detected": True,
        "worker_heartbeat_age_seconds": 0.5,
        "worker_heartbeat_status": "fresh",
        "worker_heartbeat_reason": "ok",
        "worker_heartbeat_detail": None,
        "heartbeat_key": "codexify:worker:chat:heartbeat",
        "status_reason": "ok",
        "error": None,
        "dependency": None,
        "dependency_unavailable": False,
    }


def _mock_local_runtime_request(url: str, *args, **kwargs):
    _ = (args, kwargs)
    if url.endswith("/api/tags"):
        return type(
            "Resp",
            (),
            {
                "status_code": 200,
                "json": lambda self=None: {
                    "models": [{"name": "qwen3.5:0.8b"}]
                },
            },
        )()
    return type(
        "Resp",
        (),
        {
            "status_code": 200,
            "json": lambda self=None: {"status": "ok"},
        },
    )()


def _apply_local_runtime(settings) -> dict[str, object]:
    snapshot = {
        "LLM_PROVIDER": settings.LLM_PROVIDER,
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "LOCAL_BASE_URL": settings.LOCAL_BASE_URL,
        "LOCAL_API_KEY": settings.LOCAL_API_KEY,
        "LOCAL_LLM_MODEL": settings.LOCAL_LLM_MODEL,
        "LOCAL_CHAT_MODEL": settings.LOCAL_CHAT_MODEL,
        "DEFAULT_LOCAL_MODEL": settings.DEFAULT_LOCAL_MODEL,
        "LLM_MODEL": settings.LLM_MODEL,
    }
    settings.LLM_PROVIDER = "local"
    settings.ALLOW_CLOUD_PROVIDERS = False
    settings.CODEXIFY_LOCAL_ONLY_MODE = True
    settings.CODEXIFY_EGRESS_ALLOWLIST = ""
    settings.LOCAL_BASE_URL = "http://host.docker.internal:11434/v1"
    settings.LOCAL_API_KEY = "local"
    settings.LOCAL_LLM_MODEL = "library2/ministral-3:8b"
    settings.LOCAL_CHAT_MODEL = "qwen3.5:0.8b"
    settings.DEFAULT_LOCAL_MODEL = "library2/ministral-3:8b"
    settings.LLM_MODEL = "library2/ministral-3:8b"
    return snapshot


def _restore_settings(settings, snapshot: dict[str, object]) -> None:
    for field, value in snapshot.items():
        setattr(settings, field, value)


def test_health_root_returns_structured_json(test_client):
    response = test_client.get("/health")

    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "core"
    assert isinstance(payload["timestamp"], str)
    assert isinstance(payload["details"], dict)
    assert "<!DOCTYPE html>" not in response.text


def test_health_endpoints_surface_structured_service_payloads(
    test_client,
    monkeypatch,
):
    monkeypatch.setattr(
        "guardian.core.ai_router.requests.get",
        _mock_local_runtime_request,
    )
    monkeypatch.setattr(
        "guardian.routes.health.requests.get",
        _mock_local_runtime_request,
    )
    monkeypatch.setattr(
        health_routes,
        "_collect_completion_service_health",
        _healthy_completion_service,
    )
    health_routes._LLM_HEALTH_PROBE_CACHE = None
    health_routes._LLM_HEALTH_PROBE_TS = 0.0

    settings = get_settings()
    snapshot = _apply_local_runtime(settings)
    try:
        paths = [
            ("/health/llm", "llm"),
            ("/health/deps", "deps"),
            ("/health/vector", "vector"),
            ("/health/memory", "memory"),
        ]

        for path, service in paths:
            response = test_client.get(path)
            assert response.status_code == 200
            payload = response.json()
            assert payload["service"] == service
            assert payload["status"] in {"ok", "degraded", "down"}
            assert isinstance(payload["timestamp"], str)
            assert isinstance(payload["details"], dict)

        llm_payload = test_client.get("/health/llm").json()
        assert llm_payload["status"] == "ok"
        assert llm_payload["details"]["provider"] == "local"
        assert llm_payload["details"]["provider_truth"]["configured"] is True
    finally:
        _restore_settings(settings, snapshot)
        health_routes._LLM_HEALTH_PROBE_CACHE = None
        health_routes._LLM_HEALTH_PROBE_TS = 0.0


def test_health_vector_returns_down_when_dependency_is_malformed(
    test_client,
    monkeypatch,
):
    class BrokenVectorStore:
        embedder = type("Embedder", (), {"store": "mock"})()

        def add_texts(self, *_args, **_kwargs):
            raise ValueError("vector dependency malformed")

        def search(self, *_args, **_kwargs):
            raise ValueError("vector dependency malformed")

    monkeypatch.setattr(
        "guardian.core.dependencies._vector_store",
        BrokenVectorStore(),
        raising=False,
    )

    response = test_client.get("/health/vector")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "vector"
    assert payload["status"] == "down"
    assert payload["details"]["ok"] is False
    assert "error" in payload["details"]


def test_health_executors_returns_all_registry_executors(test_client):
    response = test_client.get("/api/health/executors")

    assert response.status_code == 200
    payload = response.json()
    assert "executors" in payload
    executors = payload["executors"]
    assert isinstance(executors, list)
    executor_ids = {e["executor_id"] for e in executors}
    assert executor_ids == {"codex", "claude_code", "opencode"}


def test_health_executors_includes_required_fields(test_client):
    response = test_client.get("/api/health/executors")

    assert response.status_code == 200
    payload = response.json()
    executors = payload["executors"]

    for executor in executors:
        assert "executor_id" in executor
        assert "label" in executor
        assert "release_posture" in executor
        assert "installed" in executor
        assert "binary_path" in executor
        assert "auth_state" in executor
        assert "availability_state" in executor
        assert "supports_local_models" in executor
        assert "supports_gateway_routing" in executor
        assert "supports_direct_provider_config" in executor
        assert "supported_auth_modes" in executor
        assert "status_detail" in executor


def test_health_executors_preserves_release_posture(test_client):
    response = test_client.get("/api/health/executors")

    assert response.status_code == 200
    payload = response.json()
    executors = {e["executor_id"]: e for e in payload["executors"]}

    assert executors["codex"]["release_posture"] == "official"
    assert executors["claude_code"]["release_posture"] == "optional"
    assert executors["opencode"]["release_posture"] == "optional"


def test_health_executors_unknown_auth_remains_explicit(test_client):
    response = test_client.get("/api/health/executors")

    assert response.status_code == 200
    payload = response.json()
    executors_list = payload["executors"]

    for executor in executors_list:
        assert executor["auth_state"] in {
            "authenticated",
            "unauthenticated",
            "unknown",
        }


def test_health_executors_availability_states_are_valid(test_client):
    response = test_client.get("/api/health/executors")

    assert response.status_code == 200
    payload = response.json()
    executors = payload["executors"]

    valid_states = {"ready", "degraded", "unavailable", "not_installed"}
    for executor in executors:
        assert executor["availability_state"] in valid_states
