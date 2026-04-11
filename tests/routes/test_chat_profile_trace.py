from __future__ import annotations

import uuid

import pytest

from guardian.core import chat_completion_service
from guardian.core.chat_completion_service import (
    DEBUG_LATEST_COMPLETION_TASK_ID_METADATA_KEY,
    DEBUG_LATEST_RAG_TRACE_METADATA_KEY,
    DEBUG_RAG_TRACE_CANDIDATE_METADATA_KEY,
)
from guardian.routes import chat
from guardian.tasks.types import ChatCompletionTask


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
    assert "slash_intent" not in trace["payload_summary"]
    assert "retrieval_override" not in trace["payload_summary"]

    chat._thread_latest_task.pop(77, None)
    chat._rag_traces.pop(77, None)


def test_rag_trace_preserves_slash_intent_in_payload_summary(monkeypatch):
    chat._thread_latest_task[78] = "task-78"

    slash_intent = {
        "commandId": "project",
        "intentKind": "workspace",
        "retrievalHint": "project",
    }
    retrieval_override = {"mode": "project", "reason": "slash_project_hint"}

    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda _task_id: {
            "trace": {"documents": [], "graph": []},
            "payload_summary": {
                "payload_char_count": 10,
                "message_count": 2,
                "slash_intent": slash_intent,
                "retrieval_override": retrieval_override,
            },
        },
    )

    trace = chat.get_latest_rag_trace(78, api_key="test-key")
    assert trace["payload_summary"]["slash_intent"] == slash_intent
    assert trace["payload_summary"]["retrieval_override"] == retrieval_override

    chat._thread_latest_task.pop(78, None)
    chat._rag_traces.pop(78, None)


def test_rag_trace_preserves_retrieval_override_and_effective_source_mode(
    monkeypatch,
):
    chat._thread_latest_task[79] = "task-79"

    slash_intent = {
        "commandId": "project",
        "intentKind": "workspace",
        "retrievalHint": "project",
    }
    retrieval_override = {
        "mode": "personal_knowledge",
        "reason": "slash command",
    }

    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda _task_id: {
            "trace": {
                "documents": [],
                "graph": [],
                "source_mode": "personal_knowledge",
                "widen_reason": "explicit_personal_knowledge",
            },
            "payload_summary": {
                "payload_char_count": 10,
                "message_count": 2,
                "slash_intent": slash_intent,
                "retrieval_override": retrieval_override,
                "source_mode": "personal_knowledge",
                "effective_source_mode": "personal_knowledge",
            },
        },
    )

    trace = chat.get_latest_rag_trace(79, api_key="test-key")

    assert trace["payload_summary"]["slash_intent"] == slash_intent
    assert trace["payload_summary"]["retrieval_override"] == retrieval_override
    assert trace["payload_summary"]["source_mode"] == "personal_knowledge"
    assert trace["payload_summary"]["effective_source_mode"] == (
        "personal_knowledge"
    )
    assert trace["source_mode"] == "personal_knowledge"
    assert trace["widen_reason"] == "explicit_personal_knowledge"

    chat._thread_latest_task.pop(79, None)
    chat._rag_traces.pop(79, None)


def test_rag_trace_preserves_conversation_override_and_effective_source_mode(
    monkeypatch,
):
    chat._thread_latest_task[80] = "task-80"

    slash_intent = {
        "commandId": "thread",
        "intentKind": "conversation",
        "retrievalHint": "conversation",
    }
    retrieval_override = {
        "mode": "conversation",
        "reason": "slash_conversation_hint",
    }

    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda _task_id: {
            "trace": {
                "documents": [],
                "graph": [],
                "source_mode": "conversation",
                "widen_reason": "none",
            },
            "payload_summary": {
                "payload_char_count": 12,
                "message_count": 2,
                "slash_intent": slash_intent,
                "retrieval_override": retrieval_override,
                "source_mode": "conversation",
                "effective_source_mode": "conversation",
            },
        },
    )

    trace = chat.get_latest_rag_trace(80, api_key="test-key")

    assert trace["payload_summary"]["slash_intent"] == slash_intent
    assert trace["payload_summary"]["retrieval_override"] == retrieval_override
    assert trace["payload_summary"]["source_mode"] == "conversation"
    assert trace["payload_summary"]["effective_source_mode"] == "conversation"
    assert trace["source_mode"] == "conversation"
    assert trace["widen_reason"] == "none"

    chat._thread_latest_task.pop(80, None)
    chat._rag_traces.pop(80, None)


