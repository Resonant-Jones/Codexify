"""Redis-backed per-thread turn lock helpers."""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from guardian.queue.redis_queue import _with_reconnect

logger = logging.getLogger(__name__)

_DEFAULT_TTL_SECONDS = 180


@dataclass(frozen=True)
class TurnLockEnvelope:
    thread_id: int
    owner_task_id: str
    turn_id: str
    acquired_at: str
    renewed_at: str
    lease_expires_at: str
    lease_ttl_seconds: int
    lease_token: str
    source: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _lock_ttl_seconds() -> int:
    raw = os.getenv("CODEXIFY_TURN_LOCK_TTL_SECONDS", str(_DEFAULT_TTL_SECONDS))
    try:
        value = int(raw)
    except Exception:
        value = _DEFAULT_TTL_SECONDS
    return max(15, value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _coerce_lock_ttl_seconds(ttl_seconds: int | None) -> int:
    return max(1, int(ttl_seconds or _lock_ttl_seconds()))


def _coerce_text(raw: Any) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, bytes):
        return raw.decode("utf-8")
    return str(raw)


def _parse_iso8601(raw: str | None) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def build_turn_lock_envelope(
    thread_id: int,
    owner_task_id: str,
    *,
    turn_id: str | None = None,
    ttl_seconds: int | None = None,
    source: str | None = None,
    acquired_at: str | None = None,
    renewed_at: str | None = None,
    lease_token: str | None = None,
) -> TurnLockEnvelope:
    ttl = _coerce_lock_ttl_seconds(ttl_seconds)
    acquired_dt = _parse_iso8601(acquired_at) or _utc_now()
    renewed_dt = _parse_iso8601(renewed_at) or acquired_dt
    lease_expires_at = renewed_dt + timedelta(seconds=ttl)
    return TurnLockEnvelope(
        thread_id=int(thread_id),
        owner_task_id=str(owner_task_id),
        turn_id=str(turn_id or uuid.uuid4()),
        acquired_at=acquired_dt.isoformat(),
        renewed_at=renewed_dt.isoformat(),
        lease_expires_at=lease_expires_at.isoformat(),
        lease_ttl_seconds=ttl,
        lease_token=str(lease_token or uuid.uuid4()),
        source=str(source).strip() or None if source is not None else None,
    )


def _envelope_from_mapping(payload: dict[str, Any]) -> TurnLockEnvelope | None:
    try:
        thread_id = int(payload.get("thread_id") or 0)
        owner_task_id = str(payload.get("owner_task_id") or "").strip()
        acquired_at = str(payload.get("acquired_at") or "").strip()
        renewed_at = str(payload.get("renewed_at") or "").strip()
        lease_expires_at = str(payload.get("lease_expires_at") or "").strip()
        lease_token = str(payload.get("lease_token") or "").strip()
    except Exception:
        return None

    if not (
        thread_id
        and owner_task_id
        and acquired_at
        and renewed_at
        and lease_expires_at
        and lease_token
    ):
        return None

    return TurnLockEnvelope(
        thread_id=thread_id,
        owner_task_id=owner_task_id,
        turn_id=str(payload.get("turn_id") or uuid.uuid4()),
        acquired_at=acquired_at,
        renewed_at=renewed_at,
        lease_expires_at=lease_expires_at,
        lease_ttl_seconds=int(
            payload.get("lease_ttl_seconds") or _DEFAULT_TTL_SECONDS
        ),
        lease_token=lease_token,
        source=str(payload.get("source") or "").strip() or None,
    )


def _decode_turn_lock_value(raw: Any) -> TurnLockEnvelope | None:
    text = _coerce_text(raw)
    if not text:
        return None
    try:
        payload = json.loads(text)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return _envelope_from_mapping(payload)


def _serialize_turn_lock(lock: TurnLockEnvelope) -> str:
    return json.dumps(lock.as_dict(), separators=(",", ":"), sort_keys=True)


def _expected_owner_and_token(
    expected: str | TurnLockEnvelope,
) -> tuple[str, str]:
    if isinstance(expected, TurnLockEnvelope):
        return expected.owner_task_id, expected.lease_token
    return str(expected), ""


def _matches_expected_lock(
    current_raw: Any, expected: str | TurnLockEnvelope
) -> bool:
    owner_task_id, lease_token = _expected_owner_and_token(expected)
    current_text = _coerce_text(current_raw)
    current_lock = _decode_turn_lock_value(current_raw)
    if current_lock is not None:
        if current_lock.owner_task_id != owner_task_id:
            return False
        if lease_token and current_lock.lease_token != lease_token:
            return False
        return True
    return current_text == owner_task_id


def turn_lock_key(thread_id: int) -> str:
    return f"turn_lock:{int(thread_id)}"


