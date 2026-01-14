"""
Test bootstrap: seed env and harmonize imports.
"""

import os
import sys
from pathlib import Path
from types import ModuleType

# Ensure legacy `memoryos.*` imports resolve to in-repo `guardian.memoryos.*`
try:
    import guardian.memoryos as _gm

    sys.modules.setdefault("memoryos", _gm)
except Exception:
    pass

# Ensure the repository root takes precedence over any installed packages
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

"""
pytest bootstrap (quiet by default)
- Seeds dummy env so import-time Settings() validation can't crash collection.
- To debug loading order, run with: PYTEST_VERBOSE_BOOT=1 pytest -s
"""


# ---- Redis test fallback (in-memory, no external dependency) ----
class _InMemoryRedis:
    def __init__(self) -> None:
        self._lists: dict[str, list[str]] = {}
        self._sets: dict[str, set[str]] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._strings: dict[str, str] = {}
        self._streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self._stream_seq: dict[str, int] = {}

    def ping(self) -> bool:
        return True

    def publish(self, *_args, **_kwargs) -> int:
        return 1

    def lpush(self, name: str, value: str) -> int:
        self._lists.setdefault(name, []).insert(0, value)
        return len(self._lists[name])

    def rpop(self, name: str) -> str | None:
        queue = self._lists.get(name)
        if not queue:
            return None
        return queue.pop()

    def brpop(self, name: str, timeout: int = 0):
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

    def get(self, name: str) -> str | None:
        return self._strings.get(name)

    def setex(self, name: str, _ttl: int, value: str) -> bool:
        self._strings[name] = value
        return True

    def hget(self, name: str, key: str) -> str | None:
        return self._hashes.get(name, {}).get(key)

    def hset(self, name: str, key: str, value: str) -> int:
        self._hashes.setdefault(name, {})[key] = value
        return 1

    def xadd(self, name: str, fields: dict[str, str]) -> str:
        seq = self._stream_seq.get(name, 0) + 1
        self._stream_seq[name] = seq
        event_id = f"{seq}-0"
        self._streams.setdefault(name, []).append((event_id, dict(fields)))
        return event_id

    def xread(
        self,
        streams: dict[str, str],
        count: int = 100,
        block: int | None = None,
    ):
        _ = block
        results = []
        for name, last_id in streams.items():
            events = self._streams.get(name, [])
            start_index = 0
            if last_id not in (None, "", "0", "0-0", "$"):
                for idx, (event_id, _fields) in enumerate(events):
                    if event_id == last_id:
                        start_index = idx + 1
                        break
            sliced = events[start_index : start_index + count]
            if sliced:
                results.append((name, sliced))
        return results


_FAKE_REDIS = _InMemoryRedis()


def _install_fake_redis() -> None:
    try:
        import redis as _redis  # type: ignore
    except Exception:
        fake_module = ModuleType("redis")
        fake_exceptions = ModuleType("redis.exceptions")

        class _RedisConnectionError(Exception):
            pass

        class _RedisTimeoutError(Exception):
            pass

        fake_exceptions.ConnectionError = _RedisConnectionError
        fake_exceptions.TimeoutError = _RedisTimeoutError

        class _Redis:
            @classmethod
            def from_url(cls, *_args, **_kwargs):
                return _FAKE_REDIS

        fake_module.Redis = _Redis
        fake_module.from_url = lambda *_args, **_kwargs: _FAKE_REDIS
        fake_module.exceptions = fake_exceptions

        sys.modules.setdefault("redis", fake_module)
        sys.modules.setdefault("redis.exceptions", fake_exceptions)
        return

    _redis.Redis.from_url = classmethod(
        lambda cls, *_args, **_kwargs: _FAKE_REDIS
    )
    if hasattr(_redis, "from_url"):
        _redis.from_url = lambda *_args, **_kwargs: _FAKE_REDIS


_install_fake_redis()

# ---- Quiet banner (opt-in) ----
if os.getenv("PYTEST_VERBOSE_BOOT") == "1":
    print(">>> conftest.py:", __file__)
    print(">>> sys.path[0]:", sys.path[0])

# ---- Env seeding for tests/CI ----
os.environ.setdefault("GUARDIAN_ALLOW_DUMMY_SETTINGS", "1")
os.environ.setdefault("GENAI_API_KEY", "dummy")
os.environ.setdefault("NOTION_API_KEY", "dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")
os.environ.setdefault("OPENAI_API_KEY", "dummy")
os.environ.setdefault("GEMINI_API_KEY", "dummy")
os.environ.setdefault("GOOGLE_API_KEY", "dummy")

# Force mock embeddings backend in tests to avoid loading local model files
os.environ.setdefault("CODEXIFY_EMBEDDINGS_BACKEND", "mock")

# ---- Simple secret masker for test logs ----
import logging


class _MaskSecrets(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage())
        # Replace long token-like strings; keep messages readable
        record.msg = msg.replace(
            os.environ.get("OPENAI_API_KEY", "dummy"), "***"
        )
        for k in (
            "GENAI_API_KEY",
            "NOTION_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
        ):
            v = os.environ.get(k)
            if v and len(v) > 6:
                record.msg = record.msg.replace(v, "***")
        return True


logging.getLogger().addFilter(_MaskSecrets())
