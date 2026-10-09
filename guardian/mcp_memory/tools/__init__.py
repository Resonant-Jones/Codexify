"""MCP tool implementations for the read-only memory adapter.

Registered tools, and nothing else:

* :func:`memory_status`           -- surface reachability (tool 1)
* :func:`vault_list`              -- Memory Vault listing (tool 2)
* :func:`vault_get`               -- one canonical Vault item (tool 3)
* :func:`memory_list`             -- memory silo listing (tool 4)
* :func:`list_fact_candidates`    -- Personal Fact candidates (tool 5)

There is deliberately no recall/search tool and no mutating tool. Each tool
returns the shared response envelope rather than raising, because under MCP v2
an exception escaping a handler surfaces as an opaque JSON-RPC error and would
hide the structured error code a client needs.
"""

from __future__ import annotations

from .read import list_fact_candidates, memory_list, vault_get, vault_list
from .status import memory_status

#: The complete, authoritative v1 tool surface.
TOOL_NAMES: tuple[str, ...] = (
    "memory_status",
    "vault_list",
    "vault_get",
    "memory_list",
    "list_fact_candidates",
)

__all__ = [
    "TOOL_NAMES",
    "list_fact_candidates",
    "memory_list",
    "memory_status",
    "vault_get",
    "vault_list",
]
