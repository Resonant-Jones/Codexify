# MemoryOS_main/__init__.py
"""
"""


import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())

# Prefer in-repo guardian.memoryos; fall back to external package if present.
try:
    from guardian.memoryos.embedders.local_embedder import (
        LocalEmbedder,  # type: ignore
    )
except Exception:
    try:
        from memoryos.embedders.local_embedder import (
            LocalEmbedder,  # type: ignore
        )
    except Exception:
        LocalEmbedder = None  # type: ignore

__all__ = ["LocalEmbedder"]
__version__ = "0.1.0"
__author__ = "Resonant Jones"
