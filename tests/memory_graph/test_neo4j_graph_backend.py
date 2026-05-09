from __future__ import annotations

import copy
import json

from guardian.memory_graph.graph_backend import (
    GRAPH_BACKEND_RESULT_STATUS_FAILED,
    GRAPH_BACKEND_RESULT_STATUS_WRITTEN,
)
from guardian.memory_graph.neo4j_graph_backend import Neo4jGraphBackend


class _FakeSession:
    def __init__(self, sink: list[tuple[str, dict]], fail: bool = False):
        self._sink = sink
        self._fail = fail

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute_write(self, fn):
        if self._fail:
            raise RuntimeError("neo4j unavailable")

        class _Tx:
            def run(_, query, **params):
                self._sink.append((" ".join(query.split()), params))

        fn(_Tx())


class _FakeDriver:
    def __init__(self, sink: list[tuple[str, dict]], fail: bool = False):
        self._sink = sink
        self._fail = fail

    def session(self, database=None):
        return _FakeSession(self._sink, fail=self._fail)


def _task() -> dict:
    return {
        "graph_write_id": "gwr-1",
        "nodes": [
            {
                "node_key": "n1",
                "node_type": "Document",
                "source_type": "retrieval",
                "source_id": "doc-1",
                "content": "hello",
                "metadata": {"k": "v"},
            },
            {
                "node_key": "n2",
                "node_type": "Thread",
                "source_type": "thread",
                "source_id": "t-1",
                "content": "",
                "metadata": {},
            },
        ],
        "edges": [
            {
                "edge_type": "PART_OF_THREAD",
                "from_node_key": "n1",
                "to_node_key": "n2",
                "metadata": {"source": "mapper"},
            }
        ],
    }


def test_neo4j_graph_backend_writes_nodes_and_edges_idempotently() -> None:
    sink: list[tuple[str, dict]] = []
    backend = Neo4jGraphBackend(
        uri="bolt://neo4j:7687",
        username="neo4j",
        password="pw",
        driver=_FakeDriver(sink),
    )

    task = _task()
    backend.write_graph_candidates(task)
    backend.write_graph_candidates(task)

    node_ops = [op for op in sink if "MERGE (n:GraphEntity" in op[0]]
    edge_ops = [op for op in sink if "MERGE (src)-[r:GRAPH_EDGE" in op[0]]
    assert len(node_ops) == 4
    assert len(edge_ops) == 2
    assert all(op[1]["node_key"] in {"n1", "n2"} for op in node_ops)
    assert all(isinstance(op[1]["metadata_json"], str) for op in node_ops)
    assert all(isinstance(op[1]["metadata_json"], str) for op in edge_ops)
    assert json.loads(node_ops[0][1]["metadata_json"]) in (
        {"k": "v"},
        {},
    )


def test_neo4j_graph_backend_returns_written_result() -> None:
    sink: list[tuple[str, dict]] = []
    backend = Neo4jGraphBackend(
        uri="bolt://neo4j:7687",
        username="neo4j",
        password="pw",
        driver=_FakeDriver(sink),
    )

    result = backend.write_graph_candidates(_task())
    assert result.status == GRAPH_BACKEND_RESULT_STATUS_WRITTEN
    assert result.graph_write_id == "gwr-1"
    assert result.node_count == 2
    assert result.edge_count == 1


def test_neo4j_graph_backend_does_not_mutate_task() -> None:
    sink: list[tuple[str, dict]] = []
    backend = Neo4jGraphBackend(
        uri="bolt://neo4j:7687",
        username="neo4j",
        password="pw",
        driver=_FakeDriver(sink),
    )
    task = _task()
    baseline = copy.deepcopy(task)

    backend.write_graph_candidates(task)

    assert task == baseline


def test_neo4j_graph_backend_failure_is_bounded() -> None:
    sink: list[tuple[str, dict]] = []
    backend = Neo4jGraphBackend(
        uri="bolt://neo4j:7687",
        username="neo4j",
        password="pw",
        driver=_FakeDriver(sink, fail=True),
    )

    result = backend.write_graph_candidates(_task())
    assert result.status == GRAPH_BACKEND_RESULT_STATUS_FAILED
    assert result.graph_write_id == "gwr-1"
    assert result.metadata.get("reason") == "neo4j_write_failed"
