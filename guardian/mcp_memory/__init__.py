"""Read-only MCP adapter for Codexify memory.

This package exposes a bounded, read-only view of Codexify's account-owned
memory to local MCP clients. Guardian remains the sole memory and identity
authority: the adapter holds no database handle, imports no Guardian service,
and reaches memory exclusively through allowlisted, authenticated Guardian HTTP
GET endpoints.

Scope of v1 is intentionally structural reads only. Semantic/vector recall is
not implemented and is not a pending feature inside this package.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "1.0.0"
