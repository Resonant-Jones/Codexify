"""Redis-backed queue adapter for async tasks."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Callable, Optional

import redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

logger = logging.getLogger(__name__)

_DEFAULT_REDIS_URL = "redis://redis:6379/0"
_CANCEL_SET_KEY = "codexify:queue:cancelled"
_CLIENT: redis.Redis | None = None


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


def get_redis_client() -> redis.Redis:
    return _get_client()
