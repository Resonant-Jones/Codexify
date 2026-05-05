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


def test_live_rag_trace_promotes_containment_fields(monkeypatch):
    chat._thread_latest_task[101] = "task-101"

    retrieval_policy = {
        "source_mode": "project",
        "widening_enabled": True,
        "identity_scope": "project",
    }
    retrieval_provenance = {
        "requested_source_mode": "project",
        "normalized_source_mode": "project",
        "source_hit_counts": {
            "semantic_total": 0,
            "thread_semantic": 0,
            "obsidian_semantic": 0,
            "other_semantic": 0,
            "project_documents": 0,
            "thread_documents": 0,
            "global_documents": 0,
            "other_documents": 0,
            "memory": 0,
            "graph": 0,
        },
        "retrieval_status": "no_candidates",
    }
    retrieval_suppression = {
        "items": [
            {
                "suppressed": True,
                "suppression_reason": "assistant_vision_refusal_on_image_turn",
                "source_type": "semantic_context",
                "role": "assistant",
                "thread_id": 101,
                "project_id": 8,
                "retrieval_lane": "semantic",
                "score": 0.12,
                "policy_reason": "assistant_vision_refusal_on_image_turn",
            }
        ],
        "summary": {
            "total_suppressed": 1,
            "assistant_vision_refusal_on_image_turn": 1,
        },
    }
    model_selection = {
        "requested_provider": "local",
        "requested_model": "medgemma:4b-it-q8_0",
        "attempted_provider": "local",
        "attempted_model": "medgemma:4b-it-q8_0",
        "final_provider": "local",
        "final_model": "library2/ministral-3:8b",
        "selection_source": "LOCAL_CHAT_MODEL",
        "policy_reason": "LOCAL_CHAT_MODEL",
        "fallback_reason": None,
        "model_resolution": {
            "source": "LOCAL_CHAT_MODEL",
            "message": (
                "requested model 'medgemma:4b-it-q8_0' was overridden "
                "by configured local chat model 'library2/ministral-3:8b' "
                "from LOCAL_CHAT_MODEL"
            ),
        },
    }

    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda _task_id: {
            "trace": {
                "documents": [],
                "graph": [],
                "effective_policy": retrieval_policy,
                "retrieval_policy": retrieval_policy,
                "retrieval_provenance": retrieval_provenance,
                "retrieval_suppression": retrieval_suppression,
                "retrieval_executed": True,
                "retrieval_absence_reason": None,
                "image_routing_path": "vlm",
                "image_routing_absence_reason": None,
                "model_selection": model_selection,
                "source_mode": "project",
                "widen_reason": "none",
            },
            "payload_summary": {
                "retrieval_policy": retrieval_policy,
                "retrieval_provenance": retrieval_provenance,
                "retrieval_suppression": retrieval_suppression,
                "retrieval_executed": True,
                "retrieval_absence_reason": None,
                "image_routing_path": "vlm",
                "image_routing_absence_reason": None,
                "model_selection": model_selection,
                "source_mode": "project",
                "effective_source_mode": "project",
            },
        },
    )

    trace = chat.get_latest_rag_trace(101, api_key="test-key")

    assert trace["retrieval_policy"] == retrieval_policy
    assert trace["retrieval_provenance"] == retrieval_provenance
    assert trace["retrieval_suppression"] == retrieval_suppression
    assert trace["image_routing_path"] == "vlm"
    assert trace["retrieval_executed"] is True
    assert trace["model_selection"] == model_selection
    assert trace["payload_summary"]["model_selection"] == model_selection
    assert (
        trace["retrieval_suppression"]["items"][0]["suppression_reason"]
        == "assistant_vision_refusal_on_image_turn"
    )

    chat._thread_latest_task.pop(101, None)
    chat._rag_traces.pop(101, None)


