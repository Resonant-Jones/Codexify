"""Strict environment validation for the memory MCP adapter.

Every rule here fails closed. A misconfigured adapter raises
:class:`~guardian.mcp_memory.errors.ConfigurationError` at startup instead of
degrading into a partially-working state, because "silently unauthenticated" and
"silently scoped to the wrong thing" are both worse than refusing to start.

Two invariants deserve emphasis:

* **No implicit port default.** ``CODEXIFY_MCP_BASE_URL`` is required. Port 8000
  on this host belongs to Whoosh'd, not Guardian, so a default would actively
  point the adapter at the wrong service.
* **No identity override.** ``CODEXIFY_MCP_USER_ID`` is *rejected* when
  populated rather than ignored, so an operator who sets it gets a clear error
  instead of believing an inert variable is in effect.
"""

from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from .errors import ConfigurationError

#: Environment variable naming Guardian's loopback origin.
ENV_BASE_URL = "CODEXIFY_MCP_BASE_URL"
#: Preferred credential; falls back to :data:`ENV_GUARDIAN_API_KEY`.
ENV_API_KEY = "CODEXIFY_MCP_API_KEY"
ENV_GUARDIAN_API_KEY = "GUARDIAN_API_KEY"
ENV_TIMEOUT = "CODEXIFY_MCP_TIMEOUT"
#: Explicitly unsupported. Rejected when populated.
ENV_USER_ID = "CODEXIFY_MCP_USER_ID"
#: Guardian auth mode / exposure mode, read only to refuse unsupported modes.
ENV_AUTH_MODE = "GUARDIAN_AUTH_MODE"
ENV_EXPOSURE_MODE = "GUARDIAN_EXPOSURE_MODE"

DEFAULT_TIMEOUT = 10.0
MIN_TIMEOUT = 0.1
MAX_TIMEOUT = 120.0

#: Auth modes in which Guardian rejects static API keys and demands a session
#: token (``guardian/core/dependencies.py``). v1 only supports local auth.
_REMOTE_AUTH_MODES = frozenset(
    {"remote", "cloud", "hosted", "public", "prod", "production"}
)
_PUBLIC_EXPOSURE_MODE = "public_allowlist"

_LOOPBACK_HOSTNAMES = frozenset({"localhost", "localhost.localdomain"})


def _is_loopback_host(host: str) -> bool:
    """Return True only for a literal loopback destination.

    ``localhost`` is accepted as an explicit operator choice. Any other name
    must resolve *textually* to a loopback IP literal; the adapter deliberately
    does not perform DNS resolution at startup, so a remote name that merely
    happens to point at 127.0.0.1 is still rejected.
    """
    if not host:
        return False
    hostname = host.strip().lower()
    if hostname in _LOOPBACK_HOSTNAMES:
        return True
    candidate = hostname
    if candidate.startswith("[") and candidate.endswith("]"):
        candidate = candidate[1:-1]
    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        return False


@dataclass(frozen=True)
class MCPConfig:
    """Validated, immutable adapter configuration."""

    base_url: str
    api_key: str
    timeout: float

    @property
    def origin(self) -> str:
        """Scheme + host + port, with no trailing slash."""
        return self.base_url.rstrip("/")


