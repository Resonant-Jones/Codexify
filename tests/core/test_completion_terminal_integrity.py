from __future__ import annotations

import logging
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
from guardian.protocol_tokens import CompletionTerminalStatus, TaskEventType
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


_TERMINAL_TURN_ID = "6f0a1b2c-3d4e-4f50-8a9b-0c1d2e3f4a5b"


def _worker_task() -> ChatCompletionTask:
    """Task whose durable identities agree with the worker's attempt port.

    The worker admits a task only when a durable attempt matches the
    request, backend task, thread, and turn identity exactly, so the
    terminal-evidence tests must supply one mutually consistent set rather
    than relying on a request identity that normalization invented.
    """
    return ChatCompletionTask(
        user_id="local",
        task_id="task-terminal",
        thread_id=7,
        provider="local",
        model="test-model",
        origin=f"api:chat.complete|turn_id={_TERMINAL_TURN_ID}",
        request_id="request-terminal-evidence",
        turn_id=_TERMINAL_TURN_ID,
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


class _SyntheticDurableAttempt:
    """Test double for the worker's durable chat-attempt port.

    This is not live PostgreSQL durability. It models the acknowledged
    boundary the worker depends on, so the worker keeps its real admission
    gate (an attempt must be confirmed before any work executes), its real
    durable terminal acknowledgement requirement, and its real
    capability-gated Redis cleanup while terminal behavior is under test.

    The double keeps four durable facts apart:

    * an *attempted* terminal write, recorded with its exact request,
      task, thread and turn identity;
    * an *acknowledged* write, which becomes visible to later observation;
    * a *rejected* write, which leaves the observed durable state alone;
    * the *observed* durable terminal state itself.

    An attempted write is not an acknowledged terminal result, so the two are
    never reported as the same thing.

    The private turn-lock capability is withheld by default, so the
    production cleanup path declines the Redis release on its own. It is
    granted only by an observed durable terminal state, never by the test
    asking for it, and the strict cleanup seam releases only the original
    persisted capability for its own task.
    """

    def __init__(
        self,
        *,
        task: ChatCompletionTask,
        confirmed: bool = True,
        acknowledged_terminal: bool = True,
        durable_completion_message_id: int | None = None,
        observation_uncertain: bool = False,
        expose_lock_capability: bool = False,
    ):
        self.task = task
        self.confirmed = confirmed
        self.acknowledged_terminal = acknowledged_terminal
        self.durable_completion_message_id = durable_completion_message_id
        self.observation_uncertain = observation_uncertain
        self.expose_lock_capability = expose_lock_capability
        self.read_attempts: list[str] = []
        self.attempted_writes: list[tuple] = []
        self.acknowledged_writes: list[tuple] = []
        self.rejected_writes: list[tuple] = []
        self.recorded_terminals: list[str] = []
        self.observed_authorities: list[ChatAttemptReconciliation] = []
        self.releases: list[tuple] = []
        self.terminal_event_type: str | None = None

    @property
    def identity(self) -> tuple[str, str, int, str]:
        return (
            self.task.request_id,
            self.task.task_id,
            self.task.thread_id,
            str(self.task.turn_id or ""),
        )

    @property
    def durable_terminal_visible(self) -> bool:
        """Whether the durable state shows a terminal outcome at all."""
        return (
            self.terminal_event_type is not None
            or self.durable_completion_message_id is not None
        )

    def read_attempt(self, _chatlog_db, backend_task_id):
        self.read_attempts.append(backend_task_id)
        if not self.confirmed:
            return None
        if backend_task_id != self.task.task_id:
            # A read for a different backend task cannot return a valid row
            # for the requested task.
            return None
        return {
            "request_id": self.task.request_id,
            "backend_task_id": self.task.task_id,
            "thread_id": self.task.thread_id,
            "turn_id": self.task.turn_id,
            "completed_message_id": self.durable_completion_message_id,
            "terminal_event_type": None,
            "terminal_outcome": None,
            "deadline_snapshot": None,
        }

    def record_terminal(
        self,
        _chatlog_db,
        *,
        request_id,
        backend_task_id,
        thread_id,
        turn_id,
        event_type,
    ) -> bool:
        write = (request_id, backend_task_id, thread_id, turn_id, event_type)
        self.attempted_writes.append(write)
        if (request_id, backend_task_id, thread_id, turn_id) != self.identity:
            # A write with mismatched identity is never acknowledged.
            self.rejected_writes.append(write)
            return False
        if not self.acknowledged_terminal:
            # A rejected write leaves the observed durable state unchanged.
            self.rejected_writes.append(write)
            return False
        self.acknowledged_writes.append(write)
        self.recorded_terminals.append(event_type)
        self.terminal_event_type = event_type
        return True

    def observe_terminal(
        self,
        _chatlog_db,
        *,
        request_id,
        backend_task_id,
        thread_id,
        turn_id,
    ) -> ChatAttemptReconciliation:
        if self.observation_uncertain:
            # The acknowledgement is genuinely lost, so no durable terminal
            # state can be established at all.
            raise RuntimeError("injected lost durable acknowledgement")
        if (request_id, backend_task_id, thread_id, turn_id) != self.identity:
            raise ValueError(
                "Terminal observation does not match its durable attempt"
            )
        authority = ChatAttemptReconciliation(
            completed_message_id=self.durable_completion_message_id,
            terminal_event_type=self.terminal_event_type,
            terminal_outcome=None,
            # The private lock capability is present only when an observed
            # durable terminal state grants it. Otherwise the production
            # cleanup path must decline the Redis release.
            turn_lock_token=(
                _DURABLE_ORIGINAL_LOCK_TOKEN
                if self.expose_lock_capability and self.durable_terminal_visible
                else None
            ),
        )
        self.observed_authorities.append(authority)
        return authority

    def release_lock(self, thread_id, *, owner_task_id, lease_token) -> bool:
        """Stand in for the strict task/thread/token cleanup seam.

        Only the original persisted capability, released for its own task, is
        released. A replacement lock cannot be released by the old task, and
        a mutable packet token is not the persisted capability.
        """
        self.releases.append((thread_id, owner_task_id, lease_token))
        return (
            owner_task_id == self.task.task_id
            and lease_token == _DURABLE_ORIGINAL_LOCK_TOKEN
        )


def _seed_worker_terminal_harness(
    monkeypatch,
    *,
    confirmed_attempt: bool = True,
    acknowledged_terminal: bool = True,
    durable_completion_message_id: int | None = None,
    cancelled: bool = False,
    observation_uncertain: bool = False,
    expose_lock_capability: bool = False,
):
    published: list[tuple[str, dict]] = []
    effects: list[str] = []
    task = _worker_task()
    durable = _SyntheticDurableAttempt(
        task=task,
        confirmed=confirmed_attempt,
        acknowledged_terminal=acknowledged_terminal,
        durable_completion_message_id=durable_completion_message_id,
        observation_uncertain=observation_uncertain,
        expose_lock_capability=expose_lock_capability,
    )
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_args: cancelled)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_args: None)
    # Durable-attempt port. The worker stays behind its real admission gate:
    # it may execute only a confirmed attempt, and may publish a terminal
    # outcome only when the durable store acknowledged it.
    monkeypatch.setattr(
        chat_worker,
        "get_chat_completion_attempt_by_task_id",
        durable.read_attempt,
    )
    monkeypatch.setattr(
        chat_worker,
        "record_chat_completion_attempt_terminal_event",
        durable.record_terminal,
    )
    monkeypatch.setattr(
        chat_worker,
        "observe_chat_completion_attempt_terminal",
        durable.observe_terminal,
    )
    # The strict task/thread/token cleanup seam. The worker still decides
    # whether cleanup is authorized: the persisted capability comes from the
    # observed durable state, and this recorder only stands in for Redis.
    monkeypatch.setattr(
        chat_worker,
        "release_terminal_attempt_turn_lock",
        durable.release_lock,
    )
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
    return published, effects, task, durable


