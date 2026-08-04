"""Deterministic synthetic Guardian contract stub.

Implements only the minimum synthetic contract required by the comparative
proof specification:

- Unauthenticated health / reachability
- Authenticated synthetic session inspection
- Authenticated context-attachment receiver (validates Tier 1 Browser Context Envelopes)
- Authenticated synthetic companion completion response
- Authenticated receipt inspection
- Bounded deterministic attachment-failure scenario

Uses a run-scoped synthetic sentinel credential that is unmistakably
non-production.  The stub never imports or starts the production Guardian,
accesses Postgres/Redis, invokes providers, or mutates identity/memory.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Callable

GUARDIAN_STUB_VERSION = "0.1.0"

# Maximum inline text context size (Tier 1 budget)
MAX_CONTENT_LENGTH = 64 * 1024  # 64 KB


class GuardianStubError(Exception):
    """Raised when Guardian stub operations fail."""


def _make_sentinel_credential() -> str:
    """Generate a run-scoped synthetic sentinel credential.

    The format is deliberately unlike a real Guardian API key or JWT so it can
    never be accepted by the production Guardian.
    """
    return f"CODEXIFY-HARNESS-SENTINEL-{uuid.uuid4().hex}-NOT-A-REAL-CREDENTIAL"


def _build_synthetic_account_id() -> str:
    return f"harness-account-{uuid.uuid4().hex[:12]}"


def _build_synthetic_session_id() -> str:
    return f"harness-session-{uuid.uuid4().hex[:12]}"


def _build_synthetic_thread_id() -> str:
    return f"harness-thread-{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Context envelope validation
# ---------------------------------------------------------------------------

_REQUIRED_ENVELOPE_FIELDS = frozenset(
    {
        "contextId",
        "captureRequestId",
        "sourceKind",
        "sourceUrl",
        "sourceOrigin",
        "sourceTitle",
        "capturedAt",
        "captureMode",
        "contentType",
        "content",
        "contentHash",
        "contentLength",
        "truncated",
        "extractorVersion",
        "permissionScope",
        "retentionClass",
        "userInitiated",
        "requestId",
        "attemptNumber",
    }
)

_SECRET_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "credential",
        "credentials",
        "apiKey",
        "api_key",
        "token",
        "jwt",
        "cookie",
        "cookies",
        "localStorage",
        "local_storage",
        "sessionStorage",
        "session_storage",
        "password",
        "passwords",
        "hiddenValue",
        "hidden_value",
        "csrf",
        "commandGrant",
        "command_grants",
        "filesystemPath",
        "filesystem_path",
        "filePath",
        "identityMutation",
        "identity_mutation",
        "memoryMutation",
        "memory_mutation",
    }
)


def _parse_origin(url: str) -> str:
    """Extract origin from a URL string."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname}{port}"


def _validate_content_hash(content: str, expected_hash: str) -> bool:
    actual = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return actual == expected_hash


def _has_secret_fields(obj: Any, depth: int = 0) -> bool:
    """Recursively check for secret-bearing field names."""
    if depth > 10:
        return False
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = key.lower().replace("_", "").replace("-", "")
            for secret in _SECRET_FIELD_NAMES:
                secret_norm = secret.lower().replace("_", "").replace("-", "")
                if secret_norm in key_lower:
                    return True
            if _has_secret_fields(value, depth + 1):
                return True
    elif isinstance(obj, list):
        for item in obj:
            if _has_secret_fields(item, depth + 1):
                return True
    return False


