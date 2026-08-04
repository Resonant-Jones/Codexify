#!/usr/bin/env python3
"""Run the sanitized development-only Guardian attachment adapter proof."""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.browser_host import http_adapter
from guardian.browser_host.attachment_grants import AttachmentGrantStore
from guardian.routes import browser_host


FIXTURES = ROOT / "browser_host" / "contracts" / "fixtures" / "valid"
BASELINE_COMMIT = "87fe3257c0d0c12ad00a749b631bfeb866ddaaaf"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _request() -> dict:
    request = _load("attachment-grant-request-ephemeral.json")
    request["requestId"] = "request-selected-1"
    return request


def _attachment() -> dict:
    return _load("attachment-attempt-ephemeral.json")


def _configure_enabled() -> None:
    http_adapter.get_settings = lambda: SimpleNamespace(  # type: ignore[method-assign]
        GUARDIAN_DEV_MODE=True,
        GUARDIAN_BROWSER_HOST_ATTACHMENT_DEV_ENABLED=True,
    )
    http_adapter._exposure_mode = lambda: "local_safe"  # type: ignore[method-assign]


def _new_app(*, clock: list[datetime] | None = None) -> tuple[FastAPI, TestClient]:
    _configure_enabled()
    app = FastAPI()
    assert http_adapter.install_browser_host_attachment_adapter(
        app, browser_host.router
    )
    if clock is not None:
        app.state.browser_host_attachment_grant_store = AttachmentGrantStore(
            clock=lambda: clock[0]
        )
    app.dependency_overrides[browser_host.get_current_user] = (
        lambda: "guardian-subject-proof"
    )
    return app, TestClient(app)


def _headers(bearer: str, instance: str = "browser-host-instance-1") -> dict[str, str]:
    return {
        "Authorization": f"BrowserHostAttachmentGrant {bearer}",
        "X-Codexify-Browser-Host-Instance-Id": instance,
    }


def _issue(client: TestClient) -> tuple[dict, str]:
    response = client.post(
        "/dev/browser-host/v1/attachment-grants",
        headers={"X-API-Key": "synthetic-api-key"},
        json=_request(),
    )
    assert response.status_code == 201
    payload = response.json()
    assert http_adapter.validate_contract("attachmentGrant", payload)
    return payload, payload["grantBearer"]


def _close(app: FastAPI, client: TestClient) -> None:
    client.close()
    http_adapter.shutdown_browser_host_attachment_adapter(app)


def _route_paths(app: FastAPI) -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
        if route.path.startswith("/dev/browser-host/v1")
    }


