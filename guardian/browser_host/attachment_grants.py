"""Process-local Guardian-owned one-use attachment grant issuer and consumer."""

from __future__ import annotations

import base64
import hashlib
import re
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from types import MappingProxyType
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from .contract_loader import BrowserHostContractMetadata, load_contract_metadata


_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")
_BEARER_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{43,128}$")
_GRANT_REQUEST_FIELDS = frozenset({
    "schemaVersion", "protocolVersion", "attachmentVersion", "requestId",
    "browserHostInstanceId", "requestedRetention", "requestedAttachmentCount",
    "requestedMaxContentBytes", "requestedTtlSeconds", "userConfirmationMode",
    "generatedAt",
})
_GRANT_RESPONSE_FIELDS = frozenset({
    "schemaVersion", "grantId", "authorizationScheme", "grantBearer",
    "protocolVersion", "attachmentVersion", "browserHostInstanceId", "requestId",
    "retentionClass", "maxContentBytes", "remainingUses", "issuedAt", "expiresAt",
})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _wire_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _bounded_id(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 256 and bool(_ID_PATTERN.fullmatch(value))


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _sha256_bearer(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AttachmentGrantPolicy:
    """Policy values sourced from the shared Browser Host manifest."""

    protocol_version: str
    attachment_version: str
    retention_class: str
    max_content_bytes: int
    default_ttl_seconds: int
    minimum_ttl_seconds: int
    maximum_ttl_seconds: int
    allowed_uses: int
    authorization_scheme: str
    confirmation_mode: str = "explicit_each_attachment"

    @classmethod
    def from_contract(cls, contract: BrowserHostContractMetadata | None = None) -> "AttachmentGrantPolicy":
        metadata = contract or load_contract_metadata()
        return cls(
            protocol_version=metadata.protocol_version,
            attachment_version=metadata.attachment_version,
            retention_class=metadata.retention_class,
            max_content_bytes=metadata.max_capture_bytes,
            default_ttl_seconds=metadata.default_ttl_seconds,
            minimum_ttl_seconds=metadata.minimum_ttl_seconds,
            maximum_ttl_seconds=metadata.maximum_ttl_seconds,
            allowed_uses=metadata.allowed_uses,
            authorization_scheme=metadata.authorization_scheme,
        )


@dataclass(frozen=True)
class AttachmentGrantAuthorizationContext:
    """Internal Guardian authorization context; subject never crosses the grant wire."""

    subject_id: str
    authorized: bool = False
    can_issue_attachment_grant: bool = False

    @classmethod
    def explicitly_authorized(cls, subject_id: str) -> "AttachmentGrantAuthorizationContext":
        return cls(subject_id=subject_id, authorized=True, can_issue_attachment_grant=True)


@dataclass(frozen=True, repr=False)
class AttachmentGrantIssueResult:
    accepted: bool
    grant_response: Mapping[str, Any] | None = field(default=None, repr=False, compare=False)
    error_code: str | None = None
    lifecycle: str = "grant_rejected"
    _raw_bearer: str | None = field(default=None, repr=False, compare=False)

    @property
    def grant(self) -> Mapping[str, Any] | None:
        return self.grant_response

    @property
    def raw_bearer(self) -> str | None:
        return self._raw_bearer

    def safe_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "errorCode": self.error_code,
            "lifecycle": self.lifecycle,
            "grantIssued": self.accepted,
        }

    def __repr__(self) -> str:
        return f"AttachmentGrantIssueResult(accepted={self.accepted!r}, error_code={self.error_code!r}, lifecycle={self.lifecycle!r})"


@dataclass(frozen=True, repr=False)
class AttachmentGrantDecision:
    authorized: bool
    lifecycle: str
    error_code: str | None = None
    grant_id: str | None = None
    remaining_uses: int = 0

    def safe_dict(self) -> dict[str, Any]:
        return {
            "authorized": self.authorized,
            "lifecycle": self.lifecycle,
            "errorCode": self.error_code,
            "grantId": self.grant_id,
            "remainingUses": self.remaining_uses,
        }

    def __repr__(self) -> str:
        return f"AttachmentGrantDecision(authorized={self.authorized!r}, lifecycle={self.lifecycle!r}, error_code={self.error_code!r}, grant_id={self.grant_id!r}, remaining_uses={self.remaining_uses!r})"


@dataclass
class _GrantRecord:
    grant_id: str
    bearer_digest: str
    subject_id: str
    browser_host_instance_id: str
    request_id: str
    protocol_version: str
    attachment_version: str
    retention_class: str
    max_content_bytes: int
    confirmation_mode: str
    issued_at: datetime
    expires_at: datetime
    remaining_uses: int
    consumed: bool = False


class AttachmentGrantStore:
    """Ephemeral in-memory issuer/consumer with atomic single-use consumption."""

    def __init__(
        self,
        policy: AttachmentGrantPolicy | None = None,
        *,
        contract: BrowserHostContractMetadata | None = None,
        clock: Callable[[], datetime] | None = None,
        random_bytes: Callable[[int], bytes] | None = None,
    ) -> None:
        self._contract = contract or load_contract_metadata()
        canonical_policy = AttachmentGrantPolicy.from_contract(self._contract)
        if policy is not None and policy != canonical_policy:
            raise ValueError("attachment_grant_policy_invalid")
        self.policy = policy or canonical_policy
        self._clock = clock or _utc_now
        self._random_bytes = random_bytes or secrets.token_bytes
        self._lock = threading.RLock()
        self._records: dict[str, _GrantRecord] = {}

    def _now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError("attachment_grant_clock_invalid")
        return value.astimezone(timezone.utc)

    def _decision(self, authorized: bool, lifecycle: str, error_code: str | None, record: _GrantRecord | None = None) -> AttachmentGrantDecision:
        if error_code is not None and error_code not in self._contract.grant_error_codes:
            error_code = "attachment_grant_invalid"
        if lifecycle not in self._contract.grant_lifecycle:
            lifecycle = "grant_rejected"
        return AttachmentGrantDecision(
            authorized=authorized,
            lifecycle=lifecycle,
            error_code=error_code,
            grant_id=record.grant_id if record else None,
            remaining_uses=record.remaining_uses if record else 0,
        )

    def _request_error(self, request: Mapping[str, Any]) -> str | None:
        if set(request) != _GRANT_REQUEST_FIELDS:
            return "attachment_grant_invalid"
        if request.get("schemaVersion") != "1.0.0":
            return "attachment_grant_invalid"
        if request.get("protocolVersion") != self.policy.protocol_version or request.get("attachmentVersion") != self.policy.attachment_version:
            return "attachment_grant_version_mismatch"
        if not _bounded_id(request.get("requestId")) or not _bounded_id(request.get("browserHostInstanceId")):
            return "attachment_grant_invalid"
        if request.get("requestedRetention") != self.policy.retention_class:
            return "attachment_grant_retention_denied"
        if not _integer(request.get("requestedAttachmentCount")) or request.get("requestedAttachmentCount") != self.policy.allowed_uses:
            return "attachment_grant_invalid"
        if not _integer(request.get("requestedMaxContentBytes")) or not 1 <= request["requestedMaxContentBytes"] <= self.policy.max_content_bytes:
            return "attachment_grant_budget_exceeded"
        if not _integer(request.get("requestedTtlSeconds")) or not self.policy.minimum_ttl_seconds <= request["requestedTtlSeconds"] <= self.policy.maximum_ttl_seconds:
            return "attachment_grant_invalid"
        if request.get("userConfirmationMode") != self.policy.confirmation_mode:
            return "attachment_grant_confirmation_required"
        if _timestamp(request.get("generatedAt")) is None:
            return "attachment_grant_invalid"
        return None

    def issue(self, request: Mapping[str, Any], authorization: AttachmentGrantAuthorizationContext) -> AttachmentGrantIssueResult:
        """Issue a grant only from an explicitly authorized Guardian context."""

        if not isinstance(request, Mapping):
            return AttachmentGrantIssueResult(False, error_code="attachment_grant_invalid")
        request_error = self._request_error(request)
        if request_error is not None:
            return AttachmentGrantIssueResult(False, error_code=request_error)
        if not isinstance(authorization, AttachmentGrantAuthorizationContext) or not authorization.authorized or not authorization.can_issue_attachment_grant or not isinstance(authorization.subject_id, str) or not authorization.subject_id:
            return AttachmentGrantIssueResult(False, error_code="attachment_grant_required")

        issued_at = self._now()
        expires_at = issued_at + timedelta(seconds=request["requestedTtlSeconds"])
        grant_id = "grant-" + self._random_bytes(16).hex()
        bearer = base64.urlsafe_b64encode(self._random_bytes(32)).decode("ascii").rstrip("=")
        if not _BEARER_PATTERN.fullmatch(bearer):
            return AttachmentGrantIssueResult(False, error_code="attachment_grant_invalid")
        record = _GrantRecord(
            grant_id=grant_id,
            bearer_digest=_sha256_bearer(bearer),
            subject_id=authorization.subject_id,
            browser_host_instance_id=request["browserHostInstanceId"],
            request_id=request["requestId"],
            protocol_version=self.policy.protocol_version,
            attachment_version=self.policy.attachment_version,
            retention_class=self.policy.retention_class,
            max_content_bytes=request["requestedMaxContentBytes"],
            confirmation_mode=self.policy.confirmation_mode,
            issued_at=issued_at,
            expires_at=expires_at,
            remaining_uses=self.policy.allowed_uses,
        )
        response = MappingProxyType({
            "schemaVersion": "1.0.0",
            "grantId": grant_id,
            "authorizationScheme": self.policy.authorization_scheme,
            "grantBearer": bearer,
            "protocolVersion": self.policy.protocol_version,
            "attachmentVersion": self.policy.attachment_version,
            "browserHostInstanceId": request["browserHostInstanceId"],
            "requestId": request["requestId"],
            "retentionClass": self.policy.retention_class,
            "maxContentBytes": request["requestedMaxContentBytes"],
            "remainingUses": self.policy.allowed_uses,
            "issuedAt": _wire_timestamp(issued_at),
            "expiresAt": _wire_timestamp(expires_at),
        })
        with self._lock:
            self._records[record.bearer_digest] = record
        return AttachmentGrantIssueResult(True, response, lifecycle="grant_issued", _raw_bearer=bearer)

    def _validate_attachment(self, attachment: Mapping[str, Any], record: _GrantRecord, browser_host_instance_id: str | None) -> str | None:
        if browser_host_instance_id != record.browser_host_instance_id:
            return "attachment_grant_scope_mismatch"
        if not isinstance(attachment, Mapping) or set(attachment) != frozenset(self._contract.schemas["attachment"]["required"]):
            return "attachment_grant_invalid"
        if attachment.get("schemaVersion") != "1.0.0" or attachment.get("protocolVersion") != record.protocol_version or attachment.get("attachmentVersion") != record.attachment_version:
            return "attachment_grant_version_mismatch"
        if attachment.get("requestId") != record.request_id:
            return "attachment_grant_scope_mismatch"
        if not _integer(attachment.get("attemptNumber")) or attachment["attemptNumber"] < 1:
            return "attachment_grant_invalid"
        idempotency_key = attachment.get("idempotencyKey")
        if not isinstance(idempotency_key, str) or not 8 <= len(idempotency_key) <= 256 or not _ID_PATTERN.fullmatch(idempotency_key):
            return "attachment_grant_invalid"
        if attachment.get("requestedRetention") != record.retention_class:
            return "attachment_grant_retention_denied"
        confirmation = attachment.get("userConfirmation")
        if not isinstance(confirmation, Mapping) or set(confirmation) != {"confirmed", "confirmedAt", "method"} or confirmation.get("confirmed") is not True or confirmation.get("method") != "trusted_shell" or _timestamp(confirmation.get("confirmedAt")) is None:
            return "attachment_grant_confirmation_required"
        envelope = attachment.get("envelope")
        if not isinstance(envelope, Mapping) or set(envelope) != frozenset(self._contract.schemas["envelope"]["required"]):
            return "attachment_grant_invalid"
        if envelope.get("schemaVersion") != record.protocol_version:
            return "attachment_grant_version_mismatch"
        if envelope.get("sourceKind") != "browser_page":
            return "attachment_grant_invalid"
        if envelope.get("retentionClass") != record.retention_class or envelope.get("userInitiated") is not True:
            return "attachment_grant_retention_denied" if envelope.get("retentionClass") != record.retention_class else "attachment_grant_invalid"
        if envelope.get("requestId") != record.request_id or envelope.get("attemptNumber") != attachment.get("attemptNumber"):
            return "attachment_grant_scope_mismatch"
        if not _bounded_id(envelope.get("requestId")):
            return "attachment_grant_invalid"
        content = envelope.get("content")
        if not isinstance(content, str):
            return "attachment_grant_invalid"
        content_bytes = content.encode("utf-8")
        content_length = envelope.get("contentLength")
        if not _integer(content_length) or content_length < 0:
            return "attachment_grant_invalid"
        if len(content_bytes) > record.max_content_bytes or content_length > record.max_content_bytes:
            return "attachment_grant_budget_exceeded"
        if content_length != len(content_bytes):
            return "attachment_grant_invalid"
        content_hash = envelope.get("contentHash")
        if not isinstance(content_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", content_hash) or content_hash != hashlib.sha256(content_bytes).hexdigest():
            return "attachment_grant_invalid"
        if not _integer(envelope.get("originalContentLength")) or envelope["originalContentLength"] < len(content_bytes):
            return "attachment_grant_invalid"
        if not isinstance(envelope.get("truncated"), bool):
            return "attachment_grant_invalid"
        if envelope.get("truncated") is False and envelope.get("originalContentLength") != len(content_bytes):
            return "attachment_grant_invalid"
        if envelope.get("contentType") != "text/plain" or envelope.get("permissionScope") != "browser_context_capture_only":
            return "attachment_grant_invalid"
        if envelope.get("captureMode") not in self._contract.tokens["captureModes"]:
            return "attachment_grant_invalid"
        if not _bounded_id(envelope.get("contextId")) or not _bounded_id(envelope.get("captureRequestId")):
            return "attachment_grant_invalid"
        if not isinstance(envelope.get("sourceTitle"), str) or len(envelope["sourceTitle"]) > 512:
            return "attachment_grant_invalid"
        extractor_version = envelope.get("extractorVersion")
        if not isinstance(extractor_version, str) or not 0 < len(extractor_version) <= 128:
            return "attachment_grant_invalid"
        if not _integer(envelope.get("documentGeneration")) or envelope["documentGeneration"] < 0:
            return "attachment_grant_invalid"
        document_fingerprint = envelope.get("documentFingerprint")
        if not isinstance(document_fingerprint, str) or not re.fullmatch(r"[a-f0-9]{64}", document_fingerprint):
            return "attachment_grant_invalid"
        if _timestamp(envelope.get("capturedAt")) is None or _timestamp(attachment.get("generatedAt")) is None:
            return "attachment_grant_invalid"
        source_url = envelope.get("sourceUrl")
        source_origin = envelope.get("sourceOrigin")
        parsed = urlparse(source_url) if isinstance(source_url, str) else None
        if parsed is None or parsed.scheme not in {"http", "https"} or not parsed.netloc or source_origin != f"{parsed.scheme}://{parsed.netloc}":
            return "attachment_grant_invalid"
        sanitization = envelope.get("sanitizationEvidence")
        expected_sanitization = frozenset(self._contract.schemas["envelope"]["properties"]["sanitizationEvidence"]["required"])
        if not isinstance(sanitization, Mapping) or set(sanitization) != expected_sanitization or any(value is not True for value in sanitization.values()):
            return "attachment_grant_invalid"
        target_scope = attachment.get("targetScope")
        if target_scope is not None:
            if not isinstance(target_scope, Mapping) or set(target_scope) != {"kind", "id"} or target_scope.get("kind") not in {"request", "thread", "project"} or not _bounded_id(target_scope.get("id")):
                return "attachment_grant_invalid"
            if target_scope.get("kind") == "request" and target_scope.get("id") != record.request_id:
                return "attachment_grant_scope_mismatch"
        return None

    def consume(self, bearer: str, attachment: Mapping[str, Any], *, browser_host_instance_id: str | None = None) -> AttachmentGrantDecision:
        """Atomically authorize exactly one valid v1 attachment attempt."""

        if not isinstance(bearer, str) or len(bearer) > 128:
            return self._decision(False, "grant_rejected", "attachment_grant_required")
        digest = _sha256_bearer(bearer)
        with self._lock:
            record = self._records.get(digest)
            if record is None:
                return self._decision(False, "grant_rejected", "attachment_grant_invalid")
            now = self._now()
            if record.consumed:
                return self._decision(False, "grant_replayed", "attachment_grant_replayed" if "attachment_grant_replayed" in self._contract.grant_error_codes else "attachment_grant_consumed", record)
            if now >= record.expires_at:
                return self._decision(False, "grant_expired", "attachment_grant_expired", record)
            error_code = self._validate_attachment(attachment, record, browser_host_instance_id)
            if error_code is not None:
                return self._decision(False, "grant_rejected", error_code, record)
            record.consumed = True
            record.remaining_uses = 0
            return self._decision(True, "grant_consumed", None, record)

    def cleanup_expired(self) -> Mapping[str, int]:
        """Remove expired records and return counts only."""

        now = self._now()
        with self._lock:
            expired = [digest for digest, record in self._records.items() if now >= record.expires_at]
            for digest in expired:
                del self._records[digest]
            return MappingProxyType({"expiredRemoved": len(expired), "remainingRecords": len(self._records)})

    def snapshot_for_testing(self) -> tuple[Mapping[str, Any], ...]:
        """Expose redacted storage evidence for tests; never exposes raw bearer material."""

        with self._lock:
            return tuple(MappingProxyType({
                "grantId": record.grant_id,
                "bearerDigest": record.bearer_digest,
                "subjectId": record.subject_id,
                "browserHostInstanceId": record.browser_host_instance_id,
                "requestId": record.request_id,
                "remainingUses": record.remaining_uses,
                "consumed": record.consumed,
            }) for record in self._records.values())
