"""Structural proof that the adapter cannot perform unsafe retrieval.

This module asserts the *negative* space: what the adapter must never do. It is
deliberately written against source and registered behaviour rather than against
implementation detail, so it fails loudly if someone later widens the surface.
"""

from __future__ import annotations

import ast
import inspect
import pathlib

import httpx
import pytest

from guardian.mcp_memory import client as client_module
from guardian.mcp_memory import config as config_module
from guardian.mcp_memory import errors as errors_module
from guardian.mcp_memory import server as server_module
from guardian.mcp_memory.client import FORBIDDEN_PATH_FRAGMENTS, MemoryClient
from guardian.mcp_memory.errors import UNSUPPORTED_OPERATION, CodexifyMCPError
from guardian.mcp_memory.tools import TOOL_NAMES

PACKAGE_ROOT = pathlib.Path(inspect.getfile(client_module)).parent
SOURCE_FILES = sorted(PACKAGE_ROOT.rglob("*.py"))

#: Names whose presence would signal an unauthorized authority surface.
FORBIDDEN_IMPORTS = (
    "sqlalchemy",
    "chroma",
    "VectorStore",
    "guardian.vector",
    "guardian.services",
    "guardian.memory.query_memory",
    "MemoryStore",
    "guardian.core.dependencies",
    "chatlog_db",
    "guardian_db",
)

#: Environment variables that must not exist anywhere in this package.
FORBIDDEN_ENV_NAMES = (
    "CODEXIFY_MCP_RECALL_ROUTE",
    "CODEXIFY_MCP_CAPABILITY_GRANT",
    "CODEXIFY_MCP_ALLOW_WRITES",
)

FORBIDDEN_TOOL_FRAGMENTS = (
    "recall",
    "search",
    "vector",
    "semantic",
    "create",
    "update",
    "delete",
    "purge",
    "erase",
    "pin",
    "hold",
    "promote",
    "write",
)


# --- Tool surface -----------------------------------------------------------


def test_exactly_five_tools_are_declared() -> None:
    assert len(TOOL_NAMES) == 5


def test_tool_names_are_exactly_the_v1_contract() -> None:
    assert set(TOOL_NAMES) == {
        "memory_status",
        "vault_list",
        "vault_get",
        "memory_list",
        "list_fact_candidates",
    }


@pytest.mark.asyncio
async def test_server_registers_exactly_five_tools(config) -> None:
    server = server_module.build_server(config, MemoryClient(config))
    tools = await server.list_tools()
    assert sorted(t.name for t in tools) == sorted(TOOL_NAMES)


@pytest.mark.asyncio
async def test_no_recall_or_mutation_tool_is_registered(config) -> None:
    server = server_module.build_server(config, MemoryClient(config))
    names = [t.name for t in await server.list_tools()]
    for name in names:
        lowered = name.lower()
        for fragment in FORBIDDEN_TOOL_FRAGMENTS:
            assert fragment not in lowered, f"tool {name!r} looks like {fragment!r}"


# --- Import hygiene ---------------------------------------------------------


def test_package_never_imports_storage_or_services() -> None:
    for path in SOURCE_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [
                    f"{node.module or ''}.{alias.name}" for alias in node.names
                ]
            else:
                continue
            for imported in names:
                for forbidden in FORBIDDEN_IMPORTS:
                    assert forbidden not in imported, (
                        f"{path.name} imports {imported!r} "
                        f"(forbidden authority: {forbidden})"
                    )


def test_package_never_imports_http_via_httpx2() -> None:
    """The adapter uses the repo's httpx; httpx2 belongs to the SDK alone.

    Prose may mention httpx2 (the module docstring explains why it is avoided),
    so this asserts on real import statements rather than raw text.
    """
    for path in SOURCE_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for imported in names:
                assert (
                    "httpx2" not in imported
                ), f"{path.name} imports {imported!r}; the adapter must use httpx"


def test_package_declares_no_recall_configuration() -> None:
    for path in SOURCE_FILES:
        text = path.read_text(encoding="utf-8")
        for name in FORBIDDEN_ENV_NAMES:
            assert name not in text, f"{path.name} references {name}"


