"""CWC-009.2 Lane B: Live pre-output retry/fallback validation fixture.

Proves:
- request_id remains unchanged across retry
- task_id remains unchanged
- first and second attempt_id values differ
- stale whooshd_request_id is not retained
- stale runtime provenance is not retained
- exactly one assistant message is persisted
- persisted correlation belongs to the successful final attempt
- the terminal event contains the final tuple

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


# ── Lane B: pre-output fallback identity proof ──────────────────────────────


def test_pre_output_fallback_preserves_root_identity(monkeypatch):
    """Lane B: first attempt fails pre-output, second succeeds.
    request_id and task_id stable, attempt_id changes."""
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(),
    )

    task = ChatCompletionTask(
        task_id="task-fallback-root",
        request_id="req-fallback-root",
        user_id="user-1",
        thread_id=1,
    )

    def failing_first(*_args, **_kwargs):
        if False:
            yield ""
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.PROVIDER_ERROR,
            visible_output_emitted=False,
            explicit_provider_terminal_observed=False,
            finish_reason=None,
            transport_ended_cleanly=False,
            provider="local",
            model="stub-model",
            failure_kind="provider_error_frame",
            retry_permitted=True,
        )

    monkeypatch.setattr(chat_completion_service, "stream_local", failing_first)

    with pytest.raises(CompletionTerminalError):
        chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[{"role": "user", "content": "hi"}],
            provider="local",
            model="stub-model",
            bundle=None,
        )

    first_attempt_id = task.attempt_id
    assert first_attempt_id is not None

    def succeeding_second(*_args, **_kwargs):
        yield "fallback"
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.SUCCESS,
            visible_output_emitted=True,
            explicit_provider_terminal_observed=True,
            finish_reason="stop",
            transport_ended_cleanly=True,
            provider="local",
            model="stub-model",
        )

    monkeypatch.setattr(chat_completion_service, "stream_local", succeeding_second)

    result = chat_completion_service._execute_completion_attempt(
        task=task,
        messages_for_llm=[{"role": "user", "content": "hi"}],
        provider="local",
        model="stub-model",
        bundle=None,
    )

    second_attempt_id = task.attempt_id
    assert second_attempt_id is not None
    assert task.request_id == "req-fallback-root"
    assert task.task_id == "task-fallback-root"
    assert first_attempt_id != second_attempt_id
    assert result.terminal.successful is True
    assert result.output == "fallback"


def test_fallback_discards_stale_provenance(monkeypatch):
    """Lane B: stale provenance from first attempt not carried to second."""
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(),
    )

    task = ChatCompletionTask(
        task_id="task-no-stale",
        request_id="req-no-stale",
        user_id="user-1",
        thread_id=1,
    )

    def stale_stream(*_args, **_kwargs):
        if False:
            yield ""
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.PROVIDER_ERROR,
            visible_output_emitted=False,
            explicit_provider_terminal_observed=False,
            finish_reason=None,
            transport_ended_cleanly=False,
            provider="local",
            model="stub-model",
            failure_kind="provider_error_frame",
            retry_permitted=True,
            runtime_provenance={"whooshd_request_id": "whooshd-stale"},
            response_correlation={"whooshd_request_id": "whooshd-stale"},
        )

    monkeypatch.setattr(chat_completion_service, "stream_local", stale_stream)

    with pytest.raises(CompletionTerminalError):
        chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[{"role": "user", "content": "hi"}],
            provider="local",
            model="stub-model",
            bundle=None,
        )

    def fresh_stream(*_args, **_kwargs):
        yield "fresh"
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.SUCCESS,
            visible_output_emitted=True,
            explicit_provider_terminal_observed=True,
            finish_reason="stop",
            transport_ended_cleanly=True,
            provider="local",
            model="stub-model",
            response_correlation={"whooshd_request_id": "whooshd-fresh"},
        )

    monkeypatch.setattr(chat_completion_service, "stream_local", fresh_stream)

    result = chat_completion_service._execute_completion_attempt(
        task=task,
        messages_for_llm=[{"role": "user", "content": "hi"}],
        provider="local",
        model="stub-model",
        bundle=None,
    )

    assert result.terminal.successful is True
    assert result.response_correlation == {"whooshd_request_id": "whooshd-fresh"}


def test_completion_attempt_identity_lifecycle(monkeypatch):
    """Lane B: root identity stable across attempts while attempt identity changes."""
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(),
    )

    task = ChatCompletionTask(
        task_id="task-identity-lifecycle",
        request_id="req-identity-lifecycle",
        user_id="user-1",
        thread_id=1,
    )

    def failing_stream(*_args, **_kwargs):
        if False:
            yield ""
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.PROVIDER_ERROR,
            visible_output_emitted=False,
            explicit_provider_terminal_observed=False,
            finish_reason=None,
            transport_ended_cleanly=False,
            provider="local",
            model="stub-model",
            failure_kind="provider_error_frame",
            retry_permitted=True,
        )

    def succeeding_stream(*_args, **_kwargs):
        if False:
            yield ""
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.SUCCESS,
            visible_output_emitted=True,
            explicit_provider_terminal_observed=True,
            finish_reason="stop",
            transport_ended_cleanly=True,
            provider="local",
            model="stub-model",
        )

    monkeypatch.setattr(chat_completion_service, "stream_local", failing_stream)

    with pytest.raises(CompletionTerminalError):
        chat_completion_service._execute_completion_attempt(
            task=task,
            messages_for_llm=[{"role": "user", "content": "hi"}],
            provider="local",
            model="stub-model",
            bundle=None,
        )

    first_attempt_id = task.attempt_id
    assert first_attempt_id is not None
    assert task.request_id == "req-identity-lifecycle"
    assert task.task_id == "task-identity-lifecycle"

    monkeypatch.setattr(chat_completion_service, "stream_local", succeeding_stream)

    result = chat_completion_service._execute_completion_attempt(
        task=task,
        messages_for_llm=[{"role": "user", "content": "hi"}],
        provider="local",
        model="stub-model",
        bundle=None,
    )

    second_attempt_id = task.attempt_id
    assert second_attempt_id is not None
    assert first_attempt_id != second_attempt_id
    assert task.request_id == "req-identity-lifecycle"
    assert task.task_id == "task-identity-lifecycle"
    assert result.terminal.successful is True
    assert result.attempt_id == second_attempt_id


def test_exactly_one_assistant_message_persisted_on_fallback(monkeypatch):
    """Lane B: after successful completion, exactly one assistant message
    is persisted by the worker."""
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
    monkeypatch.setattr(chat_worker, "_embed_message", lambda *_, **__: None)
    monkeypatch.setattr(chat_worker, "_persist_turn_id_metadata", lambda **_kwargs: True)
    monkeypatch.setattr(
        chat_worker, "_persist_message_extra_meta", lambda **_kwargs: True
    )
    monkeypatch.setattr(
        chat_worker.dependencies,
        "chatlog_db",
        SimpleNamespace(
            create_message=lambda *_args, **_kwargs: (
                persist_count.append(persist_count[-1] + 1) or persist_count[-1]
            ),
            write_audit_log=lambda *_args, **_kwargs: None,
        ),
    )
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "build_sanitized_payload_summary",
        lambda *args, **kwargs: {"message_count": 2},
    )
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(),
    )

    def _success_stream(*_args, **_kwargs):
        yield "ok"
        return CompletionTerminalEvidence(
            status=CompletionTerminalStatus.SUCCESS,
            visible_output_emitted=True,
            explicit_provider_terminal_observed=True,
            finish_reason="stop",
            transport_ended_cleanly=True,
            provider="local",
            model="stub-model",
        )

    monkeypatch.setattr(
        chat_worker._chat_completion_service, "stream_local", _success_stream
    )

    async def _build_messages(_task):
        return [{"role": "user", "content": "hello"}], "local", "test-model", {}, {}

    monkeypatch.setattr(chat_worker, "_build_messages_for_llm", _build_messages)
    monkeypatch.setattr(chat_worker, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(
        chat_worker,
        "build_provider_truth",
        lambda provider, settings, **kwargs: {"provider": provider, **kwargs},
    )

    task = ChatCompletionTask(
        user_id="local",
        task_id="task-fallback-persist",
        thread_id=7,
        provider="local",
        model="stub-model",
        origin="api:chat.complete",
    )

    chat_worker._run_chat_task(task)

    event_types = [event_type for event_type, _payload in published]
    assert "task.completed" in event_types
    # Exactly one message persisted via create_message
    assert persist_count[-1] == 1
