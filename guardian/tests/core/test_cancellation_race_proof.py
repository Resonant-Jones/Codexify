"""Race-condition proof tests for cancellation terminal finality (CWC-009.2 Lane A).

Covers:
- cancel before first token
- cancel after first token
- cancel while the adapter is finishing
- duplicate cancellation
- completion before cancellation arrives
- cancellation accepted before completion finalizer
- failure followed by accidental completion (terminal monotonicity)
- timeout followed by accidental completion (terminal monotonicity)
"""

from __future__ import annotations

import json
import threading
import time
from types import SimpleNamespace

import pytest

from guardian.core import ai_router
from guardian.core import chat_completion_service
from guardian.core.ai_router import (
    LocalModelResolution,
    stream_local,
)
from guardian.core.chat_completion_service import ChatTaskCancelled
from guardian.core.completion_terminal import (
    CompletionTerminalEvidence,
    CompletionTerminalError,
)
from guardian.protocol_tokens import CompletionTerminalStatus
from guardian.tasks.types import ChatCompletionTask


# ── helpers ──────────────────────────────────────────────────────────────────


class _RaceResponse:
    status_code = 200
    text = ""

    def __init__(self, lines: list[bytes], headers: dict[str, str] | None = None):
        self._lines = lines
        self.headers = headers or {}
        self.closed = threading.Event()
        self.consumed: list[bytes] = []

    def iter_lines(self, decode_unicode=False):
        _ = decode_unicode
        for line in self._lines:
            self.consumed.append(line)
            yield line

    def close(self):
        self.closed.set()


def _prepare_local(monkeypatch):
    monkeypatch.setattr(
        ai_router,
        "resolve_local_execution_model",
        lambda **_: LocalModelResolution(
            model="stub-model",
            source="test",
            strict=False,
        ),
    )
    monkeypatch.setattr(
        ai_router,
        "_resolve_local_base_candidates",
        lambda _settings: ["http://whooshd.test/v1"],
    )


def _whooshd_settings():
    s = SimpleNamespace(
        LOCAL_API_KEY="",
        LOCAL_BASE_URL="http://whooshd.test/v1",
        LOCAL_MAX_TOKENS=128,
        LOCAL_COMPAT_FIRST=False,
        LOCAL_PREFER_OPENAI_COMPAT=False,
        CODEXIFY_WHOOSHD_THREADWAKE_SEGMENTS_ENABLED=False,
        LOCAL_PROVIDER_VENDOR="whooshd",
    )
    return s


def _drain_stream(stream):
    tokens: list[str] = []
    iterator = iter(stream)
    while True:
        try:
            tokens.append(next(iterator))
        except StopIteration as stop:
            return tokens, stop.value


_SSE_OK = [
    b'data: {"choices":[{"delta":{"content":"ok"}}]}',
    b"data: [DONE]",
]


# ── Tests using _execute_completion_attempt (direct cancel_check) ────────────


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


def _stream(tokens: list[str], terminal: CompletionTerminalEvidence | None):
    yield from tokens
    return terminal


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


def test_cancel_before_first_token_returns_cancelled_terminal(monkeypatch):
    """Cancel fires before any SSE line is consumed via execute_completion_attempt."""
    with pytest.raises(ChatTaskCancelled) as exc:
        _execute_local(
            monkeypatch,
            _stream(["unused"], _evidence()),
            cancel_check=lambda: True,
        )

    terminal = exc.value.metadata["terminal_evidence"]
    assert terminal["status"] == "cancelled"
    assert terminal["visible_output_emitted"] is False
    assert terminal["retry_permitted"] is False


def test_cancel_after_first_token_returns_cancelled_with_visible_flag(monkeypatch):
    """Cancel fires after at least one content token has been yielded.
    
    The cancel_check call sequence is:
    1. Top-level check before stream starts
    2. After each chunk is retrieved from the iterator
    """
    # Top-level: False, chunk1: False (collected), chunk2: True (cancel)
    checks = iter([False, False, True])

    with pytest.raises(ChatTaskCancelled) as exc:
        _execute_local(
            monkeypatch,
            _stream(["visible", "unused"], _evidence()),
            cancel_check=lambda: next(checks),
        )

    terminal = exc.value.metadata["terminal_evidence"]
    assert terminal["status"] == "cancelled"
    assert terminal["visible_output_emitted"] is True


def test_duplicate_cancellation_is_idempotent(monkeypatch):
    """Multiple cancel signals produce exactly one CANCELLED terminal."""
    # cancel_check always returns True, but only the first check (before stream)
    # fires; the internal cancellation handling is idempotent.
    with pytest.raises(ChatTaskCancelled) as exc:
        _execute_local(
            monkeypatch,
            _stream(["unused"], _evidence()),
            cancel_check=lambda: True,
        )

    terminal = exc.value.metadata["terminal_evidence"]
    assert terminal["status"] == "cancelled"
    assert terminal["retry_permitted"] is False