@pytest.mark.parametrize(
    ("trace_payload", "expected_effective_policy"),
    [
        (
            {
                "source_mode": "personal_knowledge",
                "retrieval_override": {
                    "mode": "personal_knowledge",
                    "reason": "slash_personal_knowledge_hint",
                },
                "effective_policy": {
                    "source_mode": "personal_knowledge",
                    "widening_enabled": True,
                    "identity_scope": "personal_knowledge",
                },
            },
            {
                "source_mode": "personal_knowledge",
                "widening_enabled": True,
                "identity_scope": "personal_knowledge",
            },
        ),
        (
            {
                "source_mode": "conversation",
                "retrieval_override": {
                    "mode": "conversation",
                    "reason": "slash_conversation_hint",
                },
                "effective_policy": {
                    "source_mode": "thread",
                    "widening_enabled": False,
                    "identity_scope": "thread",
                },
            },
            {
                "source_mode": "thread",
                "widening_enabled": False,
                "identity_scope": "thread",
            },
        ),
    ],
)
def test_run_chat_completion_task_surfaces_effective_policy_in_payload_summary(
    monkeypatch,
    trace_payload,
    expected_effective_policy,
):
    async def _fake_build_messages_for_llm(_task):
        return (
            [{"role": "system", "content": "SYSTEM"}],
            "groq",
            "mock-model",
            {},
            trace_payload,
        )

    monkeypatch.setattr(
        chat_completion_service,
        "build_messages_for_llm",
        _fake_build_messages_for_llm,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *args, **kwargs: "assistant reply",
    )

    task = ChatCompletionTask(
        thread_id=1,
        provider="groq",
        model="mock-model",
        origin="api:chat.complete|turn_id=abc|source_mode=project",
    )
    task.retrieval_override = trace_payload["retrieval_override"]

    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    assert result["trace"]["effective_policy"] == expected_effective_policy
    assert result["payload_summary"]["effective_policy"] == (
        expected_effective_policy
    )
    assert (
        result["payload_summary"]["source_mode"] == trace_payload["source_mode"]
    )


