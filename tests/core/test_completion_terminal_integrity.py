from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from guardian.core import chat_completion_service
from guardian.core.completion_terminal import (
    CompletionTerminalEvidence,
    CompletionTerminalError,
    require_successful_terminal,
)
from guardian.core.db import ChatAttemptReconciliation
from guardian.protocol_tokens import CompletionTerminalStatus
from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker

# The original persisted lock capability of a durably completed attempt. A
# mutable packet field can never stand in for it.
_DURABLE_ORIGINAL_LOCK_TOKEN = "durable-original-token"


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
            tool_exposure={
                "automatic": False,
                "advertisedToolCount": 0,
                "advertisedToolCommandIds": [],
                "providerDispatchToolCount": 0,
                "providerDispatchToolCommandIds": [],
                "commandIdsTruncated": False,
            },
        )


def _seed_worker_terminal_harness(
    monkeypatch,
    task,
    *,
    terminal_write_acknowledged: bool = True,
    durable_completion_message_id: int | None = None,
    cancelled: bool = False,
):
    published: list[tuple[str, dict]] = []
    effects: list[str] = []
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_args: cancelled)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_args: None)
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

    # Durable-authority seams. The worker reads its durable attempt before any
    # accepted work, and may publish a newly generated terminal event only
    # after the matching durable terminal write has been acknowledged. The
    # identity below is exact: request, task, thread and turn.
    #
    # `durable_completion_message_id` models an attempt that is already
    # durably complete. That durable truth outranks any later local outcome,
    # and it carries the original persisted lock capability that cleanup is
    # allowed to use. `cancelled` models a cancellation signal that is present
    # while the worker runs.
    terminal_writes: list[tuple] = []
    observations: list[str] = []
    releases: list[tuple] = []

    def _read_attempt(_db, backend_task_id):
        observations.append(backend_task_id)
        return {
            "request_id": task.request_id,
            "backend_task_id": task.task_id,
            "thread_id": task.thread_id,
            "turn_id": chat_worker._extract_turn_id(task),
            "completed_message_id": durable_completion_message_id,
            "terminal_event_type": None,
            "terminal_outcome": None,
            "deadline_snapshot": None,
        }

    def _record_terminal(
        _db, *, request_id, backend_task_id, thread_id, turn_id, event_type, **_kwargs
    ):
        terminal_writes.append(
            (request_id, backend_task_id, thread_id, turn_id, event_type)
        )
        return terminal_write_acknowledged

    def _observe(_db, *, request_id, backend_task_id, thread_id, turn_id, **_kwargs):
        if durable_completion_message_id is None:
            # No durable terminal truth exists, so there is no persisted
            # capability and cleanup must not be attempted.
            return ChatAttemptReconciliation(None, None, None, None)
        return ChatAttemptReconciliation(
            durable_completion_message_id, None, None, _DURABLE_ORIGINAL_LOCK_TOKEN
        )

    def _release(thread_id, *, owner_task_id, lease_token):
        releases.append((thread_id, owner_task_id, lease_token))
        return True

    monkeypatch.setattr(
        chat_worker, "get_chat_completion_attempt_by_task_id", _read_attempt
    )
    monkeypatch.setattr(
        chat_worker, "record_chat_completion_attempt_terminal_event", _record_terminal
    )
    monkeypatch.setattr(
        chat_worker, "observe_chat_completion_attempt_terminal", _observe
    )
    monkeypatch.setattr(chat_worker, "release_terminal_attempt_turn_lock", _release)
    return published, effects, terminal_writes, observations, releases


def test_incomplete_output_publishes_failed_without_completion_effects(monkeypatch):
    task = _task()
    published, effects, terminal_writes, _observations, _releases = (
        _seed_worker_terminal_harness(monkeypatch, task)
    )
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

    chat_worker._run_chat_task(task)

    event_types = [event_type for event_type, _payload in published]
    assert "task.failed" in event_types
    assert "task.completed" not in event_types
    assert effects == []
    # The terminal event is published because the durable terminal write
    # was acknowledged, with exact identity.
    assert terminal_writes == [
        (
            task.request_id,
            task.task_id,
            task.thread_id,
            chat_worker._extract_turn_id(task),
            "task.failed",
        )
    ]
    failed = next(
        payload for event_type, payload in published if event_type == "task.failed"
    )
    assert failed["terminal_evidence"]["status"] == "stream_incomplete"
    # The visible output that was already produced is preserved in the
    # terminal evidence rather than dropped with the incomplete stream.
    assert failed["terminal_evidence"]["visible_output_emitted"] is True
    assert failed["first_output_observed"] is True


def test_cancelled_output_publishes_cancelled_without_persistence(monkeypatch):
    task = _task()
    published, effects, terminal_writes, _observations, _releases = (
        _seed_worker_terminal_harness(monkeypatch, task)
    )
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

    chat_worker._run_chat_task(task)

    event_types = [event_type for event_type, _payload in published]
    assert "task.cancelled" in event_types
    assert "task.completed" not in event_types
    assert effects == []
    # The terminal event is published because the durable terminal write
    # was acknowledged, with exact identity.
    assert terminal_writes == [
        (
            task.request_id,
            task.task_id,
            task.thread_id,
            chat_worker._extract_turn_id(task),
            "task.cancelled",
        )
    ]
    payload = next(
        item for event_type, item in published if event_type == "task.cancelled"
    )
    assert payload["terminal_evidence"]["visible_output_emitted"] is True


