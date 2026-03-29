from __future__ import annotations

from guardian.core.ai_router import LOCAL_MODEL_RESOLUTION_ERROR
from guardian.core.config import get_settings
from guardian.routes import health as health_routes


class _MockResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


def _mock_local_runtime_request(
    url: str,
    *args,
    **kwargs,
) -> _MockResponse:
    _ = (args, kwargs)
    if url.endswith("/api/tags"):
        return _MockResponse({"models": [{"name": "qwen3.5:0.8b"}]})
    return _MockResponse({"status": "ok"})


def _healthy_completion_service() -> dict[str, object]:
    return {
        "ok": True,
        "redis_reachable": True,
        "enqueue_test_ok": True,
        "worker_heartbeat_detected": True,
        "worker_heartbeat_age_seconds": 0.5,
        "worker_heartbeat_status": "fresh",
        "heartbeat_key": "codexify:worker:chat:heartbeat",
        "status_reason": "ok",
        "error": None,
        "dependency": None,
        "dependency_unavailable": False,
    }


def _healthy_queue() -> dict[str, object]:
    return {
        "depth": 0,
        "status": "progressing",
        "error": None,
        "dependency": None,
        "dependency_unavailable": False,
    }


def _snapshot_settings(settings):
    return {
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


def _apply_local_only_runtime(settings) -> None:
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


def test_health_llm_reports_effective_local_chat_model(
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
    snapshot = _snapshot_settings(settings)
    try:
        _apply_local_only_runtime(settings)
        payload = test_client.get("/health/llm").json()
        assert payload["model"] == "qwen3.5:0.8b"
        assert payload["provider_runtime"]["default_model"] == "qwen3.5:0.8b"
        assert payload["model_resolution"]["source"] == "LOCAL_CHAT_MODEL"
        assert payload["runtime"]["reasoning"]["mode"] == "no_think"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)
        health_routes._LLM_HEALTH_PROBE_CACHE = None
        health_routes._LLM_HEALTH_PROBE_TS = 0.0


def test_health_chat_reports_effective_local_chat_model(
    test_client,
    monkeypatch,
):
    monkeypatch.setattr(
        "guardian.core.ai_router.requests.get",
        _mock_local_runtime_request,
    )
    monkeypatch.setattr(
        health_routes,
        "_collect_completion_service_health",
        _healthy_completion_service,
    )
    monkeypatch.setattr(
        health_routes, "_collect_chat_queue_health", _healthy_queue
    )

    settings = get_settings()
    snapshot = _snapshot_settings(settings)
    try:
        _apply_local_only_runtime(settings)
        payload = test_client.get("/health/chat").json()
        assert payload["model"] == "qwen3.5:0.8b"
        assert payload["provider_runtime"]["default_model"] == "qwen3.5:0.8b"
        assert payload["model_resolution"]["source"] == "LOCAL_CHAT_MODEL"
        assert payload["runtime"]["reasoning"]["mode"] == "no_think"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_health_llm_surfaces_local_model_resolution_error(
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
    snapshot = _snapshot_settings(settings)
    try:
        _apply_local_only_runtime(settings)
        settings.LOCAL_CHAT_MODEL = ""
        payload = test_client.get("/health/llm").json()
        assert payload["status"] == "misconfigured"
        assert payload["error"] == LOCAL_MODEL_RESOLUTION_ERROR
        assert payload["failure_kind"] == "local_model_missing"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)
        health_routes._LLM_HEALTH_PROBE_CACHE = None
        health_routes._LLM_HEALTH_PROBE_TS = 0.0
