"""Fixed-host OAuth protocol adapters; no persistence, grants or ambient secrets.

Callers own authenticated, single-use state, connection generation/CAS, encrypted
storage and explicit resource selection. Notion read-content-only capability is
an operator registration prerequisite; its token response cannot prove it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode, urlsplit
from uuid import UUID

import requests

from guardian.connections.github.service import normalize_repository

MAX_RESPONSE_BYTES = 262144
MAX_ITEMS = 100
TIMEOUT = 15
GITHUB_VERSION = "2026-03-10"


class OAuthProviderError(RuntimeError):
    error_code = "oauth_provider_error"

    def __init__(self) -> None:
        super().__init__("OAuth provider request could not be completed")


def _string(value: Any, maximum: int = 8192) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > maximum
        or any(ord(c) < 32 or ord(c) == 127 for c in value)
    ):
        raise OAuthProviderError()
    return value


def _integer(value: Any) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 < value <= 2**63 - 1
    ):
        raise OAuthProviderError()
    return value


@dataclass(frozen=True)
class OAuthConfig:
    provider: str
    client_id: str
    client_secret: str = field(repr=False)
    redirect_uri: str

    def __post_init__(self) -> None:
        if self.provider not in {"github", "notion"}:
            raise OAuthProviderError()
        _string(self.client_id, 255)
        _string(self.client_secret)
        _string(self.redirect_uri, 2048)
        try:
            parsed = urlsplit(self.redirect_uri)
            valid = parsed.scheme == "https" or (
                parsed.scheme == "http"
                and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
            )
            if (
                not valid
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.fragment
                or parsed.query
            ):
                raise OAuthProviderError()
            parsed.port
        except (ValueError, TypeError):
            raise OAuthProviderError() from None


@dataclass(frozen=True)
class OAuthTokens:
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    expires_in: int | None = None
    refresh_token_expires_in: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def authorization_url(
    config: OAuthConfig, *, state: str, code_challenge: str | None = None
) -> str:
    parameters = {
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "state": _string(state, 1024),
        "response_type": "code",
    }
    if config.provider == "github":
        if not isinstance(code_challenge, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{43}", code_challenge
        ):
            raise OAuthProviderError()
        parameters.update(
            code_challenge=code_challenge,
            code_challenge_method="S256",
            scope="offline_access",
        )
        base = "https://github.com/login/oauth/authorize"
    else:
        parameters["owner"] = "user"
        base = "https://api.notion.com/v1/oauth/authorize"
    return base + "?" + urlencode(parameters)


def _request(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    # Hosts/paths are selected only by the narrow exported protocol operations.
    try:
        with requests.request(
            method, url, timeout=TIMEOUT, allow_redirects=False, stream=True, **kwargs
        ) as response:
            if response.status_code != 200:
                raise OAuthProviderError()
            raw = bytearray()
            for chunk in response.iter_content(chunk_size=8192):
                raw.extend(chunk)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise OAuthProviderError()
            result = json.loads(raw)
            if not isinstance(result, dict) or "error" in result:
                raise OAuthProviderError()
            return result
    except Exception:
        # Never chain HTTP exceptions, response bodies or token-bearing URLs.
        raise OAuthProviderError() from None


def _tokens(config: OAuthConfig, data: dict[str, Any], *, initial: bool) -> OAuthTokens:
    access = _string(data.get("access_token"))
    refresh = _string(data.get("refresh_token"))
    if str(data.get("token_type", "bearer")).lower() != "bearer":
        raise OAuthProviderError()
    expires = data.get("expires_in")
    refresh_expires = data.get("refresh_token_expires_in")
    if expires is not None:
        expires = _integer(expires)
    if refresh_expires is not None:
        refresh_expires = _integer(refresh_expires)
    metadata: dict[str, Any] = {}
    if config.provider == "github":
        # A classic OAuth broad-scope token is not an acceptable substitute.
        if (
            data.get("scope", "") != ""
            or expires is None
            or refresh_expires is None
            or not access.startswith("ghu_")
            or not refresh.startswith("ghr_")
        ):
            raise OAuthProviderError()
    else:
        for key in ("workspace_id", "bot_id"):
            value = data.get(key)
            if value is None and not initial:
                continue
            try:
                metadata[key] = str(UUID(_string(value, 36)))
            except ValueError:
                raise OAuthProviderError() from None
    return OAuthTokens(access, refresh, expires, refresh_expires, metadata)


def _exchange(
    config: OAuthConfig, parameters: dict[str, str], *, initial: bool
) -> OAuthTokens:
    headers = {"Accept": "application/json"}
    if config.provider == "github":
        parameters = {
            **parameters,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
        }
        data = _request(
            "POST",
            "https://github.com/login/oauth/access_token",
            headers=headers,
            data=parameters,
        )
    else:
        data = _request(
            "POST",
            "https://api.notion.com/v1/oauth/token",
            headers=headers,
            auth=(config.client_id, config.client_secret),
            json=parameters,
        )
    return _tokens(config, data, initial=initial)


def exchange_code(
    config: OAuthConfig, *, code: str, code_verifier: str | None = None
) -> OAuthTokens:
    parameters = {
        "grant_type": "authorization_code",
        "code": _string(code),
        "redirect_uri": config.redirect_uri,
    }
    if config.provider == "github":
        if not isinstance(code_verifier, str) or not re.fullmatch(
            r"[A-Za-z0-9._~-]{43,128}", code_verifier
        ):
            raise OAuthProviderError()
        parameters["code_verifier"] = code_verifier
    return _exchange(config, parameters, initial=True)


def refresh_tokens(config: OAuthConfig, *, refresh_token: str) -> OAuthTokens:
    return _exchange(
        config,
        {"grant_type": "refresh_token", "refresh_token": _string(refresh_token)},
        initial=False,
    )


def _github_get(access_token: str, path: str, **params: Any) -> dict[str, Any]:
    return _request(
        "GET",
        "https://api.github.com" + path,
        params=params,
        headers={
            "Authorization": "Bearer " + _string(access_token),
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_VERSION,
        },
    )


def _login(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", value
    ):
        raise OAuthProviderError()
    return value


def github_identity(access_token: str) -> dict[str, Any]:
    data = _github_get(access_token, "/user")
    return {"id": _integer(data.get("id")), "login": _login(data.get("login"))}


def validate_github_installation(installation: dict[str, Any]) -> None:
    """Reject broad/write-capable installation before choosing its resources."""
    permissions = installation.get("permissions")
    if (
        not isinstance(permissions, dict)
        or len(permissions) > 100
        or permissions.get("issues") != "read"
        or permissions.get("pull_requests") != "read"
        or any(
            not isinstance(value, str) or value not in {"read", "none"}
            for value in permissions.values()
        )
        or installation.get("suspended_at") is not None
    ):
        raise OAuthProviderError()


def _page(data: dict[str, Any], key: str) -> tuple[list[Any], bool]:
    items = data.get(key)
    total = data.get("total_count")
    if (
        not isinstance(items, list)
        or len(items) > MAX_ITEMS
        or isinstance(total, bool)
        or not isinstance(total, int)
        or total < len(items)
    ):
        raise OAuthProviderError()
    return items, total > len(items)


def github_installations(access_token: str) -> dict[str, Any]:
    """One bounded page, explicitly incomplete; discovery never grants access."""
    items, incomplete = _page(
        _github_get(access_token, "/user/installations", per_page=MAX_ITEMS, page=1),
        "installations",
    )
    projected = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("account"), dict):
            raise OAuthProviderError()
        validate_github_installation(item)
        if item.get("repository_selection") not in {"all", "selected"}:
            raise OAuthProviderError()
        permissions = item["permissions"]
        if any(not isinstance(k, str) or len(k) > 100 for k in permissions):
            raise OAuthProviderError()
        projected.append(
            {
                "id": _integer(item.get("id")),
                "account_login": _login(item["account"].get("login")),
                "repository_selection": item["repository_selection"],
                "permissions": dict(permissions),
            }
        )
    return {"installations": projected, "incomplete": incomplete}


def github_installation_repositories(
    access_token: str, installation_id: int
) -> dict[str, Any]:
    identifier = _integer(installation_id)
    items, incomplete = _page(
        _github_get(
            access_token,
            f"/user/installations/{identifier}/repositories",
            per_page=MAX_ITEMS,
            page=1,
        ),
        "repositories",
    )
    projected = []
    for item in items:
        if not isinstance(item, dict):
            raise OAuthProviderError()
        try:
            repository = normalize_repository(item.get("full_name"))
        except Exception:
            raise OAuthProviderError() from None
        projected.append({"id": _integer(item.get("id")), "full_name": repository})
    return {"repositories": projected, "incomplete": incomplete}
