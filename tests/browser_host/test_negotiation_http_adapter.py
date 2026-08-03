from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.browser_host import http_adapter
from guardian.routes import browser_host


ROOT = Path(__file__).resolve().parents[2]
HELLO = json.loads(
    (ROOT / "browser_host/contracts/fixtures/valid/hello-compatible.json").read_text()
)


def _client(monkeypatch):
    monkeypatch.setattr(
        http_adapter,
        "get_settings",
        lambda: SimpleNamespace(
            GUARDIAN_DEV_MODE=True,
            GUARDIAN_BROWSER_HOST_NEGOTIATION_DEV_ENABLED=True,
            GUARDIAN_BROWSER_HOST_ATTACHMENT_DEV_ENABLED=False,
        ),
    )
    monkeypatch.setattr(http_adapter, "_exposure_mode", lambda: "local_safe")
    app = FastAPI()
    assert http_adapter.install_browser_host_negotiation_adapter(
        app, browser_host.negotiation_router
    )
    return app, TestClient(app)


def test_credential_free_hello_returns_contract_valid_compatible_result(monkeypatch):
    app, client = _client(monkeypatch)
    response = client.post(
        "/dev/browser-host/v1/negotiate",
        json=HELLO,
        headers={"Cookie": "gc_session=must_not_be_required"},
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    payload = response.json()
    assert http_adapter.validate_contract("negotiation", payload)
    assert payload["compatibilityOutcome"] == "compatible"
    assert "apiKey" not in response.text
    assert "cookie" not in response.text
    assert "jwt" not in response.text
    http_adapter.shutdown_browser_host_negotiation_adapter(app)


def test_incompatible_hello_returns_valid_fail_closed_result(monkeypatch):
    app, client = _client(monkeypatch)
    hello = copy.deepcopy(HELLO)
    hello["supportedProtocolVersions"] = ["9.0.0"]
    response = client.post("/dev/browser-host/v1/negotiate", json=hello)
    assert response.status_code == 200
    payload = response.json()
    assert http_adapter.validate_contract("negotiation", payload)
    assert payload["compatibilityOutcome"] == "incompatible"
    assert payload["selectedProtocolVersion"] is None
    assert payload["errorCode"] == "unsupported_protocol_version"
    http_adapter.shutdown_browser_host_negotiation_adapter(app)


def test_malformed_body_uses_bounded_validation_error_and_no_policy_side_effect(
    monkeypatch, caplog
):
    app, client = _client(monkeypatch)
    sentinel = "raw-negotiation-body-must-not-be-logged"
    response = client.post(
        "/dev/browser-host/v1/negotiate", json={"sentinel": sentinel}
    )
    assert response.status_code == 422
    assert http_adapter.validate_contract("error", response.json())
    assert sentinel not in caplog.text
    assert sentinel not in response.text
    http_adapter.shutdown_browser_host_negotiation_adapter(app)


def test_disabled_route_is_normal_not_found(monkeypatch):
    monkeypatch.setattr(
        http_adapter,
        "get_settings",
        lambda: SimpleNamespace(
            GUARDIAN_DEV_MODE=False,
            GUARDIAN_BROWSER_HOST_NEGOTIATION_DEV_ENABLED=False,
        ),
    )
    monkeypatch.setattr(http_adapter, "_exposure_mode", lambda: "local_safe")
    app = FastAPI()
    assert not http_adapter.install_browser_host_negotiation_adapter(
        app, browser_host.negotiation_router
    )
    assert TestClient(app).post("/dev/browser-host/v1/negotiate", json=HELLO).status_code == 404