def test_rag_trace_exposes_latest_turn_targeting_fields(monkeypatch):
    chat._thread_latest_task[91] = "task-91"

    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda _task_id: {
            "trace": {
                "documents": [],
                "graph": [],
                "latest_turn_message_id": 12,
                "latest_turn_content": "question B",
                "retrieval_query": "question B",
                "retrieval_target": "latest_turn",
                "retrieval_query_matches_latest_turn": True,
                "queued_at": "2026-04-02T00:00:00+00:00",
                "awaiting_model_at": "2026-04-02T00:00:01+00:00",
                "awaiting_first_token_at": "2026-04-02T00:00:02+00:00",
                "first_token_at": "2026-04-02T00:00:03+00:00",
                "first_output_at": "2026-04-02T00:00:03+00:00",
                "completed_at": "2026-04-02T00:00:04+00:00",
            },
            "payload_summary": {"message_count": 2},
        },
    )

    trace = chat.get_latest_rag_trace(91, api_key="test-key")

    assert trace["latest_turn_message_id"] == 12
    assert trace["latest_turn_content"] == "question B"
    assert trace["retrieval_query"] == "question B"
    assert trace["retrieval_target"] == "latest_turn"
    assert trace["retrieval_query_matches_latest_turn"] is True
    assert trace["queued_at"] == "2026-04-02T00:00:00+00:00"
    assert trace["awaiting_model_at"] == "2026-04-02T00:00:01+00:00"
    assert trace["awaiting_first_token_at"] == "2026-04-02T00:00:02+00:00"
    assert trace["first_token_at"] == "2026-04-02T00:00:03+00:00"
    assert trace["first_output_at"] == "2026-04-02T00:00:03+00:00"
    assert trace["completed_at"] == "2026-04-02T00:00:04+00:00"

    chat._thread_latest_task.pop(91, None)
    chat._rag_traces.pop(91, None)


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
    assert trace["thread_id"] == thread_id
    assert trace["project_id"] is None
    assert trace["depth_mode"] is None
    assert trace["source_mode"] is None
    assert trace["widen_reason"] == "none"

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
        "slash_intent": "slash:thread-one",
        "retrieval_override": {"mode": "project"},
        "source_mode": "project",
        "widen_reason": "none",
    }
    trace_two = {
        "documents": [
            {"id": "doc-b", "title": "b.md", "score": 0.7, "snippet": "b..."}
        ],
        "graph": [{"node_id": "node-b", "kind": "memory", "text": "b node"}],
        "slash_intent": "slash:thread-two",
        "retrieval_override": {"mode": "personal_knowledge"},
        "source_mode": "personal_knowledge",
        "widen_reason": "explicit_personal_knowledge",
    }
    task_one_id = str(uuid.uuid4())
    task_two_id = str(uuid.uuid4())
    slash_intent = {
        "commandId": "doc",
        "intentKind": "knowledge",
        "retrievalHint": "personal_knowledge",
    }
    retrieval_override = {
        "mode": "personal_knowledge",
        "reason": "slash command",
    }
    metadata_by_thread = {
        thread_one: {
            DEBUG_LATEST_RAG_TRACE_METADATA_KEY: {
                "task_id": task_one_id,
                "thread_id": thread_one,
                "trace": trace_one,
            }
        },
        thread_two: {
            DEBUG_LATEST_RAG_TRACE_METADATA_KEY: {
                "task_id": task_two_id,
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
    chat._thread_latest_task[thread_one] = task_one_id
    chat._thread_latest_task[thread_two] = task_two_id
    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda task_id: {
            "trace": trace_one
            if task_id
            == metadata_by_thread[thread_one][
                DEBUG_LATEST_RAG_TRACE_METADATA_KEY
            ]["task_id"]
            else trace_two,
            "payload_summary": {
                "message_count": 2,
                **(
                    {
                        "slash_intent": slash_intent,
                        "retrieval_override": retrieval_override,
                        "source_mode": "personal_knowledge",
                        "effective_source_mode": "personal_knowledge",
                    }
                    if task_id == task_one_id
                    else {}
                ),
            },
        },
    )

    first = chat.get_latest_rag_trace(thread_one, api_key="test-key")
    second = chat.get_latest_rag_trace(thread_two, api_key="test-key")

    assert first["documents"] == trace_one["documents"]
    assert first["graph"] == trace_one["graph"]
    assert first["slash_intent"] == trace_one["slash_intent"]
    assert first["retrieval_override"] == trace_one["retrieval_override"]
    assert first["source_mode"] == "project"
    assert first["widen_reason"] == "none"
    assert first["payload_summary"]["slash_intent"] == slash_intent
    assert first["payload_summary"]["retrieval_override"] == retrieval_override
    assert first["payload_summary"]["source_mode"] == "personal_knowledge"
    assert first["payload_summary"]["effective_source_mode"] == (
        "personal_knowledge"
    )
    assert second["documents"] == trace_two["documents"]
    assert second["graph"] == trace_two["graph"]
    assert second["slash_intent"] == trace_two["slash_intent"]
    assert second["retrieval_override"] == trace_two["retrieval_override"]
    assert second["source_mode"] == "personal_knowledge"
    assert second["widen_reason"] == "explicit_personal_knowledge"
    assert "slash_intent" not in second["payload_summary"]
    assert "retrieval_override" not in second["payload_summary"]

    chat._thread_latest_task.pop(thread_one, None)
    chat._thread_latest_task.pop(thread_two, None)
    chat._rag_traces.pop(thread_one, None)
    chat._rag_traces.pop(thread_two, None)


def test_rag_trace_candidate_preserves_source_mode_and_widen_reason(
    monkeypatch,
):
    thread_id = 301
    task_id = str(uuid.uuid4())
    candidate_trace = {
        "thread_id": thread_id,
        "project_id": 11,
        "depth_mode": "normal",
        "slash_intent": "slash:search",
        "retrieval_override": {"mode": "personal_knowledge"},
        "documents": [
            {
                "id": "doc-1",
                "title": "thread-note.md",
                "score": 0.92,
                "snippet": "relevant snippet...",
            }
        ],
        "graph": [],
        "source_mode": "personal_knowledge",
        "widen_reason": "explicit_personal_knowledge",
    }
    payload_summary = {
        "message_count": 2,
        "slash_intent": "slash:search",
        "retrieval_override": {"mode": "personal_knowledge"},
        "effective_source_mode": "personal_knowledge",
    }

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
            "payload_summary": payload_summary,
        },
    )

    trace = chat.get_latest_rag_trace(thread_id, api_key="test-key")

    assert trace["documents"] == candidate_trace["documents"]
    assert trace["thread_id"] == thread_id
    assert trace["project_id"] == 11
    assert trace["depth_mode"] == "normal"
    assert trace["slash_intent"] == "slash:search"
    assert trace["retrieval_override"] == {"mode": "personal_knowledge"}
    assert trace["source_mode"] == "personal_knowledge"
    assert trace["widen_reason"] == "explicit_personal_knowledge"
    assert trace["payload_summary"] == payload_summary

    chat._thread_latest_task.pop(thread_id, None)
    chat._rag_traces.pop(thread_id, None)


