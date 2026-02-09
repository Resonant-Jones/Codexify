"""WebSocket RPC rate limiting helpers."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as redis_async
except Exception:  # pragma: no cover - optional dependency at runtime
    redis_async = None


@dataclass(frozen=True)
class RateLimitDecision:
    """Result for a single rate-limit check."""

    allowed: bool
    remaining_tokens: float
    retry_after_seconds: float | None
    backend: str


class TokenBucketRateLimiter:
    """Token bucket limiter with optional Redis-backed state."""

    def __init__(
        self,
        *,
        capacity: int,
        refill_per_second: float,
        namespace: str = "guardian:ws:rate_limit",
    ) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if refill_per_second <= 0:
            raise ValueError("refill_per_second must be > 0")
        self._capacity = float(capacity)
        self._refill_per_second = float(refill_per_second)
        self._namespace = namespace.strip() or "guardian:ws:rate_limit"
        self._memory_state: dict[str, tuple[float, float]] = {}
        self._memory_lock = asyncio.Lock()
        self._redis_client: Any | None = None
        self._redis_disabled = False

    async def allow(
        self,
        key: str,
        *,
        cost: float = 1.0,
    ) -> RateLimitDecision:
        """Consume bucket tokens and return whether the request is allowed."""

        if cost <= 0:
            raise ValueError("cost must be > 0")
        normalized_key = key.strip()
        if not normalized_key:
            raise ValueError("key must be non-empty")

        redis_decision = await self._allow_redis(normalized_key, cost)
        if redis_decision is not None:
            return redis_decision
        return await self._allow_memory(normalized_key, cost)

    async def _allow_memory(self, key: str, cost: float) -> RateLimitDecision:
        now = time.time()
        async with self._memory_lock:
            tokens, last_refill = self._memory_state.get(key, (self._capacity, now))
            elapsed = max(0.0, now - last_refill)
            tokens = min(self._capacity, tokens + (elapsed * self._refill_per_second))
            if tokens >= cost:
                tokens -= cost
                decision = RateLimitDecision(
                    allowed=True,
                    remaining_tokens=tokens,
                    retry_after_seconds=None,
                    backend="memory",
                )
            else:
                retry_after = (cost - tokens) / self._refill_per_second
                decision = RateLimitDecision(
                    allowed=False,
                    remaining_tokens=tokens,
                    retry_after_seconds=max(retry_after, 0.0),
                    backend="memory",
                )
            self._memory_state[key] = (tokens, now)
            return decision

    async def _allow_redis(
        self,
        key: str,
        cost: float,
    ) -> RateLimitDecision | None:
        client = await self._redis_client_or_none()
        if client is None:
            return None

        redis_key = f"{self._namespace}:{key}"
        now = time.time()
        try:
            raw_state = await client.get(redis_key)
            tokens = self._capacity
            last_refill = now
            if raw_state:
                parsed = json.loads(raw_state)
                if isinstance(parsed, dict):
                    tokens = float(parsed.get("tokens", self._capacity))
                    last_refill = float(parsed.get("last_refill", now))
            elapsed = max(0.0, now - last_refill)
            tokens = min(self._capacity, tokens + (elapsed * self._refill_per_second))
            if tokens >= cost:
                tokens -= cost
                decision = RateLimitDecision(
                    allowed=True,
                    remaining_tokens=tokens,
                    retry_after_seconds=None,
                    backend="redis",
                )
            else:
                retry_after = (cost - tokens) / self._refill_per_second
                decision = RateLimitDecision(
                    allowed=False,
                    remaining_tokens=tokens,
                    retry_after_seconds=max(retry_after, 0.0),
                    backend="redis",
                )

            ttl_seconds = max(1, int(self._capacity / self._refill_per_second))
            await client.set(
                redis_key,
                json.dumps({"tokens": tokens, "last_refill": now}),
                ex=ttl_seconds,
            )
            return decision
        except Exception as exc:  # pragma: no cover - fallback safety
            logger.warning("[ws.rate_limit] redis unavailable, using memory fallback: %s", exc)
            await self._disable_redis_client()
            return None

    async def _redis_client_or_none(self) -> Any | None:
        if self._redis_disabled:
            return None
        if self._redis_client is not None:
            return self._redis_client
        if redis_async is None:
            self._redis_disabled = True
            return None

        redis_url = (os.getenv("REDIS_URL") or "").strip()
        if not redis_url:
            self._redis_disabled = True
            return None

        try:
            client = redis_async.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
            )
            await client.ping()
            self._redis_client = client
            return client
        except Exception as exc:  # pragma: no cover - fallback safety
            logger.warning("[ws.rate_limit] redis connect failed, using memory fallback: %s", exc)
            self._redis_disabled = True
            return None

    async def _disable_redis_client(self) -> None:
        if self._redis_client is None:
            self._redis_disabled = True
            return
        try:
            await self._redis_client.close()
        except Exception:
            pass
        self._redis_client = None
        self._redis_disabled = True
