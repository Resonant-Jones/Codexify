"""Security and idempotency tests for GitHub Watchdog webhook intake."""

from __future__ import annotations

import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import GitHubWatchdogDeliveryReceipt
from guardian.routes import github_watchdog
from guardian.watchdog.store import GitHubWatchdogDeliveryReceiptStore


WEBHOOK_PATH = "/api/watchdog/github/webhook"
WEBHOOK_SECRET = "watchdog-test-secret"


class IntakeHarness:
    """Small app and isolated receipt table for ingress behavior tests."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        GitHubWatchdogDeliveryReceipt.__table__.create(engine)
        self.Session = sessionmaker(
            bind=engine, autoflush=False, autocommit=False, future=True
        )
        self.settings = SimpleNamespace(
            CODEXIFY_GITHUB_WATCHDOG_WEBHOOK_SECRET=WEBHOOK_SECRET
        )
        app = FastAPI()
        app.state.github_watchdog_receipt_store = GitHubWatchdogDeliveryReceiptStore(
            session_factory=self.Session
        )
        app.include_router(github_watchdog.router)
        monkeypatch.setattr(github_watchdog, "get_settings", lambda: self.settings)
        self.client = TestClient(app)

    def receipt_rows(self) -> list[GitHubWatchdogDeliveryReceipt]:
        with self.Session() as session:
            return list(session.scalars(select(GitHubWatchdogDeliveryReceipt)))


@pytest.fixture()
def intake(monkeypatch: pytest.MonkeyPatch) -> IntakeHarness:
    return IntakeHarness(monkeypatch)


def _payload() -> dict:
    return {
        "action": "opened",
        "installation": {"id": 42},
        "repository": {"id": 99, "full_name": "octo/example"},
        "sender": {"id": 7, "login": "octocat"},
        "number": 12,
        "pull_request": {"head": {"sha": "a" * 40}},
    }


def _body(payload: object) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _signature(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return (
        "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    )


def _headers(
    body: bytes,
    *,
    delivery_id: str | None = "delivery-1",
    event_name: str | None = "pull_request",
    signature: str | None = None,
) -> dict[str, str]:
    headers = {"X-Hub-Signature-256": signature or _signature(body)}
    if delivery_id is not None:
        headers["X-GitHub-Delivery"] = delivery_id
    if event_name is not None:
        headers["X-GitHub-Event"] = event_name
    return headers


def test_secret_absent_fails_closed_before_any_write(intake: IntakeHarness) -> None:
    intake.settings.CODEXIFY_GITHUB_WATCHDOG_WEBHOOK_SECRET = None
    body = _body(_payload())

    response = intake.client.post(WEBHOOK_PATH, content=body, headers=_headers(body))

    assert response.status_code == 503
    assert response.json() == {"error": "secret_not_configured"}
    assert intake.receipt_rows() == []


@pytest.mark.parametrize(
    ("signature", "expected_error"),
    [
        (None, "missing_signature"),
        ("sha1=not-a-sha256-signature", "malformed_signature"),
        ("sha256=" + "0" * 64, "invalid_signature"),
    ],
)
def test_signature_rejections_never_write(
    intake: IntakeHarness,
    signature: str | None,
    expected_error: str,
) -> None:
    body = _body(_payload())
    headers = _headers(body)
    if signature is None:
        headers.pop("X-Hub-Signature-256")
    else:
        headers["X-Hub-Signature-256"] = signature

    response = intake.client.post(WEBHOOK_PATH, content=body, headers=headers)

    assert response.status_code == 401
    assert response.json() == {"error": expected_error}
    assert intake.receipt_rows() == []


@pytest.mark.parametrize(
    ("delivery_id", "event_name", "expected_error"),
    [
        (None, "pull_request", "missing_delivery_id"),
        ("delivery-1", None, "missing_event"),
    ],
)
def test_required_headers_reject_after_hmac_without_write(
    intake: IntakeHarness,
    delivery_id: str | None,
    event_name: str | None,
    expected_error: str,
) -> None:
    body = _body(_payload())

    response = intake.client.post(
        WEBHOOK_PATH,
        content=body,
        headers=_headers(body, delivery_id=delivery_id, event_name=event_name),
    )

    assert response.status_code == 400
    assert response.json() == {"error": expected_error}
    assert intake.receipt_rows() == []


def test_valid_hmac_with_malformed_json_never_writes(intake: IntakeHarness) -> None:
    body = b'{"action":'

    response = intake.client.post(WEBHOOK_PATH, content=body, headers=_headers(body))

    assert response.status_code == 400
    assert response.json() == {"error": "malformed_json"}
    assert intake.receipt_rows() == []


def test_valid_delivery_persists_only_normalized_metadata(
    intake: IntakeHarness,
) -> None:
    body = _body(_payload())

    response = intake.client.post(WEBHOOK_PATH, content=body, headers=_headers(body))

    assert response.status_code == 202
    assert response.json() == {
        "receiptId": response.json()["receiptId"],
        "deliveryId": "delivery-1",
        "event": "pull_request",
        "action": "opened",
        "duplicate": False,
        "disposition": "accepted",
    }
    rows = intake.receipt_rows()
    assert len(rows) == 1
    receipt = rows[0]
    assert receipt.receipt_id == response.json()["receiptId"]
    assert receipt.github_delivery_id == "delivery-1"
    assert receipt.installation_id == "42"
    assert receipt.repository_id == "99"
    assert receipt.repository_full_name == "octo/example"
    assert receipt.trigger_actor_id == "7"
    assert receipt.trigger_actor_login == "octocat"
    assert receipt.pull_request_number == 12
    assert receipt.head_sha == "a" * 40
    assert receipt.payload_sha256 == hashlib.sha256(body).hexdigest()
    assert receipt.redelivery_count == 0
    assert "payload" not in GitHubWatchdogDeliveryReceipt.__table__.columns


def test_valid_redelivery_reuses_receipt_and_records_evidence(
    intake: IntakeHarness,
) -> None:
    body = _body(_payload())
    headers = _headers(body)

    first = intake.client.post(WEBHOOK_PATH, content=body, headers=headers)
    second = intake.client.post(WEBHOOK_PATH, content=body, headers=headers)

    assert first.status_code == second.status_code == 202
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    assert second.json()["receiptId"] == first.json()["receiptId"]
    rows = intake.receipt_rows()
    assert len(rows) == 1
    assert rows[0].redelivery_count == 1
    assert rows[0].last_received_at >= rows[0].first_received_at


def test_conflicting_digest_does_not_overwrite_original_receipt(
    intake: IntakeHarness,
) -> None:
    first_body = _body(_payload())
    first_headers = _headers(first_body)
    first = intake.client.post(WEBHOOK_PATH, content=first_body, headers=first_headers)
    changed_payload = _payload()
    changed_payload["unpersisted_change"] = "different authenticated body"
    changed_body = _body(changed_payload)
    conflict = intake.client.post(
        WEBHOOK_PATH,
        content=changed_body,
        headers=_headers(changed_body),
    )

    assert first.status_code == 202
    assert conflict.status_code == 409
    assert conflict.json() == {"error": "conflicting_delivery"}
    rows = intake.receipt_rows()
    assert len(rows) == 1
    assert rows[0].receipt_id == first.json()["receiptId"]
    assert rows[0].payload_sha256 == hashlib.sha256(first_body).hexdigest()
    assert rows[0].redelivery_count == 0


def test_authenticated_unsupported_event_is_ignored_without_a_receipt(
    intake: IntakeHarness,
) -> None:
    payload = _payload()
    payload["action"] = "closed"
    body = _body(payload)

    response = intake.client.post(WEBHOOK_PATH, content=body, headers=_headers(body))

    assert response.status_code == 202
    assert response.json() == {
        "receiptId": None,
        "deliveryId": "delivery-1",
        "event": "pull_request",
        "action": "closed",
        "duplicate": False,
        "disposition": "ignored",
    }
    assert intake.receipt_rows() == []


def test_authenticated_issue_comment_not_on_a_pr_is_ignored(
    intake: IntakeHarness,
) -> None:
    payload = {
        "action": "created",
        "issue": {"number": 12},
        "repository": {"id": 99, "full_name": "octo/example"},
        "sender": {"id": 7, "login": "octocat"},
    }
    body = _body(payload)

    response = intake.client.post(
        WEBHOOK_PATH,
        content=body,
        headers=_headers(body, event_name="issue_comment"),
    )

    assert response.status_code == 202
    assert response.json()["disposition"] == "ignored"
    assert intake.receipt_rows() == []


def test_authenticated_issue_comment_on_a_pr_receipts_without_comment_parsing(
    intake: IntakeHarness,
) -> None:
    payload = {
        "action": "created",
        "installation": {"id": 42},
        "issue": {"number": 12, "pull_request": {}},
        "repository": {"id": 99, "full_name": "octo/example"},
        "sender": {"id": 7, "login": "octocat"},
    }
    body = _body(payload)

    response = intake.client.post(
        WEBHOOK_PATH,
        content=body,
        headers=_headers(body, event_name="issue_comment"),
    )

    assert response.status_code == 202
    assert response.json()["disposition"] == "accepted"
    rows = intake.receipt_rows()
    assert len(rows) == 1
    assert rows[0].event_name == "issue_comment"
    assert rows[0].pull_request_number == 12
    assert rows[0].head_sha is None
