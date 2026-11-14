"""Shared, bounded password-login admission for Private Preview."""

from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import HTTPException, Request

from guardian.core.preview_access import normalize_preview_email
from guardian.queue.redis_queue import get_redis_client, redis_operation_scope

# Fixed windows start on the first admitted attempt, including successful ones.
# The source is the ASGI-observed peer, often the shared Preview proxy. No
# forwarding header is interpreted here; identity and global caps remain
# authoritative even when upstream address attribution is unavailable.
LIMITS = ((120, 60), (10, 300), (30, 60))  # global, identity, observed source
PREFIX = "guardian:{preview-login}:"

# One atomic decision across workers. Check every bucket before writing any;
# denial neither allocates keys nor extends an existing cooldown. The global
# budget also bounds allocation when an attacker varies identities/sources.
_ADMIT = """
local retry = 0
for i, key in ipairs(KEYS) do
    local value = redis.call('GET', key)
    if value then
        local count = tonumber(value)
        local ttl = redis.call('PTTL', key)
        if not count or count < 0 or count ~= math.floor(count) or ttl < 0 then
            return redis.error_reply('invalid login limiter state')
        end
        if count >= tonumber(ARGV[2*i-1]) then
            retry = math.max(retry, math.max(1, ttl))
        end
    end
end
if retry > 0 then return retry end
for i, key in ipairs(KEYS) do
    if redis.call('INCR', key) == 1 then
        redis.call('PEXPIRE', key, ARGV[2*i])
    end
end
return 0
"""


def enforce_preview_login_limit(username: str, request: Request | None) -> None:
    """Reject before account lookup/bcrypt; Redis failure never admits a login."""
    try:
        secret = (os.getenv("GUARDIAN_SESSION_SECRET") or "").strip()
        if not secret:
            raise ValueError("missing Preview signing secret")
        peer = request.client.host if request and request.client else "unknown"

        def key(kind: str, value: str) -> str:
            digest = hmac.new(
                secret.encode(), (kind + ":" + value).encode(), hashlib.sha256
            ).hexdigest()
            return PREFIX + kind + ":" + digest

        keys = (
            PREFIX + "global",
            key("identity", normalize_preview_email(username)),
            key("source", peer),
        )
        args = [value for limit, seconds in LIMITS for value in (limit, seconds * 1000)]
        with redis_operation_scope(timeout_seconds=2):
            retry_ms = get_redis_client().eval(_ADMIT, len(keys), *keys, *args)
        if type(retry_ms) is not int or retry_ms < 0:
            raise ValueError("invalid login limiter reply")
    except Exception:
        # Do not include Redis exceptions, addresses, identifiers or credentials.
        raise HTTPException(
            status_code=503,
            detail="Login temporarily unavailable",
            headers={"Retry-After": "5", "Cache-Control": "no-store"},
        ) from None
    if retry_ms:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts; try again later",
            headers={
                "Retry-After": str((retry_ms + 999) // 1000),
                "Cache-Control": "no-store",
            },
        )
