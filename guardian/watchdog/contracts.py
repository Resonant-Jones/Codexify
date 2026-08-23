"""Stable contracts for the bounded GitHub Watchdog intake surface."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


class WatchdogReceiptDisposition(str, Enum):
    """Acknowledgement disposition for an authenticated delivery."""

    ACCEPTED = "accepted"
    IGNORED = "ignored"


class WatchdogIntakeErrorCode(str, Enum):
    """Bounded machine-readable errors emitted by webhook intake."""

    SECRET_NOT_CONFIGURED = "secret_not_configured"
    MISSING_SIGNATURE = "missing_signature"
    MALFORMED_SIGNATURE = "malformed_signature"
    INVALID_SIGNATURE = "invalid_signature"
    MISSING_DELIVERY_ID = "missing_delivery_id"
    MISSING_EVENT = "missing_event"
    MALFORMED_JSON = "malformed_json"
    INVALID_PAYLOAD = "invalid_payload"
    CONFLICTING_DELIVERY = "conflicting_delivery"
    PERSISTENCE_UNAVAILABLE = "persistence_unavailable"
    PERSISTENCE_FAILED = "persistence_failed"


SUPPORTED_GITHUB_EVENT_ACTIONS = frozenset(
    {
        ("pull_request", "opened"),
        ("pull_request", "synchronize"),
        ("pull_request", "reopened"),
        ("issue_comment", "created"),
    }
)


class GitHubWebhookPayloadError(ValueError):
    """Raised when an authenticated webhook body is not a supported object."""


@dataclass(frozen=True)
class NormalizedGitHubDelivery:
    """Bounded delivery metadata permitted to enter durable receipt storage."""

    github_delivery_id: str
    idempotency_key: str
    event_name: str
    action: str
    installation_id: str | None
    repository_id: str | None
    repository_full_name: str | None
    trigger_actor_id: str | None
    trigger_actor_login: str | None
    pull_request_number: int | None
    head_sha: str | None
    payload_sha256: str


def github_action_from_payload(payload: object) -> str | None:
    """Return the bounded action token without inspecting comment contents."""
    if not isinstance(payload, dict):
        raise GitHubWebhookPayloadError("payload must be a JSON object")
    return _optional_text(payload.get("action"))


def is_supported_github_event_action(event_name: str, action: str | None) -> bool:
    """Return whether an event/action pair belongs to this intake slice."""
    return (event_name, action or "") in SUPPORTED_GITHUB_EVENT_ACTIONS


def is_supported_github_delivery(
    *, event_name: str, action: str | None, payload: object
) -> bool:
    """Return whether authenticated metadata is eligible for receipt storage."""
    if not is_supported_github_event_action(event_name, action):
        return False
    if event_name != "issue_comment":
        return True
    if not isinstance(payload, dict):
        raise GitHubWebhookPayloadError("payload must be a JSON object")
    issue = _object(payload.get("issue"))
    return isinstance(issue.get("pull_request"), dict)


def normalize_github_delivery(
    *,
    github_delivery_id: str,
    event_name: str,
    payload: object,
    payload_sha256: str,
) -> NormalizedGitHubDelivery:
    """Normalize the allowed metadata for a supported authenticated delivery."""
    if not isinstance(payload, dict):
        raise GitHubWebhookPayloadError("payload must be a JSON object")

    action = github_action_from_payload(payload)
    if not is_supported_github_delivery(
        event_name=event_name, action=action, payload=payload
    ):
        raise GitHubWebhookPayloadError("delivery is not supported")
    assert action is not None

    installation = _object(payload.get("installation"))
    repository = _object(payload.get("repository"))
    sender = _object(payload.get("sender"))

    installation_id = _optional_identifier(installation.get("id"))
    repository_id = _optional_identifier(repository.get("id"))
    repository_full_name = _optional_text(repository.get("full_name"))
    trigger_actor_id = _optional_identifier(sender.get("id"))
    trigger_actor_login = _optional_text(sender.get("login"))

    pull_request_number: int | None = None
    head_sha: str | None = None
    if event_name == "pull_request":
        pull_request_number = _optional_positive_int(payload.get("number"))
        pull_request = _object(payload.get("pull_request"))
        head = _object(pull_request.get("head"))
        head_sha = _optional_text(head.get("sha"))
    elif event_name == "issue_comment":
        issue = _object(payload.get("issue"))
        pull_request_number = _optional_positive_int(issue.get("number"))

    return NormalizedGitHubDelivery(
        github_delivery_id=github_delivery_id,
        idempotency_key=build_delivery_idempotency_key(
            github_delivery_id=github_delivery_id,
            installation_id=installation_id,
            repository_id=repository_id,
            event_name=event_name,
            action=action,
        ),
        event_name=event_name,
        action=action,
        installation_id=installation_id,
        repository_id=repository_id,
        repository_full_name=repository_full_name,
        trigger_actor_id=trigger_actor_id,
        trigger_actor_login=trigger_actor_login,
        pull_request_number=pull_request_number,
        head_sha=head_sha,
        payload_sha256=payload_sha256,
    )


def build_delivery_idempotency_key(
    *,
    github_delivery_id: str,
    installation_id: str | None,
    repository_id: str | None,
    event_name: str,
    action: str,
) -> str:
    """Produce a deterministic receipt identity without retaining the payload."""
    material = {
        "action": action,
        "delivery_id": github_delivery_id,
        "event": event_name,
        "installation_id": installation_id,
        "repository_id": repository_id,
    }
    encoded = json.dumps(material, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _object(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    value_text = str(value).strip()
    return value_text or None


def _optional_identifier(value: object) -> str | None:
    return _optional_text(value)


def _optional_positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        candidate = int(value)
    except (TypeError, ValueError):
        return None
    return candidate if candidate > 0 else None
