"""Redis-backed session token store."""

from __future__ import annotations

from dataclasses import dataclass

from guardian.queue.redis_queue import get_redis_client, run_with_redis_timeout

DEFAULT_SESSION_TTL_SECONDS = 24 * 60 * 60
SESSION_KEY_PREFIX = "session:"


@dataclass(slots=True)
class SessionStore:
    redis_client: object | None = None

    def _client(self):
        return self.redis_client or get_redis_client()

    def _key(self, token: str) -> str:
        return f"{SESSION_KEY_PREFIX}{token}"

    def store(self, token: str, user_id: str, ttl: int) -> None:
        token_value = str(token or "").strip()
        user_value = str(user_id or "").strip()
        if not token_value:
            raise ValueError("token is required")
        if not user_value:
            raise ValueError("user_id is required")
        ttl_value = int(ttl or DEFAULT_SESSION_TTL_SECONDS)
        if ttl_value <= 0:
            ttl_value = DEFAULT_SESSION_TTL_SECONDS
        client = self._client()
        run_with_redis_timeout(
            lambda: client.set(self._key(token_value), user_value, ex=ttl_value)
        )

    def verify(self, token: str) -> str | None:
        token_value = str(token or "").strip()
        if not token_value:
            return None
        client = self._client()
        raw_value = run_with_redis_timeout(
            lambda: client.get(self._key(token_value))
        )
        if raw_value is None:
            return None
        if isinstance(raw_value, bytes):
            decoded = raw_value.decode("utf-8", "ignore").strip()
        else:
            decoded = str(raw_value or "").strip()
        return decoded or None

    def revoke(self, token: str) -> None:
        token_value = str(token or "").strip()
        if not token_value:
            return
        client = self._client()
        run_with_redis_timeout(lambda: client.delete(self._key(token_value)))


_SESSION_STORE: SessionStore | None = None


def get_session_store() -> SessionStore:
    global _SESSION_STORE
    if _SESSION_STORE is None:
        _SESSION_STORE = SessionStore()
    return _SESSION_STORE