def test_unconfirmed_durable_authority_infers_no_terminal_outcome(monkeypatch):
    """A rejected durable write plus an uncertain read must publish nothing.

    The worker's local exception is not authority. With neither the durable
    write acknowledged nor an existing durable outcome confirmed, the worker
    infers no terminal event, and it manufactures no completion.
    """
    task = _task()
    published, effects, terminal_writes, _observations, _releases = (
        _seed_worker_terminal_harness(
            monkeypatch, task, terminal_write_acknowledged=False
        )
    )
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

    def _uncertain_observation(*_args, **_kwargs):
        raise RuntimeError("injected lost durable acknowledgement")

    monkeypatch.setattr(
        chat_worker, "observe_chat_completion_attempt_terminal", _uncertain_observation
    )

    chat_worker._run_chat_task(task)

    event_types = [event_type for event_type, _payload in published]
    assert "task.failed" not in event_types
    assert "task.cancelled" not in event_types
    assert "task.completed" not in event_types
    assert effects == []
    # The durable write was attempted with exact identity, and it was not
    # acknowledged, so nothing was published.
    assert terminal_writes == [
        (
            task.request_id,
            task.task_id,
            task.thread_id,
            chat_worker._extract_turn_id(task),
            "task.failed",
        )
    ]


def test_durable_completion_outranks_late_cancellation(monkeypatch):
    """A durable completion outranks a cancellation that arrives late.

    The accepted attempt is already durably complete, so the worker must
    project that durable truth and must never reach the cancellation branch.
    A cancellation seen afterwards may not rewrite a completion that already
    happened, and it may not cause provider work to run again.
    """
    task = _task()
    # A mutable packet field names a replacement lock. It grants no cleanup
    # authority.
    task.turn_lock_owner = "mutable-replacement-owner"
    task.turn_lock = {"lease_token": "mutable-replacement-token"}
    published, effects, terminal_writes, _observations, releases = (
        _seed_worker_terminal_harness(
            monkeypatch,
            task,
            durable_completion_message_id=42,
            cancelled=True,
        )
    )
    run_completion = Mock()
    monkeypatch.setattr(chat_worker, "run_chat_completion_task", run_completion)

    chat_worker._run_chat_task(task)

    event_types = [event_type for event_type, _payload in published]
    assert "task.cancelled" not in event_types
    assert "task.failed" not in event_types
    assert "task.completed" in event_types
    # The provider was not asked to run again for an already durable result,
    # and no execution identity was created for it.
    run_completion.assert_not_called()
    assert "task.running" not in event_types
    # No assistant message, evaluation or audio effect is repeated.
    assert effects == []
    # The durable completion was not rewritten by the late cancellation.
    assert terminal_writes == []
    completed = next(
        payload for event_type, payload in published if event_type == "task.completed"
    )
    assert completed["message_id"] == 42
    assert completed["reason"] == "durable_completion_recorded"
    # The durable completion identity is unchanged.
    assert completed["request_id"] == task.request_id
    assert completed["task_id"] == task.task_id
    assert completed["thread_id"] == task.thread_id
    assert completed["turn_id"] == chat_worker._extract_turn_id(task)
    # Cleanup used the original persisted lock capability, not the mutable
    # packet fields.
    assert releases == [(task.thread_id, task.task_id, _DURABLE_ORIGINAL_LOCK_TOKEN)]


def test_rejected_cancellation_write_manufactures_no_terminal_authority(monkeypatch):
    """A rejected durable cancellation write cannot become terminal authority.

    The worker's own durable terminal write is the authority for a
    request-bearing accepted attempt. When the cancellation write is not
    acknowledged and the durable observation is still pending, the worker
    must fail closed: it must not publish a cancellation, a failure or a
    completion, and it must not persist an assistant message or schedule
    completion effects.

    This is the cancellation counterpart of the rejected-failure case above.
    That case withholds the acknowledgement and makes the durable read
    uncertain; here the read is merely pending, so the two cover the
    distinct ways a durable outcome can stay unresolved.
    """
    task = _task()
    published, effects, terminal_writes, _observations, releases = (
        _seed_worker_terminal_harness(
            monkeypatch, task, terminal_write_acknowledged=False
        )
    )
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

    chat_worker._run_chat_task(task)

    event_types = [event_type for event_type, _payload in published]
    assert "task.cancelled" not in event_types
    assert "task.failed" not in event_types
    assert "task.completed" not in event_types
    # No assistant message, evaluation or audio effect was produced.
    assert effects == []
    # The rejected write carried the exact attempt identity.
    assert terminal_writes == [
        (
            task.request_id,
            task.task_id,
            task.thread_id,
            chat_worker._extract_turn_id(task),
            "task.cancelled",
        )
    ]
    # Without durable terminal truth there is no persisted capability, so no
    # cleanup is attempted.
    assert releases == []