def acquire_turn_lock(
    thread_id: int,
    owner: str,
    *,
    ttl_seconds: int | None = None,
    turn_id: str | None = None,
    source: str | None = None,
    return_envelope: bool = False,
) -> bool | TurnLockEnvelope | None:
    """Acquire a per-thread lock using SET NX EX semantics."""
    key = turn_lock_key(thread_id)
    ttl = _coerce_lock_ttl_seconds(ttl_seconds)
    envelope = build_turn_lock_envelope(
        thread_id,
        owner,
        turn_id=turn_id,
        ttl_seconds=ttl,
        source=source,
    )
    value = (
        _serialize_turn_lock(envelope)
        if return_envelope or turn_id is not None or source is not None
        else owner
    )

    def _acquire(client) -> bool:
        return bool(client.set(key, value, nx=True, ex=ttl))

    acquired = bool(_with_reconnect(_acquire))
    if not acquired:
        logger.info("[turn-lock] in-flight thread_id=%s key=%s", thread_id, key)
        return None if return_envelope else False
    return envelope if return_envelope else True


def renew_turn_lock(
    thread_id: int,
    lock: TurnLockEnvelope,
    *,
    ttl_seconds: int | None = None,
    return_envelope: bool = False,
) -> bool | TurnLockEnvelope | None:
    ttl = _coerce_lock_ttl_seconds(ttl_seconds)
    renewed = build_turn_lock_envelope(
        thread_id,
        lock.owner_task_id,
        turn_id=lock.turn_id,
        ttl_seconds=ttl,
        source=lock.source,
        acquired_at=lock.acquired_at,
        renewed_at=_utc_now_iso(),
        lease_token=lock.lease_token,
    )
    key = turn_lock_key(thread_id)

    def _renew(client) -> bool:
        return bool(client.set(key, _serialize_turn_lock(renewed), ex=ttl))

    updated = bool(_with_reconnect(_renew))
    if not updated:
        return None if return_envelope else False
    return renewed if return_envelope else True


def release_turn_lock(thread_id: int, owner: str | TurnLockEnvelope) -> bool:
    """Release lock only when current owner matches."""
    key = turn_lock_key(thread_id)

    def _release(client) -> bool:
        owner_task_id, lease_token = _expected_owner_and_token(owner)
        if hasattr(client, "eval"):
            try:
                released = client.eval(
                    """
                    local value = redis.call('GET', KEYS[1])
                    if not value then
                        return 0
                    end
                    if value == ARGV[1] and ARGV[2] == '' then
                        return redis.call('DEL', KEYS[1])
                    end
                    local ok, payload = pcall(cjson.decode, value)
                    if ok and payload and payload.owner_task_id == ARGV[1] then
                        if ARGV[2] == '' or payload.lease_token == ARGV[2] then
                            return redis.call('DEL', KEYS[1])
                        end
                    end
                    return 0
                    """,
                    1,
                    key,
                    owner_task_id,
                    lease_token,
                )
                return bool(released)
            except Exception:
                logger.debug(
                    "[turn-lock] eval release fallback thread_id=%s",
                    thread_id,
                    exc_info=True,
                )
        current = client.get(key)
        if not _matches_expected_lock(current, owner):
            return False
        return bool(client.delete(key))

    return bool(_with_reconnect(_release))


def clear_turn_lock(
    thread_id: int,
    expected: str | TurnLockEnvelope | None = None,
) -> bool:
    key = turn_lock_key(thread_id)

    def _clear(client) -> bool:
        if expected is None:
            return bool(client.delete(key))
        current = client.get(key)
        if not _matches_expected_lock(current, expected):
            return False
        return bool(client.delete(key))

    return bool(_with_reconnect(_clear))


def get_turn_lock(thread_id: int) -> TurnLockEnvelope | None:
    key = turn_lock_key(thread_id)

    def _get_lock(client) -> TurnLockEnvelope | None:
        return _decode_turn_lock_value(client.get(key))

    return _with_reconnect(_get_lock)


def turn_lock_is_stale(
    lock: TurnLockEnvelope,
    *,
    now: datetime | None = None,
) -> bool:
    lease_expires_at = _parse_iso8601(lock.lease_expires_at)
    if lease_expires_at is None:
        return False
    return lease_expires_at <= (now or _utc_now())


def get_turn_lock_owner(thread_id: int) -> str | None:
    """Return lock owner for diagnostics."""
    key = turn_lock_key(thread_id)

    def _get_owner(client) -> str | None:
        value = client.get(key)
        lock = _decode_turn_lock_value(value)
        if lock is not None:
            return lock.owner_task_id
        text = _coerce_text(value)
        return text if text is not None else None

    return _with_reconnect(_get_owner)
