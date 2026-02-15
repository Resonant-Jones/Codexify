from __future__ import annotations

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
        },
    )

    trace = chat.get_latest_rag_trace(42, api_key="test-key")
    assert trace["active_profile_id"] == "local_mode"
    assert trace["provider_override"] == "local"
    assert trace["model_override"] == "mlx-community/Llama-3B"

    chat._thread_latest_task.pop(42, None)
    chat._rag_traces.pop(42, None)
