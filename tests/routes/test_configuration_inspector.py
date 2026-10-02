from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
import requests
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import ValidationError

from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    OPERATOR_SESSION_PURPOSE,
    issue_session_token,
)
from guardian.core.hosted_room_session import issue_guest_session_token
import guardian.core.provider_registry as provider_registry
from guardian.routes import configuration_inspector as inspector

PATH = "/api/operator/configuration"
OPERATOR_KEY = "configuration-inspector-operator-key"
SESSION_SECRET = "configuration-inspector-session-secret"
SECRET_SENTINELS = (
    "LOCAL_API_KEY_SENTINEL_DO_NOT_EXPOSE",
    "OPENAI_API_KEY_SENTINEL_DO_NOT_EXPOSE",
    "DATABASE_DSN_SENTINEL_DO_NOT_EXPOSE",
    "REDIS_URL_SENTINEL_DO_NOT_EXPOSE",
    "EGRESS_LIST_SENTINEL_DO_NOT_EXPOSE",
)


def _settings(**overrides):
    values = {
        "LLM_PROVIDER": "local",
        "CODEXIFY_LOCAL_ONLY_MODE": True,
        "ALLOW_CLOUD_PROVIDERS": False,
        "CODEXIFY_EGRESS_ALLOWLIST": "openai",
        "LOCAL_CHAT_MODEL": "library2/ministral-3:8b",
        "LOCAL_LLM_MODEL": "local-fallback-model",
        "DEFAULT_LOCAL_MODEL": "default-local-model",
        "LLM_MODEL": "logical-local-model",
        "LOCAL_API_KEY": SECRET_SENTINELS[0],
        "OPENAI_API_KEY": SECRET_SENTINELS[1],
        "DATABASE_URL": SECRET_SENTINELS[2],
        "REDIS_URL": SECRET_SENTINELS[3],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _profile_state() -> dict[str, object]:
    return {
        "name": "v1-local-core-web-mcp",
        "version": 1,
        "surface": "web_mcp",
        "valid": True,
        "provider_contract": {
            "expected": {"provider": "local"},
            "actual": {"api_key": SECRET_SENTINELS[1]},
        },
        "criticality": {"critical": {"services": [], "routes": []}},
        "mismatches": [SECRET_SENTINELS[2]],
        "routes": {
            "declared": {"secret_like_label": SECRET_SENTINELS[3]},
            "mounted": ["admin", "health", "connections"],
        },
    }


@pytest.fixture
def inspector_settings(monkeypatch):
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    monkeypatch.setenv("GUARDIAN_API_KEY", OPERATOR_KEY)
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", SESSION_SECRET)
    settings = _settings()
    monkeypatch.setattr(inspector, "get_settings", lambda: settings)
    return settings


@pytest.fixture
def client(inspector_settings):
    _ = inspector_settings
    app = FastAPI()
    app.state.supported_profile = _profile_state()
    app.include_router(inspector.router)
    # Root conftest installs a default operator key on every TestClient;
    # override it here so unauthenticated behavior remains testable.
    with TestClient(app, headers={"X-API-Key": ""}) as test_client:
        yield test_client


def _operator_get(client: TestClient, **kwargs):
    return client.get(PATH, headers={"X-API-Key": OPERATOR_KEY}, **kwargs)


def test_route_contract_is_one_get_with_explicit_bounded_models(client):
    routes = [route for route in inspector.router.routes if isinstance(route, APIRoute)]
    assert len(routes) == 1
    route = routes[0]
    assert route.path == PATH
    assert route.methods == {"GET"}
    assert route.dependant.query_params == []

    models = (
        inspector.ConfigurationSnapshot,
        inspector.ProcessScope,
        inspector.SupportedProfileSection,
        inspector.MountedRoutesSection,
        inspector.ProviderEgressSection,
        inspector.LocalInferenceSection,
    )
    for model in models:
        assert model.model_config["extra"] == "forbid"

    assert set(inspector.ConfigurationSnapshot.model_fields) == {
        "schema_version",
        "generated_at",
        "process",
        "supported_profile",
        "mounted_routes",
        "provider_egress",
        "local_inference",
    }
    response = _operator_get(client)
    assert response.status_code == 200, response.text
    payload = response.json()
    with pytest.raises(ValidationError):
        inspector.ConfigurationSnapshot.model_validate(
            {**payload, "arbitrary": {}}
        )
    assert payload["schema_version"] == 1
    assert payload["process"]["service"] == "guardian"
    assert payload["process"]["process_id"] > 0
    assert payload["process"]["scope"] == "responding_guardian_process"

    arbitrary_selector = _operator_get(
        client, params={"key": "OPENAI_API_KEY", "family": "all"}
    )
    assert arbitrary_selector.status_code == 200
    selected_payload = arbitrary_selector.json()
    selected_payload.pop("generated_at")
    payload.pop("generated_at")
    assert selected_payload == payload
    assert client.post(PATH, headers={"X-API-Key": OPERATOR_KEY}).status_code == 405


def test_operator_auth_accepts_raw_key_and_exact_operator_session(client):
    raw_key = client.get(PATH, headers={"X-API-Key": OPERATOR_KEY})
    assert raw_key.status_code == 200, raw_key.text

    operator_token, _ = issue_session_token(
        subject="operator", purpose=OPERATOR_SESSION_PURPOSE
    )
    operator_session = client.get(
        PATH, headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert operator_session.status_code == 200, operator_session.text

    account_token, _ = issue_session_token(
        subject="account-user", purpose=ACCOUNT_SESSION_PURPOSE
    )
    guest_token, _ = issue_guest_session_token(
        room_id="room-a",
        room_slug="room-a",
        participant_id="guest-a",
        invitation_id="invite-a",
    )
    for token in (account_token, guest_token):
        denied = client.get(PATH, headers={"Authorization": f"Bearer {token}"})
        assert denied.status_code == 401

    anonymous = client.get(PATH)
    assert anonymous.status_code == 401


def test_o02_projects_only_startup_resolved_profile_posture(client):
    response = _operator_get(client)
    assert response.status_code == 200
    profile = response.json()["supported_profile"]
    assert profile == {
        "evidence": "resolved",
        "owner": "guardian.core.supported_profile",
        "profile_name": "v1-local-core-web-mcp",
        "version": 1,
        "surface_class": "web_mcp",
        "valid": True,
        "unavailable_reason": None,
    }
    serialized = response.text
    for sentinel in SECRET_SENTINELS:
        assert sentinel not in serialized
    assert "provider_contract" not in response.json()["supported_profile"]
    assert "mismatches" not in response.json()["supported_profile"]


def test_o02_missing_or_invalid_startup_state_is_unavailable(client):
    client.app.state.supported_profile = None
    response = _operator_get(client)
    assert response.status_code == 200
    profile = response.json()["supported_profile"]
    assert profile["evidence"] == "unavailable"
    assert profile["unavailable_reason"] == "supported_profile_state_unavailable"
    assert profile["profile_name"] is None

    client.app.state.supported_profile = {**_profile_state(), "version": True}
    response = _operator_get(client)
    assert response.json()["supported_profile"]["evidence"] == "unavailable"


def test_o15_uses_startup_published_mounted_route_inventory(client):
    response = _operator_get(client)
    assert response.status_code == 200
    mounted = response.json()["mounted_routes"]
    assert mounted["evidence"] == "observed"
    assert mounted["owner"] == "guardian.guardian_api._refresh_supported_profile_state"
    assert mounted["route_families"] == ["admin", "connections", "health"]
    assert mounted["interpretation"] == (
        "mounted_only_not_authorization_health_or_release_support"
    )

    client.app.state.supported_profile = {
        **_profile_state(),
        "routes": {"declared": {"admin": "enabled"}},
    }
    unavailable = _operator_get(client).json()["mounted_routes"]
    assert unavailable["evidence"] == "unavailable"
    assert unavailable["unavailable_reason"] == "mounted_route_inventory_unavailable"


def test_o07_reports_only_configured_provider_and_egress_posture(
    client, monkeypatch
):
    response = _operator_get(client)
    assert response.status_code == 200
    posture = response.json()["provider_egress"]
    assert posture == {
        "evidence": "resolved",
        "owner": "guardian.core.config.Settings+guardian.core.egress",
        "configured_provider_class": "local",
        "local_only_mode": True,
        "cloud_providers_allowed": False,
        "egress_allowlist_configured": True,
        "unavailable_reason": None,
    }
    assert "provider_available" not in posture
    assert "available" not in posture
    assert SECRET_SENTINELS[4] not in response.text

    client_settings = _settings(LLM_PROVIDER="not-a-supported-provider")
    client_settings.CODEXIFY_EGRESS_ALLOWLIST = SECRET_SENTINELS[4]
    client.app.state.supported_profile = _profile_state()
    # A malformed/unrecognized provider cannot be emitted as an arbitrary value.
    monkeypatch.setattr(inspector, "get_settings", lambda: client_settings)
    unavailable = _operator_get(client).json()["provider_egress"]
    assert unavailable["evidence"] == "unavailable"
    assert unavailable["unavailable_reason"] == "provider_egress_posture_unavailable"
    assert SECRET_SENTINELS[4] not in json.dumps(unavailable)


def test_o08_uses_canonical_local_target_resolver_and_fails_independently(
    client, monkeypatch
):
    response = _operator_get(client)
    assert response.status_code == 200
    local = response.json()["local_inference"]
    assert local == {
        "evidence": "resolved",
        "owner": "guardian.core.provider_registry.default_model_for_provider",
        "provider_class": "local",
        "configured_target": "library2/ministral-3:8b",
        "unavailable_reason": None,
    }
    assert "served_model" not in local
    assert "effective_model" not in local

    monkeypatch.setattr(
        inspector,
        "default_model_for_provider",
        lambda *_args, **_kwargs: "",
    )
    failed = _operator_get(client).json()
    assert failed["local_inference"]["evidence"] == "unavailable"
    assert failed["local_inference"]["unavailable_reason"] == (
        "local_inference_target_unavailable"
    )
    assert failed["supported_profile"]["evidence"] == "resolved"
    assert failed["mounted_routes"]["evidence"] == "observed"
    assert failed["provider_egress"]["evidence"] == "resolved"


def test_provider_and_local_target_resolution_failures_are_sanitized(
    client, monkeypatch
):
    def fail_settings():
        raise RuntimeError(SECRET_SENTINELS[2])

    monkeypatch.setattr(inspector, "get_settings", fail_settings)
    response = _operator_get(client)
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_egress"]["evidence"] == "unavailable"
    assert payload["local_inference"]["evidence"] == "unavailable"
    assert SECRET_SENTINELS[2] not in response.text
    assert payload["supported_profile"]["evidence"] == "resolved"
    assert payload["mounted_routes"]["evidence"] == "observed"


def test_secret_sentinels_never_appear_in_serialized_snapshot(client):
    response = _operator_get(client)
    assert response.status_code == 200
    for sentinel in SECRET_SENTINELS:
        assert sentinel not in response.text


def test_schema_has_no_account_selector_and_endpoint_needs_no_account_lookup(client):
    models = (
        inspector.ConfigurationSnapshot,
        inspector.ProcessScope,
        inspector.SupportedProfileSection,
        inspector.MountedRoutesSection,
        inspector.ProviderEgressSection,
        inspector.LocalInferenceSection,
    )
    forbidden_names = {"account_id", "user_id", "thread_id", "persona_id"}
    for model in models:
        assert not forbidden_names.intersection(model.model_fields)

    response = _operator_get(client)
    assert response.status_code == 200
    assert "account" not in response.json()["process"]


def test_inspector_does_not_call_network_provider_discovery_or_health(
    client, monkeypatch
):
    def forbidden_call(*_args, **_kwargs):
        raise AssertionError("active probe called by Configuration Inspector")

    monkeypatch.setattr(requests.sessions.Session, "request", forbidden_call)
    monkeypatch.setattr(
        provider_registry, "_discover_dynamic_provider_models", forbidden_call
    )
    from guardian.routes import health as health_routes

    monkeypatch.setattr(health_routes, "health_llm", forbidden_call)
    response = _operator_get(client)
    assert response.status_code == 200, response.text
    assert response.json()["provider_egress"]["evidence"] == "resolved"