# ------------------------------------------------------------------
# Retrieval posture route tests
# ------------------------------------------------------------------


def test_retrieval_posture_returns_canonical_snapshot_when_present(monkeypatch):
    """Route returns status=ok and the canonical retrieval_posture when emitted."""
    chat._thread_latest_task[201] = "task-201"

    canonical_posture = {
        "source_mode": "conversation",
        "boundary_label": "active_conversation_only",
        "retrieval_override_mode": "conversation",
        "widen_reason": "none",
        "conversation_only": True,
    }

    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda _task_id: {
            "trace": {"documents": [], "graph": []},
            "payload_summary": {
                "message_count": 2,
                "retrieval_posture": canonical_posture,
            },
        },
    )

    result = chat.get_latest_retrieval_posture(201, api_key="test-key")

    assert result["thread_id"] == 201
    assert result["status"] == "ok"
    assert result["retrieval_posture"] == canonical_posture

    chat._thread_latest_task.pop(201, None)
    chat._rag_traces.pop(201, None)


def test_retrieval_posture_returns_empty_state_without_completed_evidence(
    monkeypatch,
):
    """Route returns status=empty when no completed trace evidence exists."""
    thread_id = 202
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
                            "id": "doc-x",
                            "title": "x.md",
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

    result = chat.get_latest_retrieval_posture(thread_id, api_key="test-key")

    assert result["thread_id"] == thread_id
    assert result["status"] == "empty"
    assert result["retrieval_posture"] is None

    chat._thread_latest_task.pop(thread_id, None)
    chat._rag_traces.pop(thread_id, None)


def test_retrieval_posture_does_not_bleed_across_threads(monkeypatch):
    """Posture evidence from one thread does not leak into another thread."""
    thread_one = 301
    thread_two = 302
    task_one_id = str(uuid.uuid4())
    task_two_id = str(uuid.uuid4())

    posture_one = {
        "source_mode": "conversation",
        "boundary_label": "active_conversation_only",
        "retrieval_override_mode": "conversation",
        "widen_reason": "none",
        "conversation_only": True,
    }
    posture_two = {
        "source_mode": "personal_knowledge",
        "boundary_label": "same_user_only",
        "retrieval_override_mode": "personal_knowledge",
        "widen_reason": "explicit_personal_knowledge",
        "conversation_only": False,
    }

    metadata_by_thread = {
        thread_one: {
            DEBUG_LATEST_COMPLETION_TASK_ID_METADATA_KEY: task_one_id,
        },
        thread_two: {
            DEBUG_LATEST_COMPLETION_TASK_ID_METADATA_KEY: task_two_id,
        },
    }

    monkeypatch.setattr(
        chat,
        "_fetch_thread_metadata",
        lambda thread_id: metadata_by_thread.get(thread_id, {}),
    )
    chat._thread_latest_task[thread_one] = task_one_id
    chat._thread_latest_task[thread_two] = task_two_id
    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda task_id: {
            "trace": {"documents": [], "graph": []},
            "payload_summary": {
                "message_count": 2,
                "retrieval_posture": posture_one
                if task_id == task_one_id
                else posture_two,
            },
        },
    )

    result_one = chat.get_latest_retrieval_posture(
        thread_one, api_key="test-key"
    )
    result_two = chat.get_latest_retrieval_posture(
        thread_two, api_key="test-key"
    )

    assert result_one["status"] == "ok"
    assert result_one["retrieval_posture"]["source_mode"] == "conversation"
    assert result_two["status"] == "ok"
    assert (
        result_two["retrieval_posture"]["source_mode"] == "personal_knowledge"
    )

    chat._thread_latest_task.pop(thread_one, None)
    chat._thread_latest_task.pop(thread_two, None)
    chat._rag_traces.pop(thread_one, None)
    chat._rag_traces.pop(thread_two, None)


