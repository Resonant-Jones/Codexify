from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from guardian.tasks.chat_deadline import (
    ACCEPTED_CHAT_TASK_TERMINAL_BUDGET_SECONDS,
    ACCEPTED_CHAT_TASK_TOTAL_BUDGET_SECONDS,
    ACCEPTED_CHAT_TASK_TURN_LOCK_LEASE_SECONDS,
    ACCEPTED_CHAT_TASK_WORK_BUDGET_SECONDS,
    DEADLINE_FIELDS,
    TURN_LOCK_SAFETY_MARGIN_SECONDS,
    build_accepted_chat_task_deadline,
    parse_accepted_chat_task_deadline,
)
from guardian.queue.redis_queue import _deserialize, _serialize
from guardian.tasks.types import ChatCompletionTask, task_from_dict

NOW = datetime(2026, 9, 12, 12, tzinfo=timezone.utc)


def test_frozen_deadline_arithmetic():
    deadline = build_accepted_chat_task_deadline(NOW)
    assert deadline.accepted_at == NOW
    assert deadline.work_deadline_at - NOW == timedelta(seconds=720)
    assert deadline.terminal_deadline_at - NOW == timedelta(seconds=780)
    assert deadline.terminal_deadline_at - deadline.work_deadline_at == timedelta(seconds=60)
    assert ACCEPTED_CHAT_TASK_WORK_BUDGET_SECONDS == 720
    assert ACCEPTED_CHAT_TASK_TERMINAL_BUDGET_SECONDS == 60
    assert ACCEPTED_CHAT_TASK_TOTAL_BUDGET_SECONDS == 780
    assert TURN_LOCK_SAFETY_MARGIN_SECONDS == 60
    assert ACCEPTED_CHAT_TASK_TURN_LOCK_LEASE_SECONDS == 840
    assert all(getattr(deadline, name).tzinfo is timezone.utc for name in DEADLINE_FIELDS)
    with pytest.raises(FrozenInstanceError):
        deadline.accepted_at = NOW + timedelta(seconds=1)


@pytest.mark.parametrize('offset', [0, 120])
def test_exact_queue_roundtrip_without_clock_refresh(offset):
    zone = timezone(timedelta(minutes=offset))
    snapshot = {name: getattr(build_accepted_chat_task_deadline(NOW), name).astimezone(zone).isoformat()
                for name in DEADLINE_FIELDS}
    task = ChatCompletionTask(user_id='owner', **snapshot)
    restored = task_from_dict(_deserialize(_serialize(task)))
    assert {name: getattr(restored, name) for name in DEADLINE_FIELDS} == snapshot
    assert restored.to_dict() == task.to_dict()
    assert parse_accepted_chat_task_deadline(snapshot).accepted_at == NOW


def test_legacy_task_has_no_authority_keys():
    task = ChatCompletionTask(user_id='owner')
    assert all(getattr(task, name) is None for name in DEADLINE_FIELDS)
    assert not set(DEADLINE_FIELDS) & task.to_dict().keys()
    assert task_from_dict(task.to_dict()).to_dict() == task.to_dict()
    assert parse_accepted_chat_task_deadline({}) is None


@pytest.mark.parametrize('fields', [DEADLINE_FIELDS[:1], DEADLINE_FIELDS[:2], DEADLINE_FIELDS[1:]])
def test_partial_snapshot_rejected(fields):
    snapshot = build_accepted_chat_task_deadline(NOW).to_dict()
    with pytest.raises(ValueError, match='incomplete'):
        task_from_dict({'type': 'chat_completion', 'user_id': 'owner',
                        **{name: snapshot[name] for name in fields}})


@pytest.mark.parametrize('field,value', [
    ('accepted_at', NOW.replace(tzinfo=None).isoformat()),
    ('work_deadline_at', (NOW - timedelta(seconds=1)).isoformat()),
    ('terminal_deadline_at', (NOW + timedelta(seconds=700)).isoformat()),
    ('work_deadline_at', (NOW + timedelta(seconds=721)).isoformat()),
    ('terminal_deadline_at', (NOW + timedelta(seconds=781)).isoformat()),
    ('accepted_at', 'invalid'), ('accepted_at', None), ('accepted_at', 123),
])
def test_invalid_snapshot_rejected(field, value):
    snapshot = build_accepted_chat_task_deadline(NOW).to_dict()
    snapshot[field] = value
    with pytest.raises(ValueError, match='snapshot is invalid'):
        task_from_dict({'type': 'chat_completion', 'user_id': 'owner', **snapshot})


def test_naive_clock_rejected():
    with pytest.raises(ValueError, match='aware'):
        build_accepted_chat_task_deadline(NOW.replace(tzinfo=None))