def test_incomplete_output_publishes_failed_without_completion_effects(
    monkeypatch, caplog
):
    published, effects, task, durable = _seed_worker_terminal_harness(monkeypatch)
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

    with caplog.at_level(logging.WARNING, logger="guardian.workers.chat_worker"):
        chat_worker._run_chat_task(task)

    event_types = [event_type for event_type, _payload in published]
    assert "task.failed" in event_types
    assert "task.completed" not in event_types
    assert effects == []
    # The terminal event is published because the durable terminal write
    # was acknowledged, with exact identity.
    assert durable.attempted_writes == [
        (
            task.request_id,
            task.task_id,
            task.thread_id,
            chat_worker._extract_turn_id(task),
            "task.failed",
        )
    ]
    assert durable.acknowledged_writes == durable.attempted_writes
    assert durable.rejected_writes == []
    failed = next(
        payload for event_type, payload in published if event_type == "task.failed"
    )
    assert failed["terminal_evidence"]["status"] == "stream_incomplete"
    # The visible output that was already produced is preserved in the
    # terminal evidence rather than dropped with the incomplete stream.
    assert failed["terminal_evidence"]["visible_output_emitted"] is True
    assert failed["first_output_observed"] is True
    # Publication followed an acknowledged durable terminal write, and the
    # absent turn-lock capability made the production cleanup path decline
    # the Redis release instead of releasing an unverified lock.
    assert durable.recorded_terminals == [TaskEventType.TASK_FAILED.value]
    assert "terminal_cleanup_capability_unavailable" in caplog.text


