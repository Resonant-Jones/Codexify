"""Strict terminal cleanup must never degrade into separate GET and DELETE."""

import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from urllib.parse import unquote, urlparse
from unittest.mock import Mock

import pytest
from redis import Redis
from redis.exceptions import ResponseError

from guardian.queue import turn_lock


def test_terminal_cleanup_uses_one_script_and_requires_both_bindings(monkeypatch):
    client = Mock()
    client.eval.return_value = 1
    monkeypatch.setattr(turn_lock, "_with_reconnect", lambda fn: fn(client))
    assert turn_lock.release_terminal_attempt_turn_lock(1, owner_task_id="task", lease_token="token")
    script, numkeys, key, owner, token, thread = client.eval.call_args.args
    assert (numkeys, key, owner, token, thread) == (1, "turn_lock:1", "task", "token", 1)
    assert script.index("payload.lease_token") < script.index("redis.call('DEL'")
    client.get.assert_not_called()
    client.delete.assert_not_called()
    for owner, token in (("", "token"), ("task", " "), (None, "token"), ("task", None)):
        with pytest.raises(ValueError):
            turn_lock.release_terminal_attempt_turn_lock(1, owner_task_id=owner, lease_token=token)
    assert client.eval.call_count == 1


def test_terminal_cleanup_script_failure_does_not_fall_back(monkeypatch):
    client = Mock()
    error = ResponseError("injected EVAL failure")
    client.eval.side_effect = error
    monkeypatch.setattr(turn_lock, "_with_reconnect", lambda fn: fn(client))
    with pytest.raises(ResponseError, match="injected EVAL failure"):
        turn_lock.release_terminal_attempt_turn_lock(1, owner_task_id="task", lease_token="token")
    client.get.assert_not_called()
    client.delete.assert_not_called()


def test_terminal_cleanup_without_eval_support_fails_closed(monkeypatch):
    class NoEval:
        def get(self, *_args):
            pytest.fail("non-atomic read attempted")

        def delete(self, *_args):
            pytest.fail("non-atomic deletion attempted")

    monkeypatch.setattr(turn_lock, "_with_reconnect", lambda fn: fn(NoEval()))
    with pytest.raises(AttributeError):
        turn_lock.release_terminal_attempt_turn_lock(1, owner_task_id="task", lease_token="token")


@pytest.fixture
def native_lock(monkeypatch):
    url = os.getenv("TEST_TERMINAL_LOCK_REDIS_URL")
    if not url:
        pytest.skip("TEST_TERMINAL_LOCK_REDIS_URL required for native cleanup proof")
    parsed = urlparse(url)
    assert parsed.scheme == "redis" and parsed.path == "/15"
    client = Redis(host=parsed.hostname, port=parsed.port or 6379, db=15,
                   username=unquote(parsed.username) if parsed.username else None,
                   password=unquote(parsed.password) if parsed.password else None,
                   decode_responses=True, socket_timeout=2, socket_connect_timeout=2)
    identity = uuid.uuid4().hex
    thread = int(identity[:7], 16)
    lock = turn_lock.build_turn_lock_envelope(thread, f"terminal-proof-{identity}")
    key = turn_lock.turn_lock_key(thread)
    value = json.dumps(lock.as_dict())
    assert client.set(key, value, nx=True, ex=60), "generated key already occupied"
    monkeypatch.setattr(turn_lock, "_with_reconnect", lambda fn: fn(client))
    try:
        yield client, key, lock
    finally:
        # Own only this generated DB-15 key, and do not erase an unrelated owner.
        current = client.get(key)
        if current is not None:
            allowed = {value, "not-json", "[]", "null", "42", lock.owner_task_id, json.dumps(lock.owner_task_id)}
            try:
                payload = json.loads(current)
            except ValueError:
                payload = None
            owned = (
                isinstance(payload, dict)
                and (payload.get("owner_task_id") or "").startswith("terminal-proof-")
                and identity in payload.get("owner_task_id", "")
            )
            assert current in allowed or owned, "unrelated replacement retained"
            client.delete(key)
        assert client.exists(key) == 0
        client.close()


@pytest.mark.integration
def test_native_terminal_cleanup_exact_and_idempotent(native_lock):
    client, key, lock = native_lock
    assert turn_lock.release_terminal_attempt_turn_lock(
        lock.thread_id, owner_task_id=lock.owner_task_id, lease_token=lock.lease_token
    )
    assert client.get(key) is None
    assert turn_lock.release_terminal_attempt_turn_lock(
        lock.thread_id, owner_task_id=lock.owner_task_id, lease_token=lock.lease_token
    )


@pytest.mark.integration
@pytest.mark.parametrize("replacement", ["owner", "token", "thread", "legacy", "string", "malformed", "array", "null", "number", "incomplete"])
def test_native_terminal_cleanup_preserves_replacement_bytes(native_lock, replacement):
    client, key, lock = native_lock
    values = {
        "owner": json.dumps(replace(lock, owner_task_id=lock.owner_task_id+"-replacement").as_dict()),
        "token": json.dumps(replace(lock, lease_token="replacement-token").as_dict()),
        "thread": json.dumps(replace(lock, thread_id=lock.thread_id+1).as_dict()),
        "legacy": lock.owner_task_id, "string": json.dumps(lock.owner_task_id), "malformed": "not-json",
        "incomplete": json.dumps({"owner_task_id": lock.owner_task_id, "lease_token": lock.lease_token}),
        "array": "[]", "null": "null", "number": "42",
    }
    client.set(key, values[replacement], ex=60)
    before, ttl = client.get(key), client.pttl(key)
    assert not turn_lock.release_terminal_attempt_turn_lock(
        lock.thread_id, owner_task_id=lock.owner_task_id, lease_token=lock.lease_token
    )
    assert client.get(key) == before
    assert 0 < client.pttl(key) <= ttl


@pytest.mark.integration
def test_native_terminal_cleanup_cannot_delete_concurrent_replacement(native_lock):
    client, key, lock = native_lock
    replacement = json.dumps(replace(lock, lease_token="replacement-token").as_dict())
    # SET and EVAL serialize in either order. Final replacement must survive both.
    with ThreadPoolExecutor(max_workers=2) as pool:
        cleanup = pool.submit(turn_lock.release_terminal_attempt_turn_lock,
                              lock.thread_id, owner_task_id=lock.owner_task_id, lease_token=lock.lease_token)
        replace_lock = pool.submit(client.set, key, replacement, ex=60)
        cleanup.result(timeout=5)
        assert replace_lock.result(timeout=5)
    assert client.get(key) == replacement