def validate_context_envelope(envelope: dict) -> tuple[bool, str | None, dict | None]:
    """Validate a Tier 1 Browser Context Envelope.

    Returns (is_valid, failure_reason, sanitized_receipt_metadata).
    """
    failures: list[str] = []

    # --- Required fields ---
    missing = _REQUIRED_ENVELOPE_FIELDS - set(envelope.keys())
    if missing:
        return False, f"missing required fields: {sorted(missing)}", None

    context_id = envelope.get("contextId", "")
    capture_request_id = envelope.get("captureRequestId", "")
    source_url = envelope.get("sourceUrl", "")
    source_origin = envelope.get("sourceOrigin", "")
    content = envelope.get("content", "")
    content_hash = envelope.get("contentHash", "")
    content_length = envelope.get("contentLength", 0)
    user_initiated = envelope.get("userInitiated", False)
    retention_class = envelope.get("retentionClass", "")
    attempt_number = envelope.get("attemptNumber", 0)
    request_id = envelope.get("requestId", "")
    content_type = envelope.get("contentType", "")

    # --- userInitiated must be true ---
    if not user_initiated:
        failures.append("userInitiated must be true")

    # --- retentionClass must be ephemeral ---
    if retention_class != "ephemeral":
        failures.append("retentionClass must be 'ephemeral'")

    # --- sourceOrigin must match parsed origin of sourceUrl ---
    try:
        parsed_origin = _parse_origin(source_url)
        if parsed_origin != source_origin:
            failures.append(
                f"sourceOrigin '{source_origin}' does not match parsed origin '{parsed_origin}'"
            )
    except Exception:
        failures.append(f"cannot parse sourceUrl '{source_url}'")

    # --- contentHash must match actual content ---
    if isinstance(content, str):
        if not _validate_content_hash(content, content_hash):
            failures.append("contentHash does not match submitted content")
    else:
        failures.append("content must be a string")

    # --- contentLength must match ---
    if isinstance(content, str) and len(content.encode("utf-8")) != content_length:
        failures.append("contentLength does not match actual content length")

    # --- attemptNumber must be positive ---
    if not isinstance(attempt_number, int) or attempt_number < 1:
        failures.append("attemptNumber must be a positive integer")

    # --- Correlation identifiers non-empty ---
    if not context_id:
        failures.append("contextId must not be empty")
    if not capture_request_id:
        failures.append("captureRequestId must not be empty")
    if not request_id:
        failures.append("requestId must not be empty")

    # --- Content length budget ---
    if isinstance(content, str) and len(content.encode("utf-8")) > MAX_CONTENT_LENGTH:
        failures.append(
            f"content exceeds maximum length {MAX_CONTENT_LENGTH} bytes"
        )

    # --- Unsupported content types ---
    if content_type not in {"text/html", "text/plain"}:
        failures.append(f"unsupported contentType '{content_type}'")

    # --- Recursive secret-field check ---
    if _has_secret_fields(envelope):
        failures.append("envelope contains secret-bearing fields")

    if failures:
        return False, "; ".join(failures), None

    # Build sanitized receipt metadata
    receipt_meta = {
        "contextId": context_id,
        "captureRequestId": capture_request_id,
        "requestId": request_id,
        "attemptNumber": attempt_number,
        "sourceOrigin": source_origin,
        "sourceKind": envelope.get("sourceKind", ""),
        "contentHash": content_hash,
        "contentLength": content_length,
        "truncated": envelope.get("truncated", False),
        "contentType": content_type,
    }
    return True, None, receipt_meta


# ---------------------------------------------------------------------------
# Guardian Stub HTTP handler
# ---------------------------------------------------------------------------