def test_cancelled_output_publishes_cancelled_without_persistence(
    monkeypatch, caplog
):
    published, effects, task, durable = _seed_worker_terminal_harness(monkeypatch)
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

    with caplog.at_level(logging.WARNING, logger="guardian.workers.chat_worker"):
        chat_worker._run_chat_task(task)

    event_types = [event_type for event_type, _payload in published]
    assert "task.cancelled" in event_types
    assert "task.completed" not in event_types
    assert effects == []
    # The terminal event is published because the durable terminal write
    # was acknowledged, with exact identity.
    assert durable.attempted_writes == [
        (
            task.request_id,
            task.task_id,
            task.thread_id,
            chat_worker._extract_turn_id(task),
            "task.cancelled",
        )
    ]
    assert durable.acknowledged_writes == durable.attempted_writes
    assert durable.rejected_writes == []
    payload = next(
        item for event_type, item in published if event_type == "task.cancelled"
    )
    assert payload["terminal_evidence"]["visible_output_emitted"] is True
    assert durable.recorded_terminals == [TaskEventType.TASK_CANCELLED.value]
    assert "terminal_cleanup_capability_unavailable" in caplog.text


def test_unacknowledged_durable_terminal_publishes_no_outcome(monkeypatch):
    published, effects, task, durable = _seed_worker_terminal_harness(
        monkeypatch, acknowledged_terminal=False
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
    assert "task.failed" not in event_types
    assert "task.cancelled" not in event_types
    assert "task.completed" not in event_types
    assert effects == []
    # The durable store acknowledged no terminal outcome, so the worker
    # published none and manufactured none.
    assert durable.recorded_terminals == []
    assert all(
        authority.terminal_event_type is None
        for authority in durable.observed_authorities
    )


def test_unconfirmed_durable_attempt_never_executes(monkeypatch):
    published, effects, task, durable = _seed_worker_terminal_harness(
        monkeypatch, confirmed_attempt=False
    )
    executions: list[str] = []

    def _never_execute(*_args, **_kwargs):
        executions.append("executed")
        raise AssertionError("provider execution must not be authorized")

    monkeypatch.setattr(chat_worker, "run_chat_completion_task", _never_execute)

    chat_worker._run_chat_task(task)

    assert executions == []
    assert published == []
    assert effects == []
    # Without a confirmed attempt there is no durable receipt, so no terminal
    # outcome could be recorded, observed, or cleaned up.
    assert durable.read_attempts == [task.task_id]
    assert durable.recorded_terminals == []
    assert durable.observed_authorities == []
    # No request or turn identity was synthesized into execution authority.
    assert task.request_id == "request-terminal-evidence"
    assert task.turn_id == _TERMINAL_TURN_ID


def test_durable_attempt_double_enforces_exact_identity_and_strict_cleanup():
    """The durable double admits only the exact attempt identity.

    A read for a different backend task cannot return a valid row for the
    requested task, a write with mismatched identity is attempted but never
    acknowledged, an observation with mismatched identity returns no usable
    terminal authority, and the strict cleanup seam releases only the
    original persisted capability, for its own task.
    """
    task = _worker_task()
    durable = _SyntheticDurableAttempt(task=task)

    # A read for a different backend task cannot return a valid row for the
    # requested task.
    assert durable.read_attempt(None, "other-task") is None
    assert durable.read_attempts == ["other-task"]
    assert durable.read_attempt(None, task.task_id) is not None

    # A write with mismatched identity is attempted but never acknowledged.
    assert (
        durable.record_terminal(
            None,
            request_id=task.request_id,
            backend_task_id="other-task",
            thread_id=task.thread_id,
            turn_id=task.turn_id,
            event_type=TaskEventType.TASK_FAILED.value,
        )
        is False
    )
    assert durable.acknowledged_writes == []
    assert len(durable.attempted_writes) == 1
    assert durable.rejected_writes == durable.attempted_writes

    # An observation with mismatched identity returns no usable authority.
    with pytest.raises(ValueError):
        durable.observe_terminal(
            None,
            request_id=task.request_id,
            backend_task_id="other-task",
            thread_id=task.thread_id,
            turn_id=task.turn_id,
        )
    assert durable.observed_authorities == []

    # The strict cleanup seam releases only the original persisted capability,
    # and only for its own task. A replacement lock cannot be released by the
    # old task, and a mutable packet token is not the persisted capability.
    assert (
        durable.release_lock(
            task.thread_id,
            owner_task_id=task.task_id,
            lease_token=_DURABLE_ORIGINAL_LOCK_TOKEN,
        )
        is True
    )
    assert (
        durable.release_lock(
            task.thread_id,
            owner_task_id="mutable-replacement-owner",
            lease_token=_DURABLE_ORIGINAL_LOCK_TOKEN,
        )
        is False
    )
    assert (
        durable.release_lock(
            task.thread_id,
            owner_task_id=task.task_id,
            lease_token="mutable-replacement-token",
        )
        is False
    )


def test_rejected_failure_write_with_uncertain_read_infers_no_terminal_outcome(
    monkeypatch,
):
    """A rejected durable write plus an uncertain read must publish nothing.

    The worker's local exception is not authority. With neither the durable
    write acknowledged nor the durable read able to establish any terminal
    state, the worker infers no terminal event and manufactures no
    completion.
    """
    published, effects, task, durable = _seed_worker_terminal_harness(
        monkeypatch, acknowledged_terminal=False, observation_uncertain=True
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
    assert "task.failed" not in event_types
    assert "task.cancelled" not in event_types
    assert "task.completed" not in event_types
    assert effects == []
    # The durable write was attempted with exact identity, and it was
    # rejected, so nothing was published.
    assert durable.attempted_writes == [
        (
            task.request_id,
            task.task_id,
            task.thread_id,
            chat_worker._extract_turn_id(task),
            "task.failed",
        )
    ]
    assert durable.acknowledged_writes == []
    assert durable.rejected_writes == durable.attempted_writes
    # The uncertain read established no durable terminal state, so it
    # authorized no cleanup either.
    assert durable.observed_authorities == []
    assert durable.releases == []


def test_durable_completion_outranks_late_cancellation(monkeypatch):
    """A durable completion outranks a cancellation that arrives late.

    The accepted attempt is already durably complete, so the worker must
    project that durable truth and must never reach the cancellation branch.
    A cancellation seen afterwards may not rewrite a completion that already
    happened, and it may not cause provider work to run again.
    """
    published, effects, task, durable = _seed_worker_terminal_harness(
        monkeypatch,
        durable_completion_message_id=42,
        cancelled=True,
        expose_lock_capability=True,
    )
    # A mutable packet field names a replacement lock. It grants no cleanup
    # authority.
    task.turn_lock_owner = "mutable-replacement-owner"
    task.turn_lock = {"lease_token": "mutable-replacement-token"}
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
    assert durable.attempted_writes == []
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
    assert durable.releases == [
        (task.thread_id, task.task_id, _DURABLE_ORIGINAL_LOCK_TOKEN)
    ]


def test_rejected_cancellation_write_manufactures_no_terminal_authority(monkeypatch):
    """A rejected durable cancellation write cannot become terminal authority.

    The worker's own durable terminal write is the authority for a
    request-bearing accepted attempt. When the cancellation write is not
    acknowledged and the durable observation is still pending, the worker
    must fail closed: it must not publish a cancellation, a failure or a
    completion, and it must not persist an assistant message or schedule
    completion effects.

    This is the cancellation counterpart of the rejected-failure case: that
    case makes the durable read uncertain, while this one leaves the read
    merely pending.
    """
    published, effects, task, durable = _seed_worker_terminal_harness(
        monkeypatch, acknowledged_terminal=False
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
    assert durable.attempted_writes == [
        (
            task.request_id,
            task.task_id,
            task.thread_id,
            chat_worker._extract_turn_id(task),
            "task.cancelled",
        )
    ]
    assert durable.acknowledged_writes == []
    assert durable.rejected_writes == durable.attempted_writes
    # The pending read established no durable terminal state, so no persisted
    # capability authorized cleanup.
    assert all(
        authority.terminal_event_type is None
        for authority in durable.observed_authorities
    )
    assert durable.releases == []


def test_durable_cleanup_needs_a_confirmed_observation(monkeypatch, caplog):
    """Cleanup is authorized by the observed durable state, not by a flag.

    Even when the fixture is willing to expose a capability, an uncertain
    durable read establishes no authority, so the production cleanup path
    cannot clean with it.
    """
    _published, _effects, task, durable = _seed_worker_terminal_harness(
        monkeypatch, expose_lock_capability=True, observation_uncertain=True
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

    with caplog.at_level(logging.WARNING, logger="guardian.workers.chat_worker"):
        chat_worker._run_chat_task(task)

    assert durable.releases == []
    assert "terminal_cleanup_authority_unconfirmed" in caplog.text
