from __future__ import annotations

import copy
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from guardian.browser_host.attachment_grants import AttachmentGrantStore
from guardian.browser_host import http_adapter
from guardian.routes import browser_host


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "browser_host" / "contracts" / "fixtures" / "valid"
API_KEY = "synthetic-guardian-api-key-not-a-secret"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _request() -> dict:
    request = _load("attachment-grant-request-ephemeral.json")
    request["requestId"] = "request-selected-1"
    return request


def _attachment() -> dict:
    return _load("attachment-attempt-ephemeral.json")


def _enabled_app(
    monkeypatch: pytest.MonkeyPatch,
    *,
    clock: list[datetime] | None = None,
) -> tuple[FastAPI, TestClient, list[datetime] | None]:
    monkeypatch.setattr(
        http_adapter,
        "get_settings",
        lambda: SimpleNamespace(
            GUARDIAN_DEV_MODE=True,
            GUARDIAN_BROWSER_HOST_ATTACHMENT_DEV_ENABLED=True,
        ),
    )
    monkeypatch.setattr(http_adapter, "_exposure_mode", lambda: "local_safe")
    app = FastAPI()
    assert http_adapter.install_browser_host_attachment_adapter(
        app, browser_host.router
    ) is True
    if clock is not None:
        app.state.browser_host_attachment_grant_store = AttachmentGrantStore(
            clock=lambda: clock[0]
        )
    app.dependency_overrides[browser_host.get_current_user] = (
        lambda: "guardian-subject-test"
    )
    client = TestClient(app)
    return app, client, clock


