from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from guardian.core import chat_completion_service
from guardian.core.completion_terminal import (
    CompletionTerminalEvidence,
    CompletionTerminalError,
    require_successful_terminal,
)
from guardian.protocol_tokens import CompletionTerminalStatus
from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker


def _task(*, provider: str = "local") -> ChatCompletionTask:
    return ChatCompletionTask(
        user_id="local",
        task_id="task-terminal",
        thread_id=7,
        provider=provider,
        model="test-model",
        origin="api:chat.complete",
    )


def _evidence(
    status: CompletionTerminalStatus = CompletionTerminalStatus.SUCCESS,
    *,
    visible: bool = True,
    failure_kind: str | None = None,
    retry_permitted: bool = False,
) -> CompletionTerminalEvidence:
    return CompletionTerminalEvidence(
        status=status,
        visible_output_emitted=visible,
        explicit_provider_terminal_observed=(
            status
            in {
                CompletionTerminalStatus.SUCCESS,
                CompletionTerminalStatus.PROVIDER_ERROR,
            }
        ),
        finish_reason="stop" if status is CompletionTerminalStatus.SUCCESS else None,
        transport_ended_cleanly=(status is CompletionTerminalStatus.SUCCESS),
        provider="local",
        model="test-model",
        failure_kind=failure_kind,
        retry_permitted=retry_permitted,
    )


def _stream(
    tokens: list[str],
    terminal: CompletionTerminalEvidence | None,
):
    yield from tokens
    return terminal


def _raising_stream(tokens: list[str], exc: Exception):
    yield from tokens
    raise exc


def _execute_local(monkeypatch, stream, *, cancel_check=None):
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "stream_local",
        lambda *_args, **_kwargs: stream,
    )
    return chat_completion_service._execute_completion_attempt(
        task=_task(),
        messages_for_llm=[{"role": "user", "content": "hello"}],
        provider="local",
        model="test-model",
        bundle={},
        cancel_check=cancel_check,
    )


def test_successful_stream_requires_explicit_terminal(monkeypatch):
    result = _execute_local(
        monkeypatch,
        _stream(["Hel", "lo"], _evidence()),
    )

    assert result.output == "Hello"
    assert result.terminal.successful is True
    assert result.terminal.visible_output_emitted is True


def test_successful_non_streaming_completion_maps_to_terminal(monkeypatch):
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: "complete answer",
    )

    result = chat_completion_service._execute_completion_attempt(
        task=_task(provider="groq"),
        messages_for_llm=[{"role": "user", "content": "hello"}],
        provider="groq",
        model="test-model",
        bundle={},
    )

    assert result.output == "complete answer"
    assert result.terminal.successful is True
    assert result.terminal.explicit_provider_terminal_observed is True


@pytest.mark.parametrize(
    ("terminal", "expected_status"),
    [
        (None, CompletionTerminalStatus.STREAM_INCOMPLETE),
        (
            _evidence(
                CompletionTerminalStatus.PROVIDER_ERROR,
                failure_kind="provider_error_frame",
            ),
            CompletionTerminalStatus.PROVIDER_ERROR,
        ),
        (
            _evidence(
                CompletionTerminalStatus.MALFORMED_TERMINAL,
                failure_kind="malformed_stream_frame",
            ),
            CompletionTerminalStatus.MALFORMED_TERMINAL,
        ),
    ],
)
def test_partial_stream_never_accepts_incomplete_terminal(
    monkeypatch,
    terminal,
    expected_status,
):
    with pytest.raises(CompletionTerminalError) as exc:
        _execute_local(monkeypatch, _stream(["partial"], terminal))

    assert exc.value.evidence.status is expected_status
    assert exc.value.evidence.visible_output_emitted is True
    assert exc.value.evidence.retry_permitted is False


@pytest.mark.parametrize("tokens", [[], ["partial"]])
def test_timeout_terminal_tracks_output_boundary(monkeypatch, tokens):
    timeout = HTTPException(
        status_code=502,
        detail={
            "failure_kind": "provider_timeout",
            "transport_classification": "timeout",
        },
    )

    with pytest.raises(HTTPException) as exc:
        _execute_local(monkeypatch, _raising_stream(tokens, timeout))

    terminal = exc.value.detail["terminal_evidence"]
    assert terminal["status"] == "execution_timeout"
    assert terminal["visible_output_emitted"] is bool(tokens)
    assert terminal["retry_permitted"] is (not bool(tokens))


def test_cancellation_before_first_token_is_terminal_and_nonretryable(monkeypatch):
    with pytest.raises(chat_completion_service.ChatTaskCancelled) as exc:
        _execute_local(
            monkeypatch,
            _stream(["unused"], _evidence()),
            cancel_check=lambda: True,
        )

    terminal = exc.value.metadata["terminal_evidence"]
    assert terminal["status"] == "cancelled"
    assert terminal["visible_output_emitted"] is False
    assert terminal["retry_permitted"] is False


