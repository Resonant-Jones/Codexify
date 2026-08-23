"""Authenticated GitHub Watchdog webhook receipt endpoint."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from guardian.core.config import get_settings
from guardian.watchdog.contracts import (
    GitHubWebhookPayloadError,
    WatchdogIntakeErrorCode,
    WatchdogReceiptDisposition,
    github_action_from_payload,
    is_supported_github_delivery,
    normalize_github_delivery,
)
from guardian.watchdog.security import (
    GitHubWebhookSignatureError,
    verify_github_webhook_signature,
)
from guardian.watchdog.store import (
    ConflictingGitHubDeliveryError,
    GitHubWatchdogDeliveryReceiptStore,
    WatchdogReceiptPersistenceError,
    WatchdogReceiptStoreUnavailable,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/watchdog/github", tags=["GitHub Watchdog"])

_CLIENT_ERROR_STATUS = {
    WatchdogIntakeErrorCode.MISSING_SIGNATURE: 401,
    WatchdogIntakeErrorCode.MALFORMED_SIGNATURE: 401,
    WatchdogIntakeErrorCode.INVALID_SIGNATURE: 401,
    WatchdogIntakeErrorCode.MISSING_DELIVERY_ID: 400,
    WatchdogIntakeErrorCode.MISSING_EVENT: 400,
    WatchdogIntakeErrorCode.MALFORMED_JSON: 400,
    WatchdogIntakeErrorCode.INVALID_PAYLOAD: 400,
    WatchdogIntakeErrorCode.CONFLICTING_DELIVERY: 409,
}


def _error_response(error_code: WatchdogIntakeErrorCode) -> JSONResponse:
    status_code = _CLIENT_ERROR_STATUS.get(error_code, 503)
    return JSONResponse(status_code=status_code, content={"error": error_code.value})


def _required_header(request: Request, header_name: str) -> str | None:
    value = request.headers.get(header_name)
    return value.strip() if value is not None and value.strip() else None


def _receipt_store(request: Request) -> GitHubWatchdogDeliveryReceiptStore:
    test_store = getattr(request.app.state, "github_watchdog_receipt_store", None)
    if test_store is not None:
        return test_store
    return GitHubWatchdogDeliveryReceiptStore()


def _log_rejection(
    error_code: WatchdogIntakeErrorCode,
    *,
    delivery_id: str | None = None,
    event_name: str | None = None,
    action: str | None = None,
    repository_id: str | None = None,
    pull_request_number: int | None = None,
) -> None:
    logger.warning(
        "GitHub Watchdog intake rejected error_code=%s delivery_id=%s event=%s "
        "action=%s repository_id=%s pull_request_number=%s",
        error_code.value,
        delivery_id,
        event_name,
        action,
        repository_id,
        pull_request_number,
    )


@router.post("/webhook", status_code=202)
async def receive_github_watchdog_webhook(request: Request) -> JSONResponse:
    """Authenticate, normalize, and durably receipt a single GitHub delivery."""
    raw_body = await request.body()
    settings = get_settings()
    try:
        payload_sha256 = verify_github_webhook_signature(
            secret=getattr(settings, "CODEXIFY_GITHUB_WATCHDOG_WEBHOOK_SECRET", None),
            raw_body=raw_body,
            supplied_signature=request.headers.get("X-Hub-Signature-256"),
        )
    except GitHubWebhookSignatureError as exc:
        _log_rejection(exc.error_code)
        return _error_response(exc.error_code)

    delivery_id = _required_header(request, "X-GitHub-Delivery")
    if delivery_id is None:
        _log_rejection(WatchdogIntakeErrorCode.MISSING_DELIVERY_ID)
        return _error_response(WatchdogIntakeErrorCode.MISSING_DELIVERY_ID)

    event_name = _required_header(request, "X-GitHub-Event")
    if event_name is None:
        _log_rejection(WatchdogIntakeErrorCode.MISSING_EVENT, delivery_id=delivery_id)
        return _error_response(WatchdogIntakeErrorCode.MISSING_EVENT)

    try:
        payload: Any = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        _log_rejection(
            WatchdogIntakeErrorCode.MALFORMED_JSON,
            delivery_id=delivery_id,
            event_name=event_name,
        )
        return _error_response(WatchdogIntakeErrorCode.MALFORMED_JSON)

    try:
        action = github_action_from_payload(payload)
        supported_delivery = is_supported_github_delivery(
            event_name=event_name, action=action, payload=payload
        )
    except GitHubWebhookPayloadError:
        _log_rejection(
            WatchdogIntakeErrorCode.INVALID_PAYLOAD,
            delivery_id=delivery_id,
            event_name=event_name,
        )
        return _error_response(WatchdogIntakeErrorCode.INVALID_PAYLOAD)

    if not supported_delivery:
        logger.info(
            "GitHub Watchdog delivery ignored delivery_id=%s event=%s action=%s",
            delivery_id,
            event_name,
            action,
        )
        return JSONResponse(
            status_code=202,
            content={
                "receiptId": None,
                "deliveryId": delivery_id,
                "event": event_name,
                "action": action,
                "duplicate": False,
                "disposition": WatchdogReceiptDisposition.IGNORED.value,
            },
        )

    try:
        delivery = normalize_github_delivery(
            github_delivery_id=delivery_id,
            event_name=event_name,
            payload=payload,
            payload_sha256=payload_sha256,
        )
    except GitHubWebhookPayloadError:
        _log_rejection(
            WatchdogIntakeErrorCode.INVALID_PAYLOAD,
            delivery_id=delivery_id,
            event_name=event_name,
            action=action,
        )
        return _error_response(WatchdogIntakeErrorCode.INVALID_PAYLOAD)

    try:
        result = _receipt_store(request).persist(delivery)
    except ConflictingGitHubDeliveryError:
        _log_rejection(
            WatchdogIntakeErrorCode.CONFLICTING_DELIVERY,
            delivery_id=delivery_id,
            event_name=event_name,
            action=action,
            repository_id=delivery.repository_id,
            pull_request_number=delivery.pull_request_number,
        )
        return _error_response(WatchdogIntakeErrorCode.CONFLICTING_DELIVERY)
    except WatchdogReceiptStoreUnavailable:
        _log_rejection(
            WatchdogIntakeErrorCode.PERSISTENCE_UNAVAILABLE,
            delivery_id=delivery_id,
            event_name=event_name,
            action=action,
            repository_id=delivery.repository_id,
            pull_request_number=delivery.pull_request_number,
        )
        return _error_response(WatchdogIntakeErrorCode.PERSISTENCE_UNAVAILABLE)
    except WatchdogReceiptPersistenceError:
        _log_rejection(
            WatchdogIntakeErrorCode.PERSISTENCE_FAILED,
            delivery_id=delivery_id,
            event_name=event_name,
            action=action,
            repository_id=delivery.repository_id,
            pull_request_number=delivery.pull_request_number,
        )
        return _error_response(WatchdogIntakeErrorCode.PERSISTENCE_FAILED)

    logger.info(
        "GitHub Watchdog receipt accepted receipt_id=%s delivery_id=%s event=%s "
        "action=%s repository_id=%s pull_request_number=%s duplicate=%s",
        result.receipt_id,
        delivery_id,
        event_name,
        action,
        delivery.repository_id,
        delivery.pull_request_number,
        result.duplicate,
    )
    return JSONResponse(
        status_code=202,
        content={
            "receiptId": result.receipt_id,
            "deliveryId": delivery_id,
            "event": event_name,
            "action": action,
            "duplicate": result.duplicate,
            "disposition": WatchdogReceiptDisposition.ACCEPTED.value,
        },
    )
