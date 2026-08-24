"""Focused proof for the Watchdog GitHub App read-only authentication seam."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from guardian.watchdog.contracts import (
    WatchdogGitHubAppError,
    WatchdogGitHubAppErrorCode,
)
from guardian.watchdog.github_app import (
    GITHUB_API_VERSION,
    GITHUB_APP_JWT_LIFETIME_SECONDS,
    GITHUB_REQUEST_TIMEOUT_SECONDS,
    GITHUB_WATCHDOG_USER_AGENT,
    GitHubWatchdogAppReadClient,
    WatchdogPullRequestHeadState,
    create_github_app_jwt,
    validate_pull_request_head,
)

FROZEN_NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)
WEBHOOK_SECRET = "webhook-secret-is-not-an-app-credential"
INSTALLATION_TOKEN = "ephemeral-installation-token"


@dataclass
class FakeResponse:
    """Minimal request-boundary response with no body-string access."""

    status_code: int
    payload: object
    headers: dict[str, str] = field(default_factory=dict)

    def json(self) -> object:
        return self.payload


class RecordingSession:
    """Records exact request semantics while supplying predetermined responses."""

    def __init__(
        self,
        *,
        post_responses: list[FakeResponse] | None = None,
        get_responses: list[FakeResponse] | None = None,
    ) -> None:
        self.post_responses = list(post_responses or [])
        self.get_responses = list(get_responses or [])
        self.calls: list[dict[str, Any]] = []

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        timeout: int,
    ) -> FakeResponse:
        self.calls.append(
            {"method": "POST", "url": url, "headers": headers, "timeout": timeout}
        )
        return self.post_responses.pop(0)

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str],
        timeout: int,
    ) -> FakeResponse:
        self.calls.append(
            {"method": "GET", "url": url, "headers": headers, "timeout": timeout}
        )
        return self.get_responses.pop(0)


@pytest.fixture()
def app_private_key() -> str:
    """Generate a test-only key at runtime so no key material enters the repo."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("utf-8")


