"""Read-only GitHub App installation authentication for the Watchdog.

This module deliberately owns no durable state and is not connected to webhook
intake. It authenticates one explicit installation, reads one PR, and returns
only bounded metadata needed by a later snapshot-capture boundary.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from urllib.parse import quote

import jwt
import requests

from guardian.connectors.github import API_ROOT as GITHUB_API_ROOT
from guardian.core.egress import EgressDeniedError, assert_egress_allowed
from guardian.watchdog.contracts import (
    WatchdogGitHubAppError,
    WatchdogGitHubAppErrorCode,
)

GITHUB_EGRESS_TARGET = "github"
GITHUB_API_VERSION = "2022-11-28"
GITHUB_ACCEPT_HEADER = "application/vnd.github+json"
GITHUB_WATCHDOG_USER_AGENT = "codexify-watchdog/1.0"
GITHUB_REQUEST_TIMEOUT_SECONDS = 15
GITHUB_APP_JWT_BACKDATE_SECONDS = 60
GITHUB_APP_JWT_LIFETIME_SECONDS = 9 * 60


class WatchdogPullRequestHeadState(str, Enum):
    """The immutable-attempt relationship to a live GitHub PR head."""

    EXACT = "exact"
    STALE = "stale"
    MISSING_OR_INVALID = "missing_or_invalid"


@dataclass(frozen=True)
class GitHubInstallationAccessToken:
    """Ephemeral installation credential; never suitable for persistence."""

    installation_id: str
    token: str = field(repr=False)
    expires_at: datetime


@dataclass(frozen=True)
class GitHubPullRequestMetadata:
    """Bounded authoritative GitHub metadata for one pull request."""

    repository_id: str
    repository_full_name: str
    pull_request_number: int
    title: str
    state: str
    base_sha: str
    head_sha: str
    author_id: str | None
    author_login: str | None
    draft: bool
    head_repository_id: str | None
    head_repository_full_name: str | None
    head_repository_owner_id: str | None
    head_repository_owner_login: str | None
    head_is_fork: bool


@dataclass(frozen=True)
class WatchdogPullRequestHeadValidation:
    """Pure comparison result; it never changes durable attempt state."""

    state: WatchdogPullRequestHeadState
    expected_head_sha: str | None
    actual_head_sha: str | None
    error_code: WatchdogGitHubAppErrorCode | None

    @property
    def matches(self) -> bool:
        """Return true only when the immutable expected head exactly matches."""
        return self.state is WatchdogPullRequestHeadState.EXACT


def create_github_app_jwt(
    *,
    app_id: object,
    private_key: object,
    now: datetime,
) -> str:
    """Create a bounded GitHub App JWT with deterministic caller-supplied time."""
    normalized_app_id = _required_config_text(app_id)
    normalized_private_key = _required_config_text(private_key)
    now_utc = _require_aware_utc(now)

    try:
        signing_key = jwt.algorithms.RSAAlgorithm(
            jwt.algorithms.RSAAlgorithm.SHA256
        ).prepare_key(normalized_private_key)
    except Exception as exc:
        raise WatchdogGitHubAppError(
            WatchdogGitHubAppErrorCode.PRIVATE_KEY_INVALID
        ) from exc

    issued_at = now_utc - timedelta(seconds=GITHUB_APP_JWT_BACKDATE_SECONDS)
    expires_at = now_utc + timedelta(seconds=GITHUB_APP_JWT_LIFETIME_SECONDS)
    try:
        encoded = jwt.encode(
            {
                "iat": int(issued_at.timestamp()),
                "exp": int(expires_at.timestamp()),
                "iss": normalized_app_id,
            },
            signing_key,
            algorithm="RS256",
        )
    except Exception as exc:
        raise WatchdogGitHubAppError(
            WatchdogGitHubAppErrorCode.JWT_CREATION_FAILED
        ) from exc
    if not isinstance(encoded, str) or not encoded:
        raise WatchdogGitHubAppError(WatchdogGitHubAppErrorCode.JWT_CREATION_FAILED)
    return encoded


def validate_pull_request_head(
    pull_request: GitHubPullRequestMetadata,
    expected_head_sha: str | None,
) -> WatchdogPullRequestHeadValidation:
    """Compare immutable attempt identity without accepting a changed GitHub head."""
    actual_head_sha = pull_request.head_sha
    if not _is_valid_git_sha(expected_head_sha) or not _is_valid_git_sha(actual_head_sha):
        return WatchdogPullRequestHeadValidation(
            state=WatchdogPullRequestHeadState.MISSING_OR_INVALID,
            expected_head_sha=expected_head_sha,
            actual_head_sha=actual_head_sha,
            error_code=WatchdogGitHubAppErrorCode.EXPECTED_HEAD_MISSING_OR_INVALID,
        )
    if actual_head_sha != expected_head_sha:
        return WatchdogPullRequestHeadValidation(
            state=WatchdogPullRequestHeadState.STALE,
            expected_head_sha=expected_head_sha,
            actual_head_sha=actual_head_sha,
            error_code=WatchdogGitHubAppErrorCode.EXPECTED_HEAD_MISMATCH,
        )
    return WatchdogPullRequestHeadValidation(
        state=WatchdogPullRequestHeadState.EXACT,
        expected_head_sha=expected_head_sha,
        actual_head_sha=actual_head_sha,
        error_code=None,
    )


class GitHubWatchdogAppReadClient:
    """Read exactly one installation's PR metadata through GitHub App auth."""

    def __init__(
        self,
        *,
        settings: Any,
        installation_id: object,
        session: Any | None = None,
        api_base_url: str = GITHUB_API_ROOT,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self._settings = settings
        self._installation_id = _normalize_installation_id(installation_id)
        self._session = session or requests.Session()
        self._api_base_url = api_base_url.rstrip("/")
        self._now_factory = now_factory or _utcnow

    def get_pull_request(
        self,
        repository_full_name: str,
        pull_request_number: int,
    ) -> GitHubPullRequestMetadata:
        """Return bounded metadata for one PR using a fresh installation token."""
        owner, repository = _normalize_repository_full_name(repository_full_name)
        number = _normalize_pull_request_number(pull_request_number)
        try:
            assert_egress_allowed(GITHUB_EGRESS_TARGET, settings=self._settings)
        except EgressDeniedError as exc:
            raise WatchdogGitHubAppError(
                WatchdogGitHubAppErrorCode.EGRESS_DENIED
            ) from exc

        app_id, private_key = _configured_app_identity(self._settings)
        app_jwt = create_github_app_jwt(
            app_id=app_id,
            private_key=private_key,
            now=self._now_factory(),
        )
        installation_token = self._exchange_installation_token(app_jwt)
        response = self._get_json(
            f"{self._api_base_url}/repos/{quote(owner, safe='')}/"
            f"{quote(repository, safe='')}/pulls/{number}",
            token=installation_token.token,
        )
        return _normalize_pull_request_metadata(
            response,
            requested_repository_full_name=repository_full_name,
            requested_pull_request_number=number,
        )

    def _exchange_installation_token(self, app_jwt: str) -> GitHubInstallationAccessToken:
        response = self._post_json(
            f"{self._api_base_url}/app/installations/{self._installation_id}/access_tokens",
            token=app_jwt,
        )
        token = _required_response_text(response.get("token"))
        expires_at = _parse_github_expiration(response.get("expires_at"))
        return GitHubInstallationAccessToken(
            installation_id=self._installation_id,
            token=token,
            expires_at=expires_at,
        )

    def _post_json(self, url: str, *, token: str) -> Mapping[str, object]:
        try:
            response = self._session.post(
                url,
                headers=_github_headers(token),
                timeout=GITHUB_REQUEST_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            raise WatchdogGitHubAppError(
                WatchdogGitHubAppErrorCode.TRANSPORT_FAILURE
            ) from exc

        status_code = _response_status(response)
        if status_code in {401, 404}:
            raise WatchdogGitHubAppError(
                WatchdogGitHubAppErrorCode.INSTALLATION_UNKNOWN_OR_UNAUTHORIZED
            )
        if status_code != 201:
            raise WatchdogGitHubAppError(
                WatchdogGitHubAppErrorCode.INSTALLATION_TOKEN_EXCHANGE_REJECTED
            )
        return _response_json_object(response)

    def _get_json(self, url: str, *, token: str) -> Mapping[str, object]:
        try:
            response = self._session.get(
                url,
                headers=_github_headers(token),
                timeout=GITHUB_REQUEST_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            raise WatchdogGitHubAppError(
                WatchdogGitHubAppErrorCode.TRANSPORT_FAILURE
            ) from exc

        status_code = _response_status(response)
        if status_code == 401:
            raise WatchdogGitHubAppError(
                WatchdogGitHubAppErrorCode.GITHUB_API_AUTHENTICATION_REJECTED
            )
        if status_code == 404:
            raise WatchdogGitHubAppError(
                WatchdogGitHubAppErrorCode.PULL_REQUEST_NOT_FOUND
            )
        if status_code == 429 or (
            status_code == 403 and _response_header(response, "X-RateLimit-Remaining") == "0"
        ):
            raise WatchdogGitHubAppError(
                WatchdogGitHubAppErrorCode.GITHUB_API_RATE_LIMITED
            )
        if status_code == 403:
            raise WatchdogGitHubAppError(
                WatchdogGitHubAppErrorCode.GITHUB_API_FORBIDDEN
            )
        if status_code < 200 or status_code >= 300:
            raise WatchdogGitHubAppError(
                WatchdogGitHubAppErrorCode.GITHUB_API_REQUEST_REJECTED
            )
        return _response_json_object(response)


def _configured_app_identity(settings: Any) -> tuple[str, str]:
    return (
        _required_config_text(
            getattr(settings, "CODEXIFY_GITHUB_WATCHDOG_APP_ID", None)
        ),
        _required_config_text(
            getattr(settings, "CODEXIFY_GITHUB_WATCHDOG_APP_PRIVATE_KEY", None)
        ),
    )


def _required_config_text(value: object) -> str:
    if not isinstance(value, str):
        raise WatchdogGitHubAppError(WatchdogGitHubAppErrorCode.CONFIGURATION_MISSING)
    normalized = value.strip()
    if not normalized:
        raise WatchdogGitHubAppError(WatchdogGitHubAppErrorCode.CONFIGURATION_MISSING)
    return normalized


def _require_aware_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise WatchdogGitHubAppError(WatchdogGitHubAppErrorCode.JWT_CREATION_FAILED)
    return value.astimezone(timezone.utc)


def _normalize_installation_id(value: object) -> str:
    if isinstance(value, bool):
        raise WatchdogGitHubAppError(WatchdogGitHubAppErrorCode.INVALID_READ_REQUEST)
    normalized = str(value).strip()
    if not normalized.isdecimal() or int(normalized) <= 0:
        raise WatchdogGitHubAppError(WatchdogGitHubAppErrorCode.INVALID_READ_REQUEST)
    return normalized


def _normalize_repository_full_name(value: str) -> tuple[str, str]:
    if not isinstance(value, str):
        raise WatchdogGitHubAppError(WatchdogGitHubAppErrorCode.INVALID_READ_REQUEST)
    parts = value.strip().split("/")
    if len(parts) != 2 or not all(parts):
        raise WatchdogGitHubAppError(WatchdogGitHubAppErrorCode.INVALID_READ_REQUEST)
    return parts[0], parts[1]


def _normalize_pull_request_number(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise WatchdogGitHubAppError(WatchdogGitHubAppErrorCode.INVALID_READ_REQUEST)
    return value


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": GITHUB_ACCEPT_HEADER,
        "Authorization": f"Bearer {token}",
        "User-Agent": GITHUB_WATCHDOG_USER_AGENT,
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }


def _response_status(response: Any) -> int:
    status_code = getattr(response, "status_code", None)
    if isinstance(status_code, bool) or not isinstance(status_code, int):
        raise WatchdogGitHubAppError(
            WatchdogGitHubAppErrorCode.MALFORMED_GITHUB_RESPONSE
        )
    return status_code


def _response_header(response: Any, name: str) -> str | None:
    headers = getattr(response, "headers", {})
    if not isinstance(headers, Mapping):
        return None
    for key, value in headers.items():
        if str(key).lower() == name.lower():
            return str(value)
    return None


def _response_json_object(response: Any) -> Mapping[str, object]:
    try:
        payload = response.json()
    except Exception as exc:
        raise WatchdogGitHubAppError(
            WatchdogGitHubAppErrorCode.MALFORMED_GITHUB_RESPONSE
        ) from exc
    if not isinstance(payload, Mapping):
        raise WatchdogGitHubAppError(
            WatchdogGitHubAppErrorCode.MALFORMED_GITHUB_RESPONSE
        )
    return payload


def _normalize_pull_request_metadata(
    payload: Mapping[str, object],
    *,
    requested_repository_full_name: str,
    requested_pull_request_number: int,
) -> GitHubPullRequestMetadata:
    base = _object(payload.get("base"))
    head = _object(payload.get("head"))
    repository = _object(base.get("repo"))
    head_repository = _object(head.get("repo"))
    author = _object(payload.get("user"))
    owner = _object(head_repository.get("owner"))

    repository_full_name = _required_response_text(repository.get("full_name"))
    pull_request_number = _required_positive_int(payload.get("number"))
    if (
        repository_full_name != requested_repository_full_name
        or pull_request_number != requested_pull_request_number
    ):
        raise WatchdogGitHubAppError(
            WatchdogGitHubAppErrorCode.MALFORMED_GITHUB_RESPONSE
        )

    draft = payload.get("draft")
    if not isinstance(draft, bool):
        raise WatchdogGitHubAppError(
            WatchdogGitHubAppErrorCode.MALFORMED_GITHUB_RESPONSE
        )
    head_repository_full_name = _optional_response_text(head_repository.get("full_name"))
    return GitHubPullRequestMetadata(
        repository_id=_required_response_identifier(repository.get("id")),
        repository_full_name=repository_full_name,
        pull_request_number=pull_request_number,
        title=_required_response_text(payload.get("title")),
        state=_required_response_text(payload.get("state")),
        base_sha=_required_response_text(base.get("sha")),
        head_sha=_required_response_text(head.get("sha")),
        author_id=_optional_response_identifier(author.get("id")),
        author_login=_optional_response_text(author.get("login")),
        draft=draft,
        head_repository_id=_optional_response_identifier(head_repository.get("id")),
        head_repository_full_name=head_repository_full_name,
        head_repository_owner_id=_optional_response_identifier(owner.get("id")),
        head_repository_owner_login=_optional_response_text(owner.get("login")),
        head_is_fork=(
            head_repository_full_name is not None
            and head_repository_full_name != repository_full_name
        ),
    )


def _object(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _required_response_text(value: object) -> str:
    if not isinstance(value, str):
        raise WatchdogGitHubAppError(
            WatchdogGitHubAppErrorCode.MALFORMED_GITHUB_RESPONSE
        )
    normalized = value.strip()
    if not normalized:
        raise WatchdogGitHubAppError(
            WatchdogGitHubAppErrorCode.MALFORMED_GITHUB_RESPONSE
        )
    return normalized


def _optional_response_text(value: object) -> str | None:
    if value is None:
        return None
    return _required_response_text(value)


def _required_response_identifier(value: object) -> str:
    normalized = _optional_response_identifier(value)
    if normalized is None:
        raise WatchdogGitHubAppError(
            WatchdogGitHubAppErrorCode.MALFORMED_GITHUB_RESPONSE
        )
    return normalized


def _optional_response_identifier(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise WatchdogGitHubAppError(WatchdogGitHubAppErrorCode.MALFORMED_GITHUB_RESPONSE)


def _required_positive_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise WatchdogGitHubAppError(
            WatchdogGitHubAppErrorCode.MALFORMED_GITHUB_RESPONSE
        )
    return value


def _parse_github_expiration(value: object) -> datetime:
    text = _required_response_text(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WatchdogGitHubAppError(
            WatchdogGitHubAppErrorCode.MALFORMED_GITHUB_RESPONSE
        ) from exc
    if parsed.tzinfo is None:
        raise WatchdogGitHubAppError(
            WatchdogGitHubAppErrorCode.MALFORMED_GITHUB_RESPONSE
        )
    return parsed.astimezone(timezone.utc)


def _is_valid_git_sha(value: str | None) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "GITHUB_API_ROOT",
    "GitHubPullRequestMetadata",
    "GitHubWatchdogAppReadClient",
    "WatchdogPullRequestHeadState",
    "WatchdogPullRequestHeadValidation",
    "create_github_app_jwt",
    "validate_pull_request_head",
]
