from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from guardian.core.dependencies import RequestUserScope
from guardian.protocol_tokens import (
    ImageRoutingPath,
    TraceSnapshotAbsenceReason,
)
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
    assert (
        trace["retrieval_suppression"]["counts_by_reason"][
            "assistant_vision_refusal_on_image_turn"
        ]
        == 1
    )
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
        "image_routing_path": ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value,
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
    assert "trace_unavailable_reason" not in trace
    assert trace["effective_policy"] == expected_effective_policy
    assert trace["retrieval_provenance"] == expected_retrieval_provenance
    assert trace["retrieval_summary"]["document_count"] == 1
    assert trace["retrieval_summary"]["graph_count"] == 1
    assert trace["retrieval_summary"]["source_mode"] == "workspace"
    assert trace["retrieval_summary"]["retrieval_target"] == "latest_turn"
    assert (
        trace["retrieval_summary"]["retrieval_query_matches_latest_turn"]
        is True
    )
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
        "image_routing_path": ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value,
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
                "image_routing_path": ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value,
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
                "image_routing_path": ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value,
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
    assert (
        trace["image_routing_path"]
        == ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value
    )
    assert trace["image_routing_absence_reason"] is None
    assert trace["retrieval_executed"] is True
    assert trace["model_selection"] == model_selection
    assert trace["payload_summary"]["model_selection"] == model_selection
    assert (
        trace["retrieval_suppression"]["items"][0]["suppression_reason"]
        == "assistant_vision_refusal_on_image_turn"
    )

    chat._thread_latest_task.pop(101, None)
    chat._rag_traces.pop(101, None)


def test_live_rag_trace_returns_empty_surface_without_trace(
    monkeypatch,
):
    thread_id = 502
    task_id = "task-502"

    chat._thread_latest_task[thread_id] = task_id
    monkeypatch.setattr(chat, "_fetch_thread_metadata", lambda _thread_id: {})
    monkeypatch.setattr(
        chat, "_get_task_completed_payload", lambda _task_id: None
    )
    monkeypatch.setattr(
        chat,
        "get_latest_eval_diagnostics",
        lambda *args, **kwargs: None,
    )

    trace = chat.get_latest_rag_trace(thread_id, api_key="test-key")
    trace_text = json.dumps(trace, sort_keys=True)

    assert trace["trace_available"] is False
    assert trace["trace_unavailable_reason"] == (
        TraceSnapshotAbsenceReason.TRACE_SOURCE_UNAVAILABLE.value
    )
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
    assert "trace_unavailable_reason" not in trace

    chat._thread_latest_task.pop(102, None)
    chat._rag_traces.pop(102, None)


def test_live_rag_trace_promotes_eval_snapshot_when_task_trace_missing(
    monkeypatch,
):
    chat._thread_latest_task[103] = "task-103"

    monkeypatch.setattr(
        chat, "_get_task_completed_payload", lambda _task_id: None
    )

    snapshot_trace = {
        "retrieval_policy": {
            "source_mode": "project",
            "widening_enabled": True,
            "identity_scope": "project",
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
            "retrieval_status": "no_obsidian_results",
        },
        "retrieval_suppression": {
            "items": [],
            "summary": {
                "total_suppressed": 0,
                "assistant_vision_refusal_on_image_turn": 0,
            },
        },
        "retrieval_executed": True,
        "retrieval_absence_reason": None,
        "image_attachment_count": 1,
        "image_routing_path": None,
        "image_routing_absence_reason": (
            "local_model_substitution_selected_nonvision_model"
        ),
        "model_selection": {
            "requested_provider": "local",
            "requested_model": "medgemma:4b-it-q8_0",
            "final_provider": "local",
            "final_model": "library2/ministral-3:8b",
            "selection_source": "explicit",
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
        },
    }

    monkeypatch.setattr(
        chat,
        "get_latest_eval_diagnostics",
        lambda _db, *, thread_id: {
            "thread_id": thread_id,
            "trace_snapshot": {
                "trace_snapshot_id": "snapshot-103",
                "task_id": "task-103",
                "thread_id": thread_id,
                "trace": dict(snapshot_trace),
                "payload_summary": dict(snapshot_trace),
            },
            "verdicts": [],
        },
    )

    trace = chat.get_latest_rag_trace(103, api_key="test-key")
    assert trace["retrieval_policy"] == snapshot_trace["retrieval_policy"]
    assert (
        trace["retrieval_provenance"] == snapshot_trace["retrieval_provenance"]
    )
    assert (
        trace["retrieval_suppression"]
        == snapshot_trace["retrieval_suppression"]
    )
    assert trace["retrieval_executed"] is True
    assert trace["image_routing_absence_reason"] == (
        "local_model_substitution_selected_nonvision_model"
    )
    assert trace["image_routing_path"] is None
    assert trace["image_routing"]["image_attachment_count"] == 1
    assert (
        trace["image_routing_absence_reason"]
        != TraceSnapshotAbsenceReason.IMAGE_ROUTING_NOT_EVALUATED.value
    )
    assert "trace_unavailable_reason" not in trace

    chat._thread_latest_task.pop(103, None)
    chat._rag_traces.pop(103, None)


