"""Development-only HTTP boundary for the pure Browser Host grant seam.

This module deliberately contains transport and response shaping only.  The
``AttachmentGrantStore`` remains the authority for grant validation, policy,
expiry, replay, and atomic consumption.
"""

from __future__ import annotations

import hashlib
import re
from contextlib import suppress
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Mapping
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from jsonschema import Draft202012Validator, FormatChecker, RefResolver

from guardian.browser_host.attachment_grants import (
    AttachmentGrantAuthorizationContext,
    AttachmentGrantDecision,
    AttachmentGrantStore,
)
from guardian.browser_host.contract_loader import (
    BrowserHostContractMetadata,
    load_contract_metadata,
)
from guardian.core.config import get_settings
from guardian.core.dependencies import _exposure_mode


ROUTE_PREFIX = "/dev/browser-host/v1"
STORE_STATE_KEY = "browser_host_attachment_grant_store"
ADAPTER_STATE_KEY = "browser_host_attachment_adapter_enabled"
FEATURE_FLAG = "GUARDIAN_BROWSER_HOST_ATTACHMENT_DEV_ENABLED"
AUTHORIZATION_SCHEME = "BrowserHostAttachmentGrant"
INSTANCE_HEADER = "X-Codexify-Browser-Host-Instance-Id"
_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")
_BEARER_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{43,128}$")
_DIGEST_PATTERN = re.compile(r"^[a-f0-9]{64}$")

_ERROR_MESSAGES = {
    "attachment_grant_required": "Attachment grant authorization is required.",
    "attachment_grant_invalid": "The attachment grant request is invalid.",
    "attachment_grant_expired": "The attachment grant has expired.",
    "attachment_grant_consumed": "The attachment grant has already been used.",
    "attachment_grant_replayed": "The attachment grant has already been used.",
    "attachment_grant_scope_mismatch": "The attachment is outside the grant scope.",
    "attachment_grant_version_mismatch": "The attachment version is not supported by the grant.",
    "attachment_grant_retention_denied": "Only ephemeral attachment retention is supported.",
    "attachment_grant_budget_exceeded": "The attachment exceeds the granted content budget.",
    "attachment_grant_confirmation_required": "Explicit trusted-shell confirmation is required.",
    "invalid_contract": "The Browser Host contract payload is invalid.",
}

_RECEIPT_ERROR_CODES = {
    "attachment_grant_consumed": "attachment_failed",
    "attachment_grant_replayed": "attachment_failed",
    "attachment_grant_expired": "attachment_failed",
    "attachment_grant_scope_mismatch": "permission_denied",
    "attachment_grant_version_mismatch": "guardian_rejected",
    "attachment_grant_retention_denied": "context_rejected",
    "attachment_grant_confirmation_required": "permission_denied",
    "attachment_grant_budget_exceeded": "context_rejected",
}


def _wire_timestamp(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _bounded_id(value: Any, *, minimum: int = 1, maximum: int = 256) -> bool:
    return (
        isinstance(value, str)
        and minimum <= len(value) <= maximum
        and bool(_ID_PATTERN.fullmatch(value))
    )


def is_bounded_identifier(value: Any, *, minimum: int = 1, maximum: int = 256) -> bool:
    """Expose the contract's bounded identifier check to the thin route module."""

    return _bounded_id(value, minimum=minimum, maximum=maximum)


def _timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _integer(value: Any, *, minimum: int | None = None) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and (minimum is None or value >= minimum)
    )


@lru_cache(maxsize=1)
def _contract() -> BrowserHostContractMetadata:
    return load_contract_metadata()


@lru_cache(maxsize=8)
def _validator(kind: str) -> Draft202012Validator:
    metadata = _contract()
    schema = metadata.schemas[kind]
    schema_store: dict[str, Mapping[str, Any]] = {}
    for candidate in metadata.schemas.values():
        identifier = candidate.get("$id")
        if isinstance(identifier, str):
            schema_store[identifier] = candidate
            schema_store[identifier.rsplit("/", 1)[-1]] = candidate
    resolver = RefResolver(
        base_uri="https://codexify.local/contracts/",
        referrer=schema,
        store=schema_store,
    )
    return Draft202012Validator(schema, resolver=resolver, format_checker=FormatChecker())


