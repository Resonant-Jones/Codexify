"""Client boundary and Guardian origin-gate tests.

The security-critical property asserted here: **no request carrying the API key
is ever made until the listener has proven it is Guardian.**
"""

from __future__ import annotations

import httpx
import pytest

from guardian.mcp_memory.client import (
    FACT_CANDIDATES_PATH,
    FORBIDDEN_PATH_FRAGMENTS,
    MEMORY_SILO_PATH,
    VAULT_LIST_PATH,
    MemoryClient,
    validate_limit,
    validate_memory_id,
    validate_offset,
    validate_silo,
)
from guardian.mcp_memory.config import MCPConfig
from guardian.mcp_memory.errors import (
    ACCESS_DENIED,
    AUTH_REQUIRED,
    CONFLICT,
    GUARDIAN_TIMEOUT,
    GUARDIAN_UNREACHABLE,
    INVALID_REQUEST,
    NOT_FOUND,
    UPSTREAM_ERROR,
    UPSTREAM_RATE_LIMITED,
    WRONG_UPSTREAM,
    CodexifyMCPError,
)

from .conftest import GUARDIAN_HEALTH, WHOOSHD_HEALTH, make_client

# --- Origin gate ------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_preflight_is_sent_without_api_key() -> None:
    client, transport = make_client(lambda r: httpx.Response(200, json=GUARDIAN_HEALTH))
    await client.verify_origin()
    assert transport.paths() == ["/health"]
    assert transport.keys_sent() == [None], "preflight must be unauthenticated"
    await client.aclose()


@pytest.mark.asyncio
async def test_guardian_health_unlocks_credentials() -> None:
    client, transport = make_client(lambda r: httpx.Response(200, json=GUARDIAN_HEALTH))
    await client.list_vault_items({"limit": 1})
    # First request unauthenticated, second authenticated.
    assert transport.keys_sent() == [None, "secret-key"]
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        WHOOSHD_HEALTH,
        {"ok": True},
        {"status": "ok"},
        {"service": "vector", "status": "ok"},
        {"service": "core", "status": "weird"},
    ],
    ids=["whooshd", "no-service", "no-service-alt", "wrong-service", "bad-status"],
)
async def test_non_guardian_health_rejected_without_sending_key(body: dict) -> None:
    client, transport = make_client(lambda r: httpx.Response(200, json=body))
    with pytest.raises(CodexifyMCPError) as exc:
        await client.list_vault_items({"limit": 1})
    assert exc.value.code == WRONG_UPSTREAM
    assert transport.keys_sent() == [None], "API key must never be sent"
    await client.aclose()


@pytest.mark.asyncio
async def test_non_json_health_rejected_without_sending_key() -> None:
    client, transport = make_client(
        lambda r: httpx.Response(200, text="<html>hi</html>")
    )
    with pytest.raises(CodexifyMCPError) as exc:
        await client.list_vault_items({"limit": 1})
    assert exc.value.code == WRONG_UPSTREAM
    assert transport.keys_sent() == [None]
    await client.aclose()


@pytest.mark.asyncio
async def test_json_array_health_rejected() -> None:
    client, _ = make_client(lambda r: httpx.Response(200, json=[1, 2, 3]))
    with pytest.raises(CodexifyMCPError) as exc:
        await client.list_vault_items({"limit": 1})
    assert exc.value.code == WRONG_UPSTREAM
    await client.aclose()


@pytest.mark.asyncio
async def test_origin_gate_result_is_cached() -> None:
    """A verified origin must not re-probe on every call."""
    client, transport = make_client(lambda r: httpx.Response(200, json=GUARDIAN_HEALTH))
    await client.list_vault_items({"limit": 1})
    await client.list_vault_items({"limit": 1})
    assert transport.paths().count("/health") == 1
    await client.aclose()


# --- Status mapping ---------------------------------------------------------


