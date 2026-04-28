from __future__ import annotations

from guardian.memory_graph.graph_write_identity import (
    build_graph_write_identity,
    compute_graph_write_fingerprint,
)


def _graph_payload() -> tuple[list[dict], list[dict], list[str]]:
    nodes = [
        {
            "node_key": "graph:document:2",
            "node_type": "Document",
            "source_type": "retrieval",
            "source_id": "doc-2",
            "content": "Project brief",
            "metadata": {
                "project_id": "project-1",
                "thread_id": "thread-1",
                "labels": ["b", "a"],
            },
        },
        {
            "node_key": "graph:message:1",
            "node_type": "Message",
            "source_type": "thread",
            "source_id": "msg-1",
            "content": "Source message",
            "metadata": {
                "thread_id": "thread-1",
                "project_id": "project-1",
            },
        },
    ]
    edges = [
        {
            "edge_type": "PART_OF_THREAD",
            "from_node_key": "graph:document:2",
            "to_node_key": "graph:message:1",
            "metadata": {"thread_id": "thread-1"},
        }
    ]
    warnings = ["late", "early"]
    return nodes, edges, warnings


def test_graph_write_identity_is_deterministic_for_same_payload():
    nodes, edges, warnings = _graph_payload()

    first = build_graph_write_identity(
        request_id="req-1",
        thread_id=7,
        candidate_trace_id="trace-1",
        nodes=nodes,
        edges=edges,
        warnings=warnings,
    )
    second = build_graph_write_identity(
        request_id="req-1",
        thread_id=7,
        candidate_trace_id="trace-1",
        nodes=nodes,
        edges=edges,
        warnings=warnings,
    )

    assert first["graph_write_id"] == second["graph_write_id"]
    assert first["idempotency_key"] == second["idempotency_key"]
    assert first["graph_fingerprint"] == second["graph_fingerprint"]


def test_graph_write_identity_is_order_insensitive_for_equivalent_graph_payload():
    nodes, edges, warnings = _graph_payload()
    reversed_nodes = list(reversed(nodes))
    reversed_edges = list(reversed(edges))
    reversed_warnings = list(reversed(warnings))

    fingerprint_one = compute_graph_write_fingerprint(nodes, edges, warnings)
    fingerprint_two = compute_graph_write_fingerprint(
        reversed_nodes,
        reversed_edges,
        reversed_warnings,
    )

    identity_one = build_graph_write_identity(
        request_id="req-1",
        thread_id=7,
        candidate_trace_id="trace-1",
        nodes=nodes,
        edges=edges,
        warnings=warnings,
    )
    identity_two = build_graph_write_identity(
        request_id="req-1",
        thread_id=7,
        candidate_trace_id="trace-1",
        nodes=reversed_nodes,
        edges=reversed_edges,
        warnings=reversed_warnings,
    )

    assert fingerprint_one == fingerprint_two
    assert identity_one["graph_write_id"] == identity_two["graph_write_id"]
    assert identity_one["idempotency_key"] == identity_two["idempotency_key"]


def test_graph_write_identity_changes_when_graph_shape_changes():
    nodes, edges, warnings = _graph_payload()

    baseline = build_graph_write_identity(
        request_id="req-1",
        thread_id=7,
        candidate_trace_id="trace-1",
        nodes=nodes,
        edges=edges,
        warnings=warnings,
    )
    changed = build_graph_write_identity(
        request_id="req-1",
        thread_id=7,
        candidate_trace_id="trace-1",
        nodes=nodes
        + [
            {
                "node_key": "graph:fact:3",
                "node_type": "MemoryFact",
                "source_type": "memory",
                "source_id": "fact-1",
                "content": "New fact",
                "metadata": {"thread_id": "thread-1"},
            }
        ],
        edges=edges,
        warnings=warnings,
    )

    assert baseline["graph_fingerprint"] != changed["graph_fingerprint"]
    assert baseline["graph_write_id"] != changed["graph_write_id"]
    assert baseline["idempotency_key"] != changed["idempotency_key"]


def test_graph_write_identity_keeps_candidate_trace_boundary():
    nodes, edges, warnings = _graph_payload()

    first = build_graph_write_identity(
        request_id="req-1",
        thread_id=7,
        candidate_trace_id="trace-1",
        nodes=nodes,
        edges=edges,
        warnings=warnings,
    )
    second = build_graph_write_identity(
        request_id="req-1",
        thread_id=7,
        candidate_trace_id="trace-2",
        nodes=nodes,
        edges=edges,
        warnings=warnings,
    )

    assert first["graph_fingerprint"] == second["graph_fingerprint"]
    assert first["graph_write_id"] != second["graph_write_id"]
    assert first["idempotency_key"] != second["idempotency_key"]
