from __future__ import annotations

import uuid

from guardian.core.chat_completion_service import (
    DEBUG_LATEST_COMPLETION_TASK_ID_METADATA_KEY,
    DEBUG_LATEST_RAG_TRACE_METADATA_KEY,
    DEBUG_RAG_TRACE_CANDIDATE_METADATA_KEY,
)
from guardian.routes import chat


def test_rag_trace_includes_profile_debug_fields(monkeypatch):
    chat._thread_latest_task[42] = "task-42"

    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda _task_id: {
            "trace": {"documents": [], "graph": []},
            "active_profile_id": "local_mode",
            "provider_override": "local",
            "model_override": "mlx-community/Llama-3B",
            "injection_hash": "abc123",
            "retrieval_mode": "deep",
            "model_mode": "local",
        },
    )

    trace = chat.get_latest_rag_trace(42, api_key="test-key")
    assert trace["active_profile_id"] == "local_mode"
    assert trace["provider_override"] == "local"
    assert trace["model_override"] == "mlx-community/Llama-3B"
    assert trace["injection_hash"] == "abc123"
    assert trace["retrieval_mode"] == "deep"
    assert trace["model_mode"] == "local"

    chat._thread_latest_task.pop(42, None)
    chat._rag_traces.pop(42, None)


def test_rag_trace_exposes_payload_summary(monkeypatch):
    chat._thread_latest_task[77] = "task-77"

    payload_summary = {"payload_char_count": 10, "message_count": 2}

    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda _task_id: {
            "trace": {"documents": [], "graph": []},
            "payload_summary": payload_summary,
        },
    )

    trace = chat.get_latest_rag_trace(77, api_key="test-key")
    assert trace["payload_summary"] == payload_summary

    chat._thread_latest_task.pop(77, None)
    chat._rag_traces.pop(77, None)


def test_rag_trace_uses_persisted_candidate_for_completed_task(monkeypatch):
    thread_id = 88
    task_id = str(uuid.uuid4())
    candidate_trace = {
        "documents": [
            {
                "id": "doc-1",
                "title": "thread-note.md",
                "score": 0.92,
                "snippet": "relevant snippet...",
            }
        ],
        "graph": [],
    }
    promoted: list[tuple[int, str, dict[str, object]]] = []

    monkeypatch.setattr(
        chat,
        "_fetch_thread_metadata",
        lambda _thread_id: {
            DEBUG_LATEST_COMPLETION_TASK_ID_METADATA_KEY: task_id,
            DEBUG_RAG_TRACE_CANDIDATE_METADATA_KEY: {
                "task_id": task_id,
                "thread_id": thread_id,
                "trace": candidate_trace,
            },
        },
    )
    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda _task_id: {
            "thread_id": thread_id,
            "payload_summary": {"message_count": 2},
        },
    )
    monkeypatch.setattr(
        chat,
        "_persist_thread_latest_rag_trace",
        lambda _thread_id, _task_id, trace: promoted.append(
            (_thread_id, _task_id, dict(trace))
        ),
    )

    trace = chat.get_latest_rag_trace(thread_id, api_key="test-key")

    assert trace["documents"] == candidate_trace["documents"]
    assert trace["graph"] == []
    assert trace["payload_summary"] == {"message_count": 2}
    assert promoted == [(thread_id, task_id, candidate_trace)]
    assert chat._thread_latest_task[thread_id] == task_id

    chat._thread_latest_task.pop(thread_id, None)
    chat._rag_traces.pop(thread_id, None)


def test_rag_trace_remains_empty_without_completed_evidence(monkeypatch):
    thread_id = 99
    task_id = str(uuid.uuid4())

    monkeypatch.setattr(
        chat,
        "_fetch_thread_metadata",
        lambda _thread_id: {
            DEBUG_LATEST_COMPLETION_TASK_ID_METADATA_KEY: task_id,
            DEBUG_RAG_TRACE_CANDIDATE_METADATA_KEY: {
                "task_id": task_id,
                "thread_id": thread_id,
                "trace": {
                    "documents": [
                        {
                            "id": "doc-2",
                            "title": "x",
                            "score": 1.0,
                            "snippet": "x",
                        }
                    ],
                    "graph": [],
                },
            },
        },
    )
    monkeypatch.setattr(
        chat, "_get_task_completed_payload", lambda _task_id: None
    )

    trace = chat.get_latest_rag_trace(thread_id, api_key="test-key")

    assert trace["documents"] == []
    assert trace["graph"] == []

    chat._thread_latest_task.pop(thread_id, None)
    chat._rag_traces.pop(thread_id, None)


def test_rag_trace_does_not_bleed_across_threads(monkeypatch):
    thread_one = 101
    thread_two = 202
    trace_one = {
        "documents": [
            {"id": "doc-a", "title": "a.md", "score": 0.8, "snippet": "a..."}
        ],
        "graph": [],
    }
    trace_two = {
        "documents": [
            {"id": "doc-b", "title": "b.md", "score": 0.7, "snippet": "b..."}
        ],
        "graph": [{"node_id": "node-b", "kind": "memory", "text": "b node"}],
    }
    metadata_by_thread = {
        thread_one: {
            DEBUG_LATEST_RAG_TRACE_METADATA_KEY: {
                "task_id": str(uuid.uuid4()),
                "thread_id": thread_one,
                "trace": trace_one,
            }
        },
        thread_two: {
            DEBUG_LATEST_RAG_TRACE_METADATA_KEY: {
                "task_id": str(uuid.uuid4()),
                "thread_id": thread_two,
                "trace": trace_two,
            }
        },
    }

    monkeypatch.setattr(
        chat,
        "_fetch_thread_metadata",
        lambda thread_id: metadata_by_thread.get(thread_id, {}),
    )
    monkeypatch.setattr(
        chat, "_get_task_completed_payload", lambda _task_id: None
    )

    first = chat.get_latest_rag_trace(thread_one, api_key="test-key")
    second = chat.get_latest_rag_trace(thread_two, api_key="test-key")

    assert first["documents"] == trace_one["documents"]
    assert first["graph"] == trace_one["graph"]
    assert second["documents"] == trace_two["documents"]
    assert second["graph"] == trace_two["graph"]

    chat._thread_latest_task.pop(thread_one, None)
    chat._thread_latest_task.pop(thread_two, None)
    chat._rag_traces.pop(thread_one, None)
    chat._rag_traces.pop(thread_two, None)
