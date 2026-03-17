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
