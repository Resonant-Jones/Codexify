"""Factory for selecting the derived graph-write backend."""

from __future__ import annotations

import os

from guardian.core.config import get_settings
from guardian.memory_graph.graph_backend import (
    GRAPH_BACKEND_KIND_NEO4J,
    GRAPH_BACKEND_KIND_NOOP,
)
from guardian.memory_graph.neo4j_graph_backend import Neo4jGraphBackend
from guardian.memory_graph.noop_graph_backend import NoOpGraphBackend


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def get_graph_backend():
    settings = get_settings()
    enabled = _env_bool(
        "CODEXIFY_ENABLE_GRAPH_WRITES",
        bool(getattr(settings, "CODEXIFY_ENABLE_GRAPH_WRITES", False)),
    )
    configured_kind = (
        str(
            os.getenv("CODEXIFY_GRAPH_BACKEND")
            or getattr(
                settings, "CODEXIFY_GRAPH_BACKEND", GRAPH_BACKEND_KIND_NOOP
            )
            or GRAPH_BACKEND_KIND_NOOP
        )
        .strip()
        .lower()
    )

    if enabled and configured_kind == GRAPH_BACKEND_KIND_NEO4J:
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


__all__ = [
    "get_graph_backend",
]
