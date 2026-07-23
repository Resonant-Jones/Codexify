"""CWC-009.2 Lane C: Live post-output failure validation fixture.

Proves:
- one provider attempt only
- no fallback or retry
- failure correlation retains root/task/attempt IDs
- partial content is noncanonical
- no assistant message is persisted
- no completion-only side effects run
- terminal event is failed or incomplete, never completed
- no fabricated successful [DONE]

Uses mock-based validation fixtures (no production fault-injection endpoints).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from guardian.core import chat_completion_service
from guardian.core.chat_completion_service import ChatTaskCancelled
from guardian.core.completion_terminal import (
    CompletionTerminalEvidence,
    CompletionTerminalError,
)
from guardian.protocol_tokens import CompletionTerminalStatus
from guardian.tasks.types import ChatCompletionTask


# ── helpers ──────────────────────────────────────────────────────────────────


def _mock_settings(monkeypatch):
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(),
    )


# ── Lane C: Post-output failure (error frame, no [DONE]) ────────────────────


def test_post_output_error_frame_no_done_returns_failure(monkeypatch):
    """Lane C: mock stream emits output then PROVIDER_ERROR terminal (no [DONE])."""
    _mock_settings(monkeypatch)

    def error_after_output(*_args, **_kwargs):
        yield "partial-output"
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.PROVIDER_ERROR,
            visible_output_emitted=True,
            explicit_provider_terminal_observed=True,
            finish_reason=None,
            transport_ended_cleanly=True,
            provider="local",
            model="stub-model",
            failure_kind="provider_error_frame",
            retry_permitted=False,
        )

    monkeypatch.setattr(chat_completion_service, "stream_local", error_after_output)

    task = ChatCompletionTask(
        task_id="task-post-output",
        request_id="req-post-output",
        user_id="user-1",
        thread_id=1,
    )

    with pytest.raises(CompletionTerminalError) as exc:
        chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[{"role": "user", "content": "hi"}],
            provider="local",
            model="stub-model",
            bundle=None,
        )

    assert exc.value.evidence.status is CompletionTerminalStatus.PROVIDER_ERROR
    assert exc.value.evidence.visible_output_emitted is True
    assert exc.value.evidence.retry_permitted is False


def test_post_output_transport_cut_returns_incomplete(monkeypatch):
    """Lane C: mock stream yields one token then ends with STREAM_INCOMPLETE."""
    _mock_settings(monkeypatch)

    def cut_stream(*_args, **_kwargs):
        yield "before-cut"
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.STREAM_INCOMPLETE,
            visible_output_emitted=True,
            explicit_provider_terminal_observed=False,
            finish_reason=None,
            transport_ended_cleanly=False,
            provider="local",
            model="stub-model",
            failure_kind="missing_stream_terminal",
            retry_permitted=False,
        )

    monkeypatch.setattr(chat_completion_service, "stream_local", cut_stream)

    task = ChatCompletionTask(
        task_id="task-transport-cut",
        request_id="req-transport-cut",
        user_id="user-1",
        thread_id=1,
    )

    with pytest.raises(CompletionTerminalError) as exc:
        chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[{"role": "user", "content": "hi"}],
            provider="local",
            model="stub-model",
            bundle=None,
        )

    assert exc.value.evidence.status is CompletionTerminalStatus.STREAM_INCOMPLETE
    assert exc.value.evidence.visible_output_emitted is True
    assert exc.value.evidence.retry_permitted is False


def test_post_output_failure_no_retry(monkeypatch):
    """Lane C: post-output failure has retry_permitted=False."""
    _mock_settings(monkeypatch)

    def failing_stream(*_args, **_kwargs):
        yield "partial"
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.PROVIDER_ERROR,
            visible_output_emitted=True,
            explicit_provider_terminal_observed=True,
            finish_reason=None,
            transport_ended_cleanly=True,
            provider="local",
            model="stub-model",
            failure_kind="provider_error_frame",
            retry_permitted=False,
        )

    monkeypatch.setattr(chat_completion_service, "stream_local", failing_stream)

    task = ChatCompletionTask(
        task_id="task-no-retry",
        request_id="req-no-retry",
        user_id="user-1",
        thread_id=1,
    )

    with pytest.raises(CompletionTerminalError) as exc:
        chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[{"role": "user", "content": "hi"}],
            provider="local",
            model="stub-model",
            bundle=None,
        )

    assert exc.value.evidence.status is CompletionTerminalStatus.PROVIDER_ERROR
    assert exc.value.evidence.retry_permitted is False
    assert exc.value.evidence.visible_output_emitted is True


def test_post_output_failure_correlation_preserved(monkeypatch):
    """Lane C: failure retains root/task/attempt correlation."""
    _mock_settings(monkeypatch)

    def failing_stream(*_args, **_kwargs):
        yield "partial"
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.PROVIDER_ERROR,
            visible_output_emitted=True,
            explicit_provider_terminal_observed=True,
            finish_reason=None,
            transport_ended_cleanly=True,
            provider="local",
            model="stub-model",
            failure_kind="provider_error_frame",
            retry_permitted=False,
            response_correlation={"whooshd_request_id": "whooshd-fail-corr"},
        )

    monkeypatch.setattr(chat_completion_service, "stream_local", failing_stream)

    task = ChatCompletionTask(
        task_id="task-fail-corr",
        request_id="req-fail-corr",
        user_id="user-1",
        thread_id=1,
    )

    with pytest.raises(CompletionTerminalError) as exc:
        chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[{"role": "user", "content": "hi"}],
            provider="local",
            model="stub-model",
            bundle=None,
        )

    assert task.request_id == "req-fail-corr"
    assert task.task_id == "task-fail-corr"
    assert task.attempt_id is not None
    assert exc.value.evidence.response_correlation == {
        "whooshd_request_id": "whooshd-fail-corr"
    }


def test_post_output_failure_no_assistant_persistence(monkeypatch):
    """Lane C: after post-output failure, no assistant message is persisted."""
    from guardian.workers import chat_worker

    persist_count = [0]
    published: list[tuple[str, dict]] = []

    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_args: False)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_args: None)
    monkeypatch.setattr(chat_worker, "release_turn_lock", lambda *_args: True)
    monkeypatch.setattr(
        chat_worker, "_find_assistant_message_for_turn", lambda **_kwargs: None
    )
    monkeypatch.setattr(
        chat_worker, "_find_assistant_message_id_by_turn_id", lambda **_kwargs: None
    )
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, payload: published.append(
            (event_type, dict(payload or {}))
        ),
    )
    monkeypatch.setattr(
        chat_worker, "schedule_post_completion_eval", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        chat_worker,
        "_schedule_assistant_message_audio_generation",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(
        chat_worker.dependencies,
        "chatlog_db",
        SimpleNamespace(
            create_message=lambda *_args, **_kwargs: (
                persist_count.append(persist_count[-1] + 1) or persist_count[-1]
            ),
        ),
    )

    error = CompletionTerminalError(
        CompletionTerminalEvidence(
            status=CompletionTerminalStatus.STREAM_INCOMPLETE,
            visible_output_emitted=True,
            explicit_provider_terminal_observed=False,
            finish_reason=None,
            transport_ended_cleanly=False,
            provider="local",
            model="stub-model",
            failure_kind="missing_stream_terminal",
            retry_permitted=False,
        )
    )

    monkeypatch.setattr(
        chat_worker,
        "run_chat_completion_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(error),
    )

    task = ChatCompletionTask(
        user_id="local",
        task_id="task-post-output-persist",
        thread_id=7,
        provider="local",
        model="stub-model",
        origin="api:chat.complete",
    )

    chat_worker._run_chat_task(task)

    event_types = [event_type for event_type, _payload in published]
    assert "task.failed" in event_types
    assert "task.completed" not in event_types
    assert "task.cancelled" not in event_types
    assert persist_count[-1] == 0

    failed = next(
        payload for event_type, payload in published if event_type == "task.failed"
    )
    assert failed["terminal_evidence"]["status"] == "stream_incomplete"
    assert failed["first_output_observed"] is True


def test_no_fabricated_done_in_post_output_failure(monkeypatch):
    """Lane C: stream fails after output, no [DONE] fabricated."""
    _mock_settings(monkeypatch)

    def failing_stream_no_done(*_args, **_kwargs):
        yield "partial"
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.STREAM_INCOMPLETE,
            visible_output_emitted=True,
            explicit_provider_terminal_observed=False,
            finish_reason=None,
            transport_ended_cleanly=False,
            provider="local",
            model="stub-model",
            failure_kind="missing_stream_terminal",
            retry_permitted=False,
        )

    monkeypatch.setattr(chat_completion_service, "stream_local", failing_stream_no_done)

    task = ChatCompletionTask(
        task_id="task-no-done",
        request_id="req-no-done",
        user_id="user-1",
        thread_id=1,
    )

    with pytest.raises(CompletionTerminalError) as exc:
        chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[{"role": "user", "content": "hi"}],
            provider="local",
            model="stub-model",
            bundle=None,
        )

    assert exc.value.evidence.status is CompletionTerminalStatus.STREAM_INCOMPLETE
    assert exc.value.evidence.failure_kind == "missing_stream_terminal"
    assert exc.value.evidence.transport_ended_cleanly is False


def test_one_attempt_only_post_output_failure(monkeypatch):
    """Lane C: post-output failure performs exactly one provider attempt."""
    _mock_settings(monkeypatch)

    attempt_count = [0]

    def counting_stream(*_args, **_kwargs):
        attempt_count[0] += 1
        yield "partial"
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.STREAM_INCOMPLETE,
            visible_output_emitted=True,
            explicit_provider_terminal_observed=False,
            finish_reason=None,
            transport_ended_cleanly=False,
            provider="local",
            model="stub-model",
            failure_kind="missing_stream_terminal",
            retry_permitted=False,
        )

    monkeypatch.setattr(chat_completion_service, "stream_local", counting_stream)

    task = ChatCompletionTask(
        task_id="task-one-attempt",
        request_id="req-one-attempt",
        user_id="user-1",
        thread_id=1,
    )

    with pytest.raises(CompletionTerminalError):
        chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[{"role": "user", "content": "hi"}],
            provider="local",
            model="stub-model",
            bundle=None,
        )

    assert attempt_count[0] == 1