class _GuardianStubHandler(BaseHTTPRequestHandler):
    """Loopback-only handler implementing the synthetic Guardian contract."""

    sentinel_credential: str = ""
    trusted_origin: str = ""
    stub_version: str = GUARDIAN_STUB_VERSION
    harness_version: str = ""
    _attachment_store: list[dict] = []
    _receipt_store: list[dict] = []
    _attachment_failure_count: int = 0
    _attachment_success_count: int = 0

    @staticmethod
    def _log_safe(component: str, **kwargs: object) -> None:
        """Bridge to the module-level safe logger. Overridden per-handler class."""
        return

    def log_message(self, fmt, *args):  # type: ignore[override]
        self._log_safe(
            "guardian_stub",
            route=args[0] if args else "-",
            status=self.command,
        )

    @property
    def request_id(self) -> str:
        return f"req-{uuid.uuid4().hex[:8]}"

    def _read_body(self) -> bytes:
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len > 0:
            return self.rfile.read(content_len)
        return b""

    def _require_auth(self) -> bool:
        """Return True if request is authenticated with the sentinel credential."""
        auth = self.headers.get("Authorization", "")
        expected = f"Bearer {self.sentinel_credential}"
        if auth != expected:
            self._send_json(
                {"error": "unauthorized", "stub": True},
                code=401,
            )
            return False
        return True

    def _set_cors(self, required_origin: bool = False) -> None:
        if required_origin and self.trusted_origin:
            self.send_header("Access-Control-Allow-Origin", self.trusted_origin)
        else:
            self.send_header("Access-Control-Allow-Origin", "null")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-store")

    def _send_json(self, payload: dict, code: int = 200) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._set_cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._set_cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ---- Unauthenticated routes ----

    def do_GET(self) -> None:
        path = self.path or "/"

        if path == "/" or path == "/health":
            self._send_json(
                {
                    "status": "ok",
                    "stub": True,
                    "guardianStubVersion": self.stub_version,
                    "harnessVersion": self.harness_version,
                }
            )
            return

        if path == "/api/session":
            if not self._require_auth():
                return
            self._send_json(
                {
                    "stub": True,
                    "sessionId": _build_synthetic_session_id(),
                    "accountId": _build_synthetic_account_id(),
                    "threadId": _build_synthetic_thread_id(),
                    "createdAt": _iso_now(),
                }
            )
            return

        if path == "/api/receipts":
            if not self._require_auth():
                return
            self._send_json({"receipts": self._receipt_store, "stub": True})
            return

        if path == "/api/companion":
            if not self._require_auth():
                return
            self._send_json(
                {
                    "stub": True,
                    "message": "Synthetic companion response",
                    "text": "This is a deterministic synthetic completion proving companion continuity.",
                    "correlationId": str(uuid.uuid4()),
                    "timestamp": _iso_now(),
                }
            )
            return

        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        path = self.path or "/"

        if path == "/api/context/attach":
            self._handle_attach()
            return

        if path == "/api/context/attach-fail":
            self._handle_attach(force_failure=True)
            return

        if path == "/api/companion":
            if not self._require_auth():
                return
            body_bytes = self._read_body()
            self._send_json(
                {
                    "stub": True,
                    "message": "Synthetic companion response",
                    "text": "This is a deterministic synthetic completion proving companion continuity.",
                    "correlationId": str(uuid.uuid4()),
                    "timestamp": _iso_now(),
                }
            )
            return

        self.send_error(404, "Not found")

    def _handle_attach(self, force_failure: bool = False) -> None:
        if not self._require_auth():
            return

        body_bytes = self._read_body()
        attempt_id = f"attempt-{uuid.uuid4().hex[:8]}"
        receipt_id = f"receipt-{uuid.uuid4().hex[:8]}"
        now = _iso_now()

        # Reject empty body
        if not body_bytes:
            self._send_json(
                {
                    "receiptId": receipt_id,
                    "status": "failed",
                    "failureCode": "empty_body",
                    "detail": "Request body is empty",
                    "persisted": False,
                    "timestamp": now,
                    "stub": True,
                },
                code=400,
            )
            self._receipt_store.append(
                {
                    "receiptId": receipt_id,
                    "status": "failed",
                    "failureCode": "empty_body",
                    "timestamp": now,
                }
            )
            return

        # Force-failure mode for deterministic testing
        if force_failure:
            fail_receipt = {
                "receiptId": receipt_id,
                "status": "failed",
                "failureCode": "attachment_simulated_failure",
                "detail": "Deterministic attachment failure triggered for proof testing",
                "persisted": False,
                "timestamp": now,
                "stub": True,
            }
            self._send_json(fail_receipt, code=422)
            self._receipt_store.append(fail_receipt)
            self._attachment_failure_count += 1
            return

        # Parse envelope
        try:
            envelope = json.loads(body_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            fail_receipt = {
                "receiptId": receipt_id,
                "status": "failed",
                "failureCode": "malformed_envelope",
                "detail": "Could not parse JSON body",
                "persisted": False,
                "timestamp": now,
                "stub": True,
            }
            self._send_json(fail_receipt, code=400)
            self._receipt_store.append(fail_receipt)
            return

        # Validate
        is_valid, failure_reason, receipt_meta = validate_context_envelope(envelope)

        if not is_valid:
            fail_receipt = {
                "receiptId": receipt_id,
                "status": "failed",
                "failureCode": "context_rejected",
                "detail": failure_reason or "Validation failed",
                "persisted": False,
                "timestamp": now,
                "stub": True,
            }
            # Include safe correlation fields
            for safe_field in ("contextId", "captureRequestId", "requestId", "attemptNumber"):
                if safe_field in envelope:
                    fail_receipt[safe_field] = envelope[safe_field]
            self._send_json(fail_receipt, code=422)
            self._receipt_store.append(fail_receipt)
            return

        # Success
        assert receipt_meta is not None
        success_receipt = {
            "receiptId": receipt_id,
            "runId": envelope.get("runId", ""),
            "requestId": receipt_meta["requestId"],
            "attemptNumber": receipt_meta["attemptNumber"],
            "captureRequestId": receipt_meta["captureRequestId"],
            "contextId": receipt_meta["contextId"],
            "sourceOrigin": receipt_meta["sourceOrigin"],
            "sourceKind": receipt_meta["sourceKind"],
            "contentHash": receipt_meta["contentHash"],
            "contentLength": receipt_meta["contentLength"],
            "truncated": receipt_meta["truncated"],
            "status": "attached",
            "persisted": False,
            "retentionClass": "ephemeral",
            "timestamp": now,
            "stub": True,
        }
        self._send_json(success_receipt, code=200)
        self._receipt_store.append(success_receipt)
        self._attachment_success_count += 1


def _iso_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


class GuardianStub:
    """Synthetic Guardian contract stub for comparative proof isolation."""

    def __init__(
        self,
        harness_version: str = "0.1.0",
        trusted_origin: str = "",
        safe_logger: Callable[..., None] | None = None,
    ):
        self._harness_version = harness_version
        self._trusted_origin = trusted_origin
        self._safe_logger = safe_logger
        self._sentinel: str = _make_sentinel_credential()
        self._httpd: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._port: int = 0

    @property
    def sentinel(self) -> str:
        return self._sentinel

    @property
    def port(self) -> int:
        return self._port

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._port}"

    def start(self) -> None:
        handler = _make_guardian_handler(
            self._sentinel,
            self._trusted_origin,
            self._harness_version,
            self._safe_logger,
        )
        self._httpd = HTTPServer(("127.0.0.1", 0), handler)
        self._port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        self._port = 0

    def is_running(self) -> bool:
        return self._httpd is not None and self._port > 0