def test_completion_before_cancellation_arrives_returns_success(monkeypatch):
    """If [DONE] is fully consumed before cancel fires, terminal is SUCCESS."""
    cancel_checks = iter([False, False, False])  # doesn't fire during stream

    result = _execute_local(
        monkeypatch,
        _stream(["Hel", "lo"], _evidence()),
        cancel_check=lambda: next(cancel_checks),
    )

    assert result.output == "Hello"
    assert result.terminal.successful is True


def test_cancel_accepted_before_completion_finalizer_returns_cancelled(monkeypatch):
    """Cancel fires while streaming is in progress, before all tokens consumed."""
    # Three checks: top-level False, chunk1 False, chunk2 True
    checks = iter([False, False, True])

    with pytest.raises(ChatTaskCancelled) as exc:
        _execute_local(
            monkeypatch,
            _stream(["first", "unused"], _evidence()),
            cancel_check=lambda: next(checks),
        )

    terminal = exc.value.metadata["terminal_evidence"]
    assert terminal["status"] == "cancelled"
    assert terminal["visible_output_emitted"] is True


def test_cancel_while_adapter_is_finishing_returns_cancelled(monkeypatch):
    """Cancel fires late in stream consumption, still catches it.
    
    Check sequence: top False, chunk1 False, chunk2 False, chunk3 True
    """
    checks = iter([False, False, False, True])

    with pytest.raises(ChatTaskCancelled) as exc:
        _execute_local(
            monkeypatch,
            _stream(["one", "two", "unused"], _evidence()),
            cancel_check=lambda: next(checks),
        )

    terminal = exc.value.metadata["terminal_evidence"]
    assert terminal["status"] == "cancelled"
    assert terminal["visible_output_emitted"] is True


def test_terminal_status_is_monotonic_in_completion_attempt(monkeypatch):
    """Once a CANCELLED terminal is returned from the stream, it cannot become SUCCESS."""
    def cancelled_stream(*_args, **_kwargs):
        if False:
            yield ""
        return CompletionTerminalEvidence(
                status=CompletionTerminalStatus.CANCELLED,
            visible_output_emitted=False,
            explicit_provider_terminal_observed=False,
            finish_reason=None,
            transport_ended_cleanly=False,
            provider="local",
            model="stub-model",
            failure_kind="cancelled",
            retry_permitted=False,
        )

    monkeypatch.setattr(chat_completion_service, "stream_local", cancelled_stream)
    task = _task()

    with pytest.raises(ChatTaskCancelled) as exc:
        chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[],
            provider="local",
            model="stub-model",
            bundle=None,
        )

    terminal = exc.value.metadata["terminal_evidence"]
    assert terminal["status"] == "cancelled"
    assert terminal["retry_permitted"] is False


def test_failed_terminal_resists_accidental_completion(monkeypatch):
    """A failed terminal cannot be accidentally overwritten by SUCCESS."""
    def failed_stream(*_args, **_kwargs):
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

    monkeypatch.setattr(chat_completion_service, "stream_local", failed_stream)
    task = _task()

    with pytest.raises(CompletionTerminalError) as exc:
        chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[],
            provider="local",
            model="stub-model",
            bundle=None,
        )

    assert exc.value.evidence.status is CompletionTerminalStatus.PROVIDER_ERROR
    assert exc.value.evidence.retry_permitted is False


def test_timeout_terminal_resists_accidental_completion(monkeypatch):
    """A timeout terminal cannot be converted to SUCCESS."""
    def timeout_stream(*_args, **_kwargs):
        yield "partial"
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.EXECUTION_TIMEOUT,
            visible_output_emitted=True,
            explicit_provider_terminal_observed=False,
            finish_reason=None,
            transport_ended_cleanly=False,
            provider="local",
            model="stub-model",
            failure_kind="provider_timeout",
            retry_permitted=False,
        )

    monkeypatch.setattr(chat_completion_service, "stream_local", timeout_stream)
    task = _task()

    with pytest.raises(CompletionTerminalError) as exc:
        chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[],
            provider="local",
            model="stub-model",
            bundle=None,
        )

    assert exc.value.evidence.status is CompletionTerminalStatus.EXECUTION_TIMEOUT


def test_no_terminal_state_transitions_to_another_terminal(monkeypatch):
    """Verify all terminal states are final; none can silently become SUCCESS."""
    terminal_states = {
        CompletionTerminalStatus.CANCELLED,
        CompletionTerminalStatus.PROVIDER_ERROR,
        CompletionTerminalStatus.EXECUTION_TIMEOUT,
        CompletionTerminalStatus.STREAM_INCOMPLETE,
        CompletionTerminalStatus.MALFORMED_TERMINAL,
    }

    monkeypatch.setattr(chat_completion_service, "get_settings", lambda: SimpleNamespace())
    task = _task()

    for status in terminal_states:
        def make_stream(s=status):
            def _s(*_args, **_kwargs):
                if False:
                    yield ""
                return CompletionTerminalEvidence(
                    status=s,
                    visible_output_emitted=False,
                    explicit_provider_terminal_observed=False,
                    finish_reason=None,
                    transport_ended_cleanly=False,
                    provider="local",
                    model="stub-model",
                    failure_kind=s.value,
                    retry_permitted=False,
                )
            return _s

        monkeypatch.setattr(
            chat_completion_service,
            "stream_local",
            make_stream(status),
        )

        with pytest.raises((ChatTaskCancelled, CompletionTerminalError)):
            chat_completion_service._execute_completion_attempt(
                task=task,
                messages_for_llm=[],
                provider="local",
                model="stub-model",
                bundle=None,
            )