def validate_contract(kind: str, value: Any) -> bool:
    """Validate a response or a fully contract-shaped request with v1 schemas."""

    return _validator(kind).is_valid(value)


def browser_host_attachment_adapter_enabled(
    settings: Any | None = None,
    *,
    exposure_mode: str | None = None,
) -> bool:
    """Return the fail-closed three-gate adapter state."""

    config = settings or get_settings()
    resolved_exposure = (
        exposure_mode if exposure_mode is not None else _exposure_mode()
    )
    return (
        bool(getattr(config, "GUARDIAN_DEV_MODE", False))
        and bool(getattr(config, FEATURE_FLAG, False))
        and resolved_exposure == "local_safe"
    )


def install_browser_host_attachment_adapter(app: Any, router: Any) -> bool:
    """Mount the adapter and create exactly one store for an enabled app."""

    if not browser_host_attachment_adapter_enabled():
        return False
    if getattr(app.state, ADAPTER_STATE_KEY, False) or hasattr(
        app.state, STORE_STATE_KEY
    ):
        raise RuntimeError("browser_host_attachment_adapter_already_installed")
    setattr(app.state, STORE_STATE_KEY, AttachmentGrantStore())
    setattr(app.state, ADAPTER_STATE_KEY, True)
    app.include_router(router)
    return True


def get_attachment_grant_store(request: Request) -> AttachmentGrantStore:
    store = getattr(request.app.state, STORE_STATE_KEY, None)
    if not isinstance(store, AttachmentGrantStore):
        raise HTTPException(status_code=404, detail="Not Found")
    return store


def shutdown_browser_host_attachment_adapter(app: Any) -> bool:
    """Drop the app-owned process-local grant records during shutdown."""

    store = getattr(app.state, STORE_STATE_KEY, None)
    if not isinstance(store, AttachmentGrantStore):
        return False
    with suppress(Exception):
        store.cleanup_expired()
    # The pure seam intentionally has no persistence or close protocol.  The
    # adapter owns the process-local record map and clears it before releasing
    # the app reference, so no grant survives application shutdown.
    records = getattr(store, "_records", None)
    lock = getattr(store, "_lock", None)
    if isinstance(records, dict) and lock is not None:
        with lock:
            records.clear()
    setattr(app.state, STORE_STATE_KEY, None)
    setattr(app.state, ADAPTER_STATE_KEY, False)
    return True


def _request_correlation(request: Request, candidate: Any = None) -> str:
    if _bounded_id(candidate):
        return candidate
    state_value = getattr(request.state, "request_id", None)
    if _bounded_id(state_value):
        return state_value
    return "browser-host-attachment"


def _error_payload(
    error_code: str,
    request_correlation_id: str,
    *,
    retryable: bool = False,
) -> dict[str, Any]:
    wire_error_codes = set(
        _contract().schemas["error"]["properties"]["errorCode"]["enum"]
    )
    canonical = error_code if error_code in wire_error_codes else "invalid_contract"
    payload = {
        "schemaVersion": "1.0.0",
        "errorCode": canonical,
        "message": _ERROR_MESSAGES.get(canonical, "The Browser Host request was rejected."),
        "retryable": retryable,
        "requestCorrelationId": _request_correlation_id_value(request_correlation_id),
        "generatedAt": _wire_timestamp(),
        "safeDetails": {},
    }
    if not validate_contract("error", payload):
        raise RuntimeError("browser_host_error_contract_invalid")
    return payload


def _request_correlation_id_value(value: Any) -> str:
    return value if _bounded_id(value) else "browser-host-attachment"