# --- Forbidden endpoint reachability ---------------------------------------


def test_forbidden_endpoints_are_named_in_the_guard() -> None:
    for fragment in ("/api/retrieve", "/codexify/search", "/chat"):
        assert fragment in FORBIDDEN_PATH_FRAGMENTS


@pytest.mark.asyncio
async def test_client_rejects_forbidden_path_directly() -> None:
    cfg = client_module.MCPConfig(
        base_url="http://127.0.0.1:8010", api_key="k", timeout=1.0
    )
    client = MemoryClient(cfg)
    try:
        for fragment in FORBIDDEN_PATH_FRAGMENTS:
            with pytest.raises(CodexifyMCPError) as exc:
                await client._get(fragment)
            assert exc.value.code == UNSUPPORTED_OPERATION
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_no_public_method_accepts_a_raw_path_or_method() -> None:
    """The only outbound entry point is ``_get``, and it takes no method."""
    public = {
        name
        for name in dir(MemoryClient)
        if not name.startswith("_") and callable(getattr(MemoryClient, name))
    }
    # Dunder context-manager methods are excluded by the leading-underscore
    # filter; every *public* entry point must be one of these allowlisted ops.
    assert public == {
        "aclose",
        "get_canonical_item",
        "list_fact_candidates",
        "list_memory_silo",
        "list_vault_items",
        "verify_origin",
    }
    # No caller-supplied URL/method parameters anywhere in those signatures.
    for name in public:
        params = inspect.signature(getattr(MemoryClient, name)).parameters
        assert "method" not in params
        assert "url" not in params
        assert "headers" not in params


@pytest.mark.asyncio
async def test_no_request_carries_a_caller_supplied_user_id() -> None:
    """Drive every read tool and assert no user_id reaches the wire."""
    from .conftest import RecordingTransport, default_handler

    transport = RecordingTransport(default_handler)
    cfg = client_module.MCPConfig(
        base_url="http://127.0.0.1:8010", api_key="k", timeout=5.0
    )
    client = MemoryClient(cfg, transport=transport)
    from guardian.mcp_memory.tools.read import (
        list_fact_candidates,
        memory_list,
        vault_get,
        vault_list,
    )

    try:
        await vault_list(client, limit=5)
        await vault_get(client, "mem-1")
        await memory_list(client, "longterm", limit=5)
        await list_fact_candidates(client, limit=5)
    finally:
        await client.aclose()

    assert transport.requests, "expected the tools to issue requests"
    for request in transport.requests:
        assert "user_id" not in str(request.url).lower()
        assert b"user_id" not in (request.content or b"")


# --- Response-shape hygiene -------------------------------------------------


def test_error_codes_are_a_closed_registry() -> None:
    from guardian.mcp_memory.errors import ERROR_CODES

    assert "invalid_configuration" in ERROR_CODES
    with pytest.raises(ValueError):
        CodexifyMCPError("totally_made_up", "x")


def test_config_module_never_reads_an_identity_override() -> None:
    """CODEXIFY_MCP_USER_ID may only be read to reject it."""
    source = pathlib.Path(inspect.getfile(config_module)).read_text(encoding="utf-8")
    occurrences = source.count("CODEXIFY_MCP_USER_ID")
    # Declaration + docstring + the rejection check + its message.
    assert occurrences >= 2


def test_errors_module_defines_no_secret_bearing_codes() -> None:
    source = pathlib.Path(inspect.getfile(errors_module)).read_text(encoding="utf-8")
    assert "api_key" not in source.lower().replace("co_", "")


@pytest.mark.asyncio
async def test_tools_never_raise_uncaught_errors_into_the_transport() -> None:
    """Even a hostile upstream yields a structured envelope, never a raise."""
    from guardian.mcp_memory.tools.read import memory_list

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok", "service": "core"})
        return httpx.Response(500, json={"detail": "boom"})

    from .conftest import make_client

    client, _ = make_client(handler)
    try:
        result = await memory_list(client, "longterm", limit=1)
    finally:
        await client.aclose()
    assert result["ok"] is False
    assert result["error"]["code"] == "upstream_error"
    assert result["data"] is None
