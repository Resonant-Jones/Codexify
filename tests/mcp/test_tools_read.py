"""Tool-level behaviour tests: argument mapping, response fidelity, warnings."""

from __future__ import annotations

import httpx
import pytest

from guardian.mcp_memory.errors import INVALID_REQUEST, NOT_FOUND
from guardian.mcp_memory.tools.read import (
    EPHEMERAL_WARNING,
    list_fact_candidates,
    memory_list,
    vault_get,
    vault_list,
)
from guardian.mcp_memory.tools.status import VAULT_FILTER_FIELDS, memory_status

from .conftest import GUARDIAN_HEALTH, WHOOSHD_HEALTH, make_client


@pytest.mark.asyncio
async def test_vault_list_maps_supported_filters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        return httpx.Response(
            200,
            json={"items": [], "limit": 5, "offset": 0, "returned_count": 0},
        )

    client, transport = make_client(handler)
    result = await vault_list(
        client,
        limit=5,
        offset=0,
        filters={"pinned": True, "review_posture": "approved", "project_id": 7},
    )
    assert result["ok"] is True
    url = transport.requests[-1].url
    assert url.params["pinned"] == "true"
    assert url.params["review_posture"] == "approved"
    assert url.params["project_id"] == "7"
    await client.aclose()


@pytest.mark.asyncio
async def test_vault_list_rejects_unknown_filter_fields() -> None:
    client, _ = make_client(lambda r: httpx.Response(200, json={}))
    result = await vault_list(client, filters={"user_id": "someone-else"})
    assert result["ok"] is False
    assert result["error"]["code"] == INVALID_REQUEST
    assert "unsupported vault filter" in result["error"]["message"]
    await client.aclose()


def test_vault_filter_fields_exclude_any_account_filter() -> None:
    assert "user_id" not in VAULT_FILTER_FIELDS
    assert "account_id" not in VAULT_FILTER_FIELDS


@pytest.mark.asyncio
async def test_vault_get_returns_upstream_item_intact() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        return httpx.Response(
            200,
            json={
                "identity": {"kind": "canonical", "canonical_memory_id": "mem-9"},
                "semantic_species": "user_knowledge",
                "content": "hello",
                "account_owner": "acct-1",
                "project_id": 3,
                "review_posture": "approved",
                "lifecycle_posture": "active",
                "persona_links": [{"persona_id": "p1"}],
                "provenance": [{"source_system": "chat"}],
            },
        )

    client, _ = make_client(handler)
    result = await vault_get(client, "mem-9")
    item = result["data"]
    assert item["account_owner"] == "acct-1"
    assert item["project_id"] == 3
    assert item["review_posture"] == "approved"
    assert item["lifecycle_posture"] == "active"
    assert item["persona_links"] == [{"persona_id": "p1"}]
    assert item["provenance"] == [{"source_system": "chat"}]
    await client.aclose()


