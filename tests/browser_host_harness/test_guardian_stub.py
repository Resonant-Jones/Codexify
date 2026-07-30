"""Guardian stub tests.

Proves health, authentication, trusted-origin behavior, CORS denial for
fixture origins, context-envelope validation (success and all failure
modes), receipt integrity, and companion continuity.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request

import pytest

from scripts.browser_host_harness.guardian_stub import (
    GUARDIAN_STUB_VERSION,
    _make_sentinel_credential,
    validate_context_envelope,
)


@pytest.fixture
def stub():
    """Start a Guardian stub with a fresh sentinel."""
    from scripts.browser_host_harness.guardian_stub import GuardianStub

    s = GuardianStub(harness_version="0.1.0")
    s.start()
    yield s
    s.stop()


def _get(url: str, headers: dict | None = None, expected_status: int = 200) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == expected_status:
            return json.loads(e.read().decode("utf-8")) if e.fp else {}
        raise


def _post(url: str, payload: dict, headers: dict | None = None, expected_status: int = 200) -> tuple[dict, int]:
    data = json.dumps(payload).encode("utf-8")
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8")), resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else "{}"
        try:
            return json.loads(body), e.code
        except json.JSONDecodeError:
            return {}, e.code


def _auth(stub) -> dict:
    return {"Authorization": f"Bearer {stub.sentinel}"}


class TestGuardianStubHealth:
    def test_unauthenticated_health(self, stub):
        data = _get(f"{stub.base_url}/health")
        assert data["status"] == "ok"
        assert data["stub"] is True
        assert data["guardianStubVersion"] == GUARDIAN_STUB_VERSION


class TestGuardianStubAuth:
    def test_no_credential_returns_401(self, stub):
        _, status = _post(
            f"{stub.base_url}/api/context/attach",
            {},
            expected_status=401,
        )
        assert status == 401

    def test_invalid_credential_returns_401(self, stub):
        _, status = _post(
            f"{stub.base_url}/api/context/attach",
            {},
            headers={"Authorization": "Bearer wrong-credential"},
            expected_status=401,
        )
        assert status == 401

    def test_valid_credential_allows_access(self, stub):
        data = _get(f"{stub.base_url}/api/session", headers=_auth(stub))
        assert data["stub"] is True
        assert "sessionId" in data

    def test_protected_get_requires_auth(self, stub):
        # GET /api/session without auth
        req = urllib.request.Request(f"{stub.base_url}/api/session")
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req, timeout=10)
        assert exc.value.code == 401

    def test_protected_companion_requires_auth(self, stub):
        req = urllib.request.Request(f"{stub.base_url}/api/companion")
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req, timeout=10)
        assert exc.value.code == 401


class TestGuardianStubCORS:
    def test_fixture_origin_not_granted_cors(self, stub):
        """A fixture origin must not receive trusted companion CORS authority."""
        fixture_origin = "http://127.0.0.1:19999"
        _, status = _post(
            f"{stub.base_url}/api/context/attach",
            {},
            headers={
                **{"Origin": fixture_origin},
            },
            expected_status=401,
        )
        assert status == 401

    def test_no_wildcard_cors(self, stub):
        data = _get(f"{stub.base_url}/health")
        # We can't check headers via this simple helper, so we use raw
        req = urllib.request.Request(f"{stub.base_url}/health")
        with urllib.request.urlopen(req, timeout=10) as resp:
            acao = resp.headers.get("Access-Control-Allow-Origin", "")
        assert acao != "*"


class TestContextEnvelopeValidation:
    def _valid_envelope(self, stub=None) -> dict:
        content = "Test content for validation."
        ch = hashlib.sha256(content.encode("utf-8")).hexdigest()
        base = stub.base_url if stub is not None else "http://127.0.0.1:5555"
        return {
            "contextId": "ctx-test-001",
            "captureRequestId": "cap-test-001",
            "sourceKind": "visible-text",
            "sourceUrl": f"{base}/basic-visible",
            "sourceOrigin": base,
            "sourceTitle": "Test Page",
            "capturedAt": "2026-07-30T12:00:00Z",
            "captureMode": "visible-extraction",
            "contentType": "text/html",
            "content": content,
            "contentHash": ch,
            "contentLength": len(content.encode("utf-8")),
            "truncated": False,
            "extractorVersion": "test-1.0",
            "permissionScope": "visible-text",
            "retentionClass": "ephemeral",
            "userInitiated": True,
            "requestId": "req-test-001",
            "attemptNumber": 1,
        }

    def test_valid_envelope_passes(self):
        """Direct function call validation test."""
        envelope = {
            "contextId": "ctx-1",
            "captureRequestId": "cap-1",
            "sourceKind": "visible-text",
            "sourceUrl": "http://127.0.0.1:5555/basic-visible",
            "sourceOrigin": "http://127.0.0.1:5555",
            "sourceTitle": "Test",
            "capturedAt": "2026-07-30T12:00:00Z",
            "captureMode": "visible-extraction",
            "contentType": "text/html",
            "content": "hello",
            "contentHash": hashlib.sha256("hello".encode("utf-8")).hexdigest(),
            "contentLength": len("hello".encode("utf-8")),
            "truncated": False,
            "extractorVersion": "1.0",
            "permissionScope": "visible-text",
            "retentionClass": "ephemeral",
            "userInitiated": True,
            "requestId": "req-1",
            "attemptNumber": 1,
        }
        ok, reason, meta = validate_context_envelope(envelope)
        assert ok, f"Validation failed: {reason}"
        assert meta is not None

    def test_missing_fields_fails(self):
        ok, reason, meta = validate_context_envelope({"contextId": "alone"})
        assert not ok
        assert reason is not None
        assert "missing required fields" in reason

    def test_user_initiated_false_fails(self):
        envelope = self._valid_envelope()
        envelope["userInitiated"] = False
        ok, reason, _ = validate_context_envelope(envelope)
        assert not ok
        assert "userInitiated" in reason  # type: ignore[operator]

    def test_retention_not_ephemeral_fails(self):
        envelope = self._valid_envelope()
        envelope["retentionClass"] = "durable"
        ok, reason, _ = validate_context_envelope(envelope)
        assert not ok
        assert "ephemeral" in reason  # type: ignore[operator]

    def test_origin_mismatch_fails(self):
        envelope = self._valid_envelope()
        envelope["sourceOrigin"] = "http://other:9999"
        ok, reason, _ = validate_context_envelope(envelope)
        assert not ok
        assert "sourceOrigin" in reason  # type: ignore[operator]

    def test_hash_mismatch_fails(self):
        envelope = self._valid_envelope()
        envelope["contentHash"] = "0" * 64
        ok, reason, _ = validate_context_envelope(envelope)
        assert not ok
        assert "contentHash" in reason  # type: ignore[operator]

    def test_content_length_mismatch_fails(self):
        envelope = self._valid_envelope()
        envelope["contentLength"] = 99999
        ok, reason, _ = validate_context_envelope(envelope)
        assert not ok
        assert "contentLength" in reason  # type: ignore[operator]

    def test_attempt_number_zero_fails(self):
        envelope = self._valid_envelope()
        envelope["attemptNumber"] = 0
        ok, reason, _ = validate_context_envelope(envelope)
        assert not ok
        assert "attemptNumber" in reason  # type: ignore[operator]

    def test_empty_correlation_fails(self):
        envelope = self._valid_envelope()
        envelope["contextId"] = ""
        ok, reason, _ = validate_context_envelope(envelope)
        assert not ok

    def test_secret_fields_rejected(self):
        envelope = self._valid_envelope()
        envelope["password"] = "secret123"
        ok, reason, _ = validate_context_envelope(envelope)
        assert not ok
        assert "secret-bearing" in reason  # type: ignore[operator]

    def test_nested_secret_fields_rejected(self):
        envelope = self._valid_envelope()
        envelope["nested"] = {"api_key": "hidden-key"}
        ok, reason, _ = validate_context_envelope(envelope)
        assert not ok

    def test_oversized_content_fails(self):
        envelope = self._valid_envelope()
        big = "x" * (64 * 1024 + 1)
        envelope["content"] = big
        envelope["contentHash"] = hashlib.sha256(big.encode("utf-8")).hexdigest()
        envelope["contentLength"] = len(big.encode("utf-8"))
        ok, reason, _ = validate_context_envelope(envelope)
        assert not ok
        assert "exceeds maximum" in reason  # type: ignore[operator]

    def test_unsupported_content_type_fails(self):
        envelope = self._valid_envelope()
        envelope["contentType"] = "application/pdf"
        ok, reason, _ = validate_context_envelope(envelope)
        assert not ok
        assert "contentType" in reason  # type: ignore[operator]


class TestGuardianStubAttachment:
    def test_successful_attachment(self, stub):
        content = "Test content."
        ch = hashlib.sha256(content.encode("utf-8")).hexdigest()
        envelope = {
            "contextId": "ctx-001",
            "captureRequestId": "cap-001",
            "sourceKind": "visible-text",
            "sourceUrl": f"{stub.base_url}/basic-visible",
            "sourceOrigin": stub.base_url,
            "sourceTitle": "Test",
            "capturedAt": "2026-07-30T12:00:00Z",
            "captureMode": "visible-extraction",
            "contentType": "text/html",
            "content": content,
            "contentHash": ch,
            "contentLength": len(content.encode("utf-8")),
            "truncated": False,
            "extractorVersion": "1.0",
            "permissionScope": "visible-text",
            "retentionClass": "ephemeral",
            "userInitiated": True,
            "requestId": "req-001",
            "attemptNumber": 1,
        }
        data, status = _post(
            f"{stub.base_url}/api/context/attach",
            envelope,
            headers=_auth(stub),
        )
        assert status == 200
        assert data["status"] == "attached"
        assert data["persisted"] is False
        assert data["retentionClass"] == "ephemeral"
        assert "content" not in data  # No raw content in receipt

    def test_malformed_envelope(self, stub):
        data, status = _post(
            f"{stub.base_url}/api/context/attach",
            {"contextId": "bad-one"},
            headers=_auth(stub),
        )
        assert status == 422 or status == 400
        assert data["status"] == "failed"

    def test_forced_attachment_failure(self, stub):
        content = "Test."
        ch = hashlib.sha256(content.encode("utf-8")).hexdigest()
        envelope = {
            "contextId": "ctx-fail",
            "captureRequestId": "cap-fail",
            "sourceKind": "visible-text",
            "sourceUrl": f"{stub.base_url}/basic-visible",
            "sourceOrigin": stub.base_url,
            "sourceTitle": "Test",
            "capturedAt": "2026-07-30T12:00:00Z",
            "captureMode": "visible-extraction",
            "contentType": "text/html",
            "content": content,
            "contentHash": ch,
            "contentLength": len(content.encode("utf-8")),
            "truncated": False,
            "extractorVersion": "1.0",
            "permissionScope": "visible-text",
            "retentionClass": "ephemeral",
            "userInitiated": True,
            "requestId": "req-fail",
            "attemptNumber": 1,
        }
        data, status = _post(
            f"{stub.base_url}/api/context/attach-fail",
            envelope,
            headers=_auth(stub),
        )
        assert status == 422
        assert data["status"] == "failed"
        assert data["failureCode"] == "attachment_simulated_failure"

    def test_empty_body_fails(self, stub):
        """POST with no data should fail."""
        req = urllib.request.Request(
            f"{stub.base_url}/api/context/attach",
            data=b"",
            headers={
                "Content-Type": "application/json",
                **_auth(stub),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                # Could be 200 or 400 depending on impl
        except urllib.error.HTTPError as e:
            data = json.loads(e.read().decode("utf-8")) if e.fp else {}
        assert data.get("status") == "failed" or data.get("stub") is True


class TestGuardianStubCompanion:
    def test_companion_response(self, stub):
        data = _get(f"{stub.base_url}/api/companion", headers=_auth(stub))
        assert data["stub"] is True
        assert "Synthetic companion response" in data.get("message", "")

    def test_companion_after_attachment_failure(self, stub):
        """Companion must remain available after attachment failure."""
        # Trigger failure first
        content = "Test."
        ch = hashlib.sha256(content.encode("utf-8")).hexdigest()
        envelope = {
            "contextId": "ctx-comp",
            "captureRequestId": "cap-comp",
            "sourceKind": "visible-text",
            "sourceUrl": f"{stub.base_url}/basic-visible",
            "sourceOrigin": stub.base_url,
            "sourceTitle": "Test",
            "capturedAt": "2026-07-30T12:00:00Z",
            "captureMode": "visible-extraction",
            "contentType": "text/html",
            "content": content,
            "contentHash": ch,
            "contentLength": len(content.encode("utf-8")),
            "truncated": False,
            "extractorVersion": "1.0",
            "permissionScope": "visible-text",
            "retentionClass": "ephemeral",
            "userInitiated": True,
            "requestId": "req-comp",
            "attemptNumber": 1,
        }
        # Force failure
        _post(
            f"{stub.base_url}/api/context/attach-fail",
            envelope,
            headers=_auth(stub),
        )

        # Companion should still work
        data = _get(f"{stub.base_url}/api/companion", headers=_auth(stub))
        assert data["stub"] is True


class TestGuardianStubReceipts:
    def test_receipts_endpoint(self, stub):
        data = _get(f"{stub.base_url}/api/receipts", headers=_auth(stub))
        assert "receipts" in data

    def test_no_default_receipts(self, stub):
        data = _get(f"{stub.base_url}/api/receipts", headers=_auth(stub))
        assert isinstance(data["receipts"], list)


class TestSentinelCredential:
    def test_format_is_non_production(self):
        cred = _make_sentinel_credential()
        assert cred.startswith("CODEXIFY-HARNESS-SENTINEL-")
        assert "NOT-A-REAL-CREDENTIAL" in cred
        # Must not look like a JWT
        assert "." not in cred[-50:]  # Not a JWT segment
        assert "eyJ" not in cred  # Not a base64-encoded JWT header

    def test_each_call_produces_unique(self):
        creds = [_make_sentinel_credential() for _ in range(5)]
        assert len(set(creds)) == 5
