"""Factory for selecting the graph backend adapter at runtime.

This module provides a fail-closed, default-off factory that selects the
appropriate graph backend adapter based on explicit environment configuration.

Required env flags for non-noop selection:
- CODEXIFY_ENABLE_GRAPH_WRITES=true
- CODEXIFY_GRAPH_BACKEND=neo4j

If either flag is absent or invalid, the factory returns NoopGraphBackendAdapter.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from guardian.core.config import get_settings
from guardian.memory_graph.graph_backend import GraphBackendAdapter
from guardian.memory_graph.neo4j_graph_backend import Neo4jGraphBackend
from guardian.memory_graph.noop_graph_backend import (
    NoOpGraphBackend,
    NoopGraphBackendAdapter,
)

logger = logging.getLogger(__name__)

GRAPH_BACKEND_SELECTION_NOOP = "noop"
GRAPH_BACKEND_SELECTION_NEO4J = "neo4j"

_VALID_GRAPH_BACKENDS: frozenset[str] = frozenset(
    {GRAPH_BACKEND_SELECTION_NOOP, GRAPH_BACKEND_SELECTION_NEO4J}
)

_ENV_ENABLE_GRAPH_WRITES = "CODEXIFY_ENABLE_GRAPH_WRITES"
_ENV_GRAPH_BACKEND = "CODEXIFY_GRAPH_BACKEND"

_FACTORY_CACHE: dict[str, GraphBackendAdapter] = {}


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


def resolve_graph_backend_selection() -> str:
    """Return the effective graph backend selection string.

    Returns GRAPH_BACKEND_SELECTION_NOOP unless:
    - CODEXIFY_ENABLE_GRAPH_WRITES is truthy, AND
    - CODEXIFY_GRAPH_BACKEND is set to a valid non-noop backend.

    This is a pure config-resolution function with no side effects.
    """
    enable_writes = _is_truthy(os.getenv(_ENV_ENABLE_GRAPH_WRITES))
    if not enable_writes:
        return GRAPH_BACKEND_SELECTION_NOOP

    raw_backend = (os.getenv(_ENV_GRAPH_BACKEND) or "").strip().lower()
    if not raw_backend:
        return GRAPH_BACKEND_SELECTION_NOOP

    if raw_backend not in _VALID_GRAPH_BACKENDS:
        logger.warning(
            "[graph-backend] invalid CODEXIFY_GRAPH_BACKEND=%s; "
            "falling back to %s. Valid values: %s",
            raw_backend,
            GRAPH_BACKEND_SELECTION_NOOP,
            ", ".join(sorted(_VALID_GRAPH_BACKENDS)),
        )
        return GRAPH_BACKEND_SELECTION_NOOP

    return raw_backend


def get_graph_backend_adapter() -> GraphBackendAdapter:
    """Return the graph backend adapter selected by runtime configuration.

    This is the canonical entry point for the graph-write worker and any
    other code path that needs a GraphBackendAdapter.

    The selection is cached per backend name to avoid repeated instantiation.
    """
    selection = resolve_graph_backend_selection()

    cached = _FACTORY_CACHE.get(selection)
    if cached is not None:
        return cached

    if selection == GRAPH_BACKEND_SELECTION_NEO4J:
        try:
            from guardian.memory_graph.neo4j_graph_backend import (
                Neo4jGraphBackendAdapter,
            )

            adapter: GraphBackendAdapter = Neo4jGraphBackendAdapter()
            logger.info(
                "[graph-backend] Neo4j graph backend adapter selected "
                "(CODEXIFY_ENABLE_GRAPH_WRITES=true, CODEXIFY_GRAPH_BACKEND=neo4j)"
            )
        except ImportError:
            logger.warning(
                "[graph-backend] CODEXIFY_GRAPH_BACKEND=neo4j requested but "
                "Neo4jGraphBackendAdapter is not available; falling back to noop."
            )
            adapter = NoopGraphBackendAdapter()
    else:
        adapter = NoopGraphBackendAdapter()
        logger.info(
            "[graph-backend] NoopGraphBackendAdapter selected "
            "(graph writes disabled or backend=noop)"
        )

    _FACTORY_CACHE[selection] = adapter
    return adapter


def get_graph_backend_selection_metadata() -> dict[str, Any]:
    """Return bounded metadata about the current graph backend selection.

    Useful for tests, logging, and diagnostics. Does not instantiate adapters.
    """
    selection = resolve_graph_backend_selection()
    enable_writes = _is_truthy(os.getenv(_ENV_ENABLE_GRAPH_WRITES))
    raw_backend = (os.getenv(_ENV_GRAPH_BACKEND) or "").strip().lower()

    return {
        "effective_backend": selection,
        "enable_graph_writes_flag": enable_writes,
        "raw_backend_env": raw_backend,
        "is_noop": selection == GRAPH_BACKEND_SELECTION_NOOP,
    }


__all__ = [
    "GRAPH_BACKEND_SELECTION_NOOP",
    "GRAPH_BACKEND_SELECTION_NEO4J",
    "get_graph_backend",
    "get_graph_backend_adapter",
    "get_graph_backend_selection_metadata",
    "resolve_graph_backend_selection",
]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def get_graph_backend():
    """Compatibility factory for legacy graph backend callsites."""
    settings = get_settings()
    enabled = _env_bool(
        _ENV_ENABLE_GRAPH_WRITES,
        bool(getattr(settings, "CODEXIFY_ENABLE_GRAPH_WRITES", False)),
    )
    configured_kind = (
        str(
            os.getenv(_ENV_GRAPH_BACKEND)
            or getattr(
                settings, "CODEXIFY_GRAPH_BACKEND", GRAPH_BACKEND_SELECTION_NOOP
            )
            or GRAPH_BACKEND_SELECTION_NOOP
        )
        .strip()
        .lower()
    )

    if enabled and configured_kind == GRAPH_BACKEND_SELECTION_NEO4J:
        uri = str(
            os.getenv("NEO4J_URI")
            or getattr(settings, "NEO4J_URI", "bolt://neo4j:7687")
        )
        username = str(
            os.getenv("NEO4J_USER")
            or getattr(settings, "NEO4J_USER", "neo4j")
            or os.getenv("NEO4J_USERNAME")
            or "neo4j"
        )
        password = str(
            os.getenv("NEO4J_PASSWORD")
            or getattr(settings, "NEO4J_PASSWORD", "")
            or os.getenv("NEO4J_PASS")
            or ""
        )
        database = str(
            os.getenv("NEO4J_DATABASE")
            or getattr(settings, "NEO4J_DATABASE", "neo4j")
            or "neo4j"
        )
        return Neo4jGraphBackend(
            uri=uri,
            username=username,
            password=password,
            database=database,
        )

    return NoOpGraphBackend()
