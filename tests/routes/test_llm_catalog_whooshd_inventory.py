from __future__ import annotations

import sys
from types import SimpleNamespace

import guardian.routes.health as health_routes
from guardian.core import config as config_module
from guardian.core import llm_catalog
from guardian.core.config import Settings


_GEMMA = "mlx-community/gemma-4-e2b-it-4bit"
_LLAMA = "llama-3.2-3b-mlx"
_QWEN_VL = "qwen2-vl-2b-mlx"
_QWEN_GGUF = "qwen2.5-0.5b-gguf"
_MISMATCH = "configured_model_not_advertised_by_whooshd"


class _Response:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


def _whooshd_inventory(url: str, *args, **kwargs) -> _Response:
    _ = (args, kwargs)
    if url == "http://host.docker.internal:8000/api/tags":
        return _Response({"models": []}, status_code=404)
    if url == "http://host.docker.internal:8000/v1/models":
        return _Response(
            {
                "data": [
                    {"id": _LLAMA},
                    {"id": _QWEN_VL},
                    {"id": _QWEN_GGUF},
                ]
            }
        )
    return _Response({}, status_code=404)


def _healthy_completion_service() -> dict[str, object]:
    return {
        "ok": True,
        "redis_reachable": True,
        "enqueue_test_ok": True,
        "worker_heartbeat_detected": True,
        "worker_heartbeat_age_seconds": 0.2,
        "worker_heartbeat_reason": "ok",
        "worker_heartbeat_status": "fresh",
        "status_reason": "ok",
        "error": None,
        "dependency_unavailable": False,
    }


def _settings() -> Settings:
    return Settings(
        LLM_PROVIDER="local",
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_LOCAL_ONLY_MODE=True,
        CODEXIFY_EGRESS_ALLOWLIST="",
        LOCAL_RUNTIME_PRESET="whooshd-mlx",
        LOCAL_BASE_URL="http://host.docker.internal:8000/v1",
        LOCAL_API_KEY="local",
        LOCAL_PROVIDER_DISPLAY_NAME="Whoosh'd",
        LOCAL_PROVIDER_VENDOR="whooshd",
        LOCAL_LLM_MODEL=_LLAMA,
        LOCAL_CHAT_MODEL=_GEMMA,
        DEFAULT_LOCAL_MODEL=_LLAMA,
        LLM_MODEL=_LLAMA,
        OPENAI_API_KEY=None,
        GROQ_API_KEY=None,
        ALIBABA_API_KEY=None,
        MINIMAX_API_KEY=None,
    )


def test_llm_catalog_route_reports_whooshd_configured_model_mismatch(
    monkeypatch,
) -> None:
    monkeypatch.delenv("CODEXIFY_SUPPORTED_PROFILE", raising=False)
    monkeypatch.setattr(llm_catalog.requests, "get", _whooshd_inventory)
    settings = _settings()
    monkeypatch.setattr(llm_catalog, "get_settings", lambda: settings)

    payload = health_routes.llm_catalog(include="all")

    local = next(
        provider
        for provider in payload["providers"]
        if provider["id"] == "local"
    )
    assert [model["id"] for model in local["models"]] == [
        _LLAMA,
        _QWEN_VL,
        _QWEN_GGUF,
    ]
    assert local["configured_model"] == _GEMMA
    assert local["configured_model_available"] is False
    assert local["availability_reason"] == _MISMATCH
    assert local["model_resolution"]["failure_kind"] == _MISMATCH
    assert local["inventory_source"] == "whooshd:/v1/models"


def test_health_llm_route_degrades_when_whooshd_default_not_advertised(
    monkeypatch,
) -> None:
    monkeypatch.delenv("CODEXIFY_SUPPORTED_PROFILE", raising=False)
    monkeypatch.setattr("guardian.routes.health.requests.get", _whooshd_inventory)
    monkeypatch.setattr(
        "guardian.routes.health._collect_completion_service_health",
        _healthy_completion_service,
    )
    monkeypatch.setitem(
        sys.modules,
        "guardian.guardian_api",
        SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace())),
    )
    health_routes._LLM_HEALTH_PROBE_CACHE = None
    health_routes._LLM_HEALTH_PROBE_TS = 0.0
    settings = _settings()
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)

    try:
        payload = health_routes.health_llm()

        details = payload["details"]
        assert payload["status"] == "down"
        assert details["status"] == "misconfigured"
        assert details["models_available"] is False
        assert details["configured_model"] == _GEMMA
        assert details["configured_model_available"] is False
        assert details["availability_reason"] == _MISMATCH
        assert details["advertised_models"] == [_LLAMA, _QWEN_VL, _QWEN_GGUF]
        assert details["inventory_source"] == "whooshd:/v1/models"
        assert details["provider_truth"]["selectable"] is False
        assert details["release_hold"] is False
    finally:
        health_routes._LLM_HEALTH_PROBE_CACHE = None
        health_routes._LLM_HEALTH_PROBE_TS = 0.0
