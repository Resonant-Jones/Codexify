"""Raw-body authentication helpers for GitHub Watchdog webhook intake."""

from __future__ import annotations

import hashlib
import hmac
import re

from guardian.watchdog.contracts import WatchdogIntakeErrorCode


_SIGNATURE_PATTERN = re.compile(r"sha256=[0-9a-fA-F]{64}")


class GitHubWebhookSignatureError(ValueError):
    """A bounded signature verification failure."""

    def __init__(self, error_code: WatchdogIntakeErrorCode) -> None:
        super().__init__(error_code.value)
        self.error_code = error_code


def verify_github_webhook_signature(
    *,
    secret: str | None,
    raw_body: bytes,
    supplied_signature: str | None,
) -> str:
    """Validate GitHub's SHA-256 HMAC over unchanged request bytes."""
    if secret is None or secret == "":
        raise GitHubWebhookSignatureError(WatchdogIntakeErrorCode.SECRET_NOT_CONFIGURED)
    if supplied_signature is None:
        raise GitHubWebhookSignatureError(WatchdogIntakeErrorCode.MISSING_SIGNATURE)
    if _SIGNATURE_PATTERN.fullmatch(supplied_signature) is None:
        raise GitHubWebhookSignatureError(WatchdogIntakeErrorCode.MALFORMED_SIGNATURE)

    expected_signature = (
        "sha256="
        + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    )
    if not hmac.compare_digest(expected_signature, supplied_signature):
        raise GitHubWebhookSignatureError(WatchdogIntakeErrorCode.INVALID_SIGNATURE)
    return hashlib.sha256(raw_body).hexdigest()
