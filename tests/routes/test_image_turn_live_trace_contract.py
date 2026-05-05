from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from guardian.core.dependencies import RequestUserScope
from guardian.routes import chat


@pytest.fixture(autouse=True)
def _stub_chatlog_db(monkeypatch):
    monkeypatch.setattr(
        chat,
        "chatlog_db",
        SimpleNamespace(
            get_chat_thread=lambda thread_id: {
                "id": thread_id,
                "user_id": "local",
            }
        ),
    )

    request_scope = RequestUserScope(
        user_id="local",
        account_id="local",
        multi_user_enabled=False,
    )
    for name in (
        "get_latest_rag_trace",
        "get_latest_rag_trace_endpoint",
        "api_get_latest_rag_trace",
    ):
        func = getattr(chat, name, None)
        defaults = getattr(func, "__defaults__", None)
        if not defaults:
            continue
        patched_defaults = list(defaults)
        patched_defaults[-1] = request_scope
        monkeypatch.setattr(
            func,
            "__defaults__",
            tuple(patched_defaults),
            raising=False,
        )


def test_live_rag_trace_exposes_sanitized_policy_provenance_and_image_metadata(
    monkeypatch,
):
    thread_id = 501
    task_id = "task-501"
    expected_effective_policy = {
        "source_mode": "workspace",
        "widening_enabled": True,
        "identity_scope": "workspace",
    }
    expected_retrieval_provenance = {
        "requested_source_mode": "workspace",
        "normalized_source_mode": "workspace",
        "source_hit_counts": {
            "semantic_total": 1,
            "thread_semantic": 0,
            "obsidian_semantic": 0,
            "other_semantic": 1,
            "project_documents": 0,
            "thread_documents": 1,
            "global_documents": 0,
            "other_documents": 0,
            "memory": 0,
            "graph": 1,
        },
        "retrieval_status": "workspace_local_success",
    }
    trace_payload = {
        "documents": [
            {
                "id": "doc-1",
                "title": "vision-note.md",
                "score": 0.91,
                "snippet": "raw doc text with data:image/png;base64,AAAA",
                "provenance": {"relation": "thread"},
            }
        ],
        "graph": [
            {
                "node_id": "graph-1",
                "kind": "memory",
                "text": "raw graph content",
            }
        ],
        "source_mode": "workspace",
        "widen_reason": "explicit_workspace",
        "retrieval_target": "latest_turn",
        "retrieval_query_matches_latest_turn": True,
        "effective_policy": expected_effective_policy,
        "retrieval_provenance": expected_retrieval_provenance,
    }
    payload_summary = {
        "message_count": 2,
        "source_mode": "workspace",
        "effective_source_mode": "workspace",
        "normalized_source_mode": "workspace",
        "semantic_count": 1,
        "memory_count": 0,
        "graph_hit_count": 1,
        "linked_document_count": 1,
        "obsidian_count": 0,
        "image_routing_path": "vlm",
        "image_attachment_count": 1,
        "derived_image_context_injected": False,
        "effective_policy": expected_effective_policy,
        "retrieval_provenance": expected_retrieval_provenance,
    }

    chat._thread_latest_task[thread_id] = task_id
    monkeypatch.setattr(chat, "_fetch_thread_metadata", lambda _thread_id: {})
    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda _task_id: {
            "trace": trace_payload,
            "payload_summary": payload_summary,
        },
    )

    trace = chat.get_latest_rag_trace(thread_id, api_key="test-key")
    trace_text = json.dumps(trace, sort_keys=True)

    assert trace["trace_available"] is True
    assert trace["trace_unavailable_reason"] is None
    assert trace["effective_policy"] == expected_effective_policy
    assert trace["retrieval_provenance"] == expected_retrieval_provenance
    assert trace["retrieval_summary"]["document_count"] == 1
    assert trace["retrieval_summary"]["graph_count"] == 1
    assert trace["retrieval_summary"]["source_mode"] == "workspace"
    assert trace["retrieval_summary"]["retrieval_target"] == "latest_turn"
    assert trace["retrieval_summary"][
        "retrieval_query_matches_latest_turn"
    ] is True
    assert trace["retrieval_summary"]["source_hit_counts"] == {
        "semantic_total": 1,
        "thread_semantic": 0,
        "obsidian_semantic": 0,
        "other_semantic": 1,
        "project_documents": 0,
        "thread_documents": 1,
        "global_documents": 0,
        "other_documents": 0,
        "memory": 0,
        "graph": 1,
    }
    assert trace["image_routing"] == {
        "image_routing_path": "vlm",
        "image_attachment_count": 1,
        "derived_image_context_injected": False,
    }
    assert trace["documents"][0]["id"] == "doc-1"
    assert trace["documents"][0]["title"] == "vision-note.md"
    assert trace["documents"][0]["score"] == 0.91
    assert trace["documents"][0]["snippet"] is None
    assert trace["graph"][0]["node_id"] == "graph-1"
    assert trace["graph"][0]["kind"] == "memory"
    assert trace["graph"][0]["text"] is None
    assert "raw doc text with data:image/png;base64,AAAA" not in trace_text
    assert "raw graph content" not in trace_text
    assert "data:image/png;base64,AAAA" not in trace_text

    chat._thread_latest_task.pop(thread_id, None)
    chat._rag_traces.pop(thread_id, None)


def test_live_rag_trace_returns_empty_surface_without_trace(
    monkeypatch,
):
    thread_id = 502
    task_id = "task-502"

    chat._thread_latest_task[thread_id] = task_id
    monkeypatch.setattr(chat, "_fetch_thread_metadata", lambda _thread_id: {})
    monkeypatch.setattr(chat, "_get_task_completed_payload", lambda _task_id: None)
    monkeypatch.setattr(
        chat,
        "get_latest_eval_diagnostics",
        lambda *args, **kwargs: None,
    )

    trace = chat.get_latest_rag_trace(thread_id, api_key="test-key")
    trace_text = json.dumps(trace, sort_keys=True)

    assert trace["trace_available"] is False
    assert trace["trace_unavailable_reason"] is None
    assert trace["effective_policy"] is None
    assert trace["retrieval_summary"] is None
    assert trace["retrieval_provenance"] is None
    assert trace["image_routing"] is None
    assert trace["documents"] == []
    assert trace["graph"] == []
    assert trace["thread_id"] == thread_id
    assert trace["project_id"] is None
    assert trace["depth_mode"] is None
    assert trace["source_mode"] is None
    assert trace["widen_reason"] == "none"
    assert "raw doc text" not in trace_text
    assert "raw graph content" not in trace_text
    assert "base64" not in trace_text

    chat._thread_latest_task.pop(thread_id, None)
    chat._rag_traces.pop(thread_id, None)
