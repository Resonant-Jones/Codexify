from guardian.memory_graph.graph_write_hook import build_graph_write_candidate


def test_graph_write_candidate_structure():
    assistant_message = {
        "id": "msg_1",
        "content": "Hello world",
        "role": "assistant",
        "created_at": "2026-01-01T00:00:00Z",
    }
    assistant_message_before = dict(assistant_message)

    thread = {"id": "thread_1", "user_id": "account_1"}
    project = {"id": "project_1"}

    candidate = build_graph_write_candidate(
        assistant_message,
        thread,
        project,
    )

    assert candidate["source_id"] == "msg_1"
    assert candidate["thread_id"] == "thread_1"
    assert candidate["project_id"] == "project_1"
    assert candidate["account_id"] == "account_1"
    assert candidate["idempotency_key"] == "graph:msg_1"
    assert candidate["content"] == "Hello world"
    assert candidate["metadata"] == {
        "role": "assistant",
        "created_at": "2026-01-01T00:00:00Z",
    }
    assert candidate["identity_scope"] == {
        "account_id": "account_1",
        "thread_id": "thread_1",
        "project_id": "project_1",
        "source_id": "msg_1",
    }
    assert assistant_message == assistant_message_before
