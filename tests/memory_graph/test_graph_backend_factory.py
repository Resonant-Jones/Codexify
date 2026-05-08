from __future__ import annotations

from guardian.memory_graph.graph_backend_factory import (
    _FACTORY_CACHE,
    GRAPH_BACKEND_SELECTION_NEO4J,
    GRAPH_BACKEND_SELECTION_NOOP,
    get_graph_backend,
    get_graph_backend_adapter,
    get_graph_backend_selection_metadata,
    resolve_graph_backend_selection,
)
from guardian.memory_graph.neo4j_graph_backend import Neo4jGraphBackend
from guardian.memory_graph.noop_graph_backend import (
    NoOpGraphBackend,
    NoopGraphBackendAdapter,
)


def _clear_factory_cache():
    _FACTORY_CACHE.clear()


def test_graph_backend_factory_defaults_to_noop_when_no_env_set(monkeypatch):
    monkeypatch.delenv("CODEXIFY_ENABLE_GRAPH_WRITES", raising=False)
    monkeypatch.delenv("CODEXIFY_GRAPH_BACKEND", raising=False)
    _clear_factory_cache()

    selection = resolve_graph_backend_selection()
    assert selection == GRAPH_BACKEND_SELECTION_NOOP

    metadata = get_graph_backend_selection_metadata()
    assert metadata["effective_backend"] == GRAPH_BACKEND_SELECTION_NOOP
    assert metadata["is_noop"] is True


def test_graph_backend_factory_returns_noop_when_flag_disabled_even_if_backend_is_neo4j(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_ENABLE_GRAPH_WRITES", "false")
    monkeypatch.setenv("CODEXIFY_GRAPH_BACKEND", "neo4j")
    _clear_factory_cache()

    selection = resolve_graph_backend_selection()
    assert selection == GRAPH_BACKEND_SELECTION_NOOP

    metadata = get_graph_backend_selection_metadata()
    assert metadata["effective_backend"] == GRAPH_BACKEND_SELECTION_NOOP
    assert metadata["enable_graph_writes_flag"] is False
    assert metadata["raw_backend_env"] == "neo4j"


def test_graph_backend_factory_returns_noop_when_neo4j_env_present_but_flag_disabled(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_ENABLE_GRAPH_WRITES", "0")
    monkeypatch.setenv("CODEXIFY_GRAPH_BACKEND", "neo4j")
    _clear_factory_cache()

    selection = resolve_graph_backend_selection()
    assert selection == GRAPH_BACKEND_SELECTION_NOOP


def test_graph_backend_factory_requires_explicit_enablement_and_backend_selection(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_ENABLE_GRAPH_WRITES", "true")
    monkeypatch.delenv("CODEXIFY_GRAPH_BACKEND", raising=False)
    _clear_factory_cache()

    selection = resolve_graph_backend_selection()
    assert selection == GRAPH_BACKEND_SELECTION_NOOP

    metadata = get_graph_backend_selection_metadata()
    assert metadata["enable_graph_writes_flag"] is True
    assert metadata["raw_backend_env"] == ""
    assert metadata["effective_backend"] == GRAPH_BACKEND_SELECTION_NOOP


def test_graph_backend_factory_fails_closed_on_invalid_backend_value(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_ENABLE_GRAPH_WRITES", "true")
    monkeypatch.setenv("CODEXIFY_GRAPH_BACKEND", "invalid_backend")
    _clear_factory_cache()

    selection = resolve_graph_backend_selection()
    assert selection == GRAPH_BACKEND_SELECTION_NOOP

    metadata = get_graph_backend_selection_metadata()
    assert metadata["effective_backend"] == GRAPH_BACKEND_SELECTION_NOOP
    assert metadata["raw_backend_env"] == "invalid_backend"


def test_graph_backend_factory_selects_neo4j_when_fully_enabled(monkeypatch):
    monkeypatch.setenv("CODEXIFY_ENABLE_GRAPH_WRITES", "true")
    monkeypatch.setenv("CODEXIFY_GRAPH_BACKEND", "neo4j")
    _clear_factory_cache()

    selection = resolve_graph_backend_selection()
    assert selection == GRAPH_BACKEND_SELECTION_NEO4J

    metadata = get_graph_backend_selection_metadata()
    assert metadata["effective_backend"] == GRAPH_BACKEND_SELECTION_NEO4J
    assert metadata["is_noop"] is False


def test_graph_backend_factory_selects_noop_when_backend_is_noop_and_flag_true(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_ENABLE_GRAPH_WRITES", "true")
    monkeypatch.setenv("CODEXIFY_GRAPH_BACKEND", "noop")
    _clear_factory_cache()

    selection = resolve_graph_backend_selection()
    assert selection == GRAPH_BACKEND_SELECTION_NOOP


def test_graph_backend_factory_get_adapter_returns_noop_when_disabled(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_ENABLE_GRAPH_WRITES", "false")
    monkeypatch.setenv("CODEXIFY_GRAPH_BACKEND", "neo4j")
    _clear_factory_cache()

    adapter = get_graph_backend_adapter()
    assert isinstance(adapter, NoopGraphBackendAdapter)


def test_graph_backend_factory_truthy_variants(monkeypatch):
    for truthy in ("1", "true", "TRUE", "yes", "YES", "on", "ON"):
        monkeypatch.setenv("CODEXIFY_ENABLE_GRAPH_WRITES", truthy)
        monkeypatch.setenv("CODEXIFY_GRAPH_BACKEND", "neo4j")
        _clear_factory_cache()

        selection = resolve_graph_backend_selection()
        assert (
            selection == GRAPH_BACKEND_SELECTION_NEO4J
        ), f"Failed for truthy value: {truthy}"


def test_graph_backend_factory_falsy_variants(monkeypatch):
    for falsy in ("0", "false", "FALSE", "no", "NO", "off", "OFF", ""):
        monkeypatch.setenv("CODEXIFY_ENABLE_GRAPH_WRITES", falsy)
        monkeypatch.setenv("CODEXIFY_GRAPH_BACKEND", "neo4j")
        _clear_factory_cache()

        selection = resolve_graph_backend_selection()
        assert (
            selection == GRAPH_BACKEND_SELECTION_NOOP
        ), f"Failed for falsy value: {falsy}"


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