def test_cancellation_after_visible_token_is_terminal_and_nonretryable(monkeypatch):
    checks = iter([False, False, True])

    with pytest.raises(chat_completion_service.ChatTaskCancelled) as exc:
        _execute_local(
            monkeypatch,
            _stream(["visible", "unused"], _evidence()),
            cancel_check=lambda: next(checks),
        )

    terminal = exc.value.metadata["terminal_evidence"]
    assert terminal["status"] == "cancelled"
    assert terminal["visible_output_emitted"] is True


def test_pre_output_failure_can_remain_fallback_eligible():
    exc = CompletionTerminalError(
        _evidence(
            CompletionTerminalStatus.STREAM_INCOMPLETE,
            visible=False,
            failure_kind="missing_stream_terminal",
            retry_permitted=True,
        )
    )

    assert chat_worker._provider_fallback_allowed(
        exc,
        selection_source="default",
        provider_pinned=False,
        visible_output_emitted=False,
    )


def test_visible_output_forbids_provider_fallback():
    exc = CompletionTerminalError(
        _evidence(
            CompletionTerminalStatus.PROVIDER_ERROR,
            visible=True,
            failure_kind="provider_error_frame",
        )
    )

    assert not chat_worker._provider_fallback_allowed(
        exc,
        selection_source="default",
        provider_pinned=False,
        visible_output_emitted=True,
    )


def test_persistence_gate_rejects_missing_or_incomplete_evidence():
    with pytest.raises(CompletionTerminalError):
        require_successful_terminal({"provider": "local", "model": "test-model"})

    with pytest.raises(CompletionTerminalError):
        require_successful_terminal(
            {
                "terminal_evidence": _evidence(
                    CompletionTerminalStatus.STREAM_INCOMPLETE,
                    failure_kind="missing_stream_terminal",
                ).as_dict()
            }
        )


def test_terminal_metadata_is_content_free():
    payload = _evidence().as_dict()

    assert "content" not in payload
    assert "assistant_text" not in payload
    assert "chunks" not in payload
    assert set(payload) == {
        "status",
        "visible_output_emitted",
        "explicit_provider_terminal_observed",
        "finish_reason",
        "transport_ended_cleanly",
        "provider",
        "model",
        "failure_kind",
        "retry_permitted",
    }


def test_tool_loop_obeys_terminal_gate(monkeypatch):
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "stream_local",
        lambda *_args, **_kwargs: _stream(["partial"], None),
    )

    with pytest.raises(CompletionTerminalError):
        chat_completion_service._execute_bounded_tool_turn_completion(
            _task(),
            messages_for_llm=[{"role": "user", "content": "hello"}],
            provider="local",
            model="test-model",
            bundle={},
            trace={},
            base_payload_summary={},
        )


def _seed_worker_terminal_harness(monkeypatch):
    published: list[tuple[str, dict]] = []
    effects: list[str] = []
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_args: False)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_args: None)
    monkeypatch.setattr(chat_worker, "release_turn_lock", lambda *_args: True)
    monkeypatch.setattr(
        chat_worker,
        "_find_assistant_message_for_turn",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        chat_worker,
        "_find_assistant_message_id_by_turn_id",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, payload: published.append(
            (event_type, dict(payload or {}))
        ),
    )
    monkeypatch.setattr(
        chat_worker,
        "schedule_post_completion_eval",
        lambda *_args, **_kwargs: effects.append("eval"),
    )
    monkeypatch.setattr(
        chat_worker,
        "_schedule_assistant_message_audio_generation",
        lambda **_kwargs: effects.append("audio"),
    )
    monkeypatch.setattr(
        chat_worker.dependencies,
        "chatlog_db",
        SimpleNamespace(
            create_message=lambda *_args, **_kwargs: effects.append("persist"),
        ),
    )
    return published, effects


def test_incomplete_output_publishes_failed_without_completion_effects(monkeypatch):
    published, effects = _seed_worker_terminal_harness(monkeypatch)
    error = CompletionTerminalError(
        _evidence(
            CompletionTerminalStatus.STREAM_INCOMPLETE,
            visible=True,
            failure_kind="missing_stream_terminal",
        )
    )
    monkeypatch.setattr(
        chat_worker,
        "run_chat_completion_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(error),
    )

    chat_worker._run_chat_task(_task())

    event_types = [event_type for event_type, _payload in published]
    assert "task.failed" in event_types
    assert "task.completed" not in event_types
    assert effects == []
    failed = next(
        payload for event_type, payload in published if event_type == "task.failed"
    )
    assert failed["terminal_evidence"]["status"] == "stream_incomplete"
    assert failed["first_output_observed"] is True


def test_cancelled_output_publishes_cancelled_without_persistence(monkeypatch):
    published, effects = _seed_worker_terminal_harness(monkeypatch)
    cancelled = chat_completion_service.ChatTaskCancelled(
        provider="local",
        model="test-model",
        visible_output_emitted=True,
    )
    monkeypatch.setattr(
        chat_worker,
        "run_chat_completion_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(cancelled),
    )

    chat_worker._run_chat_task(_task())

    event_types = [event_type for event_type, _payload in published]
    assert "task.cancelled" in event_types
    assert "task.completed" not in event_types
    assert effects == []
    payload = next(
        item for event_type, item in published if event_type == "task.cancelled"
    )
    assert payload["terminal_evidence"]["visible_output_emitted"] is True