def _settings(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "CODEXIFY_GITHUB_WATCHDOG_APP_ID": "123456",
        "CODEXIFY_GITHUB_WATCHDOG_APP_PRIVATE_KEY": None,
        "CODEXIFY_GITHUB_WATCHDOG_WEBHOOK_SECRET": WEBHOOK_SECRET,
        "CODEXIFY_LOCAL_ONLY_MODE": False,
        "CODEXIFY_EGRESS_ALLOWLIST": "github",
        "ALLOW_CLOUD_PROVIDERS": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _installation_token_response() -> FakeResponse:
    return FakeResponse(
        status_code=201,
        payload={
            "token": INSTALLATION_TOKEN,
            "expires_at": "2026-08-23T13:00:00Z",
        },
    )


def _pull_request_response(*, head_sha: str = "a" * 40) -> FakeResponse:
    return FakeResponse(
        status_code=200,
        payload={
            "number": 17,
            "title": "Watchdog boundary",
            "state": "open",
            "draft": False,
            "user": {"id": 7, "login": "octocat"},
            "base": {
                "sha": "b" * 40,
                "repo": {"id": 99, "full_name": "octo/example"},
            },
            "head": {
                "sha": head_sha,
                "repo": {
                    "id": 100,
                    "full_name": "forker/example",
                    "owner": {"id": 8, "login": "forker"},
                },
            },
        },
    )


def _client(
    *,
    settings: SimpleNamespace,
    session: RecordingSession,
) -> GitHubWatchdogAppReadClient:
    return GitHubWatchdogAppReadClient(
        settings=settings,
        installation_id="42",
        session=session,
        now_factory=lambda: FROZEN_NOW,
    )


def test_missing_app_id_fails_closed_before_network(
    app_private_key: str,
) -> None:
    session = RecordingSession()
    client = _client(
        settings=_settings(
            CODEXIFY_GITHUB_WATCHDOG_APP_ID=None,
            CODEXIFY_GITHUB_WATCHDOG_APP_PRIVATE_KEY=app_private_key,
        ),
        session=session,
    )

    with pytest.raises(WatchdogGitHubAppError) as error:
        client.get_pull_request("octo/example", 17)

    assert error.value.code is WatchdogGitHubAppErrorCode.CONFIGURATION_MISSING
    assert session.calls == []


def test_missing_private_key_fails_closed_before_network() -> None:
    session = RecordingSession()
    client = _client(settings=_settings(), session=session)

    with pytest.raises(WatchdogGitHubAppError) as error:
        client.get_pull_request("octo/example", 17)

    assert error.value.code is WatchdogGitHubAppErrorCode.CONFIGURATION_MISSING
    assert session.calls == []


def test_malformed_private_key_is_sanitized_and_never_sent() -> None:
    invalid_material = "invalid-test-private-key-material"
    session = RecordingSession()
    client = _client(
        settings=_settings(CODEXIFY_GITHUB_WATCHDOG_APP_PRIVATE_KEY=invalid_material),
        session=session,
    )

    with pytest.raises(WatchdogGitHubAppError) as error:
        client.get_pull_request("octo/example", 17)

    assert error.value.code is WatchdogGitHubAppErrorCode.PRIVATE_KEY_INVALID
    assert invalid_material not in str(error.value)
    assert session.calls == []


def test_app_jwt_uses_rs256_issuer_and_bounded_lifetime(
    app_private_key: str,
) -> None:
    encoded = create_github_app_jwt(
        app_id="123456",
        private_key=app_private_key,
        now=FROZEN_NOW,
    )

    header = jwt.get_unverified_header(encoded)
    claims = jwt.decode(encoded, options={"verify_signature": False})

    assert header["alg"] == "RS256"
    assert claims["iss"] == "123456"
    assert claims["iat"] < int(FROZEN_NOW.timestamp())
    assert claims["exp"] - int(FROZEN_NOW.timestamp()) == GITHUB_APP_JWT_LIFETIME_SECONDS
    assert claims["exp"] - claims["iat"] <= 10 * 60


def test_installation_exchange_and_pr_read_use_separate_ephemeral_credentials(
    app_private_key: str,
) -> None:
    session = RecordingSession(
        post_responses=[_installation_token_response()],
        get_responses=[_pull_request_response()],
    )
    client = _client(
        settings=_settings(CODEXIFY_GITHUB_WATCHDOG_APP_PRIVATE_KEY=app_private_key),
        session=session,
    )

    pull_request = client.get_pull_request("octo/example", 17)

    post_call, get_call = session.calls
    app_jwt = post_call["headers"]["Authorization"].removeprefix("Bearer ")
    assert post_call["method"] == "POST"
    assert post_call["url"].endswith("/app/installations/42/access_tokens")
    assert app_jwt != WEBHOOK_SECRET
    assert jwt.decode(app_jwt, options={"verify_signature": False})["iss"] == "123456"
    assert get_call["method"] == "GET"
    assert get_call["url"].endswith("/repos/octo/example/pulls/17")
    assert get_call["headers"]["Authorization"] == f"Bearer {INSTALLATION_TOKEN}"
    for call in (post_call, get_call):
        assert call["headers"]["Accept"] == "application/vnd.github+json"
        assert call["headers"]["X-GitHub-Api-Version"] == GITHUB_API_VERSION
        assert call["headers"]["User-Agent"] == GITHUB_WATCHDOG_USER_AGENT
        assert call["timeout"] == GITHUB_REQUEST_TIMEOUT_SECONDS
    assert not hasattr(client, "_installation_token")
    assert pull_request.repository_id == "99"
    assert pull_request.repository_full_name == "octo/example"
    assert pull_request.pull_request_number == 17
    assert pull_request.title == "Watchdog boundary"
    assert pull_request.state == "open"
    assert pull_request.base_sha == "b" * 40
    assert pull_request.head_sha == "a" * 40
    assert pull_request.author_id == "7"
    assert pull_request.author_login == "octocat"
    assert pull_request.draft is False
    assert pull_request.head_repository_id == "100"
    assert pull_request.head_repository_full_name == "forker/example"
    assert pull_request.head_repository_owner_id == "8"
    assert pull_request.head_repository_owner_login == "forker"
    assert pull_request.head_is_fork is True


def test_installation_token_expiry_is_typed_and_not_cached(
    app_private_key: str,
) -> None:
    session = RecordingSession(post_responses=[_installation_token_response()])
    client = _client(
        settings=_settings(CODEXIFY_GITHUB_WATCHDOG_APP_PRIVATE_KEY=app_private_key),
        session=session,
    )

    installation_token = client._exchange_installation_token("test-app-jwt")

    assert installation_token.installation_id == "42"
    assert installation_token.expires_at == datetime(
        2026, 8, 23, 13, 0, tzinfo=timezone.utc
    )
    assert INSTALLATION_TOKEN not in repr(installation_token)
    assert not hasattr(client, "_installation_token")


def test_expected_head_validation_distinguishes_exact_stale_and_invalid(
    app_private_key: str,
) -> None:
    session = RecordingSession(
        post_responses=[_installation_token_response()],
        get_responses=[_pull_request_response()],
    )
    pull_request = _client(
        settings=_settings(CODEXIFY_GITHUB_WATCHDOG_APP_PRIVATE_KEY=app_private_key),
        session=session,
    ).get_pull_request("octo/example", 17)

    exact = validate_pull_request_head(pull_request, "a" * 40)
    stale = validate_pull_request_head(pull_request, "c" * 40)
    invalid = validate_pull_request_head(pull_request, None)

    assert exact.state is WatchdogPullRequestHeadState.EXACT
    assert exact.matches is True
    assert exact.error_code is None
    assert stale.state is WatchdogPullRequestHeadState.STALE
    assert stale.matches is False
    assert stale.error_code is WatchdogGitHubAppErrorCode.EXPECTED_HEAD_MISMATCH
    assert invalid.state is WatchdogPullRequestHeadState.MISSING_OR_INVALID
    assert (
        invalid.error_code
        is WatchdogGitHubAppErrorCode.EXPECTED_HEAD_MISSING_OR_INVALID
    )


def test_unknown_installation_and_rate_limit_are_bounded(
    app_private_key: str,
) -> None:
    unauthorized_session = RecordingSession(
        post_responses=[FakeResponse(status_code=404, payload={})]
    )
    unauthorized_client = _client(
        settings=_settings(CODEXIFY_GITHUB_WATCHDOG_APP_PRIVATE_KEY=app_private_key),
        session=unauthorized_session,
    )

    with pytest.raises(WatchdogGitHubAppError) as unauthorized:
        unauthorized_client.get_pull_request("octo/example", 17)

    assert (
        unauthorized.value.code
        is WatchdogGitHubAppErrorCode.INSTALLATION_UNKNOWN_OR_UNAUTHORIZED
    )

    rate_limited_session = RecordingSession(
        post_responses=[_installation_token_response()],
        get_responses=[
            FakeResponse(
                status_code=403,
                payload={},
                headers={"X-RateLimit-Remaining": "0"},
            )
        ],
    )
    rate_limited_client = _client(
        settings=_settings(CODEXIFY_GITHUB_WATCHDOG_APP_PRIVATE_KEY=app_private_key),
        session=rate_limited_session,
    )

    with pytest.raises(WatchdogGitHubAppError) as rate_limited:
        rate_limited_client.get_pull_request("octo/example", 17)

    assert rate_limited.value.code is WatchdogGitHubAppErrorCode.GITHUB_API_RATE_LIMITED


def test_egress_gate_blocks_before_credentials_or_network(
    app_private_key: str,
) -> None:
    session = RecordingSession()
    client = _client(
        settings=_settings(
            CODEXIFY_GITHUB_WATCHDOG_APP_PRIVATE_KEY=app_private_key,
            CODEXIFY_LOCAL_ONLY_MODE=True,
        ),
        session=session,
    )

    with pytest.raises(WatchdogGitHubAppError) as error:
        client.get_pull_request("octo/example", 17)

    assert error.value.code is WatchdogGitHubAppErrorCode.EGRESS_DENIED
    assert session.calls == []


def test_repository_facing_client_exposes_only_get_pull_request(
    app_private_key: str,
) -> None:
    client = _client(
        settings=_settings(CODEXIFY_GITHUB_WATCHDOG_APP_PRIVATE_KEY=app_private_key),
        session=RecordingSession(),
    )

    public_callables = {
        name for name in dir(client) if not name.startswith("_") and callable(getattr(client, name))
    }

    assert public_callables == {"get_pull_request"}
