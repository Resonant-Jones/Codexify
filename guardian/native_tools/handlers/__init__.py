"""Handlers for Guardian's native tool family.

Each handler is a pure, in-process function. No handler in this package may
mutate state, spawn a subprocess, or use the network.
"""

from __future__ import annotations

__all__ = ["read_file"]
