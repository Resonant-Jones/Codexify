import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from guardian.queue import turn_lock


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool | None:
        _ = ex
        if nx and key in self.values:
            return None
        self.values[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def delete(self, key: str) -> int:
        if key not in self.values:
            return 0
        del self.values[key]
        return 1

    def eval(self, script, numkeys, key, owner, token, renewed_at, expires_at, ttl):
        # Deterministic Redis script contract double: replacement can be injected
        # immediately before the atomic comparison, without any external Redis.
        assert numkeys == 1
        assert "payload.owner_task_id ~= ARGV[1]" in script
        assert "payload.lease_token ~= ARGV[2]" in script
        assert script.index("payload.lease_token") < script.index("redis.call('SET'")
        raw = self.get(key)
        if raw is None:
            return None
        payload = json.loads(raw)
        if payload['owner_task_id'] != owner or payload['lease_token'] != token:
            return None
        payload.update(renewed_at=renewed_at, lease_expires_at=expires_at, lease_ttl_seconds=ttl)
        value = json.dumps(payload)
        self.set(key, value, ex=ttl)
        return value


def test_turn_lock_acquire_stores_structured_envelope(monkeypatch):
    client = _FakeRedis()
    monkeypatch.setattr(turn_lock, "_with_reconnect", lambda fn: fn(client))

    acquired = turn_lock.acquire_turn_lock(
        11,
        "task-11",
        turn_id="11111111-1111-4111-8111-111111111111",
        source="test",
        return_envelope=True,
    )

    assert isinstance(acquired, turn_lock.TurnLockEnvelope)
    assert acquired.thread_id == 11
    assert acquired.owner_task_id == "task-11"
    assert acquired.turn_id == "11111111-1111-4111-8111-111111111111"
    assert acquired.source == "test"
    assert turn_lock.get_turn_lock_owner(11) == "task-11"


def test_turn_lock_renew_preserves_lease_token(monkeypatch):
    client = _FakeRedis()
    monkeypatch.setattr(turn_lock, "_with_reconnect", lambda fn: fn(client))

    acquired = turn_lock.acquire_turn_lock(
        17,
        "task-17",
        turn_id="22222222-2222-4222-8222-222222222222",
        source="test",
        return_envelope=True,
    )
    renewed = turn_lock.renew_turn_lock(
        17,
        acquired,
        return_envelope=True,
    )

    assert isinstance(renewed, turn_lock.TurnLockEnvelope)
    assert renewed.owner_task_id == "task-17"
    assert renewed.turn_id == "22222222-2222-4222-8222-222222222222"
    assert renewed.lease_token == acquired.lease_token
    assert renewed.acquired_at == acquired.acquired_at


def test_turn_lock_release_by_envelope(monkeypatch):
    client = _FakeRedis()
    monkeypatch.setattr(turn_lock, "_with_reconnect", lambda fn: fn(client))

    acquired = turn_lock.acquire_turn_lock(
        23,
        "task-23",
        turn_id="33333333-3333-4333-8333-333333333333",
        return_envelope=True,
    )

    assert turn_lock.release_turn_lock(23, acquired) is True
    assert turn_lock.get_turn_lock(23) is None


@pytest.mark.parametrize('replacement_kind', ['owner', 'token', 'absent'])
def test_stale_renewal_preserves_replacement_bytes(monkeypatch, replacement_kind):
    client = _FakeRedis()
    monkeypatch.setattr(turn_lock, '_with_reconnect', lambda fn: fn(client))
    old = turn_lock.acquire_turn_lock(1, 'old', return_envelope=True)
    replacement = replace(old, owner_task_id='new') if replacement_kind == 'owner' else replace(old, lease_token='new-token')
    key = turn_lock.turn_lock_key(1)
    if replacement_kind == 'absent':
        client.delete(key)
    else:
        client.set(key, json.dumps(replacement.as_dict()))
    before = client.get(key)
    assert turn_lock.renew_turn_lock(1, old, ttl_seconds=840) is False
    assert client.get(key) == before


def test_renewal_preserves_identity_and_reanchors_lease(monkeypatch):
    client = _FakeRedis()
    now = datetime(2026, 9, 12, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(turn_lock, '_with_reconnect', lambda fn: fn(client))
    monkeypatch.setattr(turn_lock, '_utc_now', lambda: now)
    old = turn_lock.acquire_turn_lock(1, 'owner', source='test', return_envelope=True)
    later = now + timedelta(seconds=90)
    monkeypatch.setattr(turn_lock, '_utc_now', lambda: later)
    renewed = turn_lock.renew_turn_lock(1, old, ttl_seconds=840, return_envelope=True)
    for field in ['thread_id', 'owner_task_id', 'turn_id', 'acquired_at', 'lease_token', 'source']:
        assert getattr(renewed, field) == getattr(old, field)
    assert renewed.renewed_at == later.isoformat()
    assert renewed.lease_expires_at == (later + timedelta(seconds=840)).isoformat()
    assert renewed.lease_ttl_seconds == 840


def test_renewal_without_atomic_support_fails_closed(monkeypatch):
    class NoEval:
        def set(self, *args, **kwargs):
            pytest.fail('non-atomic renewal attempted')
    monkeypatch.setattr(turn_lock, '_with_reconnect', lambda fn: fn(NoEval()))
    old = turn_lock.build_turn_lock_envelope(1, 'owner')
    assert turn_lock.renew_turn_lock(1, old) is False
