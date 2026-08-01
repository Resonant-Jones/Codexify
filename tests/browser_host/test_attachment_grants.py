"""Pure, process-local qualification of the Guardian attachment-grant seam."""

from __future__ import annotations

import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from guardian.browser_host.attachment_grants import (
    AttachmentGrantAuthorizationContext,
    AttachmentGrantStore,
)
from guardian.browser_host.contract_loader import load_contract_metadata


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = ROOT / "browser_host" / "contracts"


def _load(relative_path: str) -> dict:
    return json.loads((CONTRACT_ROOT / relative_path).read_text(encoding="utf-8"))


def _request() -> dict:
    request = _load("fixtures/valid/attachment-grant-request-ephemeral.json")
    request["requestId"] = "request-selected-1"
    return request


def _attachment() -> dict:
    return _load("fixtures/valid/attachment-attempt-ephemeral.json")


def _store(now: datetime | None = None) -> tuple[AttachmentGrantStore, list[datetime]]:
    clock = [now or datetime(2026, 8, 1, 14, 0, tzinfo=timezone.utc)]
    return AttachmentGrantStore(clock=lambda: clock[0]), clock


def _issue(store: AttachmentGrantStore):
    return store.issue(_request(), AttachmentGrantAuthorizationContext.explicitly_authorized("guardian-subject-internal"))


def test_loader_uses_immutable_canonical_contract_metadata() -> None:
    metadata = load_contract_metadata()
    assert metadata.package_version == "0.2.0"
    assert metadata.protocol_version == "1.0.0"
    assert metadata.attachment_version == "1.0.0"
    assert metadata.max_capture_bytes == 65536
    assert metadata.authorization_schemes == ("browser_host_attachment_grant",)
    assert metadata.grant_lifecycle == ("grant_issued", "grant_consumed", "grant_rejected", "grant_expired", "grant_replayed")
    assert metadata.authorization_material is True
    assert metadata.reusable_guardian_credential is False
    assert isinstance(metadata.tokens["errorCodes"], tuple)


def test_authorized_issuance_is_one_use_and_digest_only() -> None:
    store, _ = _store()
    result = _issue(store)
    assert result.accepted is True
    assert result.raw_bearer is not None
    response = dict(result.grant_response or {})
    assert response["authorizationScheme"] == "browser_host_attachment_grant"
    assert response["remainingUses"] == 1
    assert response["retentionClass"] == "ephemeral"
    assert "subjectId" not in response
    assert "apiKey" not in response
    snapshot = store.snapshot_for_testing()
    assert len(snapshot) == 1
    assert snapshot[0]["bearerDigest"] == hashlib.sha256(result.raw_bearer.encode()).hexdigest()
    assert result.raw_bearer not in repr(snapshot)
    assert snapshot[0]["subjectId"] == "guardian-subject-internal"
    assert result.raw_bearer not in repr(result)
    assert len(set(result.raw_bearer)) > 10


def test_unauthorized_context_is_rejected_without_a_bearer() -> None:
    store, _ = _store()
    result = store.issue(_request(), AttachmentGrantAuthorizationContext(subject_id="subject", authorized=True))
    assert result.accepted is False
    assert result.error_code == "attachment_grant_required"
    assert result.raw_bearer is None
    assert store.snapshot_for_testing() == ()


def test_valid_v1_attachment_is_consumed_once_without_mutating_body() -> None:
    store, _ = _store()
    result = _issue(store)
    attachment = _attachment()
    before = copy.deepcopy(attachment)
    accepted = store.consume(result.raw_bearer or "", attachment, browser_host_instance_id=_request()["browserHostInstanceId"])
    replay = store.consume(result.raw_bearer or "", attachment, browser_host_instance_id=_request()["browserHostInstanceId"])
    assert accepted.authorized is True
    assert accepted.lifecycle == "grant_consumed"
    assert replay.authorized is False
    assert replay.lifecycle == "grant_replayed"
    assert replay.error_code == "attachment_grant_consumed"
    assert attachment == before
    assert "content" not in accepted.safe_dict()
    assert result.raw_bearer not in json.dumps(accepted.safe_dict())


def test_scope_version_retention_confirmation_and_budget_fail_closed() -> None:
    cases = [
        ("scope", {"browser_host_instance_id": "other-host"}, "attachment_grant_scope_mismatch"),
        ("request", {"requestId": "other-request"}, "attachment_grant_scope_mismatch"),
        ("version", {"protocolVersion": "9.0.0"}, "attachment_grant_version_mismatch"),
        ("retention", {"requestedRetention": "durable"}, "attachment_grant_retention_denied"),
        ("confirmation", {"userConfirmation": {"confirmed": False, "confirmedAt": "2026-08-01T14:00:00.000Z", "method": "trusted_shell"}}, "attachment_grant_confirmation_required"),
        ("budget", {"envelope": {"content": "x", "contentLength": 65537}}, "attachment_grant_budget_exceeded"),
    ]
    for name, changes, expected in cases:
        store, _ = _store()
        result = _issue(store)
        attachment = _attachment()
        host = _request()["browserHostInstanceId"]
        for key, value in changes.items():
            if key == "browser_host_instance_id":
                host = value
            elif key == "envelope":
                attachment["envelope"].update(value)
            else:
                attachment[key] = value
        decision = store.consume(result.raw_bearer or "", attachment, browser_host_instance_id=host)
        assert decision.authorized is False, name
        assert decision.error_code == expected, name


def test_expiry_cleanup_and_decisions_are_redacted() -> None:
    store, clock = _store()
    result = _issue(store)
    clock[0] += timedelta(seconds=121)
    expired = store.consume(result.raw_bearer or "", _attachment(), browser_host_instance_id=_request()["browserHostInstanceId"])
    assert expired.lifecycle == "grant_expired"
    assert expired.error_code == "attachment_grant_expired"
    assert result.raw_bearer not in json.dumps(expired.safe_dict())
    cleanup = store.cleanup_expired()
    assert dict(cleanup) == {"expiredRemoved": 1, "remainingRecords": 0}
    assert set(cleanup) == {"expiredRemoved", "remainingRecords"}


def test_concurrent_consumers_yield_exactly_one_success() -> None:
    store, _ = _store()
    result = _issue(store)
    attachment = _attachment()
    host = _request()["browserHostInstanceId"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        decisions = list(pool.map(
            lambda _: store.consume(result.raw_bearer or "", attachment, browser_host_instance_id=host),
            (1, 2),
        ))
    assert sum(decision.authorized for decision in decisions) == 1
    assert sum(decision.lifecycle == "grant_replayed" for decision in decisions) == 1


def test_invalid_bearer_and_decisions_never_echo_sensitive_material() -> None:
    store, _ = _store()
    attachment = _attachment()
    fake_bearer = "SYNTHETIC_NON_SECRET_TEST_BEARER_000000000000000000000000"
    decision = store.consume(fake_bearer, attachment, browser_host_instance_id="browser-host-instance-1")
    serialized = json.dumps(decision.safe_dict())
    assert fake_bearer not in serialized
    assert "Selected evidence" not in serialized
    assert decision.error_code in load_contract_metadata().grant_error_codes
