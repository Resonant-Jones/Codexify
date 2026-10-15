from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from guardian.core import ai_router
from guardian.core.config import Settings
from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker


SENTINEL = "missing-local-model-A7K9"


def _task(model: str | None, *, explicit: bool = True) -> ChatCompletionTask:
    return ChatCompletionTask(
        user_id="local",
        thread_id=11,
        provider="local",
        model=model,
        requested_provider="local" if explicit else None,
        requested_model=model if explicit else None,
        selection_source="explicit" if explicit else None,
    )


def _local_runtime(monkeypatch: pytest.MonkeyPatch, models: list[str]) -> None:
    settings = Settings(
        _env_file=None,
        LLM_PROVIDER="local",
        LOCAL_CHAT_MODEL="local-chat",
        LOCAL_LLM_MODEL="local-chat",
        DEFAULT_LOCAL_MODEL="local-chat",
        LLM_MODEL="local-chat",
        LOCAL_PROVIDER_VENDOR="whooshd",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        ALLOW_CLOUD_PROVIDERS=False,
    )
    monkeypatch.setattr(chat_worker, "get_settings", lambda: settings)
    monkeypatch.setattr(
        chat_worker, "resolve_thread_system_profile", lambda *a, **k: None
    )
    monkeypatch.setattr(
        chat_worker, "resolve_provider_for_model", lambda *a, **k: None
    )
    monkeypatch.setattr(
        chat_worker, "validate_provider_model_selection", lambda **k: (True, None)
    )
    monkeypatch.setattr(
        ai_router,
        "discover_local_model_inventory",
        lambda *a, **k: (
            models,
            {"state": "available", "inventory_source": "synthetic:/v1/models"},
        ),
    )


def test_unavailable_explicit_model_fails_before_execution_and_releases_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _local_runtime(monkeypatch, ["local-chat"])
    fallback = Mock(return_value="local-chat")
    execute = Mock()
    persist = Mock()
    release = Mock(return_value=True)
    published: list[tuple[str, dict]] = []
    monkeypatch.setattr(chat_worker, "_degraded_provider_model_fallback", fallback)
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "_execute_bounded_tool_turn_completion",
        execute,
    )
    monkeypatch.setattr(
        chat_worker.dependencies,
        "chatlog_db",
        SimpleNamespace(create_message=persist),
        raising=False,
    )
    monkeypatch.setattr(chat_worker, "release_turn_lock", release)
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *a, **k: False)
    monkeypatch.setattr(chat_worker, "_safe_emit_live_event", lambda *a, **k: None)
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _id, event, payload: published.append((event, dict(payload))),
    )

    async def _build(task: ChatCompletionTask, **_kwargs):
        resolved = chat_worker._compat_resolve_task(task)
        return [{"role": "user", "content": "hello"}], resolved.provider, resolved.model, {}, {}

    monkeypatch.setattr(chat_worker, "_build_messages_for_llm_compat", _build)
    task = _task(SENTINEL)
    task.turn_lock_owner = "test-lock"
    chat_worker._run_chat_task(task)

    failed = [payload for event, payload in published if event == "task.failed"]
    assert len(failed) == 1
    assert not any(event == "task.completed" for event, _ in published)
    assert failed[0]["requested_model"] == SENTINEL
    assert failed[0]["selection_source"] == "explicit"
    assert failed[0]["failure_kind"] == ai_router.LOCAL_MODEL_UNAVAILABLE_FAILURE_KIND
    assert failed[0]["completion_truth"] == {
        "accepted": True,
        "attempted": False,
        "fallback_attempted": False,
        "executed": False,
        "completed": False,
    }
    assert failed[0]["visible_output_emitted"] is False
    fallback.assert_not_called()
    execute.assert_not_called()
    persist.assert_not_called()
    release.assert_called_once_with(11, "test-lock")


@pytest.mark.parametrize("model", ["local-chat", "exact-test-model"])
def test_explicit_advertised_model_is_preserved(
    monkeypatch: pytest.MonkeyPatch, model: str
) -> None:
    _local_runtime(monkeypatch, ["local-chat", "exact-test-model"])
    resolved = chat_worker._compat_resolve_task(_task(model))
    assert resolved.model == model
    assert resolved.requested_model == model
    assert resolved.selection_source == "explicit"


def test_default_request_keeps_local_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    _local_runtime(monkeypatch, ["local-chat"])
    resolved = chat_worker._compat_resolve_task(_task(None, explicit=False))
    assert resolved.model == "local-chat"
    assert resolved.selection_source == "default"


def test_explicit_unavailable_model_never_calls_degraded_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _local_runtime(monkeypatch, ["local-chat"])
    fallback = Mock(return_value="local-chat")
    monkeypatch.setattr(chat_worker, "_degraded_provider_model_fallback", fallback)
    with pytest.raises(HTTPException) as failure:
        chat_worker._compat_resolve_task(_task(SENTINEL))
    assert failure.value.detail["requested_model"] == SENTINEL
    fallback.assert_not_called()
