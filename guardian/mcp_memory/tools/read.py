"""Structural read tools: vault listing, canonical read, silo listing, fact candidates.

Each tool maps validated arguments onto a fixed allowlisted Guardian GET and
returns the upstream payload with its fields intact. No tool accepts an account
or user identity override, and none performs client-side filtering that could be
mistaken for an authorization check.
"""

from __future__ import annotations

from typing import Any

from ..client import MAX_FACT_LIMIT, MAX_LIST_LIMIT, MemoryClient, validate_limit
from ..errors import INVALID_REQUEST
from ._envelope import run_tool
from .status import VAULT_FILTER_FIELDS

#: The ephemeral silo is held in a process-local list inside Guardian and is
#: lost on restart. The route is still account-scoped (it filters on the
#: authenticated principal), so the read is allowed -- with this warning.
EPHEMERAL_WARNING = (
    "The 'ephemeral' silo is process-local in Guardian and does not survive a "
    "restart. Reads are account-scoped by the upstream route."
)


def _check_vault_filter(filters: dict[str, Any] | None) -> dict[str, Any]:
    """Keep only supported VaultListFilter fields; reject unknown keys."""
    if not filters:
        return {}
    if not isinstance(filters, dict):
        raise _invalid("filters must be a mapping of VaultListFilter fields.")
    unknown = sorted(set(filters) - set(VAULT_FILTER_FIELDS))
    if unknown:
        raise _invalid(
            "unsupported vault filter field(s): "
            f"{', '.join(unknown)}. Supported: {', '.join(VAULT_FILTER_FIELDS)}."
        )
    return {k: v for k, v in filters.items() if v is not None}


def _invalid(message: str):
    from ..errors import CodexifyMCPError

    return CodexifyMCPError(INVALID_REQUEST, message)


async def vault_list(
    client: MemoryClient,
    *,
    limit: int = MAX_LIST_LIMIT,
    offset: int = 0,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """List account-owned Memory Vault items (``GET /api/memory-vault/items``).

    ``filters`` accepts only supported ``VaultListFilter`` fields
    (semantic_species, project_id, account_scoped_only, persona_subject_id,
    review_posture, lifecycle_posture, source_system, pinned, held). Account
    scope is resolved by Guardian and cannot be overridden here.
    """

    async def body() -> tuple[dict[str, Any], list[str]]:
        params = _check_vault_filter(filters)
        params.update({"limit": validate_limit(limit), "offset": offset})
        result = await client.list_vault_items(params)
        return (
            {
                "items": (result.payload or {}).get("items", []),
                "limit": (result.payload or {}).get("limit"),
                "offset": (result.payload or {}).get("offset"),
                "returned_count": (result.payload or {}).get("returned_count"),
            },
            [],
        )

    return await run_tool("vault_list", body)


async def vault_get(client: MemoryClient, memory_id: str) -> dict[str, Any]:
    """Read one canonical Memory Vault item.

    Upstream 403/404 is returned as-is; the adapter never falls back to another
    identifier, account, or broader search to satisfy a lookup.
    """

    async def body() -> tuple[dict[str, Any], list[str]]:
        result = await client.get_canonical_item(memory_id)
        return (result.payload, [])

    return await run_tool("vault_get", body)


async def memory_list(
    client: MemoryClient,
    silo: str,
    *,
    limit: int = MAX_LIST_LIMIT,
    offset: int = 0,
) -> dict[str, Any]:
    """List memories from a silo (``GET /api/memory/{silo}``)."""

    async def body() -> tuple[dict[str, Any], list[str]]:
        result = await client.list_memory_silo(silo, limit=limit, offset=offset)
        payload = result.payload or {}
        warnings = [EPHEMERAL_WARNING] if silo.strip().lower() == "ephemeral" else []
        return (
            {
                "silo": payload.get("silo", silo),
                "count": payload.get("count"),
                "entries": payload.get("entries", []),
            },
            warnings,
        )

    return await run_tool("memory_list", body)


async def list_fact_candidates(
    client: MemoryClient,
    *,
    status: str | None = "candidate",
    limit: int = MAX_FACT_LIMIT,
    offset: int = 0,
) -> dict[str, Any]:
    """List Personal Fact candidates awaiting review.

    Records are returned exactly as Guardian reports them. A candidate is not a
    verified fact: ``status`` and ``confidence`` are preserved verbatim and are
    never upgraded or re-interpreted by this adapter.
    """

    async def body() -> tuple[dict[str, Any], list[str]]:
        result = await client.list_fact_candidates(
            status=status, limit=limit, offset=offset
        )
        payload = result.payload or {}
        return (
            {
                "facts": payload.get("facts", []),
                "total": payload.get("total"),
                "limit": payload.get("limit"),
                "offset": payload.get("offset"),
                "classification_note": (
                    "These are unpromoted Personal Fact candidates. A candidate "
                    "is not an accepted or verified personal fact."
                ),
            },
            [],
        )

    return await run_tool("list_fact_candidates", body)


__all__ = [
    "EPHEMERAL_WARNING",
    "list_fact_candidates",
    "memory_list",
    "vault_get",
    "vault_list",
]
