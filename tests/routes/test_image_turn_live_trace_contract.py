from __future__ import annotations

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
        "get_latest_retrieval_posture",
        "get_latest_retrieval_posture_endpoint",
        "get_retrieval_posture_history",
        "get_retrieval_posture_history_endpoint",
        "api_get_latest_rag_trace",
        "api_get_latest_retrieval_posture",
        "api_get_retrieval_posture_history",
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


def test_live_rag_trace_exposes_image_turn_completion_metadata(monkeypatch):
    thread_id = 804
    chat._thread_latest_task[thread_id] = "task-804"

    payload_summary = {
        "payload_char_count": 64,
        "message_count": 3,
        "image_routing_path": "vlm",
        "image_attachment_count": 1,
        "derived_image_context_injected": False,
        "requested_provider": "local",
        "requested_model": "medgemma:4b-it-q8_0",
        "attempted_provider": "local",
        "attempted_model": "medgemma:4b-it-q8_0",
        "resolved_provider": "local",
        "resolved_model": "library2/ministral-3:8b",
        "final_provider": "local",
        "final_model": "library2/ministral-3:8b",
        "selection_source": "LOCAL_LLM_MODEL",
        "fallback_reason": (
            "requested model 'medgemma:4b-it-q8_0' was overridden by "
            "configured local chat model 'library2/ministral-3:8b' from "
            "LOCAL_CHAT_MODEL"
        ),
        "model_resolution": {
            "requested_model": "medgemma:4b-it-q8_0",
            "model": "library2/ministral-3:8b",
            "source": "LOCAL_LLM_MODEL",
            "strict": False,
            "message": (
                "requested model 'medgemma:4b-it-q8_0' was overridden by "
                "configured local chat model 'library2/ministral-3:8b' from "
                "LOCAL_CHAT_MODEL"
            ),
        },
        "model_selection": {
            "requested_provider": "local",
            "requested_model": "medgemma:4b-it-q8_0",
            "attempted_provider": "local",
            "attempted_model": "medgemma:4b-it-q8_0",
            "resolved_provider": "local",
            "resolved_model": "library2/ministral-3:8b",
            "final_provider": "local",
            "final_model": "library2/ministral-3:8b",
            "selection_source": "LOCAL_LLM_MODEL",
            "policy_reason": "LOCAL_LLM_MODEL",
            "fallback_reason": (
                "requested model 'medgemma:4b-it-q8_0' was overridden by "
                "configured local chat model 'library2/ministral-3:8b' from "
                "LOCAL_CHAT_MODEL"
            ),
            "model_resolution": {
                "requested_model": "medgemma:4b-it-q8_0",
                "model": "library2/ministral-3:8b",
                "source": "LOCAL_LLM_MODEL",
                "strict": False,
                "message": (
                    "requested model 'medgemma:4b-it-q8_0' was overridden by "
                    "configured local chat model 'library2/ministral-3:8b' from "
                    "LOCAL_CHAT_MODEL"
                ),
            },
        },
        "retrieval_provenance": {
            "requested_source_mode": "project",
            "normalized_source_mode": "project",
            "source_hit_counts": {
                "semantic_total": 1,
                "thread_semantic": 1,
                "obsidian_semantic": 0,
                "other_semantic": 0,
                "project_documents": 0,
                "thread_documents": 0,
                "global_documents": 0,
                "other_documents": 0,
                "memory": 0,
                "graph": 0,
            },
            "retrieval_status": "workspace_local_success",
        },
        "retrieval_suppression": {
            "count": 1,
            "counts_by_reason": {
                "assistant_vision_refusal_on_image_turn": 1,
            },
        },
    }

    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda _task_id: {
            "trace": {
                "documents": [],
                "graph": [],
                "retrieval_policy": {"source_mode": "project"},
            },
            "payload_summary": payload_summary,
        },
    )

    trace = chat.get_latest_rag_trace(thread_id, api_key="test-key")
    assert trace["image_routing_path"] == "vlm"
    assert trace["retrieval_policy"] == {"source_mode": "project"}
    assert trace["retrieval_provenance"]["retrieval_status"] == (
        "workspace_local_success"
    )
    assert trace["retrieval_suppression"]["counts_by_reason"][
        "assistant_vision_refusal_on_image_turn"
    ] == 1
    assert trace["completion"]["requested_model"] == "medgemma:4b-it-q8_0"
    assert trace["completion"]["final_model"] == "library2/ministral-3:8b"
    assert trace["completion"]["selection_source"] == "LOCAL_LLM_MODEL"
    assert trace["completion"]["fallback_reason"] == (
        "requested model 'medgemma:4b-it-q8_0' was overridden by "
        "configured local chat model 'library2/ministral-3:8b' from "
        "LOCAL_CHAT_MODEL"
    )
    assert trace["model_selection"]["policy_reason"] == "LOCAL_LLM_MODEL"

    chat._thread_latest_task.pop(thread_id, None)
    chat._rag_traces.pop(thread_id, None)


