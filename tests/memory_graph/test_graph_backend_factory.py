from __future__ import annotations

from guardian.memory_graph.graph_backend_factory import get_graph_backend
from guardian.memory_graph.neo4j_graph_backend import Neo4jGraphBackend
from guardian.memory_graph.noop_graph_backend import NoOpGraphBackend


def test_graph_backend_factory_returns_noop_by_default(monkeypatch) -> None:
    monkeypatch.delenv("CODEXIFY_ENABLE_GRAPH_WRITES", raising=False)
    monkeypatch.delenv("CODEXIFY_GRAPH_BACKEND", raising=False)
    backend = get_graph_backend()
    assert isinstance(backend, NoOpGraphBackend)


def test_graph_backend_factory_returns_neo4j_when_explicitly_enabled(
    monkeypatch,
) -> None:
    monkeypatch.setenv("CODEXIFY_ENABLE_GRAPH_WRITES", "1")
    monkeypatch.setenv("CODEXIFY_GRAPH_BACKEND", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "secret")
    backend = get_graph_backend()
    assert isinstance(backend, Neo4jGraphBackend)


def test_graph_backend_factory_does_not_enable_neo4j_implicitly(
    monkeypatch,
) -> None:
    monkeypatch.delenv("CODEXIFY_ENABLE_GRAPH_WRITES", raising=False)
    monkeypatch.setenv("CODEXIFY_GRAPH_BACKEND", "neo4j")
    monkeypatch.setenv("NEO4J_URI", "bolt://reachable:7687")
    monkeypatch.setenv("NEO4J_PASSWORD", "secret")
    backend = get_graph_backend()
    assert isinstance(backend, NoOpGraphBackend)