def test_live_rag_trace_reports_snapshot_missing_reason(monkeypatch):
    chat._thread_latest_task[102] = "task-102"

    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda _task_id: {
            "payload_summary": {
                "retrieval_policy": {
                    "source_mode": "project",
                    "widening_enabled": True,
                    "identity_scope": "project",
                },
                "retrieval_provenance": {
                    "requested_source_mode": "project",
                    "normalized_source_mode": "project",
                    "source_hit_counts": {
                        "semantic_total": 0,
                        "thread_semantic": 0,
                        "obsidian_semantic": 0,
                        "other_semantic": 0,
                        "project_documents": 0,
                        "thread_documents": 0,
                        "global_documents": 0,
                        "other_documents": 0,
                        "memory": 0,
                        "graph": 0,
                    },
                    "retrieval_status": "no_candidates",
                },
            }
        },
    )

    trace = chat.get_latest_rag_trace(102, api_key="test-key")
    assert trace["documents"] == []
    assert trace["graph"] == []
    assert trace["trace_unavailable_reason"] == "trace_snapshot_missing"

    chat._thread_latest_task.pop(102, None)
    chat._rag_traces.pop(102, None)


def test_eval_diagnostics_route_promotes_snapshot_fields(monkeypatch):
    captured: dict[str, int] = {}

    def _fake_get_latest_eval_diagnostics(_db, *, thread_id: int):
        captured["thread_id"] = thread_id
        return {
            "thread_id": thread_id,
            "trace_snapshot": {
                "trace_snapshot_id": "snapshot-7",
                "trace": {
                    "retrieval_policy": {
                        "source_mode": "project",
                        "widening_enabled": True,
                        "identity_scope": "project",
                    },
                    "retrieval_provenance": {
                        "requested_source_mode": "project",
                        "normalized_source_mode": "project",
                        "source_hit_counts": {
                            "semantic_total": 0,
                            "thread_semantic": 0,
                            "obsidian_semantic": 0,
                            "other_semantic": 0,
                            "project_documents": 0,
                            "thread_documents": 0,
                            "global_documents": 0,
                            "other_documents": 0,
                            "memory": 0,
                            "graph": 0,
                        },
                        "retrieval_status": "no_candidates",
                    },
                    "retrieval_suppression": {
                        "items": [],
                        "summary": {"total_suppressed": 0},
                    },
                    "retrieval_executed": True,
                    "image_routing_path": "interpreter",
                    "model_selection": {
                        "requested_provider": "local",
                        "requested_model": "medgemma:4b-it-q8_0",
                        "final_provider": "local",
                        "final_model": "library2/ministral-3:8b",
                    },
                },
                "payload_summary": {
                    "retrieval_policy": {
                        "source_mode": "project",
                        "widening_enabled": True,
                        "identity_scope": "project",
                    },
                    "retrieval_provenance": {
                        "requested_source_mode": "project",
                        "normalized_source_mode": "project",
                        "source_hit_counts": {
                            "semantic_total": 0,
                            "thread_semantic": 0,
                            "obsidian_semantic": 0,
                            "other_semantic": 0,
                            "project_documents": 0,
                            "thread_documents": 0,
                            "global_documents": 0,
                            "other_documents": 0,
                            "memory": 0,
                            "graph": 0,
                        },
                        "retrieval_status": "no_candidates",
                    },
                    "retrieval_suppression": {
                        "items": [],
                        "summary": {"total_suppressed": 0},
                    },
                    "retrieval_executed": True,
                    "image_routing_path": "interpreter",
                    "model_selection": {
                        "requested_provider": "local",
                        "requested_model": "medgemma:4b-it-q8_0",
                        "final_provider": "local",
                        "final_model": "library2/ministral-3:8b",
                    },
                },
                "retrieval_summary": {},
                "metadata": {},
            },
            "verdicts": [],
        }

    monkeypatch.setattr(chat, "get_latest_eval_diagnostics", _fake_get_latest_eval_diagnostics)

    scope = RequestUserScope(
        user_id="local",
        account_id="local",
        multi_user_enabled=True,
    )
    result = chat.get_latest_eval_diagnostics_route(7, request_user_scope=scope)
    assert captured["thread_id"] == 7
    trace_snapshot = result["trace_snapshot"]
    assert trace_snapshot["retrieval_policy"]["source_mode"] == "project"
    assert trace_snapshot["trace"]["model_selection"]["final_model"] == (
        "library2/ministral-3:8b"
    )
    assert trace_snapshot["trace"]["image_routing_path"] == "interpreter"
