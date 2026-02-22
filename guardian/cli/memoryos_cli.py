"""Guardian package.

This module must remain side-effect free.

Rationale:
- CLI entrypoints executed via `python -m guardian.cli.*` will import `guardian` during module resolution.
- Import-time initialization (filesystem writes, vector backends like FAISS, etc.) makes even `--help` slow/noisy
  and can prevent Textual from taking control of the terminal.

Initialization belongs in explicit runtime entrypoints (API server, workers), not at package import time.
"""

from __future__ import annotations

__all__ = ["__version__"]

# Keep version optional and cheap.
try:
    from ._version import __version__  # type: ignore
except Exception:  # pragma: no cover
    __version__ = "0.0.0"
