"""Server lifecycle tests.

The contract under test: an upstream failure degrades a *tool result*, never the
process, because a crashed stdio server silently strips the client's tools.
"""

from __future__ import annotations

import httpx
import pytest

from guardian.mcp_memory.client import MemoryClient
from guardian.mcp_memory.config import MCPConfig
from guardian.mcp_memory.server import build_server, main
from guardian.mcp_memory.tools import TOOL_NAMES
from guardian.mcp_memory.tools.read import vault_list
from guardian.mcp_memory.tools.status import memory_status

from .conftest import GUARDIAN_HEALTH, make_client


@pytest.mark.asyncio
async def test_client_opens_and_closes_cleanly() -> None:
    client, _ = make_client(lambda r: httpx.Response(200, json=GUARDIAN_HEALTH))
    await client.aclose()
    # A second close must not raise.
    await client.aclose()


@pytest.mark.asyncio
async def test_async_context_manager_closes_client() -> None:
    async with MemoryClient(
        MCPConfig(base_url="http://127.0.0.1:8010", api_key="k", timeout=1.0)
    ) as client:
        assert client.origin_verified is False


@pytest.mark.asyncio
async def test_upstream_failure_does_not_break_later_tools() -> None:
    """After a hard upstream error, memory_status must still answer."""
    state = {"fail": True}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        if state["fail"]:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(
            200,
            json={"items": [], "limit": 1, "offset": 0, "returned_count": 0},
        )

    client, _ = make_client(handler)
    failed = await vault_list(client, limit=1)
    assert failed["ok"] is False
    assert failed["error"]["code"] == "guardian_unreachable"

    state["fail"] = False
    recovered = await vault_list(client, limit=1)
    assert recovered["ok"] is True
    await client.aclose()


@pytest.mark.asyncio
async def test_memory_status_answers_after_upstream_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        raise httpx.ConnectError("boom", request=request)

    client, _ = make_client(handler)
    result = await memory_status(client)
    assert result["ok"] is True
    surfaces = result["data"]["surfaces"]
    assert surfaces["vault_list"]["status"] == "error"
    assert surfaces["vault_list"]["error"]["code"] == "guardian_unreachable"
    await client.aclose()


@pytest.mark.asyncio
async def test_repeated_reads_reuse_one_session() -> None:
    """Many sequential reads must not open a client per call."""
    client, transport = make_client(
        lambda r: (
            httpx.Response(200, json=GUARDIAN_HEALTH)
            if r.url.path == "/health"
            else httpx.Response(
                200, json={"items": [], "limit": 1, "offset": 0, "returned_count": 0}
            )
        )
    )
    for _ in range(5):
        await vault_list(client, limit=1)
    assert transport.paths().count("/health") == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_tool_errors_are_sanitised_envelopes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        return httpx.Response(500, json={"detail": "internal"})

    client, _ = make_client(handler)
    result = await vault_list(client, limit=1)
    assert set(result) == {"ok", "data", "error", "_meta"}
    assert result["data"] is None
    assert set(result["error"]) == {"code", "message"}
    assert "Traceback" not in result["error"]["message"]
    await client.aclose()


@pytest.mark.asyncio
async def test_server_builds_with_exactly_the_five_tools(config) -> None:
    server = build_server(config, MemoryClient(config))
    tools = {t.name for t in await server.list_tools()}
    assert tools == set(TOOL_NAMES)


def test_help_exits_cleanly_without_credentials(capsys) -> None:
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    assert "codexify-memory-mcp" in out
    assert "CODEXIFY_MCP_BASE_URL" in out


def test_missing_config_exits_nonzero_with_actionable_message(
    capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key in (
        "CODEXIFY_MCP_BASE_URL",
        "CODEXIFY_MCP_API_KEY",
        "GUARDIAN_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    assert main([]) == 2
    err = capsys.readouterr().err
    assert "codexify-memory-mcp" in err
    assert "CODEXIFY_MCP_BASE_URL" in err
    assert "Traceback" not in err


def test_populated_user_id_exits_nonzero(capsys, monkeypatch, base_env) -> None:
    for key, value in base_env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("CODEXIFY_MCP_USER_ID", "someone-else")
    assert main([]) == 2
    err = capsys.readouterr().err
    assert "CODEXIFY_MCP_USER_ID" in err
    assert "Traceback" not in err
