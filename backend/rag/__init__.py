"""
RAG (Retrieval-Augmented Generation) Module.

Keep optional embedding dependencies lazy so migration/import utilities can be
used without importing the full vector stack.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["Embedder", "parse_chat_history"]

if TYPE_CHECKING:
    from .embedder import Embedder
    from .parser import parse_chat_history


def __getattr__(name: str) -> Any:
    if name == "Embedder":
        from .embedder import Embedder

        return Embedder
    if name == "parse_chat_history":
        from .parser import parse_chat_history

        return parse_chat_history
    raise AttributeError(f"module 'backend.rag' has no attribute {name!r}")
