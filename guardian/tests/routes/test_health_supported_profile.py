from __future__ import annotations

import json

from guardian import guardian_api
from guardian.core.config import get_settings
from guardian.core.supported_profile import load_supported_profile
from guardian.routes import health as health_routes


def _mock_local_runtime_request(url: str, *args, **kwargs):
    _ = (args, kwargs)
    if url.endswith("/api/tags"):
        return type(
            "Resp",
            (),
            {
                "status_code": 200,
                "json": lambda self=None: {
                    "models": [{"name": "library2/ministral-3:8b"}]
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
        "OPENAI_API_KEY": getattr(settings, "OPENAI_API_KEY", None),
        "OPENAI_BASE_URL": getattr(settings, "OPENAI_BASE_URL", None),
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "GROQ_BASE_URL": settings.GROQ_BASE_URL,
        "ALIBABA_API_KEY": getattr(settings, "ALIBABA_API_KEY", None),
        "ALIBABA_API_BASE": getattr(settings, "ALIBABA_API_BASE", None),
        "MINIMAX_API_KEY": getattr(settings, "MINIMAX_API_KEY", None),
        "MINIMAX_API_BASE": getattr(settings, "MINIMAX_API_BASE", None),
    }


def _snapshot_supported_profile_app_state():
    return {
        "supported_profile_manifest": guardian_api.app.state.supported_profile_manifest,
        "supported_profile": guardian_api.app.state.supported_profile,
        "supported_profile_enabled_labels": set(
            getattr(
                guardian_api.app.state,
                "supported_profile_enabled_labels",
                set(),
            )
        ),
        "supported_profile_hidden_paths": set(
            getattr(
                guardian_api.app.state,
                "supported_profile_hidden_paths",
                set(),
            )
        ),
    }


def _apply_supported_profile_local_runtime(settings) -> None:
    settings.LLM_PROVIDER = "local"
    settings.ALLOW_CLOUD_PROVIDERS = False
    settings.CODEXIFY_LOCAL_ONLY_MODE = True
    settings.CODEXIFY_EGRESS_ALLOWLIST = ""
    settings.LOCAL_BASE_URL = "http://host.docker.internal:11434/v1"
    settings.LOCAL_API_KEY = "local"
    settings.LOCAL_LLM_MODEL = "library2/ministral-3:8b"
    settings.LOCAL_CHAT_MODEL = "library2/ministral-3:8b"
    settings.DEFAULT_LOCAL_MODEL = "library2/ministral-3:8b"
    settings.LLM_MODEL = "library2/ministral-3:8b"
    settings.OPENAI_API_KEY = None
    settings.OPENAI_BASE_URL = None
    settings.GROQ_API_KEY = None
    settings.GROQ_BASE_URL = None
    settings.ALIBABA_API_KEY = None
    settings.ALIBABA_API_BASE = None
    settings.MINIMAX_API_KEY = None
    settings.MINIMAX_API_BASE = None


def _install_supported_profile_manifest() -> None:
    guardian_api.app.state.supported_profile_manifest = load_supported_profile(
        "v1-local-core-web-mcp"
    )
    guardian_api.app.state.supported_profile_enabled_labels = set()
    guardian_api.app.state.supported_profile_hidden_paths = set()


def test_health_root_sanitizes_supported_profile_state(client, monkeypatch):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
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

    settings = get_settings()
    snapshot = _snapshot_settings(settings)
    app_snapshot = _snapshot_supported_profile_app_state()
    try:
        _apply_supported_profile_local_runtime(settings)
        _install_supported_profile_manifest()
        guardian_api._refresh_supported_profile_state(
            guardian_api.app, settings
        )

        response = client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        supported_profile = payload["supported_profile"]

        assert supported_profile["name"] == "v1-local-core-web-mcp"
        assert supported_profile["valid"] is True
        assert supported_profile["selected_provider"] == "local"
        assert supported_profile["selected_provider_supported"] is True
        assert supported_profile["release_hold"] is False
        assert supported_profile["cloud_capable_configuration_present"] is False
        assert "provider_contract" not in supported_profile
        assert "actual" not in json.dumps(supported_profile)
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)
        guardian_api.app.state.supported_profile_manifest = app_snapshot[
            "supported_profile_manifest"
        ]
        guardian_api.app.state.supported_profile = app_snapshot[
            "supported_profile"
        ]
        guardian_api.app.state.supported_profile_enabled_labels = app_snapshot[
            "supported_profile_enabled_labels"
        ]
        guardian_api.app.state.supported_profile_hidden_paths = app_snapshot[
            "supported_profile_hidden_paths"
        ]


def test_api_health_llm_exposes_selected_provider_alignment(
    client,
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
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
    app_snapshot = _snapshot_supported_profile_app_state()
    try:
        _apply_supported_profile_local_runtime(settings)
        _install_supported_profile_manifest()
        guardian_api._refresh_supported_profile_state(
            guardian_api.app, settings
        )

        response = client.get("/api/health/llm")
        assert response.status_code == 200
        payload = response.json()
        details = payload["details"]
        supported_profile = details["supported_profile"]

        assert details["provider"] == "local"
        assert supported_profile["name"] == "v1-local-core-web-mcp"
        assert supported_profile["selected_provider"] == "local"
        assert supported_profile["selected_provider_supported"] is True
        assert supported_profile["release_hold"] is False
        assert supported_profile["cloud_capable_configuration_present"] is False
        assert details["provider_truth"]["supported_profile_name"] == (
            "v1-local-core-web-mcp"
        )
        assert details["provider_truth"]["supported_profile_approved"] is True
        assert details["provider_truth"]["executable"] is True
        assert "provider_contract" not in json.dumps(payload)
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)
        guardian_api.app.state.supported_profile_manifest = app_snapshot[
            "supported_profile_manifest"
        ]
        guardian_api.app.state.supported_profile = app_snapshot[
            "supported_profile"
        ]
        guardian_api.app.state.supported_profile_enabled_labels = app_snapshot[
            "supported_profile_enabled_labels"
        ]
        guardian_api.app.state.supported_profile_hidden_paths = app_snapshot[
            "supported_profile_hidden_paths"
        ]
        health_routes._LLM_HEALTH_PROBE_CACHE = None
        health_routes._LLM_HEALTH_PROBE_TS = 0.0


def test_api_health_llm_reports_cloud_capable_posture_as_release_hold(
    client,
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
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
    app_snapshot = _snapshot_supported_profile_app_state()
    try:
        _apply_supported_profile_local_runtime(settings)
        _install_supported_profile_manifest()
        settings.GROQ_API_KEY = "test-groq-key"
        settings.GROQ_BASE_URL = "https://api.groq.com/openai/v1"
        guardian_api._refresh_supported_profile_state(
            guardian_api.app, settings
        )

        response = client.get("/api/health/llm")
        assert response.status_code == 200
        payload = response.json()
        details = payload["details"]
        supported_profile = details["supported_profile"]

        assert supported_profile["cloud_capable_configuration_present"] is True
        assert supported_profile["release_hold"] is True
        assert details["provider_truth"]["supported_profile_approved"] is True
        assert "test-groq-key" not in response.text
        assert "provider_contract" not in response.text
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)
        guardian_api.app.state.supported_profile_manifest = app_snapshot[
            "supported_profile_manifest"
        ]
        guardian_api.app.state.supported_profile = app_snapshot[
            "supported_profile"
        ]
        guardian_api.app.state.supported_profile_enabled_labels = app_snapshot[
            "supported_profile_enabled_labels"
        ]
        guardian_api.app.state.supported_profile_hidden_paths = app_snapshot[
            "supported_profile_hidden_paths"
        ]
        health_routes._LLM_HEALTH_PROBE_CACHE = None
        health_routes._LLM_HEALTH_PROBE_TS = 0.0