def test_live_rag_trace_falls_back_to_eval_snapshot(monkeypatch):
    thread_id = 805
    chat._thread_latest_task[thread_id] = "task-805"

    monkeypatch.setattr(chat, "_get_task_completed_payload", lambda _task: None)
    monkeypatch.setattr(
        chat,
        "get_latest_eval_diagnostics",
        lambda _db, *, thread_id: {
            "thread_id": thread_id,
            "trace_snapshot": {
                "trace_snapshot_id": "snapshot-805",
                "task_id": "task-805",
                "thread_id": thread_id,
                "trace": {
                    "documents": [],
                    "graph": [],
                    "retrieval_policy": {"source_mode": "project"},
                    "retrieval_suppression": {
                        "count": 1,
                        "counts_by_reason": {
                            "assistant_vision_refusal_on_image_turn": 1,
                        },
                    },
                },
                "payload_summary": {
                    "image_routing_path": "interpreter",
                    "requested_model": "medgemma:4b-it-q8_0",
                    "final_model": "library2/ministral-3:8b",
                    "selection_source": "LOCAL_LLM_MODEL",
                    "fallback_reason": (
                        "requested model 'medgemma:4b-it-q8_0' was overridden "
                        "by configured local chat model "
                        "'library2/ministral-3:8b' from LOCAL_CHAT_MODEL"
                    ),
                    "model_resolution": {
                        "requested_model": "medgemma:4b-it-q8_0",
                        "model": "library2/ministral-3:8b",
                        "source": "LOCAL_LLM_MODEL",
                        "strict": False,
                        "message": (
                            "requested model 'medgemma:4b-it-q8_0' was "
                            "overridden by configured local chat model "
                            "'library2/ministral-3:8b' from LOCAL_CHAT_MODEL"
                        ),
                    },
                    "retrieval_provenance": {
                        "requested_source_mode": "project",
                        "normalized_source_mode": "project",
                    },
                    "retrieval_suppression": {
                        "count": 1,
                        "counts_by_reason": {
                            "assistant_vision_refusal_on_image_turn": 1,
                        },
                    },
                },
                "metadata": {
                    "selection_source": "LOCAL_LLM_MODEL",
                    "attempted_provider": "local",
                    "attempted_model": "medgemma:4b-it-q8_0",
                    "final_provider": "local",
                    "final_model": "library2/ministral-3:8b",
                },
                "retrieval_summary": {
                    "retrieval_provenance": {
                        "requested_source_mode": "project",
                        "normalized_source_mode": "project",
                        "retrieval_status": "workspace_local_success",
                    }
                },
            },
            "verdicts": [],
        },
    )

    trace = chat.get_latest_rag_trace(thread_id, api_key="test-key")
    assert trace["retrieval_policy"] == {"source_mode": "project"}
    assert trace["retrieval_suppression"]["counts_by_reason"][
        "assistant_vision_refusal_on_image_turn"
    ] == 1
    assert trace["image_routing_path"] == "interpreter"
    assert trace["completion"]["requested_model"] == "medgemma:4b-it-q8_0"
    assert trace["completion"]["final_model"] == "library2/ministral-3:8b"
    assert trace["completion"]["selection_source"] == "LOCAL_LLM_MODEL"
    assert trace["completion"]["fallback_reason"] == (
        "requested model 'medgemma:4b-it-q8_0' was overridden by "
        "configured local chat model 'library2/ministral-3:8b' from "
        "LOCAL_CHAT_MODEL"
    )
    assert trace["model_selection"]["policy_reason"] == "LOCAL_LLM_MODEL"
    assert "trace_unavailable_reason" not in trace

    chat._thread_latest_task.pop(thread_id, None)
    chat._rag_traces.pop(thread_id, None)


def test_live_rag_trace_reports_empty_shell_reason_when_no_sources(monkeypatch):
    thread_id = 806
    chat._thread_latest_task[thread_id] = "task-806"

    monkeypatch.setattr(chat, "_get_task_completed_payload", lambda _task: None)
    monkeypatch.setattr(
        chat,
        "get_latest_eval_diagnostics",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(chat, "_thread_trace_entry", lambda *args, **kwargs: None)

    trace = chat.get_latest_rag_trace(thread_id, api_key="test-key")
    assert trace["documents"] == []
    assert trace["graph"] == []
    assert trace["trace_unavailable_reason"] == "trace_source_unavailable"

    chat._thread_latest_task.pop(thread_id, None)
    chat._rag_traces.pop(thread_id, None)
