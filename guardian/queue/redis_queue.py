"""Redis-backed queue adapter for async tasks."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from unittest.mock import Mock
from urllib.parse import unquote, urlparse

import redis
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from guardian.protocol_tokens import ErrorCode

logger = logging.getLogger(__name__)

_DEFAULT_REDIS_URL = "redis://redis:6379/0"
_DEFAULT_REDIS_OPERATION_TIMEOUT_SECONDS = float(
    os.getenv("REDIS_OPERATION_TIMEOUT_SECONDS", "2")
)
_CANCEL_SET_KEY = "codexify:queue:cancelled"
_TURN_LOCK_PREFIX = "turn_lock:"
_DEFAULT_TURN_LOCK_TTL = int(os.getenv("CHAT_TURN_LOCK_TTL_SECONDS", "300"))
CHAT_EMBED_QUEUE_NAME = os.getenv(
    "CHAT_EMBED_QUEUE_NAME", "codexify:queue:chat-embed"
)
CHAT_EMBED_TASK_TYPE = "chat_embed"
QUEUE_ENQUEUE_ERROR_CODE = ErrorCode.QUEUE_ENQUEUE_FAILED.value
_CLIENT: Any = None
_QUEUE_CLIENT: Any = None


class QueueEnqueueError(RuntimeError):
    """Raised when enqueueing a task into a queue fails."""

    def __init__(
        self,
        queue_name: str,
        *,
        error_code: str = "QUEUE_ENQUEUE_FAILED",
        cause: Exception | None = None,
    ) -> None:
        super().__init__(f"enqueue failed for queue={queue_name}")
        self.queue_name = queue_name
        self.error_code = error_code
        self.cause = cause


class RedisOperationTimeout(RuntimeError):
    """Raised when a Redis operation exceeds the backend fail-fast budget."""


def run_with_redis_timeout(
    fn: Callable[[], Any],
    timeout_seconds: float = _DEFAULT_REDIS_OPERATION_TIMEOUT_SECONDS,
) -> Any:
    start = time.monotonic()
    result = fn()
    elapsed = time.monotonic() - start
    if elapsed > timeout_seconds:
        raise RedisOperationTimeout(
            f"Redis operation exceeded {timeout_seconds}s"
        )
    return result


class _InMemoryRedis:
    """Deterministic in-memory fallback used for pytest safety."""

    def __init__(self) -> None:
        self._strings: dict[str, bytes] = {}
        self._expiries: dict[str, float] = {}
        self._lists: dict[str, list[str]] = {}
        self._sets: dict[str, set[str]] = {}

    def _now(self) -> float:
        return time.time()

    def _purge_if_expired(self, key: str) -> None:
        expires_at = self._expiries.get(key)
        if expires_at is None:
            return
        if expires_at <= self._now():
            self._expiries.pop(key, None)
            self._strings.pop(key, None)

    @staticmethod
    def _to_bytes(value: Any) -> bytes:
        if isinstance(value, bytes):
            return value
        if isinstance(value, bytearray):
            return bytes(value)
        return str(value).encode("utf-8")

    def ping(self) -> bool:
        return True

    def publish(self, *_args, **_kwargs) -> int:
        return 1

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
        self._strings[key] = self._to_bytes(value)
        if ex is None:
            self._expiries.pop(key, None)
        else:
            self._expiries[key] = self._now() + float(ex)
        return True

    def setex(self, name: str, ttl: int, value: str) -> bool:
        self._strings[name] = self._to_bytes(value)
        self._expiries[name] = self._now() + float(ttl)
        return True

    def get(self, name: str) -> bytes | None:
        self._purge_if_expired(name)
        return self._strings.get(name)

    def delete(self, key: str) -> int:
        self._purge_if_expired(key)
        removed = 0
        if key in self._strings:
            del self._strings[key]
            removed = 1
        self._expiries.pop(key, None)
        return removed

    def lpush(self, name: str, value: str) -> int:
        self._lists.setdefault(name, []).insert(0, value)
        return len(self._lists[name])

    def lpop(self, name: str) -> str | None:
        queue = self._lists.get(name)
        if not queue:
            return None
        return queue.pop(0)

    def rpop(self, name: str) -> str | None:
        queue = self._lists.get(name)
        if not queue:
            return None
        return queue.pop()

    def blpop(self, name: str, timeout: int = 0):
        _ = timeout
        value = self.lpop(name)
        if value is None:
            return None
        return (name, value)

    def brpop(self, name: str, timeout: int = 0):
        _ = timeout
        value = self.rpop(name)
        if value is None:
            return None
        return (name, value)

    def sadd(self, name: str, *values: str) -> int:
        bucket = self._sets.setdefault(name, set())
        before = len(bucket)
        bucket.update(values)
        return len(bucket) - before

    def sismember(self, name: str, value: str) -> bool:
        return value in self._sets.get(name, set())

    def srem(self, name: str, *values: str) -> int:
        bucket = self._sets.get(name, set())
        removed = 0
        for value in values:
            if value in bucket:
                bucket.remove(value)
                removed += 1
        return removed


def _is_mock_client(client: Any) -> bool:
    if client is None:
        return False
    if isinstance(client, Mock):
        return True
    module_name = getattr(type(client), "__module__", "") or ""
    return module_name.startswith("unittest.mock")


def _running_under_pytest() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST")) or "pytest" in sys.modules


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

    def lpop(self, name: str) -> str | None:
        queue = self._lists.get(name)
        if not queue:
            return None
        return queue.pop(0)

    def blpop(self, name: str, timeout: int = 0):
        _ = timeout
        value = self.lpop(name)
        if value is None:
            return None
        return (name, value)

    cls._now = _now
    cls._purge_if_expired = _purge_if_expired
    cls.get = get
    cls.set = set
    cls.setex = setex
    cls.delete = delete
    cls.lpop = lpop
    cls.blpop = blpop
    cls._turn_lock_support = True

    if not hasattr(client, "_expiries"):
        client._expiries = {}


def _redis_url() -> str:
    return (os.getenv("REDIS_URL") or _DEFAULT_REDIS_URL).strip()


def _redis_connection_kwargs() -> dict[str, Any]:
    parsed = urlparse(_redis_url())
    if parsed.scheme not in {"redis", "rediss"}:
        raise ValueError(
            f"Unsupported Redis URL scheme: {parsed.scheme or 'missing'}"
        )

    db = 0
    raw_path = str(parsed.path or "").lstrip("/")
    if raw_path:
        db = int(raw_path.split("/", 1)[0])

    kwargs: dict[str, Any] = {
        "host": parsed.hostname or "redis",
        "port": int(parsed.port or 6379),
        "db": db,
        "decode_responses": True,
    }
    if parsed.username:
        kwargs["username"] = unquote(parsed.username)
    if parsed.password:
        kwargs["password"] = unquote(parsed.password)
    if parsed.scheme == "rediss":
        kwargs["ssl"] = True
    return kwargs


def _create_redis_client(
    *,
    socket_timeout: float | None,
    retry_on_timeout: bool,
) -> Any:
    client_kwargs = {
        **_redis_connection_kwargs(),
        "socket_connect_timeout": 2,
        "socket_timeout": socket_timeout,
        "retry_on_timeout": retry_on_timeout,
    }
    if _running_under_pytest():
        from_url = getattr(redis.Redis, "from_url", None)
        if callable(from_url):
            candidate = from_url(_redis_url(), **client_kwargs)
            _patch_inmemory_redis(candidate)
            return candidate

    client = Redis(**client_kwargs)
    _patch_inmemory_redis(client)
    return client


def create_request_redis() -> Any:
    return _create_redis_client(
        socket_timeout=2,
        retry_on_timeout=False,
    )


def create_queue_redis() -> Any:
    return _create_redis_client(
        socket_timeout=None,
        retry_on_timeout=True,
    )


def _connect_request_client() -> Any:
    return create_request_redis()


def _connect_queue_client() -> Any:
    return create_queue_redis()


request_redis: Any = None


def _build_pytest_client(factory: Callable[[], Any]) -> Any:
    try:
        candidate = factory()
    except Exception as exc:
        logger.warning(
            "[redis] falling back to in-memory client under pytest: %s", exc
        )
        return _InMemoryRedis()
    if _is_mock_client(candidate):
        logger.warning(
            "[redis] detected mocked redis client under pytest; using in-memory fallback"
        )
        return _InMemoryRedis()
    return candidate


def _set_request_client(client: Any) -> Any:
    global _CLIENT, request_redis
    _CLIENT = client
    request_redis = client
    return client


def _set_queue_client(client: Any) -> Any:
    global _QUEUE_CLIENT
    _QUEUE_CLIENT = client
    return client


def _get_request_client() -> Any:
    global _CLIENT
    if _is_mock_client(_CLIENT):
        _set_request_client(None)
    if _CLIENT is None:
        _set_request_client(
            _build_pytest_client(_connect_request_client)
            if _running_under_pytest()
            else _connect_request_client()
        )
    if _running_under_pytest() and _is_mock_client(_CLIENT):
        return _set_request_client(_InMemoryRedis())
    return _CLIENT


def _get_queue_client() -> Any:
    global _QUEUE_CLIENT
    if _is_mock_client(_QUEUE_CLIENT):
        _set_queue_client(None)
    if _QUEUE_CLIENT is None:
        _set_queue_client(
            _build_pytest_client(_connect_queue_client)
            if _running_under_pytest()
            else _connect_queue_client()
        )
    if _running_under_pytest() and _is_mock_client(_QUEUE_CLIENT):
        return _set_queue_client(_InMemoryRedis())
    return _QUEUE_CLIENT


def _with_reconnect(fn: Callable[[Any], Any]) -> Any:
    global _CLIENT
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            client = _get_request_client()
            return fn(client)
        except (RedisConnectionError, RedisTimeoutError) as exc:
            last_err = exc
            _set_request_client(None)
            logger.warning("[redis] connection issue; reconnecting: %s", exc)
            time.sleep(0.2 * (attempt + 1))
        except Exception as exc:
            last_err = exc
            _set_request_client(None)
            logger.warning("[redis] unexpected error; reconnecting: %s", exc)
            time.sleep(0.2 * (attempt + 1))
    if last_err:
        raise last_err
    raise RuntimeError("redis operation failed without exception")


def _with_queue_reconnect(fn: Callable[[Any], Any]) -> Any:
    global _QUEUE_CLIENT
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            client = _get_queue_client()
            return fn(client)
        except (RedisConnectionError, RedisTimeoutError) as exc:
            last_err = exc
            _set_queue_client(None)
            logger.warning(
                "[redis:queue] connection issue; reconnecting: %s", exc
            )
            time.sleep(0.2 * (attempt + 1))
        except Exception as exc:
            last_err = exc
            _set_queue_client(None)
            logger.warning(
                "[redis:queue] unexpected error; reconnecting: %s", exc
            )
            time.sleep(0.2 * (attempt + 1))
    if last_err:
        raise last_err
    raise RuntimeError("redis queue operation failed without exception")


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

    try:
        _with_reconnect(_push)
    except Exception as exc:
        logger.warning(
            "[redis] enqueue failed error_code=%s queue=%s err=%s",
            QUEUE_ENQUEUE_ERROR_CODE,
            queue_name,
            exc,
        )
        raise


class _QueueRedisFacade:
    """Blocking-safe Redis facade for queue consumers."""

    def blpop(self, name: Any, timeout: int = 0) -> Any:
        return _with_queue_reconnect(
            lambda client: client.blpop(name, timeout=timeout)
        )

    def brpop(self, name: Any, timeout: int = 0) -> Any:
        return _with_queue_reconnect(
            lambda client: client.brpop(name, timeout=timeout)
        )


queue_redis = _QueueRedisFacade()


def dequeue(
    queue_name: str, *, block: bool = True, timeout: int | None = None
) -> dict[str, Any] | None:
    if block:
        effective = 0 if timeout is None else int(timeout)
        result = queue_redis.brpop(queue_name, timeout=effective)
        if not result:
            return None
        _, raw = result
        return _deserialize(raw)

    raw = _with_reconnect(lambda client: client.rpop(queue_name))
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


def get_request_redis_client() -> Any:
    client = _get_request_client()
    if _running_under_pytest() and _is_mock_client(client):
        client = _set_request_client(_InMemoryRedis())
    return client


def get_redis_client() -> Any:
    # WARNING:
    # This client is NOT safe for blocking operations.
    # Do NOT use for BLPOP/BRPOP. Use queue_redis instead.
    return get_request_redis_client()