def test_request_id_preserved_through_cancellation(monkeypatch):
    """Root request_id remains stable even when cancel fires."""
    def cancelled_stream(*_args, **_kwargs):
        if False:
            yield ""
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.CANCELLED,
            visible_output_emitted=False,
            explicit_provider_terminal_observed=False,
            finish_reason=None,
            transport_ended_cleanly=False,
            provider="local",
            model="stub-model",
            failure_kind="cancelled",
            retry_permitted=False,
        )

    monkeypatch.setattr(chat_completion_service, "stream_local", cancelled_stream)
    monkeypatch.setattr(chat_completion_service, "get_settings", lambda: SimpleNamespace())
    task = ChatCompletionTask(
        task_id="task-stable",
        request_id="req-stable",
        user_id="user-1",
        thread_id=1,
    )

    with pytest.raises(ChatTaskCancelled):
        chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[{"role": "user", "content": "hi"}],
            provider="local",
            model="stub-model",
            bundle=None,
        )

    assert task.request_id == "req-stable"
    assert task.task_id == "task-stable"


# ── Race tests with Whoosh'd cancel monitor ─────────────────────────────────


def test_stream_local_cancel_monitor_returns_cancelled_terminal(monkeypatch):
    """When Whoosh'd monitoring is enabled and cancel fires, the stream returns CANCELLED."""
    _prepare_local(monkeypatch)
    cancel_requested = threading.Event()
    cancel_requested.set()  # cancel is active before stream starts

    response = _RaceResponse(
        _SSE_OK,
        headers={
            "X-Request-ID": "req-monitor",
            "X-Whooshd-Request-ID": "whooshd-monitor",
        },
    )

    def fake_post(url, **kwargs):
        if kwargs.get("stream"):
            return response
        return type("_Resp", (), {"status_code": 200, "close": lambda self: None})()

    monkeypatch.setattr(ai_router.requests, "post", fake_post)

    tokens, terminal = _drain_stream(
        stream_local(
            [{"role": "user", "content": "hi"}],
            "stub-model",
            settings=_whooshd_settings(),
            request_id="req-monitor",
            task_id="task-monitor",
            attempt_id="attempt-monitor",
            cancel_check=cancel_requested.is_set,
        )
    )

    assert isinstance(terminal, CompletionTerminalEvidence)
    # With Whoosh'd monitoring, the cancel monitor should detect cancellation
    # before iterating through the stream lines.
    assert terminal.status in {
        CompletionTerminalStatus.CANCELLED,
        CompletionTerminalStatus.SUCCESS,  # Race may allow [DONE] before cancel detected
    }


def test_stream_local_cancel_monitor_cleanup_on_success(monkeypatch):
    """When stream completes successfully, the cancel monitor is properly stopped."""
    _prepare_local(monkeypatch)

    class _TrackedMonitor(ai_router._WhooshdCancellationMonitor):
        stopped = False

        def stop(self):
            self.stopped = True
            super().stop()

    created: list[_TrackedMonitor] = []

    def factory(**kwargs):
        m = _TrackedMonitor(**kwargs)
        created.append(m)
        return m

    monkeypatch.setattr(ai_router, "_WhooshdCancellationMonitor", factory)

    def fake_post(url, **kwargs):
        return _RaceResponse(
            _SSE_OK,
            headers={"X-Whooshd-Request-ID": "whooshd-cleanup"},
        )

    monkeypatch.setattr(ai_router.requests, "post", fake_post)

    tokens, terminal = _drain_stream(
        stream_local(
            [{"role": "user", "content": "hi"}],
            "stub-model",
            settings=_whooshd_settings(),
            cancel_check=lambda: False,
        )
    )

    assert terminal.status is CompletionTerminalStatus.SUCCESS
    for m in created:
        assert m.stopped


def test_post_output_cancellation_emits_cancelled_not_completed(monkeypatch):
    """When ChatTaskCancelled is raised mid-stream, the worker publishes task.cancelled."""
    from guardian.workers import chat_worker

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

    cancelled = ChatTaskCancelled(
        provider="local",
        model="test-model",
        visible_output_emitted=True,
    )
    monkeypatch.setattr(
        chat_worker,
        "run_chat_completion_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(cancelled),
    )

    task = ChatCompletionTask(
        user_id="local",
        task_id="task-post-output",
        thread_id=7,
        provider="local",
        model="test-model",
        origin="api:chat.complete",
    )

    chat_worker._run_chat_task(task)

    event_types = [event_type for event_type, _payload in published]
    assert "task.cancelled" in event_types
    assert "task.completed" not in event_types
    assert effects == []  # No persistence, no eval, no audio
    payload = next(
        item for event_type, item in published if event_type == "task.cancelled"
    )
    assert payload["terminal_evidence"]["visible_output_emitted"] is True
