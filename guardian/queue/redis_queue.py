"""Redis-backed queue adapter for async tasks."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

logger = logging.getLogger(__name__)

_DEFAULT_REDIS_URL = "redis://redis:6379/0"
_CANCEL_SET_KEY = "codexify:queue:cancelled"
_TURN_LOCK_PREFIX = "turn_lock:"
_DEFAULT_TURN_LOCK_TTL = int(os.getenv("CHAT_TURN_LOCK_TTL_SECONDS", "300"))
CHAT_EMBED_QUEUE_NAME = os.getenv(
    "CHAT_EMBED_QUEUE_NAME", "codexify:queue:chat-embed"
)
CHAT_EMBED_TASK_TYPE = "chat_embed"
_CLIENT: redis.Redis | None = None


def _is_inmemory_redis(client: redis.Redis) -> bool:
    return (
        client.__class__.__name__ == "_InMemoryRedis"
        or client.__class__.__module__ == "conftest"
    )


def _patch_inmemory_redis(client: redis.Redis) -> None:
    if not _is_inmemory_redis(client):
        return
    cls = client.__class__
    if getattr(cls, "_turn_lock_support", False):
        return

    def _now(self) -> float:
        return time.time()

    def _purge_if_expired(self, key: str) -> None:
        expiries = getattr(self, "_expiries", None)
        if not isinstance(expiries, dict):
            self._expiries = {}
            return
        expires_at = self._expiries.get(key)
        if expires_at is None:
            return
        if expires_at <= self._now():
            self._expiries.pop(key, None)
            self._strings.pop(key, None)

    def get(self, name: str) -> str | None:
        self._purge_if_expired(name)
        return self._strings.get(name)

    def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool | None:
        self._purge_if_expired(key)
        if nx and key in self._strings:
            return None
        self._strings[key] = value
        if ex is None:
            self._expiries.pop(key, None)
        else:
            self._expiries[key] = self._now() + int(ex)
        return True

    def setex(self, name: str, ttl: int, value: str) -> bool:
        self._strings[name] = value
        self._expiries[name] = self._now() + int(ttl)
        return True

    def delete(self, key: str) -> int:
        self._purge_if_expired(key)
        removed = 0
        if key in self._strings:
            del self._strings[key]
            removed = 1
        self._expiries.pop(key, None)
        return removed

    cls._now = _now
    cls._purge_if_expired = _purge_if_expired
    cls.get = get
    cls.set = set
    cls.setex = setex
    cls.delete = delete
    cls._turn_lock_support = True

    if not hasattr(client, "_expiries"):
        client._expiries = {}


def _redis_url() -> str:
    return (os.getenv("REDIS_URL") or _DEFAULT_REDIS_URL).strip()


def _connect() -> redis.Redis:
    client = redis.Redis.from_url(
        _redis_url(),
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=None,
        retry_on_timeout=True,
    )
    _patch_inmemory_redis(client)
    return client


def _get_client() -> redis.Redis:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = _connect()
    return _CLIENT


def _with_reconnect(fn: Callable[[redis.Redis], Any]) -> Any:
    global _CLIENT
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            client = _get_client()
            return fn(client)
        except (RedisConnectionError, RedisTimeoutError) as exc:
            last_err = exc
            _CLIENT = None
            logger.warning("[redis] connection issue; reconnecting: %s", exc)
            time.sleep(0.2 * (attempt + 1))
        except Exception as exc:
            last_err = exc
            _CLIENT = None
            logger.warning("[redis] unexpected error; reconnecting: %s", exc)
            time.sleep(0.2 * (attempt + 1))
    if last_err:
        raise last_err
    raise RuntimeError("redis operation failed without exception")


def _serialize(task: Any) -> str:
    if hasattr(task, "to_dict"):
        payload = task.to_dict()  # type: ignore[attr-defined]
    elif isinstance(task, dict):
        payload = task
    else:
        payload = {"payload": task}
    return json.dumps(payload, default=str)


def _deserialize(raw: str | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
    if isinstance(value, dict):
        return value
    return {"payload": value}


def enqueue(task: Any, queue_name: str) -> None:
    data = _serialize(task)

    def _push(client: redis.Redis) -> int:
        return client.lpush(queue_name, data)

    _with_reconnect(_push)


def dequeue(
    queue_name: str, *, block: bool = True, timeout: int | None = None
) -> dict[str, Any] | None:
    def _pop(client: redis.Redis) -> str | None:
        if block:
            effective = 0 if timeout is None else int(timeout)
            result = client.brpop(queue_name, timeout=effective)
            if not result:
                return None
            _, payload = result
            return payload
        return client.rpop(queue_name)

    raw = _with_reconnect(_pop)
    return _deserialize(raw)


def enqueue_chat_embed(payload: dict[str, Any]) -> str:
    task_id = str(uuid.uuid4())
    record = {
        "task_id": task_id,
        "type": CHAT_EMBED_TASK_TYPE,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    enqueue(record, CHAT_EMBED_QUEUE_NAME)
    return task_id


def dequeue_chat_embed(
    *, block: bool = True, timeout: int | None = None
) -> dict[str, Any] | None:
    return dequeue(CHAT_EMBED_QUEUE_NAME, block=block, timeout=timeout)


def cancel(task_id: str) -> None:
    def _mark(client: redis.Redis) -> int:
        return client.sadd(_CANCEL_SET_KEY, task_id)

    _with_reconnect(_mark)


def is_cancelled(task_id: str) -> bool:
    def _check(client: redis.Redis) -> bool:
        return bool(client.sismember(_CANCEL_SET_KEY, task_id))

    return bool(_with_reconnect(_check))


def clear_cancelled(task_id: str) -> None:
    def _clear(client: redis.Redis) -> int:
        return client.srem(_CANCEL_SET_KEY, task_id)

    _with_reconnect(_clear)


def _turn_lock_key(thread_id: int) -> str:
    return f"{_TURN_LOCK_PREFIX}{thread_id}"


def acquire_turn_lock(
    thread_id: int,
    *,
    ttl_seconds: int | None = None,
    value: str | None = None,
) -> bool:
    ttl = int(ttl_seconds or _DEFAULT_TURN_LOCK_TTL)
    lock_value = value or str(int(time.time()))

    def _set(client: redis.Redis) -> bool:
        return bool(
            client.set(
                _turn_lock_key(thread_id),
                lock_value,
                nx=True,
                ex=ttl,
            )
        )

    return bool(_with_reconnect(_set))


def release_turn_lock(thread_id: int) -> None:
    def _clear(client: redis.Redis) -> int:
        return client.delete(_turn_lock_key(thread_id))

    _with_reconnect(_clear)


def get_redis_client() -> redis.Redis:
    return _get_client()
