"""Allowlisted, authenticated HTTP client for the memory MCP adapter.

This is the adapter's only data path. It enforces four structural properties
that the rest of the package relies on:

1. **Fixed endpoint allowlist.** Every upstream call is one of a small set of
   named operations with a hardcoded path template. There is no API through
   which a tool caller can supply a URL, an HTTP method, or a header.
2. **GET only.** The allowlist stores method per operation and every entry is
   ``GET``; a mutating method is not representable.
3. **Origin gate.** The first upstream call is an *unauthenticated* health
   probe. Credentials are attached only after the listener proves it is
   Guardian, so a misconfigured ``CODEXIFY_MCP_BASE_URL`` cannot leak the API
   key to an unrelated local service.
4. **No ambient authority.** The client imports no Guardian service, no ORM,
   no vector store, and never opens a database handle.

The adapter deliberately uses the repository's own ``httpx`` rather than
``httpx2`` (which MCP v2 pulls in for its own transport). Both coexist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Mapping

import httpx

from .config import MCPConfig
from .errors import (
    ACCESS_DENIED,
    AUTH_REQUIRED,
    CONFLICT,
    GUARDIAN_TIMEOUT,
    GUARDIAN_UNREACHABLE,
    INVALID_REQUEST,
    NOT_FOUND,
    UNSUPPORTED_OPERATION,
    UPSTREAM_ERROR,
    UPSTREAM_RATE_LIMITED,
    WRONG_UPSTREAM,
    CodexifyMCPError,
)

# --- Endpoint allowlist -----------------------------------------------------
# Each entry is the single source of truth for what this adapter may ever call.
# Adding a row here is a deliberate contract change and must come with the
# corresponding security review.

HEALTH_PATH: Final = "/health"
VAULT_LIST_PATH: Final = "/api/memory-vault/items"
VAULT_CANONICAL_PATH: Final = "/api/memory-vault/items/canonical/{memory_id}"
MEMORY_SILO_PATH: Final = "/api/memory/{silo}"
FACT_CANDIDATES_PATH: Final = "/personal-facts/candidates"

#: Paths this adapter must never reach, regardless of configuration. Named
#: explicitly so the guard can assert against them in tests and at import time.
FORBIDDEN_PATH_FRAGMENTS: Final[tuple[str, ...]] = (
    "/api/retrieve",
    "/codexify/search",
    "/chat",
)

#: Guardian's health payload identifiers. ``service`` comes from
#: ``HealthServiceName`` in ``guardian/core/health_service.py``; ``/health`` is
#: the ``"core"`` service. A listener without these is not Guardian.
GUARDIAN_HEALTH_SERVICE: Final = "core"
GUARDIAN_HEALTH_STATUSES: Final[frozenset[str]] = frozenset({"ok", "degraded", "down"})

API_KEY_HEADER: Final = "X-API-Key"

#: Bounds required by the tool contract.
MAX_LIST_LIMIT: Final = 50
MAX_FACT_LIMIT: Final = 200
SUPPORTED_SILOS: Final[tuple[str, ...]] = ("ephemeral", "midterm", "longterm")


@dataclass(frozen=True)
class UpstreamResponse:
    """A successful, already-authenticated upstream GET."""

    status: int
    payload: Any
    path: str

    @property
    def source(self) -> str:
        return self.path


def _guard_path(path: str) -> None:
    """Reject any path that touches a forbidden upstream endpoint."""
    lowered = path.lower()
    for fragment in FORBIDDEN_PATH_FRAGMENTS:
        if fragment in lowered:
            raise CodexifyMCPError(
                UNSUPPORTED_OPERATION,
                "this operation is not part of the read-only v1 adapter surface",
            )


def _map_status(status: int, path: str) -> CodexifyMCPError | None:
    """Translate a non-2xx status into a structured error, if any."""
    if status < 400:
        return None
    if status == 401:
        return CodexifyMCPError(
            AUTH_REQUIRED,
            "Guardian rejected the configured API key. Check CODEXIFY_MCP_API_KEY "
            "(or GUARDIAN_API_KEY) against the running instance.",
        )
    if status == 403:
        return CodexifyMCPError(
            ACCESS_DENIED,
            "Guardian denied access to this resource for the authenticated account.",
        )
    if status == 404:
        return CodexifyMCPError(
            NOT_FOUND,
            "Guardian returned 404 for "
            f"{path}. The resource may not exist, or the router may be "
            "quarantined by supported-profile policy "
            "(CODEXIFY_ENABLE_MEMORY_ROUTES / CODEXIFY_ENABLE_MEMORY_VAULT_ROUTES, "
            "or CODEXIFY_BETA_CORE_ONLY). This adapter does not change runtime policy.",
        )
    if status == 409:
        return CodexifyMCPError(CONFLICT, f"Guardian reported a conflict for {path}.")
    if status == 429:
        return CodexifyMCPError(
            UPSTREAM_RATE_LIMITED, "Guardian rate-limited this request."
        )
    return CodexifyMCPError(
        UPSTREAM_ERROR, f"Guardian returned HTTP {status} for {path}."
    )


def validate_memory_id(memory_id: str) -> str:
    """Validate a canonical memory id as a single safe path segment.

    Rejects path separators, traversal, query/fragment markers and empty input
    so an id can never widen the request beyond the intended endpoint.
    """
    value = (memory_id or "").strip()
    if not value:
        raise CodexifyMCPError(INVALID_REQUEST, "memory_id must not be empty.")
    if len(value) > 200:
        raise CodexifyMCPError(INVALID_REQUEST, "memory_id is too long.")
    for bad in ("/", "\\", "?", "#", "&", "%", " ", "\t", "\n"):
        if bad in value:
            raise CodexifyMCPError(
                INVALID_REQUEST,
                "memory_id must be a single path segment without separators or "
                "query characters.",
            )
    if value in (".", "..") or value.startswith(".."):
        raise CodexifyMCPError(
            INVALID_REQUEST, "memory_id must not be a relative path segment."
        )
    return value


def validate_silo(silo: str) -> str:
    """Validate a memory silo name against the supported vocabulary."""
    value = (silo or "").strip().lower()
    if value not in SUPPORTED_SILOS:
        raise CodexifyMCPError(
            INVALID_REQUEST,
            f"silo must be one of {', '.join(SUPPORTED_SILOS)}; got {silo!r}.",
        )
    return value


def validate_limit(limit: int, *, maximum: int = MAX_LIST_LIMIT) -> int:
    """Bound a requested page size."""
    try:
        value = int(limit)
    except (TypeError, ValueError):
        raise CodexifyMCPError(INVALID_REQUEST, "limit must be an integer.") from None
    if value < 1:
        raise CodexifyMCPError(INVALID_REQUEST, "limit must be at least 1.")
    return min(value, maximum)


def validate_offset(offset: int) -> int:
    """Validate a non-negative pagination offset."""
    try:
        value = int(offset)
    except (TypeError, ValueError):
        raise CodexifyMCPError(INVALID_REQUEST, "offset must be an integer.") from None
    if value < 0:
        raise CodexifyMCPError(INVALID_REQUEST, "offset must be non-negative.")
    return value


class MemoryClient:
    """Authenticated, allowlisted GET client for Guardian memory reads."""

    def __init__(self, config: MCPConfig, *, transport: Any | None = None) -> None:
        self._config = config
        self._origin_verified = False
        self._client = httpx.AsyncClient(
            base_url=config.origin,
            timeout=config.timeout,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )

    # -- lifecycle ---------------------------------------------------------
    @property
    def origin(self) -> str:
        """The configured Guardian origin (never includes credentials)."""
        return self._config.origin

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "MemoryClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    # -- origin gate -------------------------------------------------------
    @property
    def origin_verified(self) -> bool:
        return self._origin_verified

    async def verify_origin(self) -> dict[str, Any]:
        """Probe ``/health`` *without* credentials and verify Guardian identity.

        Returns the parsed health payload on success. Raises
        :class:`CodexifyMCPError` with ``wrong_upstream`` or
        ``guardian_unreachable`` otherwise. The result is cached so a later
        failure never silently re-probes while carrying the API key.
        """
        if self._origin_verified:
            return {}
        try:
            response = await self._client.get(
                HEALTH_PATH, headers={}  # deliberately unauthenticated
            )
        except httpx.TimeoutException as exc:
            raise CodexifyMCPError(
                GUARDIAN_TIMEOUT,
                f"Guardian did not answer {HEALTH_PATH} within "
                f"{self._config.timeout}s.",
                warnings=[type(exc).__name__],
            ) from None
        except httpx.HTTPError as exc:
            raise CodexifyMCPError(
                GUARDIAN_UNREACHABLE,
                f"Could not reach Guardian at {self._config.origin}.",
                warnings=[type(exc).__name__],
            ) from None

        try:
            payload = response.json()
        except ValueError:
            raise CodexifyMCPError(
                WRONG_UPSTREAM,
                "The configured origin answered, but not with a Guardian health "
                "payload. No API key was sent. Confirm CODEXIFY_MCP_BASE_URL "
                "points at Codexify Guardian and not another local service.",
            ) from None

        if not isinstance(payload, Mapping):
            raise CodexifyMCPError(
                WRONG_UPSTREAM,
                "Guardian health payload was not a JSON object. No API key was sent.",
            )
        if payload.get("service") != GUARDIAN_HEALTH_SERVICE:
            raise CodexifyMCPError(
                WRONG_UPSTREAM,
                "The configured origin is not Codexify Guardian "
                f"(expected health service {GUARDIAN_HEALTH_SERVICE!r}, got "
                f"{payload.get('service')!r}). No API key was sent.",
            )
        status = payload.get("status")
        if status not in GUARDIAN_HEALTH_STATUSES:
            raise CodexifyMCPError(
                WRONG_UPSTREAM,
                f"Guardian health reported an unrecognised status {status!r}. "
                "No API key was sent.",
            )
        self._origin_verified = True
        return dict(payload)

    # -- request core ------------------------------------------------------
    async def _get(
        self, path: str, params: Mapping[str, Any] | None = None
    ) -> UpstreamResponse:
        _guard_path(path)
        # Credentials are attached only behind the origin gate.
        await self.verify_origin()
        headers = {API_KEY_HEADER: self._config.api_key}
        try:
            response = await self._client.get(path, params=params, headers=headers)
        except httpx.TimeoutException:
            raise CodexifyMCPError(
                GUARDIAN_TIMEOUT,
                f"Guardian did not answer {path} within {self._config.timeout}s.",
            ) from None
        except httpx.HTTPError as exc:
            raise CodexifyMCPError(
                GUARDIAN_UNREACHABLE,
                f"Could not reach Guardian at {self._config.origin}.",
                warnings=[type(exc).__name__],
            ) from None

        mapped = _map_status(response.status_code, path)
        if mapped is not None:
            raise mapped
        try:
            payload = response.json()
        except ValueError:
            raise CodexifyMCPError(
                UPSTREAM_ERROR, f"Guardian returned a non-JSON body for {path}."
            ) from None
        return UpstreamResponse(status=response.status_code, payload=payload, path=path)

    # -- allowlisted operations -------------------------------------------
    async def list_vault_items(
        self, params: Mapping[str, Any] | None = None
    ) -> UpstreamResponse:
        """``GET /api/memory-vault/items``."""
        return await self._get(VAULT_LIST_PATH, _clean_params(params))

    async def get_canonical_item(self, memory_id: str) -> UpstreamResponse:
        """``GET /api/memory-vault/items/canonical/{memory_id}``."""
        safe = validate_memory_id(memory_id)
        return await self._get(VAULT_CANONICAL_PATH.format(memory_id=safe))

    async def list_memory_silo(
        self,
        silo: str,
        *,
        limit: int = MAX_LIST_LIMIT,
        offset: int = 0,
    ) -> UpstreamResponse:
        """``GET /api/memory/{silo}``."""
        safe_silo = validate_silo(silo)
        return await self._get(
            MEMORY_SILO_PATH.format(silo=safe_silo),
            {"limit": validate_limit(limit), "offset": validate_offset(offset)},
        )

    async def list_fact_candidates(
        self,
        *,
        status: str | None = "candidate",
        limit: int = MAX_FACT_LIMIT,
        offset: int = 0,
    ) -> UpstreamResponse:
        """``GET /personal-facts/candidates``."""
        params: dict[str, Any] = {
            "limit": validate_limit(limit, maximum=MAX_FACT_LIMIT),
            "offset": validate_offset(offset),
        }
        if status is not None:
            params["status"] = status
        return await self._get(FACT_CANDIDATES_PATH, params)


def _clean_params(params: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Drop ``None`` values so optional filters are simply omitted."""
    if not params:
        return None
    cleaned = {k: v for k, v in params.items() if v is not None}
    return cleaned or None


__all__ = [
    "ACCESS_DENIED",
    "API_KEY_HEADER",
    "FACT_CANDIDATES_PATH",
    "FORBIDDEN_PATH_FRAGMENTS",
    "HEALTH_PATH",
    "MAX_FACT_LIMIT",
    "MAX_LIST_LIMIT",
    "MEMORY_SILO_PATH",
    "SUPPORTED_SILOS",
    "UpstreamResponse",
    "VAULT_CANONICAL_PATH",
    "VAULT_LIST_PATH",
    "MemoryClient",
    "validate_limit",
    "validate_memory_id",
    "validate_offset",
    "validate_silo",
]