def error_response(
    status_code: int,
    error_code: str,
    request: Request,
    *,
    candidate_request_id: Any = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    response = JSONResponse(
        status_code=status_code,
        content=_error_payload(
            error_code,
            _request_correlation(request, candidate_request_id),
        ),
    )
    apply_no_store(response)
    if headers:
        for name, value in headers.items():
            response.headers[name] = value
    return response


def apply_no_store(response: JSONResponse) -> JSONResponse:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return response


def parse_attachment_grant_authorization(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    prefix = f"{AUTHORIZATION_SCHEME} "
    if not value.startswith(prefix):
        return None
    bearer = value[len(prefix) :]
    return bearer if _BEARER_PATTERN.fullmatch(bearer) else None


def _attachment_shape_valid(attachment: Any) -> bool:
    """Validate body structure before the one-use store can be reached.

    Policy mismatches intentionally remain eligible for the pure store so the
    HTTP layer preserves its 403 rejection taxonomy.  Malformed structure,
    content integrity, and forbidden sanitization evidence fail before consume.
    """

    if not isinstance(attachment, Mapping):
        return False
    if validate_contract("attachment", attachment):
        return True
    required = set(_contract().schemas["attachment"]["required"])
    if set(attachment) != required:
        return False
    if not all(
        isinstance(attachment.get(field), str)
        for field in ("schemaVersion", "protocolVersion", "attachmentVersion")
    ):
        return False
    if not _bounded_id(attachment.get("requestId")):
        return False
    if not _integer(attachment.get("attemptNumber"), minimum=1):
        return False
    if not _bounded_id(attachment.get("idempotencyKey"), minimum=8):
        return False
    if not isinstance(attachment.get("requestedRetention"), str):
        return False
    if not _timestamp(attachment.get("generatedAt")):
        return False

    envelope = attachment.get("envelope")
    if not isinstance(envelope, Mapping):
        return False
    envelope_required = set(_contract().schemas["envelope"]["required"])
    if set(envelope) != envelope_required:
        return False
    if not isinstance(envelope.get("schemaVersion"), str):
        return False
    for field in ("contextId", "captureRequestId", "requestId"):
        if not _bounded_id(envelope.get(field)):
            return False
    if not isinstance(envelope.get("sourceKind"), str):
        return False
    source_url = envelope.get("sourceUrl")
    parsed = urlparse(source_url) if isinstance(source_url, str) else None
    if (
        parsed is None
        or parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or envelope.get("sourceOrigin") != f"{parsed.scheme}://{parsed.netloc}"
    ):
        return False
    if not isinstance(envelope.get("sourceTitle"), str) or len(envelope["sourceTitle"]) > 512:
        return False
    if not _timestamp(envelope.get("capturedAt")):
        return False
    if not isinstance(envelope.get("captureMode"), str):
        return False
    if not isinstance(envelope.get("contentType"), str):
        return False
    content = envelope.get("content")
    if not isinstance(content, str):
        return False
    if not _integer(envelope.get("contentLength"), minimum=0):
        return False
    if not _integer(envelope.get("originalContentLength"), minimum=0):
        return False
    if not isinstance(envelope.get("truncated"), bool):
        return False
    if not isinstance(envelope.get("extractorVersion"), str) or not _bounded_id(
        envelope.get("extractorVersion"), maximum=128
    ):
        return False
    if not isinstance(envelope.get("permissionScope"), str):
        return False
    if not isinstance(envelope.get("retentionClass"), str):
        return False
    if not isinstance(envelope.get("userInitiated"), bool):
        return False
    if not _integer(envelope.get("attemptNumber"), minimum=1):
        return False
    sanitization = envelope.get("sanitizationEvidence")
    sanitization_required = set(
        _contract().schemas["envelope"]["properties"]["sanitizationEvidence"]["required"]
    )
    if not isinstance(sanitization, Mapping) or set(sanitization) != sanitization_required:
        return False
    if any(value is not True for value in sanitization.values()):
        return False
    if not _integer(envelope.get("documentGeneration"), minimum=0):
        return False
    if not _DIGEST_PATTERN.fullmatch(str(envelope.get("documentFingerprint"))):
        return False

    content_length = len(content.encode("utf-8"))
    declared_length = envelope["contentLength"]
    declared_hash = envelope.get("contentHash")
    # The pure store deliberately returns a budget error before checking hash
    # or length.  Keep oversized attempts eligible for that 403 decision.
    if content_length <= _contract().max_capture_bytes and declared_length <= _contract().max_capture_bytes:
        if declared_length != content_length:
            return False
        if not _DIGEST_PATTERN.fullmatch(str(declared_hash)):
            return False
        if declared_hash != hashlib.sha256(content.encode("utf-8")).hexdigest():
            return False
        if envelope["originalContentLength"] < content_length:
            return False
        if envelope["truncated"] is False and envelope["originalContentLength"] != content_length:
            return False
    elif not isinstance(declared_hash, str):
        return False

    confirmation = attachment.get("userConfirmation")
    if not isinstance(confirmation, Mapping) or set(confirmation) != {
        "confirmed",
        "confirmedAt",
        "method",
    }:
        return False
    if not isinstance(confirmation.get("confirmed"), bool):
        return False
    if not _timestamp(confirmation.get("confirmedAt")):
        return False
    if not isinstance(confirmation.get("method"), str):
        return False

    target_scope = attachment.get("targetScope")
    if target_scope is not None:
        if not isinstance(target_scope, Mapping) or set(target_scope) != {"kind", "id"}:
            return False
        if not isinstance(target_scope.get("kind"), str) or not _bounded_id(target_scope.get("id")):
            return False
    return True


def _receipt(
    attachment: Mapping[str, Any],
    *,
    accepted: bool,
    error_code: str | None = None,
) -> dict[str, Any]:
    envelope = attachment.get("envelope")
    receipt = {
        "schemaVersion": "1.0.0",
        "protocolVersion": "1.0.0",
        "requestId": attachment.get("requestId"),
        "attemptNumber": attachment.get("attemptNumber"),
        "contextId": envelope.get("contextId") if isinstance(envelope, Mapping) else None,
        "attachmentOutcome": "accepted" if accepted else "rejected",
        "persistenceOutcome": "not_persisted",
        "errorCode": None if accepted else error_code,
        "receivedAt": _wire_timestamp(),
        "guardianCorrelationId": (
            f"guardian-attachment-{uuid4().hex}" if accepted else None
        ),
    }
    if not validate_contract("receipt", receipt):
        raise RuntimeError("browser_host_receipt_contract_invalid")
    return receipt


def issue_attachment_grant(
    request: Request,
    body: Any,
    subject: Any,
    store: AttachmentGrantStore,
) -> JSONResponse:
    if not isinstance(subject, str) or not subject:
        return error_response(401, "permission_denied", request)
    if not validate_contract("attachmentGrantRequest", body):
        return error_response(
            422,
            "invalid_contract",
            request,
            candidate_request_id=body.get("requestId") if isinstance(body, Mapping) else None,
        )
    result = store.issue(
        body,
        AttachmentGrantAuthorizationContext.explicitly_authorized(subject),
    )
    if not result.accepted or result.grant_response is None:
        return error_response(
            422,
            result.error_code or "attachment_grant_invalid",
            request,
            candidate_request_id=body.get("requestId"),
        )
    response = JSONResponse(status_code=201, content=dict(result.grant_response))
    return apply_no_store(response)


def consume_attachment(
    request: Request,
    body: Any,
    bearer: str,
    instance_id: str,
    store: AttachmentGrantStore,
) -> JSONResponse:
    if not _attachment_shape_valid(body):
        return error_response(
            422,
            "invalid_contract",
            request,
            candidate_request_id=body.get("requestId") if isinstance(body, Mapping) else None,
        )
    decision = store.consume(
        bearer,
        body,
        browser_host_instance_id=instance_id,
    )
    if decision.authorized:
        response = JSONResponse(status_code=202, content=_receipt(body, accepted=True))
        return apply_no_store(response)
    if decision.error_code in {"attachment_grant_required", "attachment_grant_invalid"}:
        return error_response(
            401,
            "permission_denied",
            request,
            candidate_request_id=body.get("requestId"),
            headers={"WWW-Authenticate": AUTHORIZATION_SCHEME},
        )
    if decision.lifecycle in {"grant_replayed", "grant_expired"}:
        receipt_code = _RECEIPT_ERROR_CODES.get(
            decision.error_code or "attachment_grant_expired",
            "attachment_failed",
        )
        response = JSONResponse(
            status_code=409,
            content=_receipt(body, accepted=False, error_code=receipt_code),
        )
        return apply_no_store(response)
    if decision.error_code in _RECEIPT_ERROR_CODES:
        response = JSONResponse(
            status_code=403,
            content=_receipt(
                body,
                accepted=False,
                error_code=_RECEIPT_ERROR_CODES[decision.error_code],
            ),
        )
        return apply_no_store(response)
    return error_response(
        422,
        decision.error_code or "attachment_grant_invalid",
        request,
        candidate_request_id=body.get("requestId"),
    )
