"""Lightweight in-memory tracker for model readiness phases."""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Dict, Tuple

# Readiness phases (heuristics, no routing impact):
# - unknown: no signal yet or connectivity unclear
# - cold: server reachable but model did not return a token (timeout/loading)
# - warming: model returned a token but first-token latency is high
# - ready: model returns a token quickly and consistently

VALID_PHASES = {"unknown", "cold", "warming", "ready"}


@dataclass
class ModelHealth:
    provider: str
    model: str
    status: str = "unknown"
    last_success_ts: float | None = None
    last_error_ts: float | None = None
    last_latency_ms: float | None = None
    consecutive_failures: int = 0


class ModelHealthTracker:
    def __init__(self) -> None:
        self._lock = Lock()
        self._state: dict[tuple[str, str], ModelHealth] = {}

    def _key(self, provider: str, model: str) -> tuple[str, str]:
        return (provider.strip().lower(), model.strip())

    def get(self, provider: str, model: str) -> ModelHealth:
        key = self._key(provider, model)
        with self._lock:
            health = self._state.get(key)
            if health is None:
                health = ModelHealth(provider=key[0], model=key[1])
                self._state[key] = health
            return health

    def record_success(
        self,
        provider: str,
        model: str,
        *,
        latency_ms: float | None,
        phase: str,
    ) -> ModelHealth:
        status = phase if phase in VALID_PHASES else "unknown"
        with self._lock:
            key = self._key(provider, model)
            health = self._state.get(key)
            if health is None:
                health = ModelHealth(provider=key[0], model=key[1])
                self._state[key] = health
            health.status = status
            health.last_success_ts = time.time()
            health.last_latency_ms = latency_ms
            health.consecutive_failures = 0
            return health

    def record_failure(
        self,
        provider: str,
        model: str,
        *,
        latency_ms: float | None,
        phase: str,
    ) -> ModelHealth:
        status = phase if phase in VALID_PHASES else "unknown"
        with self._lock:
            key = self._key(provider, model)
            health = self._state.get(key)
            if health is None:
                health = ModelHealth(provider=key[0], model=key[1])
                self._state[key] = health
            health.status = status
            health.last_error_ts = time.time()
            health.last_latency_ms = latency_ms
            health.consecutive_failures += 1
            return health


tracker = ModelHealthTracker()


def get_health(provider: str, model: str) -> ModelHealth:
    return tracker.get(provider, model)


def record_success(
    provider: str,
    model: str,
    *,
    latency_ms: float | None,
    phase: str,
) -> ModelHealth:
    return tracker.record_success(
        provider,
        model,
        latency_ms=latency_ms,
        phase=phase,
    )


def record_failure(
    provider: str,
    model: str,
    *,
    latency_ms: float | None,
    phase: str,
) -> ModelHealth:
    return tracker.record_failure(
        provider,
        model,
        latency_ms=latency_ms,
        phase=phase,
    )