def test_live_rag_trace_merges_eval_snapshot_into_minimal_task_trace(
    monkeypatch,
):
    chat._thread_latest_task[104] = "task-104"

    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda _task_id: {
            "trace": {
                "documents": [],
                "graph": [],
                "trace_unavailable_reason": "trace_source_unavailable",
                "image_attachment_count": 1,
                "image_routing_path": None,
                "image_routing_absence_reason": None,
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
                    "retrieval_status": "no_obsidian_results",
                },
                "image_attachment_count": 1,
                "image_routing_path": None,
                "image_routing_absence_reason": None,
            },
        },
    )

    snapshot_trace = {
        "retrieval_policy": {
            "source_mode": "project",
            "widening_enabled": True,
            "identity_scope": "project",
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
            "retrieval_status": "no_obsidian_results",
        },
        "retrieval_suppression": {
            "items": [],
            "summary": {
                "total_suppressed": 0,
                "assistant_vision_refusal_on_image_turn": 0,
            },
        },
        "retrieval_executed": True,
        "retrieval_absence_reason": None,
        "image_attachment_count": 1,
        "image_routing_path": None,
        "image_routing_absence_reason": (
            "local_model_substitution_selected_nonvision_model"
        ),
        "model_selection": {
            "requested_provider": "local",
            "requested_model": "medgemma:4b-it-q8_0",
            "final_provider": "local",
            "final_model": "library2/ministral-3:8b",
            "selection_source": "explicit",
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
        },
    }

    monkeypatch.setattr(
        chat,
        "get_latest_eval_diagnostics",
        lambda _db, *, thread_id: {
            "thread_id": thread_id,
            "trace_snapshot": {
                "trace_snapshot_id": "snapshot-104",
                "task_id": "task-104",
                "thread_id": thread_id,
                "trace": dict(snapshot_trace),
                "payload_summary": dict(snapshot_trace),
            },
            "verdicts": [],
        },
    )

    trace = chat.get_latest_rag_trace(104, api_key="test-key")
    assert trace["retrieval_policy"] == snapshot_trace["retrieval_policy"]
    assert (
        trace["retrieval_provenance"] == snapshot_trace["retrieval_provenance"]
    )
    assert (
        trace["retrieval_suppression"]
        == snapshot_trace["retrieval_suppression"]
    )
    assert trace["retrieval_executed"] is True
    assert trace.get("retrieval_absence_reason") is None
    assert trace["image_routing_absence_reason"] == (
        "local_model_substitution_selected_nonvision_model"
    )
    assert trace["image_routing_path"] is None
    assert trace["image_routing"]["image_routing_path"] is None
    assert trace["image_routing"]["image_attachment_count"] == 1
    assert trace["payload_summary"]["image_routing_absence_reason"] == (
        "local_model_substitution_selected_nonvision_model"
    )
    assert trace["image_routing_absence_reason"] != (
        TraceSnapshotAbsenceReason.IMAGE_ROUTING_NOT_EVALUATED.value
    )
    assert "trace_unavailable_reason" not in trace

    chat._thread_latest_task.pop(104, None)
    chat._rag_traces.pop(104, None)


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
    assert (
        trace["retrieval_suppression"]["counts_by_reason"][
            "assistant_vision_refusal_on_image_turn"
        ]
        == 1
    )
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
                    },
                    "retrieval_suppression": {
                        "count": 1,
                        "counts_by_reason": {
                            "assistant_vision_refusal_on_image_turn": 1,
                        },
                    },
                    "image_routing_path": "interpreter",
                    "model_selection": {
                        "requested_provider": "local",
                        "requested_model": "medgemma:4b-it-q8_0",
                        "final_provider": "local",
                        "final_model": "library2/ministral-3:8b",
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
        }

    monkeypatch.setattr(
        chat, "get_latest_eval_diagnostics", _fake_get_latest_eval_diagnostics
    )

    scope = RequestUserScope(
        user_id="local",
        account_id="local",
        multi_user_enabled=True,
    )
    result = chat.get_latest_eval_diagnostics_route(7, request_user_scope=scope)
    assert captured["thread_id"] == 7
    trace_snapshot = result["trace_snapshot"]
    assert trace_snapshot["retrieval_policy"]["source_mode"] == "project"
    assert trace_snapshot["model_selection"]["final_model"] == (
        "library2/ministral-3:8b"
    )
    assert trace_snapshot["image_routing_path"] == "interpreter"


def test_live_rag_trace_reports_empty_shell_reason_when_no_sources(monkeypatch):
    thread_id = 806
    chat._thread_latest_task[thread_id] = "task-806"

    monkeypatch.setattr(chat, "_get_task_completed_payload", lambda _task: None)
    monkeypatch.setattr(
        chat,
        "get_latest_eval_diagnostics",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chat, "_thread_trace_entry", lambda *args, **kwargs: None
    )

    trace = chat.get_latest_rag_trace(thread_id, api_key="test-key")
    assert trace["documents"] == []
    assert trace["graph"] == []
    assert trace["trace_unavailable_reason"] == "trace_source_unavailable"

    chat._thread_latest_task.pop(thread_id, None)
    chat._rag_traces.pop(thread_id, None)
