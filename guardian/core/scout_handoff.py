"""Short-lived PKCE approval for an independent canonical native account session."""

import base64
import hashlib
import json
import re
import secrets

from guardian.core.session_store import get_session_store
from guardian.queue.redis_queue import run_with_redis_timeout

ORIGIN = "https://preview.codexify.space"
CALLBACK = "ai.resonantconstructs.codexify.scout://access-callback"
TTL = 60
_CHALLENGE = re.compile(r"[A-Za-z0-9_-]{43}\Z")
_VERIFIER = re.compile(r"[A-Za-z0-9._~-]{43,128}\Z")
_CONSUME = """
local value = redis.call('GET', KEYS[1])
if not value then return false end
local grant = cjson.decode(value)
if grant.challenge ~= ARGV[1] or grant.origin ~= ARGV[2] then return false end
redis.call('DEL', KEYS[1])
return value
"""


class HandoffUnavailable(ValueError):
    pass


def challenge_for(verifier: str) -> str:
    if not _VERIFIER.fullmatch(verifier):
        raise HandoffUnavailable()
    return (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .decode()
        .rstrip("=")
    )


class ScoutHandoffStore:
    def __init__(self, client=None):
        self.client = client

    def _client(self):
        return self.client if self.client is not None else get_session_store()._client()

    @staticmethod
    def _key(code):
        if not _CHALLENGE.fullmatch(code):
            raise HandoffUnavailable()
        return "scout:handoff:" + hashlib.sha256(code.encode("ascii")).hexdigest()

    def create(
        self,
        *,
        challenge: str,
        state: str,
        token: str,
        user_id: str,
        expires_at: int,
        origin: str,
    ) -> str:
        if (
            not _CHALLENGE.fullmatch(challenge)
            or not _CHALLENGE.fullmatch(state)
            or origin != ORIGIN
        ):
            raise HandoffUnavailable()
        code = secrets.token_urlsafe(32)
        value = json.dumps(
            {
                "challenge": challenge,
                "origin": origin,
                "token": token,
                "user_id": user_id,
                "expires_at": expires_at,
            }
        )
        created = run_with_redis_timeout(
            lambda: self._client().set(self._key(code), value, ex=TTL, nx=True)
        )
        if not created:
            raise HandoffUnavailable()
        return code

    def consume(self, *, code: str, verifier: str, origin: str) -> dict:
        if origin != ORIGIN:
            raise HandoffUnavailable()
        key = self._key(code)
        challenge = challenge_for(verifier)
        value = run_with_redis_timeout(
            lambda: self._client().eval(_CONSUME, 1, key, challenge, origin)
        )
        if not value:
            raise HandoffUnavailable()
        return json.loads(value)
