from __future__ import annotations

from guardian.core import graph_write_inspection_store
from guardian.core.graph_write_inspection_store import (
    GRAPH_WRITE_INSPECTION_STATUS_DUPLICATE_SKIPPED,
)


def _seed_snapshot(
    thread_id: int,
    *,
    receipt_status: str,
    graph_write_id: str,
    candidate_trace_id: str,
    request_id: str,
) -> dict[str, object]:
    snapshot = {
        "thread_id": thread_id,
        "request_id": request_id,
        "candidate_trace_id": candidate_trace_id,
        "graph_write_id": graph_write_id,
        "idempotency_key": f"graph-write:{candidate_trace_id}:fingerprint",
        "receipt_status": receipt_status,
        "node_count": 2,
        "edge_count": 1,
        "warning_count": 0,
        "node_types": ["Document", "Thread"],
        "edge_types": ["PART_OF_THREAD"],
        "created_at": "2026-04-28T12:00:00Z",
    }
    graph_write_inspection_store.store_graph_write_inspection_snapshot(
        thread_id,
        snapshot,
    )
    return snapshot


def test_graph_write_inspection_route_returns_latest_snapshot(
    test_client, mock_db
):
    mock_db.get_chat_thread.side_effect = lambda thread_id: {
        "id": thread_id,
        "user_id": "test_user",
    }
    _seed_snapshot(
        1,
        receipt_status="claimed",
        graph_write_id="gwr_test_latest",
        candidate_trace_id="trace-1",
        request_id="req-1",
    )

    response = test_client.get("/chat/1/debug/graph-write/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == 1
    assert body["status"] == "ok"
    snapshot = body["graph_write_inspection"]
    assert snapshot["thread_id"] == 1
    assert snapshot["graph_write_id"] == "gwr_test_latest"
    assert snapshot["receipt_status"] == "claimed"
    assert snapshot["node_count"] == 2
    assert snapshot["edge_count"] == 1
    assert snapshot["node_types"] == ["Document", "Thread"]
    assert snapshot["edge_types"] == ["PART_OF_THREAD"]


def test_graph_write_inspection_route_returns_empty_state_when_missing(
    test_client, mock_db
):
    mock_db.get_chat_thread.side_effect = lambda thread_id: {
        "id": thread_id,
        "user_id": "test_user",
    }
    response = test_client.get("/chat/2/debug/graph-write/latest")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "thread_id": 2,
        "status": "empty",
        "graph_write_inspection": None,
    }


def test_graph_write_inspection_route_is_thread_scoped(test_client, mock_db):
    mock_db.get_chat_thread.side_effect = lambda thread_id: {
        "id": thread_id,
        "user_id": "test_user",
    }
    _seed_snapshot(
        1,
        receipt_status="claimed",
        graph_write_id="gwr_thread_one",
        candidate_trace_id="trace-1",
        request_id="req-1",
    )
    _seed_snapshot(
        2,
        receipt_status="claimed",
        graph_write_id="gwr_thread_two",
        candidate_trace_id="trace-2",
        request_id="req-2",
    )

    response_one = test_client.get("/chat/1/debug/graph-write/latest")
    response_two = test_client.get("/chat/2/debug/graph-write/latest")

    assert response_one.status_code == 200
    assert response_two.status_code == 200
    assert response_one.json()["graph_write_inspection"]["graph_write_id"] == (
        "gwr_thread_one"
    )
    assert response_two.json()["graph_write_inspection"]["graph_write_id"] == (
        "gwr_thread_two"
    )


def test_graph_write_inspection_route_exposes_duplicate_skipped_status(
    test_client, mock_db
):
    mock_db.get_chat_thread.side_effect = lambda thread_id: {
        "id": thread_id,
        "user_id": "test_user",
    }
    _seed_snapshot(
        3,
        receipt_status=GRAPH_WRITE_INSPECTION_STATUS_DUPLICATE_SKIPPED,
        graph_write_id="gwr_duplicate",
        candidate_trace_id="trace-3",
        request_id="req-3",
    )

    response = test_client.get("/chat/3/debug/graph-write/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["graph_write_inspection"]["receipt_status"] == (
        GRAPH_WRITE_INSPECTION_STATUS_DUPLICATE_SKIPPED
    )
