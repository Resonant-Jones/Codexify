"""Integration proof: the MCP candidate read reaches the real Guardian handler.

The adapter's own unit tests drive a mocked ``httpx`` transport, so they
cannot observe a Guardian route that is declared but never dispatched. That is
exactly the failure this module closes: ``GET /personal-facts/candidates`` was
shadowed by the earlier ``GET /personal-facts/{fact_id}`` route, so the
adapter received HTTP 422 and could never read a candidate.

This module wires the *real* :class:`~guardian.mcp_memory.client.MemoryClient`
to the *real* personal-facts router through an in-process ASGI transport, so
the adapter, the router, and the handler all take part.

Paging arithmetic against real PostgreSQL is proven in
``tests/routes/test_personal_fact_candidates_pagination.py``; this module
proves reachability and the response contract.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

from guardian.mcp_memory.client import MemoryClient
from guardian.mcp_memory.config import load_config
from guardian.mcp_memory.errors import ConfigurationError

PRINCIPAL = "mcp-candidates-principal"
API_KEY = "mcp-candidates-test-key"
ORIGIN = "http://127.0.0.1:8010"


def _fact(fact_id: int, key: str, value: str) -> dict[str, Any]:
    return {
        "id": fact_id,
        "user_id": PRINCIPAL,
        "key": key,
        "value": value,
        "status": "candidate",
        "confidence": 0.5,
        "is_active": True,
        "updated_at": "2026-01-01T00:00:00+00:00",
    }


class _FakeFactsDB:
    """A facts DB honouring the paging contract the SQL layer implements.

    This stands in for the database only; the route, the dependency graph and
    the adapter are all real. SQL behaviour is proven separately against
    PostgreSQL.
    """

    def __init__(self, facts: list[dict[str, Any]]) -> None:
        self._facts = sorted(
            facts, key=lambda f: (f["updated_at"], f["id"]), reverse=True
        )

    def _matching(
        self,
        user_id: str,
        status: str | None,
        active_only: bool,
        thread_id: int | None,
    ) -> list[dict[str, Any]]:
        rows = [f for f in self._facts if f["user_id"] == user_id]
        if status:
            rows = [f for f in rows if f["status"] == status]
        if active_only:
            rows = [f for f in rows if f.get("is_active", True)]
        if thread_id is not None:
            rows = [
                f
                for f in rows
                if (f.get("thread_id") or None) == thread_id
            ]
        return rows

    def list_facts(
        self,
        user_id: str,
        status: str | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
        thread_id: int | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._matching(user_id, status, active_only, thread_id)
        if limit is None:
            return list(rows[offset:])
        return list(rows[offset : offset + limit])

    def count_facts(
        self,
        user_id: str,
        status: str | None = None,
        active_only: bool = True,
        thread_id: int | None = None,
    ) -> int:
        return len(self._matching(user_id, status, active_only, thread_id))

    def list_fact_evidence_for_facts(
        self, fact_ids: list[int]
    ) -> dict[int, list[dict[str, Any]]]:
        return {}

    def get_fact(self, fact_id: int) -> dict[str, Any] | None:
        for fact in self._facts:
            if fact["id"] == fact_id:
                return fact
        return None

    def list_fact_evidence(self, fact_id: int) -> list[dict[str, Any]]:
        return []


def _build_app(monkeypatch: pytest.MonkeyPatch, facts: list[dict[str, Any]]):
    """Build an app that serves the real personal-facts router."""
    from guardian.routes import personal_facts

    monkeypatch.setattr(
        personal_facts, "chatlog_db", _FakeFactsDB(facts), raising=False
    )

    def _require_api_key(
        x_api_key: str | None = Header(None, alias="X-API-Key"),
    ) -> str:
        if not x_api_key or x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Missing API key")
        return x_api_key

    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"service": "core", "status": "ok"}

    app.include_router(personal_facts.router)
    app.dependency_overrides[personal_facts.require_api_key] = _require_api_key
    app.dependency_overrides[personal_facts.get_current_user] = lambda: PRINCIPAL
    return app


def _config() -> Any:
    return load_config(
        {
            "CODEXIFY_MCP_BASE_URL": ORIGIN,
            "CODEXIFY_MCP_API_KEY": API_KEY,
            "GUARDIAN_AUTH_MODE": "local",
            "GUARDIAN_EXPOSURE_MODE": "local_safe",
        }
    )


@pytest.fixture
def facts() -> list[dict[str, Any]]:
    return [_fact(index, f"probe_key_{index}", f"synthetic-value-{index}")
            for index in range(1, 6)]


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch, facts: list[dict[str, Any]]) -> FastAPI:
    return _build_app(monkeypatch, facts)


# ── The route must be reachable over HTTP ───────────────────────────────────


def test_candidates_route_is_not_shadowed_by_fact_id(app: FastAPI) -> None:
    """Regression: /candidates must reach its own handler, not /{fact_id}."""
    with TestClient(app) as client:
        response = client.get(
            "/personal-facts/candidates", headers={"X-API-Key": API_KEY}
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["total"] == 5
    assert body["limit"] == 50
    assert body["offset"] == 0


def test_numeric_fact_id_route_still_works(app: FastAPI) -> None:
    with TestClient(app) as client:
        response = client.get(
            "/personal-facts/1", headers={"X-API-Key": API_KEY}
        )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["fact"]["id"] == 1


# ── The adapter must reach the real handler ─────────────────────────────────


@pytest.mark.asyncio
async def test_adapter_candidate_read_reaches_the_guardian_handler(
    app: FastAPI,
) -> None:
    transport = httpx.ASGITransport(app=app)
    async with MemoryClient(_config(), transport=transport) as client:
        response = await client.list_fact_candidates(status="candidate")

    assert response.status == 200
    assert response.path == "/personal-facts/candidates"
    payload = response.payload
    assert payload["ok"] is True
    assert payload["total"] == 5
    assert len(payload["facts"]) == 5


@pytest.mark.asyncio
async def test_adapter_candidate_read_pages_through_the_handler(
    app: FastAPI,
) -> None:
    transport = httpx.ASGITransport(app=app)
    async with MemoryClient(_config(), transport=transport) as client:
        first = await client.list_fact_candidates(status="candidate", limit=2)
        second = await client.list_fact_candidates(
            status="candidate", limit=2, offset=2
        )

    assert first.payload["limit"] == 2
    assert first.payload["offset"] == 0
    assert len(first.payload["facts"]) == 2
    assert second.payload["offset"] == 2
    assert len(second.payload["facts"]) == 2
    # The reported total describes the whole population, not the page.
    assert first.payload["total"] == second.payload["total"] == 5
    first_ids = {fact["id"] for fact in first.payload["facts"]}
    second_ids = {fact["id"] for fact in second.payload["facts"]}
    assert not first_ids & second_ids


@pytest.mark.asyncio
async def test_adapter_candidate_read_past_the_last_page_is_empty(
    app: FastAPI,
) -> None:
    transport = httpx.ASGITransport(app=app)
    async with MemoryClient(_config(), transport=transport) as client:
        response = await client.list_fact_candidates(
            status="candidate", limit=10, offset=500
        )
    assert response.status == 200
    assert response.payload["facts"] == []
    assert response.payload["total"] == 5


# ── The adapter's authentication restrictions stay unchanged ───────────────


def test_adapter_still_refuses_remote_auth_modes() -> None:
    with pytest.raises(ConfigurationError):
        load_config(
            {
                "CODEXIFY_MCP_BASE_URL": ORIGIN,
                "CODEXIFY_MCP_API_KEY": API_KEY,
                "GUARDIAN_AUTH_MODE": "remote",
            }
        )


def test_adapter_still_refuses_an_identity_override() -> None:
    with pytest.raises(ConfigurationError):
        load_config(
            {
                "CODEXIFY_MCP_BASE_URL": ORIGIN,
                "CODEXIFY_MCP_API_KEY": API_KEY,
                "CODEXIFY_MCP_USER_ID": "someone-else",
            }
        )


def test_adapter_still_refuses_a_non_loopback_origin() -> None:
    with pytest.raises(ConfigurationError):
        load_config(
            {
                "CODEXIFY_MCP_BASE_URL": "https://memory.example.com",
                "CODEXIFY_MCP_API_KEY": API_KEY,
            }
        )


@pytest.mark.asyncio
async def test_adapter_sends_its_api_key(app: FastAPI) -> None:
    """The key must travel with the request; the route must demand it."""
    transport = httpx.ASGITransport(app=app)
    async with MemoryClient(_config(), transport=transport) as client:
        response = await client.list_fact_candidates(status="candidate")
    assert response.status == 200

    config = load_config(
        {
            "CODEXIFY_MCP_BASE_URL": ORIGIN,
            "CODEXIFY_MCP_API_KEY": API_KEY,
        }
    )
    assert config.api_key == API_KEY
