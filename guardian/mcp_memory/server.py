"""stdio MCP server exposing read-only Codexify memory reads.

Exactly five tools are registered. The server owns one shared
:class:`~guardian.mcp_memory.client.MemoryClient` for its whole lifetime, opens
it before serving and closes it on shutdown, and never lets an upstream failure
escape into the transport (which would take the client's tool surface down).
"""

from __future__ import annotations

import contextlib
import sys
from typing import Any

from .client import MemoryClient
from .config import MCPConfig, load_config
from .errors import CodexifyMCPError, ConfigurationError

SERVER_NAME = "codexify-memory"
SERVER_INSTRUCTIONS = (
    "Read-only access to Codexify memory owned by the authenticated account. "
    "Five structural read tools are available. Semantic/vector recall is not "
    "part of this adapter. Personal Fact candidates are unpromoted and are not "
    "verified facts."
)

_DEPENDENCY_HINT = (
    "codexify-memory-mcp requires the MCP SDK.\n"
    "Install it with:\n"
    '    pip install -e ".[mcp-memory]"\n'
    "from the Codexify repository root."
)


def _import_mcp() -> Any:
    """Import the MCP SDK, failing with an actionable message if absent.

    Returns a sentinel when the SDK is missing so that ``--help`` and
    configuration errors stay usable without the extra installed; only an
    actual serve attempt requires the SDK.
    """
    try:
        from mcp.server import MCPServer
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on env
        raise ConfigurationError(f"{exc}. {_DEPENDENCY_HINT}") from None
    return MCPServer


def build_server(config: MCPConfig, client: MemoryClient) -> Any:
    """Construct the :class:`MCPServer` with the five read-only tools."""
    mcp = _import_mcp()
    server = mcp(
        SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
        log_level="ERROR",  # keep stdout clean for the stdio protocol
    )

    from .tools.read import list_fact_candidates, memory_list, vault_get, vault_list
    from .tools.status import memory_status

    @server.tool(
        name="memory_status",
        description=(
            "Report whether Codexify Guardian and its structural memory read "
            "surfaces are usable. Probes are bounded and their contents are "
            "discarded; only reachability and error classification are returned. "
            "Semantic recall is not implemented in v1."
        ),
    )
    async def _memory_status() -> dict[str, Any]:
        return await memory_status(client)

    @server.tool(
        name="vault_list",
        description=(
            "List account-owned Memory Vault items with lifecycle, review "
            "posture, project scope, persona attribution and provenance. "
            "Supports optional VaultListFilter fields and bounded pagination."
        ),
    )
    async def _vault_list(
        limit: int = 50,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await vault_list(client, limit=limit, offset=offset, filters=filters)

    @server.tool(
        name="vault_get",
        description=(
            "Read one canonical Memory Vault item by its authoritative memory "
            "id. Returns the item exactly as Guardian stores it."
        ),
    )
    async def _vault_get(memory_id: str) -> dict[str, Any]:
        return await vault_get(client, memory_id)

    @server.tool(
        name="memory_list",
        description=(
            "List memories from a silo. Supported silos: ephemeral, midterm, "
            "longterm. The ephemeral silo is process-local and does not survive "
            "a Guardian restart."
        ),
    )
    async def _memory_list(
        silo: str, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        return await memory_list(client, silo, limit=limit, offset=offset)

    @server.tool(
        name="list_fact_candidates",
        description=(
            "List Personal Fact candidates awaiting review, preserving their "
            "review status, confidence and evidence. Candidates are unpromoted "
            "and are not verified facts."
        ),
    )
    async def _list_fact_candidates(
        status: str | None = "candidate", limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        return await list_fact_candidates(
            client, status=status, limit=limit, offset=offset
        )

    return server


async def serve(config: MCPConfig) -> None:
    """Run the stdio server until the client disconnects."""
    async with MemoryClient(config) as client:
        server = build_server(config, client)
        await server.run_stdio_async()


def main(argv: list[str] | None = None) -> int:
    """Console-script entrypoint.

    Configuration problems and a missing SDK both produce an actionable
    message on stderr and a non-zero exit, never a raw traceback.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("-h", "--help"):
        print(
            "codexify-memory-mcp -- read-only Codexify memory over MCP (stdio)\n\n"
            "Required environment:\n"
            "  CODEXIFY_MCP_BASE_URL  Guardian loopback origin, e.g. "
            "http://127.0.0.1:8010\n"
            "  CODEXIFY_MCP_API_KEY   Guardian API key (or set GUARDIAN_API_KEY)\n\n"
            "Optional:\n"
            "  CODEXIFY_MCP_TIMEOUT   request timeout in seconds (default 10)\n\n"
            'Install: pip install -e ".[mcp-memory]"'
        )
        return 0

    try:
        config = load_config()
        # Fail before serving if the SDK is missing.
        _import_mcp()
    except ConfigurationError as exc:
        print(f"codexify-memory-mcp: {exc.message}", file=sys.stderr)
        return 2
    except CodexifyMCPError as exc:  # pragma: no cover - defensive
        print(f"codexify-memory-mcp: {exc.message}", file=sys.stderr)
        return 2

    with contextlib.suppress(KeyboardInterrupt):
        import anyio

        anyio.run(serve, config)
    return 0


__all__ = ["SERVER_NAME", "build_server", "main", "serve"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