def _validate_base_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ConfigurationError(
            f"{ENV_BASE_URL} is required and has no default. Set it to the "
            "loopback origin of your running Codexify Guardian, for example "
            "http://127.0.0.1:8010. Port 8000 is not assumed to be Guardian."
        )
    try:
        parts = urlsplit(value)
    except ValueError as exc:  # pragma: no cover - urlsplit rarely raises
        raise ConfigurationError(f"{ENV_BASE_URL} is not a valid URL: {exc}") from None

    if parts.scheme != "http":
        raise ConfigurationError(
            f"{ENV_BASE_URL} must use http on loopback; got scheme "
            f"{parts.scheme or '(none)'!r}. This adapter does not terminate TLS."
        )
    if parts.username or parts.password:
        raise ConfigurationError(
            f"{ENV_BASE_URL} must not embed credentials. Use {ENV_API_KEY}."
        )
    if parts.query or parts.fragment:
        raise ConfigurationError(
            f"{ENV_BASE_URL} must not carry a query string or fragment."
        )
    if parts.path not in ("", "/"):
        raise ConfigurationError(
            f"{ENV_BASE_URL} must be a bare origin without a path prefix; got "
            f"{parts.path!r}."
        )
    try:
        hostname = parts.hostname
    except ValueError as exc:
        raise ConfigurationError(f"{ENV_BASE_URL} has an invalid host: {exc}") from None
    if not _is_loopback_host(hostname or ""):
        raise ConfigurationError(
            f"{ENV_BASE_URL} must be a loopback destination (127.0.0.1, ::1, or "
            f"localhost); got {hostname!r}. This adapter refuses to send memory "
            "credentials off-host."
        )
    return value.rstrip("/")


def _validate_api_key(env: dict[str, str]) -> str:
    key = (env.get(ENV_API_KEY) or env.get(ENV_GUARDIAN_API_KEY) or "").strip()
    if not key:
        raise ConfigurationError(
            f"{ENV_API_KEY} is required (or set {ENV_GUARDIAN_API_KEY}). The "
            "adapter has no default credential."
        )
    return key


def _validate_timeout(env: dict[str, str]) -> float:
    raw = (env.get(ENV_TIMEOUT) or "").strip()
    if not raw:
        return DEFAULT_TIMEOUT
    try:
        value = float(raw)
    except ValueError:
        raise ConfigurationError(
            f"{ENV_TIMEOUT} must be a number of seconds; got {raw!r}."
        ) from None
    if not (MIN_TIMEOUT <= value <= MAX_TIMEOUT):
        raise ConfigurationError(
            f"{ENV_TIMEOUT} must be between {MIN_TIMEOUT} and {MAX_TIMEOUT} "
            f"seconds; got {value}."
        )
    return value


def _reject_identity_override(env: dict[str, str]) -> None:
    raw = env.get(ENV_USER_ID)
    if raw is not None and raw.strip():
        raise ConfigurationError(
            f"{ENV_USER_ID} is not supported and must be unset. Guardian "
            "resolves account identity from the API key; this adapter has no "
            "mechanism to override it, so the variable was rejected rather "
            "than silently ignored."
        )


def _reject_unsupported_auth_mode(env: dict[str, str]) -> None:
    mode = (env.get(ENV_AUTH_MODE) or "local").strip().lower()
    exposure = (env.get(ENV_EXPOSURE_MODE) or "").strip().lower()
    if mode in _REMOTE_AUTH_MODES or exposure == _PUBLIC_EXPOSURE_MODE:
        raise ConfigurationError(
            "Guardian is configured in an auth mode that rejects static API "
            f"keys (GUARDIAN_AUTH_MODE={mode!r}, GUARDIAN_EXPOSURE_MODE="
            f"{exposure!r}). v1 supports local API-key auth only; session-token "
            "auth is out of scope."
        )


def load_config(env: dict[str, str] | None = None) -> MCPConfig:
    """Validate the environment and return an :class:`MCPConfig`.

    Raises :class:`ConfigurationError` on any violation. Never returns a
    partially-valid configuration.
    """
    source = dict(os.environ if env is None else env)
    _reject_identity_override(source)
    _reject_unsupported_auth_mode(source)
    base_url = _validate_base_url(source.get(ENV_BASE_URL, ""))
    api_key = _validate_api_key(source)
    timeout = _validate_timeout(source)
    return MCPConfig(base_url=base_url, api_key=api_key, timeout=timeout)


__all__ = [
    "DEFAULT_TIMEOUT",
    "ENV_API_KEY",
    "ENV_AUTH_MODE",
    "ENV_BASE_URL",
    "ENV_EXPOSURE_MODE",
    "ENV_GUARDIAN_API_KEY",
    "ENV_TIMEOUT",
    "ENV_USER_ID",
    "MAX_TIMEOUT",
    "MIN_TIMEOUT",
    "MCPConfig",
    "load_config",
]
