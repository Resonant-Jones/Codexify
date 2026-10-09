"""Ephemeral, content-free Scout sign-in evidence; never authorization state.

One process, at most 128 attempts, ten minute fixed TTL. Restart/missing evidence
means unobserved, never failed authentication. No user or credential is retained.
"""

import logging
import re
import threading
import time

HEADER = "X-Scout-Auth-Attempt"
_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z"
)
STAGES = frozenset(
    {
        "browser_loaded",
        "account_login",
        "handoff_redirect",
        "handoff_exchange",
        "native_session",
        "protected_read",
    }
)
STATUSES = frozenset({"waiting", "passed", "failed"})
TTL = 600
LIMIT = 128
_lock = threading.Lock()
_attempts = {}
_logger = logging.getLogger(__name__)


def attempt_id(value):
    return value if isinstance(value, str) and _ID.fullmatch(value) else None


def request_attempt(request):
    values = request.headers.getlist(HEADER) if request is not None else []
    return attempt_id(values[0]) if len(values) == 1 else None


def _prune():
    now = time.monotonic()
    for identity in list(_attempts):
        if _attempts[identity][0] <= now:
            del _attempts[identity]


def begin(identity):
    if not attempt_id(identity):
        return False
    with _lock:
        _prune()
        if identity in _attempts:
            return True  # retries do not reset evidence or extend retention
        if len(_attempts) >= LIMIT:
            return False
        _attempts[identity] = (time.monotonic() + TTL, {})
    return True


def observe(identity, stage, status, http_status=None):
    if not attempt_id(identity) or stage not in STAGES or status not in STATUSES:
        return
    if http_status is not None and (
        type(http_status) is not int or not 100 <= http_status <= 599
    ):
        return
    with _lock:
        _prune()
        entry = _attempts.get(identity)
        if not entry:
            return
        current = entry[1].get(stage)
        if current and current["status"] == "passed":
            return  # later observations cannot retract confirmed evidence
        evidence = {"status": status}
        if http_status is not None:
            evidence["http_status"] = http_status
        entry[1][stage] = evidence
    # These four fields are explicitly safe in the existing log sanitizer.
    _logger.info(
        "scout_auth_qualification request_id=%s event_type=%s status=%s http_status=%s",
        identity,
        stage,
        status,
        http_status,
    )


def snapshot(identity):
    if not attempt_id(identity):
        return None
    with _lock:
        _prune()
        entry = _attempts.get(identity)
        if not entry:
            return None
        return {
            "attempt_id": identity,
            "stages": {key: dict(value) for key, value in entry[1].items()},
        }
