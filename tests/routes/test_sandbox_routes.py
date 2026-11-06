"""Sandbox route tests.

The route is an operator surface: the caller is a trusted worker, not an end
user. These tests cover the operator-auth boundary, the provider-agnostic
dispatch (the caller never names a provider), and the denial mapping.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.core.dependencies import require_service_capability
from guardian.routes import sandbox as sandbox_route
from guardian.sandbox import contracts as c
from guardian.sandbox import registry


class _StubProvider:
    name = "stub"

    def supported_postures(self):
        return (
            c.POSTURE_READ_ONLY_WORKSPACE,
            c.POSTURE_EGRESS_DENY,
            c.POSTURE_CPU_LIMIT,
            c.POSTURE_MEMORY_LIMIT,
            c.POSTURE_STORAGE_CEILING,
            c.POSTURE_TIMEOUT,
            c.POSTURE_TEARDOWN,
        )

    def execute(self, request):
        return c.SandboxResult(
            contract_version=c.SANDBOX_CONTRACT_VERSION,
            request_id=request.request_id,
            attempt_id=request.attempt_id,
            status=c.STATUS_COMPLETED,
            provenance=c.SandboxProvenance(
                provider="stub", adapter="stub", sandbox_id="stub-1"
            ),
            attested_posture=c.AttestedPosture(
                requested=request.required_postures(),
                established=request.required_postures(),
            ),
            exit_code=0,
            stdout=b"hello",
            stderr=b"",
            teardown_status="complete",
        )


class _DenyingProvider(_StubProvider):
    def execute(self, request):
        raise c.SandboxPolicyDenied(
            "provider cannot establish the requested sandbox posture: storage_ceiling",
            provider="stub",
            unsupported=(c.POSTURE_STORAGE_CEILING,),
        )


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(sandbox_route.router)
    app.dependency_overrides[require_service_capability] = lambda: None
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def stub_provider():
    registry.register_provider("stub", _StubProvider)
    yield
    registry.unregister_provider("stub")


@pytest.fixture()
def denying_provider():
    registry.register_provider("stub", _DenyingProvider)
    yield
    registry.unregister_provider("stub")


def _payload(**overrides):
    payload = {
        "command": "echo hello",
        "workspace_identity": "ws",
        "workspace_source": "/tmp/workspace.tar",
    }
    payload.update(overrides)
    return payload


def test_execute_dispatches_to_the_configured_provider(client, stub_provider, monkeypatch):
    monkeypatch.setenv("CODEXIFY_SANDBOX_PROVIDER", "stub")
    response = client.post("/api/sandbox/execute", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == c.STATUS_COMPLETED
    assert body["stdout"] == "hello"
    assert body["provider"] == "stub"
    assert body["attested_posture"]["conformant"] is True
    assert body["teardown_status"] == "complete"


def test_execute_rejects_a_wrong_service_credential():
    """The service gate must reject a credential that is not the service key."""
    app = FastAPI()
    app.include_router(sandbox_route.router)
    with TestClient(app, headers={"X-API-Key": "not-the-service-key"}) as client:
        response = client.post("/api/sandbox/execute", json=_payload())
    assert response.status_code in (401, 403), response.text


def test_the_route_does_not_use_operator_authority():
    """The sandbox route must not widen the frozen operator-route surface."""
    import inspect

    source = inspect.getsource(sandbox_route)
    assert "require_operator_auth" not in source
    assert "require_service_capability" in source


def test_a_policy_denial_is_reported_as_a_conflict(client, denying_provider, monkeypatch):
    monkeypatch.setenv("CODEXIFY_SANDBOX_PROVIDER", "stub")
    response = client.post("/api/sandbox/execute", json=_payload())
    assert response.status_code == 409
    assert "storage_ceiling" in response.json()["detail"]


def test_an_unconfigured_provider_is_reported_as_unavailable(client, monkeypatch):
    monkeypatch.delenv("CODEXIFY_SANDBOX_PROVIDER", raising=False)
    response = client.post("/api/sandbox/execute", json=_payload())
    assert response.status_code == 503


def test_the_provider_listing_reports_declared_postures(client, stub_provider):
    response = client.get("/api/sandbox/providers")
    assert response.status_code == 200
    providers = {item["name"]: item for item in response.json()["providers"]}
    assert "stub" in providers
    assert c.POSTURE_STORAGE_CEILING in providers["stub"]["supported_postures"]


def test_the_caller_never_names_a_provider(client, stub_provider, monkeypatch):
    """A caller-supplied provider name is not part of the request contract."""
    monkeypatch.setenv("CODEXIFY_SANDBOX_PROVIDER", "stub")
    response = client.post(
        "/api/sandbox/execute", json=_payload(provider="some_other_provider")
    )
    # The extra field is ignored; the configured provider still ran.
    assert response.status_code == 200
    assert response.json()["provider"] == "stub"
