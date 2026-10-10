"""Shared fixtures for the memory MCP adapter tests."""

from __future__ import annotations

import os
from typing import Any

import httpx
import pytest

from guardian.mcp_memory.client import MemoryClient
from guardian.mcp_memory.config import MCPConfig

#: Minimal, contract-accurate Guardian health body.
GUARDIAN_HEALTH: dict[str, Any] = {
    "status": "ok",
    "service": "core",
    "timestamp": "2026-10-08T00:00:00Z",
    "details": {},
}

#: Shaped like the Whoosh'd listener that currently occupies port 8000.
WHOOSHD_HEALTH: dict[str, Any] = {
    "ok": True,
    "runner": "whooshd",
    "version": "0.1.0rc3",
    "status": "ready",
}


class RecordingTransport(httpx.MockTransport):
    """MockTransport that records every request for post-hoc assertions."""

    def __init__(self, handler):
        self.requests: list[httpx.Request] = []
        super().__init__(self._record(handler))

    def _record(self, handler):
        def _inner(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return handler(request)

        return _inner

    def paths(self) -> list[str]:
        return [r.url.path for r in self.requests]

    def keys_sent(self) -> list[str | None]:
        return [r.headers.get("X-API-Key") for r in self.requests]


def default_handler(request: httpx.Request) -> httpx.Response:
    """Serve contract-shaped bodies for the allowlisted read surfaces."""
    path = request.url.path
    if path == "/health":
        return httpx.Response(200, json=GUARDIAN_HEALTH)
    if path == "/api/memory-vault/items":
        return httpx.Response(
            200,
            json={"items": [], "limit": 50, "offset": 0, "returned_count": 0},
        )
    if path.startswith("/api/memory-vault/items/canonical/"):
        return httpx.Response(
            200,
            json={
                "identity": {
                    "kind": "canonical",
                    "canonical_memory_id": request.url.path.rsplit("/", 1)[-1],
                },
                "semantic_species": "user_knowledge",
                "content": "an example memory",
                "account_owner": "local",
                "project_id": None,
                "review_posture": "approved",
                "lifecycle_posture": "active",
                "pinned": False,
                "held": False,
                "persona_links": [],
                "provenance": [],
            },
        )
    if path.startswith("/api/memory/"):
        silo = path.rsplit("/", 1)[-1]
        return httpx.Response(
            200, json={"ok": True, "count": 0, "entries": [], "silo": silo}
        )
    if path == "/personal-facts/candidates":
        return httpx.Response(
            200,
            json={
                "ok": True,
                "facts": [
                    {
                        "id": 7,
                        "key": "k",
                        "value": "v",
                        "status": "candidate",
                        "confidence": 0.5,
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0,
            },
        )
    return httpx.Response(404, json={"detail": "not found"})


@pytest.fixture
def base_env() -> dict[str, str]:
    return {
        "CODEXIFY_MCP_BASE_URL": "http://127.0.0.1:8010",
        "CODEXIFY_MCP_API_KEY": "test-key",
        "GUARDIAN_AUTH_MODE": "local",
    }


@pytest.fixture
def config(base_env: dict[str, str]) -> MCPConfig:
    return MCPConfig(
        base_url=base_env["CODEXIFY_MCP_BASE_URL"],
        api_key=base_env["CODEXIFY_MCP_API_KEY"],
        timeout=10.0,
    )


@pytest.fixture
def transport() -> RecordingTransport:
    return RecordingTransport(default_handler)


@pytest.fixture
async def client(config: MCPConfig, transport: RecordingTransport):
    c = MemoryClient(config, transport=transport)
    try:
        yield c
    finally:
        await c.aclose()


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove adapter variables so ambient shell state cannot leak into tests."""
    for key in (
        "CODEXIFY_MCP_BASE_URL",
        "CODEXIFY_MCP_API_KEY",
        "CODEXIFY_MCP_TIMEOUT",
        "CODEXIFY_MCP_USER_ID",
        "GUARDIAN_API_KEY",
        "GUARDIAN_AUTH_MODE",
        "GUARDIAN_EXPOSURE_MODE",
    ):
        monkeypatch.delenv(key, raising=False)


def make_client(handler, **kwargs) -> tuple[MemoryClient, RecordingTransport]:
    """Build a client bound to an ad-hoc handler, for focused assertions."""
    t = RecordingTransport(handler)
    cfg = MCPConfig(base_url="http://127.0.0.1:8010", api_key="secret-key", timeout=5.0)
    return MemoryClient(cfg, transport=t), t


@pytest.fixture
def env_guard():
    """Return a mapping that only contains explicitly-set adapter variables."""

    def _current() -> dict[str, str]:
        return {k: v for k, v in os.environ.items() if k.startswith("CODEXIFY_MCP_")}

    return _current