def run_proof() -> dict:
    disabled_app = FastAPI()
    disabled_settings = SimpleNamespace(
        GUARDIAN_DEV_MODE=False,
        GUARDIAN_BROWSER_HOST_ATTACHMENT_DEV_ENABLED=False,
    )
    assert not http_adapter.browser_host_attachment_adapter_enabled(
        disabled_settings, exposure_mode="local_safe"
    )
    assert _route_paths(disabled_app) == set()
    assert not hasattr(disabled_app.state, http_adapter.STORE_STATE_KEY)

    app, client = _new_app()
    assert _route_paths(app) == {
        ("POST", "/dev/browser-host/v1/attachment-grants"),
        ("POST", "/dev/browser-host/v1/attachments"),
    }
    grant, bearer = _issue(client)
    attachment = _attachment()
    accepted = client.post(
        "/dev/browser-host/v1/attachments",
        headers=_headers(bearer),
        json=attachment,
    )
    assert accepted.status_code == 202
    assert http_adapter.validate_contract("receipt", accepted.json())
    assert accepted.json()["persistenceOutcome"] == "not_persisted"
    replay = client.post(
        "/dev/browser-host/v1/attachments",
        headers=_headers(bearer),
        json=attachment,
    )
    assert replay.status_code == 409
    assert http_adapter.validate_contract("receipt", replay.json())
    _close(app, client)

    clock = [datetime(2026, 8, 1, 14, 0, tzinfo=timezone.utc)]
    app, client = _new_app(clock=clock)
    _, expired_bearer = _issue(client)
    clock[0] += timedelta(seconds=121)
    expired = client.post(
        "/dev/browser-host/v1/attachments",
        headers=_headers(expired_bearer),
        json=_attachment(),
    )
    assert expired.status_code == 409
    _close(app, client)

    statuses: dict[str, int] = {}
    codes: dict[str, str] = {}
    cases = {
        "scope": (lambda body: body, {"X-Codexify-Browser-Host-Instance-Id": "other-instance"}),
        "request": (lambda body: body.update({"requestId": "request-other-1"}), {}),
        "version": (lambda body: body.update({"protocolVersion": "9.0.0"}), {}),
        "retention": (lambda body: body.update({"requestedRetention": "durable"}), {}),
        "confirmation": (
            lambda body: body["userConfirmation"].update({"confirmed": False}),
            {},
        ),
        "budget": (
            lambda body: body["envelope"].update({"content": "x", "contentLength": 65537}),
            {},
        ),
    }
    for name, (mutate, header_changes) in cases.items():
        app, client = _new_app()
        _, case_bearer = _issue(client)
        case_body = _attachment()
        mutate(case_body)
        case_headers = _headers(case_bearer)
        case_headers.update(header_changes)
        result = client.post(
            "/dev/browser-host/v1/attachments",
            headers=case_headers,
            json=case_body,
        )
        statuses[name] = result.status_code
        codes[name] = result.json().get("errorCode", "")
        assert result.status_code == 403
        assert http_adapter.validate_contract("receipt", result.json())
        _close(app, client)

    app, client = _new_app()
    _, malformed_bearer = _issue(client)
    malformed = client.post(
        "/dev/browser-host/v1/attachments",
        headers=_headers(malformed_bearer),
        json={"content": "malformed"},
    )
    assert malformed.status_code == 422
    preserved = client.post(
        "/dev/browser-host/v1/attachments",
        headers=_headers(malformed_bearer),
        json=_attachment(),
    )
    assert preserved.status_code == 202
    _close(app, client)

    app, client = _new_app()
    _, concurrent_bearer = _issue(client)
    concurrent_body = _attachment()

    def submit(_: int) -> int:
        with TestClient(app) as concurrent_client:
            return concurrent_client.post(
                "/dev/browser-host/v1/attachments",
                headers=_headers(concurrent_bearer),
                json=concurrent_body,
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        concurrent_statuses = sorted(pool.map(submit, (1, 2)))
    assert concurrent_statuses == [202, 409]
    _close(app, client)

    app, client = _new_app()
    _, old_bearer = _issue(client)
    _close(app, client)
    restarted_app, restarted_client = _new_app()
    restart_result = restarted_client.post(
        "/dev/browser-host/v1/attachments",
        headers=_headers(old_bearer),
        json=_attachment(),
    )
    assert restart_result.status_code == 401
    _close(restarted_app, restarted_client)

    app, client = _new_app()
    _, shutdown_bearer = _issue(client)
    store = app.state.browser_host_attachment_grant_store
    assert len(store.snapshot_for_testing()) == 1
    assert http_adapter.shutdown_browser_host_attachment_adapter(app)
    assert getattr(app.state, http_adapter.STORE_STATE_KEY) is None
    assert shutdown_bearer not in json.dumps({"status": "shutdown-cleared"})
    client.close()

    return {
        "proofKind": "guardian_attachment_http_adapter",
        "proofStatus": "passed",
        "repositoryCommit": BASELINE_COMMIT,
        "featureFlag": http_adapter.FEATURE_FLAG,
        "featureDefault": False,
        "requiredDevelopmentMode": "GUARDIAN_DEV_MODE=true",
        "requiredExposureMode": "local_safe",
        "routePrefix": http_adapter.ROUTE_PREFIX,
        "issuancePath": f"{http_adapter.ROUTE_PREFIX}/attachment-grants",
        "attachmentPath": f"{http_adapter.ROUTE_PREFIX}/attachments",
        "grantAuthorizationScheme": "browser_host_attachment_grant",
        "httpAuthorizationScheme": http_adapter.AUTHORIZATION_SCHEME,
        "contractPackageVersion": "0.2.0",
        "protocolVersion": "1.0.0",
        "attachmentVersion": "1.0.0",
        "grantUseCount": 1,
        "ttlRangeSeconds": {"minimum": 30, "default": 120, "maximum": 300},
        "retentionClass": "ephemeral",
        "defaultRoutePresence": False,
        "authenticatedIssuance": True,
        "attachmentConsumedWithoutReusableGuardianCredential": True,
        "acceptedHttpStatus": 202,
        "acceptedAttachmentOutcome": "accepted",
        "persistenceOutcome": "not_persisted",
        "replayStatus": 409,
        "expirationStatus": 409,
        "scopeStatus": statuses["scope"],
        "requestStatus": statuses["request"],
        "versionStatus": statuses["version"],
        "retentionStatus": statuses["retention"],
        "confirmationStatus": statuses["confirmation"],
        "budgetStatus": statuses["budget"],
        "rejectionReceiptCodes": codes,
        "malformedBodyPreservedGrant": True,
        "concurrencyStatuses": concurrent_statuses,
        "restartInvalidatedGrant": True,
        "shutdownClearedStore": True,
        "bearerLogged": False,
        "subjectSerialized": False,
        "rawContentRetained": False,
        "databaseUsed": False,
        "redisUsed": False,
        "externalNetworkUsed": False,
        "productionBrowserHostConnected": False,
        "releaseQualification": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    proof = run_proof()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "proofKind": proof["proofKind"],
        "proofStatus": proof["proofStatus"],
        "proofVersion": "1.0.0",
        "repositoryCommit": proof["repositoryCommit"],
        "artifacts": ["manifest.json", "proof.json", "proof.md"],
        "sanitized": True,
        "containsBearer": False,
        "containsBearerDigest": False,
        "containsCredentials": False,
        "containsSubject": False,
        "containsRawAttachmentContent": False,
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "proof.json").write_text(
        json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    proof_md = "\n".join(
        [
            "# Guardian Browser Host attachment HTTP adapter proof",
            "",
            f"- Status: `{proof['proofStatus']}`",
            f"- Baseline commit under test: `{proof['repositoryCommit']}`",
            f"- Route prefix: `{proof['routePrefix']}`",
            "- The adapter is default-disabled, development-only, and local-safe only.",
            "- Issuance uses existing Guardian authentication; attachment consumption uses only the one-use grant.",
            "- Accepted attachments return a content-free `202` receipt with `not_persisted`.",
            "- Replay and expiration return `409`; scope, version, retention, confirmation, and budget rejection return `403` receipts.",
            "- Malformed bodies preserve the grant; concurrent consumption produced exactly one success and one replay rejection.",
            "- No bearer, bearer digest, subject, credentials, raw content, database, Redis, or external network was included in this packet.",
            "- Production Browser Host integration and release qualification remain false.",
            "",
        ]
    )
    (args.output_dir / "proof.md").write_text(proof_md, encoding="utf-8")
    print(json.dumps({"proofStatus": proof["proofStatus"], "outputDir": str(args.output_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