def test_retrieval_posture_fallback_synthesis_from_legacy_fields(monkeypatch):
    """Fallback synthesis produces canonical snapshot shape from legacy trace fields."""
    chat._thread_latest_task[401] = "task-401"

    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda _task_id: {
            "trace": {
                "documents": [],
                "graph": [],
                "source_mode": "conversation",
                "widen_reason": "none",
            },
            "payload_summary": {
                "message_count": 2,
                "retrieval_override": {
                    "mode": "conversation",
                    "reason": "slash_conversation_hint",
                },
            },
        },
    )

    result = chat.get_latest_retrieval_posture(401, api_key="test-key")

    assert result["status"] == "ok"
    assert result["retrieval_posture"]["source_mode"] == "conversation"
    assert result["retrieval_posture"]["boundary_label"] == (
        "active_conversation_only"
    )
    assert (
        result["retrieval_posture"]["retrieval_override_mode"] == "conversation"
    )
    assert result["retrieval_posture"]["widen_reason"] == "none"
    assert result["retrieval_posture"]["conversation_only"] is True

    chat._thread_latest_task.pop(401, None)
    chat._rag_traces.pop(401, None)


def test_retrieval_posture_fallback_synthesis_personal_knowledge(monkeypatch):
    """Fallback synthesis for personal_knowledge source mode produces correct shape."""
    chat._thread_latest_task[402] = "task-402"

    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda _task_id: {
            "trace": {
                "documents": [],
                "graph": [],
                "source_mode": "personal_knowledge",
                "widen_reason": "explicit_personal_knowledge",
            },
            "payload_summary": {
                "message_count": 2,
                "retrieval_override": {
                    "mode": "personal_knowledge",
                    "reason": "slash command",
                },
            },
        },
    )

    result = chat.get_latest_retrieval_posture(402, api_key="test-key")

    assert result["status"] == "ok"
    assert result["retrieval_posture"]["source_mode"] == "personal_knowledge"
    assert result["retrieval_posture"]["boundary_label"] == "same_user_only"
    assert (
        result["retrieval_posture"]["retrieval_override_mode"]
        == "personal_knowledge"
    )
    assert result["retrieval_posture"]["widen_reason"] == (
        "explicit_personal_knowledge"
    )
    assert result["retrieval_posture"]["conversation_only"] is False

    chat._thread_latest_task.pop(402, None)
    chat._rag_traces.pop(402, None)


def test_retrieval_posture_fallback_returns_empty_when_no_source_mode(
    monkeypatch,
):
    """Fallback returns empty state when trace lacks source_mode evidence."""
    chat._thread_latest_task[403] = "task-403"

    monkeypatch.setattr(
        chat,
        "_get_task_completed_payload",
        lambda _task_id: {
            "trace": {"documents": [], "graph": []},
            "payload_summary": {"message_count": 2},
        },
    )

    result = chat.get_latest_retrieval_posture(403, api_key="test-key")

    assert result["status"] == "empty"
    assert result["retrieval_posture"] is None

    chat._thread_latest_task.pop(403, None)
    chat._rag_traces.pop(403, None)
