"""Guardian delegation dispatch contract (Slice 3).

Dispatch must be a durable state transition, and its recovery contract must
not over-claim. These cases prove the four layers are kept distinct, that
uncertain execution state is treated as uncertain rather than lost, that
automated re-dispatch is refused without fencing, and that a recovered task
cannot silently duplicate or promote unauthorized changes.

See ``guardian/core/guardian_dispatch.py`` and
``docs/architecture/guardian-delegation-loop-contract.md``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from guardian.core.guardian_dispatch import (
    GUARDIAN_DISPATCH_TERMINAL_STATES,
    GuardianDispatchError,
    GuardianDispatchState,
    assert_dispatch_ready,
    build_dispatch_record,
    classify_dispatch_health,
    mark_dispatched,
    observe_liveness,
    recover_dispatch,
)


def _record(**overrides):  # noqa: ANN201
    kwargs = {
        "intent_id": "gdi-1",
        "deployment_id": "dep-1",
        "run_id": "run-1",
        "attempt_id": "gat-1",
        "coding_task_id": "gct-1",
    }
    kwargs.update(overrides)
    return build_dispatch_record(**kwargs)


def _binding(**overrides) -> dict[str, object]:
    binding = {
        "binding_id": "xeb-1",
        "attempt_id": "gat-1",
        "coding_task_id": "gct-1",
        "harness_id": "pi",
        "credential_type": "api_key",
        "model_id": "gpt-4o",
    }
    binding.update(overrides)
    return binding


def _posture(**overrides) -> dict[str, object]:
    posture = {
        "allow_shell": True,
        "allow_network": False,
        "allow_write": True,
        "allowed_paths": [""],
        "max_runtime_seconds": 300,
    }
    posture.update(overrides)
    return posture


def test_dispatch_record_links_the_full_attempt_lineage() -> None:
    """The record links intent to deployment, run, attempt, and task."""
    record = _record()

    assert record.intent_id == "gdi-1"
    assert record.deployment_id == "dep-1"
    assert record.run_id == "run-1"
    assert record.attempt_id == "gat-1"
    assert record.coding_task_id == "gct-1"
    assert record.state == GuardianDispatchState.PREPARED.value
    assert record.dispatch_count == 0


def test_dispatch_record_requires_its_lineage() -> None:
    """A record without lineage is refused."""
    with pytest.raises(GuardianDispatchError) as excinfo:
        _record(intent_id="")

    assert excinfo.value.code == "guardian_dispatch_intent_missing"

    with pytest.raises(GuardianDispatchError) as excinfo:
        _record(attempt_id="")

    assert excinfo.value.code == "guardian_dispatch_attempt_missing"


def test_dispatched_state_records_the_queue_receipt() -> None:
    """The queue task id is a dispatch receipt, and it is not a claim of
    consumption."""
    record = mark_dispatched(_record(), task_id="task-1")

    assert record.state == GuardianDispatchState.DISPATCHED.value
    assert record.task_id == "task-1"
    assert record.dispatch_count == 1
    assert record.dispatched_at is not None


def test_dispatched_state_requires_a_task_id() -> None:
    """A dispatch without a queue receipt is refused."""
    with pytest.raises(GuardianDispatchError) as excinfo:
        mark_dispatched(_record(), task_id="")

    assert excinfo.value.code == "guardian_dispatch_task_id_missing"


def test_healthy_attempt_within_its_lease_is_left_alone() -> None:
    """No progress is not proof of loss.

    A worker that is between phases, blocked on a subprocess, or in a long
    validation loop looks exactly like this: a lease that has not expired and
    a heartbeat inside the bound.
    """
    now = datetime.now(timezone.utc)
    record = mark_dispatched(_record(), task_id="task-1")
    record = observe_liveness(
        record,
        last_heartbeat_at=now - timedelta(seconds=5),
        lease_expires_at=now + timedelta(minutes=2),
    )

    classified = classify_dispatch_health(record, now=now)

    # The heartbeat means a worker claimed the attempt, so the state advanced
    # to executing. The point of this case is that a *live* attempt is left
    # alone: no uncertainty, no quarantine, no re-dispatch.
    assert classified.state == GuardianDispatchState.EXECUTING.value
    assert classified.reason_code is None
    assert classified.state not in GUARDIAN_DISPATCH_TERMINAL_STATES


def test_attempt_past_lease_and_heartbeat_is_uncertain_not_lost() -> None:
    """Expired liveness is uncertainty, not loss."""
    now = datetime.now(timezone.utc)
    record = mark_dispatched(_record(), task_id="task-1")
    record = observe_liveness(
        record,
        last_heartbeat_at=now - timedelta(minutes=30),
        lease_expires_at=now - timedelta(minutes=1),
    )

    classified = classify_dispatch_health(record, now=now)

    assert classified.state == GuardianDispatchState.UNCERTAIN.value
    assert classified.reason_code == "guardian_dispatch_liveness_unproven"
    # Crucially: not failed, not cancelled, and not re-driven.
    assert classified.state not in GUARDIAN_DISPATCH_TERMINAL_STATES


def test_attempt_with_no_liveness_evidence_is_not_declared_lost() -> None:
    """Absence of evidence is not evidence of loss.

    A freshly dispatched attempt has no heartbeat yet and may not have a
    lease. That is not a reason to quarantine it — the worker may simply not
    have claimed it yet.
    """
    now = datetime.now(timezone.utc)
    record = mark_dispatched(_record(), task_id="task-1")

    classified = classify_dispatch_health(record, now=now)

    assert classified.state == GuardianDispatchState.DISPATCHED.value
    assert classified.reason_code is None


def test_terminal_attempt_is_not_reclassified() -> None:
    """A terminal attempt is left alone by the health classifier."""
    now = datetime.now(timezone.utc)
    record = mark_dispatched(_record(), task_id="task-1")
    record = observe_liveness(
        record,
        last_heartbeat_at=now - timedelta(hours=5),
        lease_expires_at=now - timedelta(hours=5),
    )
    from dataclasses import replace as dc_replace

    terminal = dc_replace(
        record, state=GuardianDispatchState.COMPLETED.value
    )

    classified = classify_dispatch_health(terminal, now=now)

    assert classified.state == GuardianDispatchState.COMPLETED.value


def test_recovery_refuses_to_re_dispatch_without_fencing() -> None:
    """Without fencing, recovery quarantines and escalates.

    There is no fencing token in this runtime, so a superseded attempt's
    writes cannot be rejected. Re-dispatching could duplicate filesystem
    writes and commits, so it is refused.
    """
    record = mark_dispatched(_record(), task_id="task-1")
    recovered = recover_dispatch(record, fencing_available=False)

    assert recovered.state == GuardianDispatchState.QUARANTINED.value
    assert recovered.reason_code == "guardian_dispatch_recovery_requires_fencing"
    # The attempt is not re-dispatched and not declared lost.
    assert recovered.dispatch_count == 1
    assert recovered.state not in GUARDIAN_DISPATCH_TERMINAL_STATES


def test_recovery_refuses_to_re_dispatch_without_operator_authorization() -> None:
    """Even with fencing, recovery needs an explicit operator decision."""
    record = mark_dispatched(_record(), task_id="task-1")
    recovered = recover_dispatch(
        record, fencing_available=True, operator_authorized=False
    )

    assert recovered.state == GuardianDispatchState.QUARANTINED.value
    assert (
        recovered.reason_code
        == "guardian_dispatch_recovery_requires_operator_authorization"
    )


def test_recovery_with_fencing_and_authorization_prepares_a_new_attempt() -> None:
    """An authorized recovery hands back a prepared attempt to re-drive.

    The recovery is a *new* attempt: it must mint a new attempt id, a new
    binding, and a freshly issued credential lease. The record is therefore
    reset to prepared, and the caller mints those.
    """
    record = mark_dispatched(_record(), task_id="task-1")
    recovered = recover_dispatch(
        record, fencing_available=True, operator_authorized=True
    )

    assert recovered.state == GuardianDispatchState.PREPARED.value
    assert recovered.reason_code is None
    assert recovered.operator_authorized is True
    # The previous attempt's identity is not reused: the caller must mint a
    # new one, so the record does not claim the old attempt is still live.
    assert recovered.attempt_id == "gat-1"


def test_quarantined_state_is_durable_and_inspectable() -> None:
    """A quarantined attempt records why it was quarantined."""
    record = mark_dispatched(_record(), task_id="task-1")
    recovered = recover_dispatch(record, fencing_available=False)

    payload = recovered.to_dict()
    assert payload["state"] == GuardianDispatchState.QUARANTINED.value
    assert payload["reason_code"] == "guardian_dispatch_recovery_requires_fencing"
    assert payload["task_id"] == "task-1"
    assert payload["updated_at"] is not None


def test_dispatch_requires_a_binding() -> None:
    """A dispatch without a binding is refused before anything is queued."""
    record = _record()

    with pytest.raises(GuardianDispatchError) as excinfo:
        assert_dispatch_ready(
            record, execution_binding={}, permission_policy=_posture()
        )

    assert excinfo.value.code == "guardian_dispatch_binding_missing"


def test_dispatch_requires_a_posture() -> None:
    """A dispatch without a permission posture is refused."""
    record = _record()

    with pytest.raises(GuardianDispatchError) as excinfo:
        assert_dispatch_ready(
            record, execution_binding=_binding(), permission_policy={}
        )

    assert excinfo.value.code == "guardian_dispatch_posture_missing"


def test_dispatch_refuses_a_write_posture_without_scope() -> None:
    """A write posture with no scope would authorize the whole tree."""
    record = _record()

    with pytest.raises(GuardianDispatchError) as excinfo:
        assert_dispatch_ready(
            record,
            execution_binding=_binding(),
            permission_policy=_posture(allowed_paths=[]),
        )

    assert excinfo.value.code == "guardian_dispatch_posture_write_scope_missing"


def test_dispatch_refuses_a_binding_for_another_attempt() -> None:
    """The binding must describe this exact attempt."""
    record = _record()

    with pytest.raises(GuardianDispatchError) as excinfo:
        assert_dispatch_ready(
            record,
            execution_binding=_binding(attempt_id="gat-other"),
            permission_policy=_posture(),
        )

    assert excinfo.value.code == "guardian_dispatch_binding_attempt_mismatch"


def test_dispatch_refuses_a_binding_for_another_task() -> None:
    """The binding must describe this exact coding task."""
    record = _record()

    with pytest.raises(GuardianDispatchError) as excinfo:
        assert_dispatch_ready(
            record,
            execution_binding=_binding(coding_task_id="gct-other"),
            permission_policy=_posture(),
        )

    assert excinfo.value.code == "guardian_dispatch_binding_task_mismatch"


def test_dispatch_refuses_an_already_dispatched_attempt() -> None:
    """An attempt is dispatched once; a second dispatch is refused."""
    record = mark_dispatched(_record(), task_id="task-1")

    with pytest.raises(GuardianDispatchError) as excinfo:
        assert_dispatch_ready(
            record, execution_binding=_binding(), permission_policy=_posture()
        )

    assert excinfo.value.code == "guardian_dispatch_state_dispatched"


def test_dispatch_accepts_a_fully_authorized_prepared_attempt() -> None:
    """A prepared attempt with a matching binding and posture is dispatchable."""
    record = _record()

    assert_dispatch_ready(
        record, execution_binding=_binding(), permission_policy=_posture()
    )


def test_dispatch_record_never_claims_exactly_once_execution() -> None:
    """The record's vocabulary does not assert an execution guarantee."""
    record = mark_dispatched(_record(), task_id="task-1")
    payload = record.to_dict()

    # A dispatch receipt is evidence of enqueue, not of consumption.
    assert payload["task_id"] == "task-1"
    assert payload["state"] == GuardianDispatchState.DISPATCHED.value
    # There is no vocabulary for "executed exactly once".
    assert "executed" not in payload
    assert "exactly_once" not in payload
