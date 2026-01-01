"""guardian.memoryos

Package entrypoint for the in-repo MemoryOS integration.

Notes:
- We expose a lightweight `Memoryos` wrapper used by the integrated code.
- We also attempt to expose `LocalEmbedder` from the in-repo implementation,
  with a fallback to an external `memoryos` package if it exists.
"""

from __future__ import annotations

import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())


class Memoryos:
    def __init__(
        self,
        short_term_capacity: int = 100,
        mid_term_capacity: int = 50,
        long_term_knowledge_capacity: int = 1000,
        retrieval_queue_capacity: int = 50,
        mid_term_heat_threshold: float = 5.0,
        llm_model: str = "gpt-4",
        **kwargs,
    ):
        # Core config with safe defaults
        self.short_term_capacity = short_term_capacity
        self.mid_term_capacity = mid_term_capacity
        self.long_term_knowledge_capacity = long_term_knowledge_capacity
        self.retrieval_queue_capacity = retrieval_queue_capacity
        self.mid_term_heat_threshold = mid_term_heat_threshold

        # Always define the LLM model before using it downstream
        self.llm_model = llm_model

        # Now initialize any downstream components that depend on self.llm_model
        # For example:
        # self.updater = Updater(llm_model=self.llm_model)


# Prefer in-repo implementation; fall back to external package if present.
try:
    from .embedders.local_embedder import LocalEmbedder  # type: ignore
except Exception:
    try:
        from memoryos.embedders.local_embedder import (
            LocalEmbedder,  # type: ignore
        )
    except Exception:
        LocalEmbedder = None  # type: ignore


__all__ = ["Memoryos", "LocalEmbedder"]
__version__ = "0.1.0"
__author__ = "Resonant Jones"