def _issue(client: TestClient) -> tuple[dict, str]:
    response = client.post(
        "/dev/browser-host/v1/attachment-grants",
        headers={"X-API-Key": API_KEY},
        json=_request(),
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert http_adapter.validate_contract("attachmentGrant", payload)
    return payload, payload["grantBearer"]


def _attachment_headers(bearer: str, instance_id: str = "browser-host-instance-1") -> dict[str, str]:
    return {
        "Authorization": f"BrowserHostAttachmentGrant {bearer}",
        "X-Codexify-Browser-Host-Instance-Id": instance_id,
    }


def _cleanup(app: FastAPI, client: TestClient) -> None:
    client.close()
    http_adapter.shutdown_browser_host_attachment_adapter(app)


def test_unauthenticated_grant_issuance_uses_existing_auth_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client, _ = _enabled_app(monkeypatch)
    app.dependency_overrides[browser_host.get_current_user] = (
        lambda: (_ for _ in ()).throw(HTTPException(status_code=401, detail="Missing API key"))
    )
    response = client.post(
        "/dev/browser-host/v1/attachment-grants",
        json=_request(),
    )
    assert response.status_code == 401
    assert not hasattr(app.state, "browser_host_attachment_grant_store") or (
        app.state.browser_host_attachment_grant_store.snapshot_for_testing() == ()
    )
    _cleanup(app, client)


def test_authenticated_issuance_is_contract_valid_no_store_and_subject_free(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app, client, _ = _enabled_app(monkeypatch)
    payload, bearer = _issue(client)
    assert payload["remainingUses"] == 1
    assert payload["retentionClass"] == "ephemeral"
    assert "subjectId" not in payload
    assert all(
        forbidden not in json.dumps(payload)
        for forbidden in ("apiKey", "cookie", "jwt", "password", "role")
    )
    assert "no-store" in client.post(
        "/dev/browser-host/v1/attachment-grants",
        headers={"X-API-Key": API_KEY},
        json=_request(),
    ).headers["cache-control"]
    assert bearer not in caplog.text
    _cleanup(app, client)


def test_attachment_uses_only_grant_and_returns_ephemeral_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client, _ = _enabled_app(monkeypatch)
    _, bearer = _issue(client)
    response = client.post(
        "/dev/browser-host/v1/attachments",
        headers=_attachment_headers(bearer),
        json=_attachment(),
    )
    assert response.status_code == 202
    receipt = response.json()
    assert http_adapter.validate_contract("receipt", receipt)
    assert receipt["attachmentOutcome"] == "accepted"
    assert receipt["persistenceOutcome"] == "not_persisted"
    assert receipt["guardianCorrelationId"].startswith("guardian-attachment-")
    assert "content" not in receipt
    assert "X-API-Key" not in json.dumps(receipt)
    _cleanup(app, client)


def test_attachment_route_does_not_call_ordinary_guardian_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client, _ = _enabled_app(monkeypatch)
    _, bearer = _issue(client)
    app.dependency_overrides[browser_host.get_current_user] = (
        lambda: (_ for _ in ()).throw(AssertionError("ordinary auth was used"))
    )
    headers = _attachment_headers(bearer)
    headers["Cookie"] = "gc_session=synthetic-cookie"
    headers["X-API-Key"] = API_KEY
    response = client.post(
        "/dev/browser-host/v1/attachments",
        headers=headers,
        json=_attachment(),
    )
    assert response.status_code == 202
    _cleanup(app, client)


def test_replay_and_expiration_return_valid_409_rejections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client, _ = _enabled_app(monkeypatch)
    _, bearer = _issue(client)
    first = client.post(
        "/dev/browser-host/v1/attachments",
        headers=_attachment_headers(bearer),
        json=_attachment(),
    )
    replay = client.post(
        "/dev/browser-host/v1/attachments",
        headers=_attachment_headers(bearer),
        json=_attachment(),
    )
    assert first.status_code == 202
    assert replay.status_code == 409
    assert http_adapter.validate_contract("receipt", replay.json())
    assert replay.json()["attachmentOutcome"] == "rejected"

    clock = [datetime(2026, 8, 1, 14, 0, tzinfo=timezone.utc)]
    _cleanup(app, client)
    app, client, _ = _enabled_app(monkeypatch, clock=clock)
    _, expired_bearer = _issue(client)
    clock[0] += timedelta(seconds=121)
    expired = client.post(
        "/dev/browser-host/v1/attachments",
        headers=_attachment_headers(expired_bearer),
        json=_attachment(),
    )
    assert expired.status_code == 409
    assert http_adapter.validate_contract("receipt", expired.json())
    _cleanup(app, client)


@pytest.mark.parametrize(
    ("name", "mutate", "expected_code"),
    [
        ("instance", lambda body: None, "permission_denied"),
        ("request", lambda body: body.update({"requestId": "request-other-1"}), "permission_denied"),
        ("version", lambda body: body.update({"protocolVersion": "9.0.0"}), "guardian_rejected"),
        ("retention", lambda body: body.update({"requestedRetention": "durable"}), "context_rejected"),
        (
            "confirmation",
            lambda body: body["userConfirmation"].update({"confirmed": False}),
            "permission_denied",
        ),
        (
            "budget",
            lambda body: body["envelope"].update({"content": "x", "contentLength": 65537}),
            "context_rejected",
        ),
    ],
)
def test_scope_policy_and_budget_rejections_are_403_receipts(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    mutate,
    expected_code: str,
) -> None:
    app, client, _ = _enabled_app(monkeypatch)
    _, bearer = _issue(client)
    body = _attachment()
    mutate(body)
    headers = _attachment_headers(bearer)
    if name == "instance":
        headers["X-Codexify-Browser-Host-Instance-Id"] = "other-instance"
    response = client.post(
        "/dev/browser-host/v1/attachments",
        headers=headers,
        json=body,
    )
    assert response.status_code == 403
    assert http_adapter.validate_contract("receipt", response.json())
    assert response.json()["errorCode"] == expected_code
    _cleanup(app, client)


def test_malformed_body_does_not_consume_grant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client, _ = _enabled_app(monkeypatch)
    _, bearer = _issue(client)
    malformed = client.post(
        "/dev/browser-host/v1/attachments",
        headers=_attachment_headers(bearer),
        json={"content": "malformed"},
    )
    assert malformed.status_code == 422
    assert http_adapter.validate_contract("error", malformed.json())
    accepted = client.post(
        "/dev/browser-host/v1/attachments",
        headers=_attachment_headers(bearer),
        json=_attachment(),
    )
    assert accepted.status_code == 202
    _cleanup(app, client)


@pytest.mark.parametrize(
    "authorization",
    [None, "Bearer synthetic-bearer", "BrowserHostAttachmentGrant ", "BrowserHostAttachmentGrant invalid"],
)
def test_missing_or_malformed_grant_authorization_is_401(
    monkeypatch: pytest.MonkeyPatch,
    authorization: str | None,
) -> None:
    app, client, _ = _enabled_app(monkeypatch)
    _, bearer = _issue(client)
    headers = {"X-Codexify-Browser-Host-Instance-Id": "browser-host-instance-1"}
    if authorization is not None:
        headers["Authorization"] = authorization
    response = client.post(
        "/dev/browser-host/v1/attachments",
        headers=headers,
        json=_attachment(),
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "BrowserHostAttachmentGrant"
    assert http_adapter.validate_contract("error", response.json())
    assert bearer not in response.text
    _cleanup(app, client)


def test_concurrent_consumption_has_exactly_one_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client, _ = _enabled_app(monkeypatch)
    _, bearer = _issue(client)
    headers = _attachment_headers(bearer)
    body = _attachment()

    def submit(_: int) -> int:
        with TestClient(app) as concurrent_client:
            return concurrent_client.post(
                "/dev/browser-host/v1/attachments",
                headers=headers,
                json=body,
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(submit, (1, 2)))
    assert sorted(statuses) == [202, 409]
    _cleanup(app, client)


def test_redaction_and_process_local_state_exclude_content_and_bearer(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app, client, _ = _enabled_app(monkeypatch)
    _, bearer = _issue(client)
    body = _attachment()
    content = body["envelope"]["content"]
    response = client.post(
        "/dev/browser-host/v1/attachments",
        headers=_attachment_headers(bearer),
        json=body,
    )
    assert response.status_code == 202
    snapshot = app.state.browser_host_attachment_grant_store.snapshot_for_testing()
    serialized = json.dumps([dict(record) for record in snapshot])
    assert bearer not in serialized
    assert content not in serialized
    assert content not in caplog.text
    assert bearer not in caplog.text
    _cleanup(app, client)


def test_attachment_body_is_not_mutated_or_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client, _ = _enabled_app(monkeypatch)
    _, bearer = _issue(client)
    body = _attachment()
    before = copy.deepcopy(body)
    response = client.post(
        "/dev/browser-host/v1/attachments",
        headers=_attachment_headers(bearer),
        json=body,
    )
    assert response.status_code == 202
    assert body == before
    source = (ROOT / "guardian" / "browser_host" / "http_adapter.py").read_text()
    for forbidden in ("enqueue", "redis", "provider", "command_bus", "write_text"):
        assert forbidden not in source
    _cleanup(app, client)