def _make_guardian_handler(
    sentinel: str,
    trusted_origin: str,
    harness_version: str,
    safe_logger_fn: Callable[..., None] | None,
) -> type[_GuardianStubHandler]:

    if safe_logger_fn is not None:

        def _log_bridge(component: str, **kwargs: object) -> None:
            safe_logger_fn(component=component, **kwargs)

    else:

        def _log_bridge(component: str, **kwargs: object) -> None:
            return

    _log_safe_sm = staticmethod(_log_bridge)

    class ConfiguredHandler(_GuardianStubHandler):
        _log_safe = _log_safe_sm

    ConfiguredHandler.sentinel_credential = sentinel  # type: ignore[attr-defined]
    ConfiguredHandler.trusted_origin = trusted_origin  # type: ignore[attr-defined]
    ConfiguredHandler.stub_version = GUARDIAN_STUB_VERSION  # type: ignore[attr-defined]
    ConfiguredHandler.harness_version = harness_version  # type: ignore[attr-defined]
    ConfiguredHandler._attachment_store = []  # type: ignore[attr-defined]
    ConfiguredHandler._receipt_store = []  # type: ignore[attr-defined]
    ConfiguredHandler._attachment_failure_count = 0  # type: ignore[attr-defined]
    ConfiguredHandler._attachment_success_count = 0  # type: ignore[attr-defined]
    return ConfiguredHandler
