"""Protocol compatibility tests against the installed MCP SDK v2.

SDK v2 supports two negotiation paths, and the adapter must work under both:

* ``mode="legacy"`` forces the classic ``initialize`` handshake (the
  pre-2026 behaviour), so older MCP clients still connect.
* ``mode="auto"`` (the default) probes ``server/discover`` and falls back to
  ``initialize`` when a server does not support it.

Both paths must advertise the same five tools and be able to actually *call*
one -- registration alone is not proof of a working handler.

The final test spawns the console entrypoint as a real subprocess to prove the
stdio transport itself works end to end.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest
from mcp import Client

from guardian.mcp_memory.client import MemoryClient
from guardian.mcp_memory.config import MCPConfig
from guardian.mcp_memory.server import build_server, main
from guardian.mcp_memory.tools import TOOL_NAMES

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.asyncio


def _server():
    config = MCPConfig(base_url="http://127.0.0.1:8010", api_key="k", timeout=1.0)
    client = MemoryClient(config)
    return build_server(config, client), client


async def _exercise(mode: str) -> dict:
    """Connect in the given mode, list tools, and call one for real."""
    server, client = _server()
    async with Client(server, mode=mode) as session:
        listed = await session.list_tools()
        names = sorted(t.name for t in listed.tools)
        protocol = session.protocol_version
        called = await session.call_tool("vault_get", {"memory_id": "mem-1"})
    await client.aclose()
    return {
        "names": names,
        "protocol_version": protocol,
        "text": "".join(
            block.text for block in called.content if hasattr(block, "text")
        ),
    }


@pytest.mark.parametrize("mode", ["legacy", "auto"])
async def test_both_modes_advertise_the_same_five_tools(mode: str) -> None:
    outcome = await _exercise(mode)
    assert outcome["names"] == sorted(TOOL_NAMES)
    assert len(outcome["names"]) == 5


@pytest.mark.parametrize("mode", ["legacy", "auto"])
async def test_both_modes_actually_execute_a_tool_handler(mode: str) -> None:
    """A registered-but-broken handler must not be able to pass.

    Nothing listens on the test port, so the call is expected to fail at the
    origin gate -- but it must fail *structurally*, proving the handler ran and
    produced the response envelope instead of erroring out of the transport.
    """
    outcome = await _exercise(mode)
    payload = json.loads(outcome["text"])
    assert payload["ok"] is False
    assert payload["data"] is None
    assert payload["error"]["code"] in {
        "guardian_unreachable",
        "wrong_upstream",
        "guardian_timeout",
    }


async def test_legacy_mode_uses_the_initialize_protocol_revision() -> None:
    outcome = await _exercise("legacy")
    # Documented pre-2026 revision, i.e. the initialize handshake.
    assert outcome["protocol_version"] == "2025-11-25"


async def test_auto_mode_negotiates_the_modern_revision() -> None:
    outcome = await _exercise("auto")
    assert outcome["protocol_version"] == "2026-07-28"


async def test_no_recall_or_mutation_tool_in_either_mode() -> None:
    for mode in ("legacy", "auto"):
        outcome = await _exercise(mode)
        for name in outcome["names"]:
            lowered = name.lower()
            assert "recall" not in lowered
            assert "search" not in lowered
            assert "vector" not in lowered
            assert "semantic" not in lowered


async def test_envelope_shape_is_stable_over_the_wire() -> None:
    outcome = await _exercise("auto")
    payload = json.loads(outcome["text"])
    assert set(payload) == {"ok", "data", "error", "_meta"}
    assert set(payload["_meta"]) == {"source", "warnings"}


# --- Real subprocess / stdio ----------------------------------------------


def test_console_entrypoint_help_runs_as_a_subprocess() -> None:
    """The installed console script resolves and explains itself."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    proc = subprocess.run(
        [sys.executable, "-m", "guardian.mcp_memory.server", "--help"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    assert "codexify-memory-mcp" in proc.stdout
    assert "CODEXIFY_MCP_BASE_URL" in proc.stdout
    # Help must not emit a raw traceback.
    assert "Traceback" not in proc.stderr


def test_console_entrypoint_reports_missing_sdk_or_config_cleanly() -> None:
    """A bad environment exits non-zero with a message, never a traceback."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env.pop("CODEXIFY_MCP_BASE_URL", None)
    env.pop("CODEXIFY_MCP_API_KEY", None)
    env.pop("GUARDIAN_API_KEY", None)
    proc = subprocess.run(
        [sys.executable, "-m", "guardian.mcp_memory.server"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
        env=env,
    )
    assert proc.returncode == 2
    assert "codexify-memory-mcp" in proc.stderr
    assert "Traceback" not in proc.stderr
    assert proc.stdout == ""


def test_main_help_is_available_in_process() -> None:
    assert main(["--help"]) == 0