@pytest.mark.asyncio
async def test_vault_get_does_not_widen_scope_on_404() -> None:
    """A foreign/unknown id must not trigger any broader lookup."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        return httpx.Response(404, json={"detail": "unavailable"})

    client, _ = make_client(handler)
    result = await vault_get(client, "not-mine")
    assert result["ok"] is False
    assert result["error"]["code"] == NOT_FOUND
    assert seen.count("/api/memory-vault/items/canonical/not-mine") == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_memory_list_validates_silo_and_bounds_pagination() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        return httpx.Response(200, json={"ok": True, "count": 0, "entries": []})

    client, transport = make_client(handler)
    bad = await memory_list(client, "secrets", limit=5)
    assert bad["ok"] is False
    assert bad["error"]["code"] == INVALID_REQUEST

    ok = await memory_list(client, "longterm", limit=9999, offset=0)
    assert ok["ok"] is True
    assert transport.requests[-1].url.params["limit"] == "50"
    await client.aclose()


@pytest.mark.asyncio
async def test_ephemeral_silo_carries_restart_warning() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        return httpx.Response(
            200, json={"ok": True, "count": 0, "entries": [], "silo": "ephemeral"}
        )

    client, _ = make_client(handler)
    result = await memory_list(client, "ephemeral", limit=1)
    assert EPHEMERAL_WARNING in result["_meta"]["warnings"]
    await client.aclose()


@pytest.mark.asyncio
async def test_non_ephemeral_silo_has_no_ephemeral_warning() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        return httpx.Response(
            200, json={"ok": True, "count": 0, "entries": [], "silo": "longterm"}
        )

    client, _ = make_client(handler)
    result = await memory_list(client, "longterm", limit=1)
    assert EPHEMERAL_WARNING not in result["_meta"]["warnings"]
    await client.aclose()


@pytest.mark.asyncio
async def test_fact_candidates_preserve_status_and_confidence() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        return httpx.Response(
            200,
            json={
                "ok": True,
                "facts": [
                    {
                        "id": 3,
                        "key": "home_city",
                        "value": "Detroit",
                        "status": "candidate",
                        "confidence": 0.42,
                        "_evidence": [{"source": "chat"}],
                    }
                ],
                "total": 1,
                "limit": 5,
                "offset": 0,
            },
        )

    client, _ = make_client(handler)
    result = await list_fact_candidates(client, limit=5)
    fact = result["data"]["facts"][0]
    # Candidate status and confidence must survive untouched.
    assert fact["status"] == "candidate"
    assert fact["confidence"] == 0.42
    assert fact["_evidence"] == [{"source": "chat"}]
    assert (
        "not an accepted or verified personal fact"
        in result["data"]["classification_note"]
    )
    await client.aclose()


@pytest.mark.asyncio
async def test_fact_limit_caps_at_upstream_maximum() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        return httpx.Response(200, json={"ok": True, "facts": []})

    client, transport = make_client(handler)
    await list_fact_candidates(client, limit=100000)
    assert transport.requests[-1].url.params["limit"] == "200"
    await client.aclose()


# --- memory_status ----------------------------------------------------------


@pytest.mark.asyncio
async def test_memory_status_reports_healthy_surfaces() -> None:
    client, transport = make_client(_default())
    result = await memory_status(client)
    assert result["ok"] is True
    assert result["data"]["origin_verified"] is True
    surfaces = result["data"]["surfaces"]
    assert surfaces["vault_list"]["status"] == "ok"
    assert surfaces["memory_list"]["status"] == "ok"
    assert surfaces["fact_candidates"]["status"] == "ok"
    # Probes use the smallest legal limit.
    assert transport.requests[-1].url.params["limit"] == "1"
    await client.aclose()


@pytest.mark.asyncio
async def test_memory_status_discards_probe_content() -> None:
    """Status must never echo memory bodies back to the caller."""
    secret = "SUPER-SECRET-MEMORY-CONTENT"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        if request.url.path == "/api/memory/longterm":
            return httpx.Response(
                200,
                json={"ok": True, "count": 1, "entries": [{"content": secret}]},
            )
        return httpx.Response(
            200,
            json={
                "items": [{"content": secret}],
                "returned_count": 1,
                "limit": 1,
                "offset": 0,
            },
        )

    client, _ = make_client(handler)
    result = await memory_status(client)
    assert secret not in str(result)
    await client.aclose()


@pytest.mark.asyncio
async def test_memory_status_stops_at_unverified_origin() -> None:
    client, transport = make_client(lambda r: httpx.Response(200, json=WHOOSHD_HEALTH))
    result = await memory_status(client)
    assert result["ok"] is True  # the *tool* succeeded
    assert result["data"]["origin_verified"] is False
    assert result["data"]["surfaces"]["guardian_origin"]["status"] == "error"
    # Nothing past the health probe may have been attempted.
    assert transport.paths() == ["/health"]
    assert transport.keys_sent() == [None]
    await client.aclose()


@pytest.mark.asyncio
async def test_memory_status_states_recall_is_absent() -> None:
    client, _ = make_client(_default())
    result = await memory_status(client)
    assert result["data"]["semantic_recall"] is False
    assert any("Semantic" in n for n in result["data"]["notes"])
    assert any("single-account" in n for n in result["data"]["notes"])
    await client.aclose()


@pytest.mark.asyncio
async def test_memory_status_reports_quarantined_route_without_widening() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json=GUARDIAN_HEALTH)
        return httpx.Response(404, json={"detail": "Not Found"})

    client, _ = make_client(handler)
    result = await memory_status(client)
    surfaces = result["data"]["surfaces"]
    assert surfaces["vault_list"]["status"] == "error"
    assert surfaces["vault_list"]["error"]["code"] == NOT_FOUND
    assert "CODEXIFY_ENABLE_MEMORY_ROUTES" in surfaces["vault_list"]["error"]["message"]
    await client.aclose()


def _default():
    from .conftest import default_handler

    return default_handler


__all__: list[str] = []