@pytest.mark.parametrize(
    "status,expected",
    [
        (401, AUTH_REQUIRED),
        (403, ACCESS_DENIED),
        (404, NOT_FOUND),
        (409, CONFLICT),
        (429, UPSTREAM_RATE_LIMITED),
        (500, UPSTREAM_ERROR),
        (503, UPSTREAM_ERROR),
    ],
)
@pytest.mark.asyncio
async def test_status_codes_map_to_structured_errors(
    status: int, expected: str
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        return httpx.Response(status, json={"detail": "x"})

    client, _ = make_client(handler)
    with pytest.raises(CodexifyMCPError) as exc:
        await client.list_vault_items({"limit": 1})
    assert exc.value.code == expected
    await client.aclose()


@pytest.mark.asyncio
async def test_connection_error_maps_to_guardian_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        raise httpx.ConnectError("refused", request=request)

    client, _ = make_client(handler)
    with pytest.raises(CodexifyMCPError) as exc:
        await client.list_vault_items({"limit": 1})
    assert exc.value.code == GUARDIAN_UNREACHABLE
    await client.aclose()


@pytest.mark.asyncio
async def test_timeout_maps_to_guardian_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        raise httpx.ReadTimeout("slow", request=request)

    client, _ = make_client(handler)
    with pytest.raises(CodexifyMCPError) as exc:
        await client.list_vault_items({"limit": 1})
    assert exc.value.code == GUARDIAN_TIMEOUT
    await client.aclose()


@pytest.mark.asyncio
async def test_health_timeout_maps_to_guardian_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    client, _ = make_client(handler)
    with pytest.raises(CodexifyMCPError) as exc:
        await client.verify_origin()
    assert exc.value.code == GUARDIAN_TIMEOUT
    await client.aclose()


@pytest.mark.asyncio
async def test_non_json_success_body_maps_to_upstream_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        return httpx.Response(200, text="not json")

    client, _ = make_client(handler)
    with pytest.raises(CodexifyMCPError) as exc:
        await client.list_vault_items({"limit": 1})
    assert exc.value.code == UPSTREAM_ERROR
    await client.aclose()


# --- Allowlist paths --------------------------------------------------------


@pytest.mark.asyncio
async def test_allowed_paths_are_exactly_the_read_surfaces() -> None:
    from .conftest import default_handler

    client, transport = make_client(default_handler)
    await client.list_vault_items({"limit": 1})
    await client.get_canonical_item("mem-1")
    await client.list_memory_silo("longterm", limit=1)
    await client.list_fact_candidates(limit=1)
    await client.aclose()
    assert transport.paths() == [
        "/health",
        VAULT_LIST_PATH,
        "/api/memory-vault/items/canonical/mem-1",
        "/api/memory/longterm",
        FACT_CANDIDATES_PATH,
    ]


@pytest.mark.asyncio
async def test_every_upstream_request_is_a_get() -> None:
    from .conftest import default_handler

    client, transport = make_client(default_handler)
    await client.list_vault_items({"limit": 1})
    await client.list_memory_silo("midterm", limit=1)
    await client.list_fact_candidates(limit=1)
    await client.aclose()
    assert {r.method for r in transport.requests} == {"GET"}


@pytest.mark.asyncio
async def test_no_forbidden_path_is_reachable() -> None:
    for fragment in FORBIDDEN_PATH_FRAGMENTS:
        assert fragment not in VAULT_LIST_PATH
        assert fragment not in MEMORY_SILO_PATH
        assert fragment not in FACT_CANDIDATES_PATH


# --- Redirects / proxies ----------------------------------------------------


@pytest.mark.asyncio
async def test_redirects_are_not_followed() -> None:
    """A redirect must surface as an error, never re-target the credential."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        if request.url.path == VAULT_LIST_PATH:
            return httpx.Response(307, headers={"Location": "http://evil.test/steal"})
        raise AssertionError("client followed a redirect")  # pragma: no cover

    client, _ = make_client(handler)
    with pytest.raises(CodexifyMCPError) as exc:
        await client.list_vault_items({"limit": 1})
    assert exc.value.code == UPSTREAM_ERROR  # 307 is <400, so body parse fails
    await client.aclose()


@pytest.mark.asyncio
async def test_client_does_not_inherit_proxy_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9")
    cfg = MCPConfig(base_url="http://127.0.0.1:8010", api_key="k", timeout=1.0)
    client = MemoryClient(cfg)
    assert client._client.trust_env is False
    assert client._client.follow_redirects is False
    await client.aclose()


# --- Validation helpers -----------------------------------------------------


@pytest.mark.parametrize(
    "bad", ["a/b", "..", ".", "../x", "a?b", "a#b", "", "  ", "a b"]
)
def test_invalid_memory_ids_rejected(bad: str) -> None:
    with pytest.raises(CodexifyMCPError) as exc:
        validate_memory_id(bad)
    assert exc.value.code == INVALID_REQUEST


@pytest.mark.parametrize("good", ["mem-1", "abc123", "01H8_X-Y"])
def test_valid_memory_ids_accepted(good: str) -> None:
    assert validate_memory_id(good) == good


@pytest.mark.parametrize("bad", ["", "other", "mid term", "ephemeral;drop"])
def test_invalid_silos_rejected(bad: str) -> None:
    with pytest.raises(CodexifyMCPError) as exc:
        validate_silo(bad)
    assert exc.value.code == INVALID_REQUEST


@pytest.mark.parametrize("good", ["ephemeral", "MIDTERM", " longterm ", "LongTerm"])
def test_valid_silos_accepted_case_insensitively(good: str) -> None:
    assert validate_silo(good) == good.strip().lower()


def test_limits_are_bounded_and_offsets_non_negative() -> None:
    assert validate_limit(10) == 10
    assert validate_limit(10_000) == 50
    with pytest.raises(CodexifyMCPError):
        validate_limit(0)
    with pytest.raises(CodexifyMCPError):
        validate_offset(-1)


# --- Credential hygiene -----------------------------------------------------


@pytest.mark.asyncio
async def test_error_messages_never_leak_the_api_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        return httpx.Response(401, json={"detail": "bad key secret-key"})

    client, _ = make_client(handler)
    with pytest.raises(CodexifyMCPError) as exc:
        await client.list_vault_items({"limit": 1})
    assert "secret-key" not in exc.value.message
    await client.aclose()


@pytest.mark.asyncio
async def test_api_key_is_never_placed_in_query_or_body() -> None:
    from .conftest import default_handler

    client, transport = make_client(default_handler)
    await client.list_vault_items({"limit": 5})
    await client.list_memory_silo("longterm", limit=5)
    await client.list_fact_candidates(limit=5)
    await client.aclose()
    for request in transport.requests:
        assert "secret-key" not in str(request.url)
        assert request.content in (b"", b"{}") or not request.content
