"""``memory_status`` -- report whether Guardian's structural reads are usable.

The important subtlety: a healthy ``/health`` does **not** prove the memory
routers are mounted or authorized, so this tool additionally issues bounded
authenticated probes against each read surface. Those probes use the smallest
legal limit and their bodies are **discarded** -- only the resulting
classification is reported, never memory content.
"""

from __future__ import annotations

from typing import Any

from ..client import MemoryClient
from ..errors import CodexifyMCPError
from ._envelope import run_tool

SOURCE = "memory_status"

#: VaultListFilter fields exposed by ``vault_list``. Status uses no account
#: filter: scope is resolved server-side by Guardian.
VAULT_FILTER_FIELDS: tuple[str, ...] = (
    "semantic_species",
    "project_id",
    "account_scoped_only",
    "persona_subject_id",
    "review_posture",
    "lifecycle_posture",
    "source_system",
    "pinned",
    "held",
)

_RECALL_ABSENT_NOTE = (
    "Semantic and vector recall are not implemented in v1. This adapter is a "
    "structural reader by design; no search or recall tool is registered."
)
_SINGLE_USER_NOTE = (
    "v1 targets a local, single-account Guardian deployment. Authorization is "
    "enforced by Guardian per account; the adapter adds no account filtering "
    "of its own."
)


async def memory_status(client: MemoryClient) -> dict[str, Any]:
    """Report Guardian reachability and which memory read surfaces work."""

    async def body() -> tuple[dict[str, Any], list[str]]:
        warnings: list[str] = []
        surfaces: dict[str, Any] = {}

        # 1. Origin identity, proven without sending the credential.
        health: dict[str, Any]
        try:
            health = await client.verify_origin()
            surfaces["guardian_origin"] = {
                "status": "ok",
                "verified": True,
                "health_status": health.get("status"),
            }
        except CodexifyMCPError as exc:
            surfaces["guardian_origin"] = {
                "status": "error",
                "verified": False,
                "error": exc.to_error(),
            }
            # Without a verified origin we must not authenticate anything else.
            return (
                {
                    "origin_verified": False,
                    "surfaces": surfaces,
                    "notes": [_RECALL_ABSENT_NOTE, _SINGLE_USER_NOTE],
                    "upstream_host": client.origin,
                },
                warnings,
            )

        # 2. Bounded authenticated probes. Bodies are read only to prove the
        #    request succeeded, then dropped -- never returned.
        surfaces["vault_list"] = await _probe(
            client.list_vault_items({"limit": 1, "offset": 0})
        )
        surfaces["memory_list"] = await _probe(
            client.list_memory_silo("longterm", limit=1, offset=0)
        )
        surfaces["fact_candidates"] = await _probe(
            client.list_fact_candidates(limit=1, offset=0)
        )

        return (
            {
                "origin_verified": True,
                "upstream_host": client.origin,
                "surfaces": surfaces,
                "vault_filter_fields": list(VAULT_FILTER_FIELDS),
                "read_only": True,
                "semantic_recall": False,
                "notes": [_RECALL_ABSENT_NOTE, _SINGLE_USER_NOTE],
            },
            warnings,
        )

    return await run_tool(SOURCE, body)


async def _probe(awaitable) -> dict[str, Any]:
    """Run one probe and reduce it to a classification, discarding content."""
    try:
        await awaitable
    except CodexifyMCPError as exc:
        return {"status": "error", "error": exc.to_error()}
    return {"status": "ok"}


__all__ = ["VAULT_FILTER_FIELDS", "memory_status"]
