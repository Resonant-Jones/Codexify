"""Task-event SSE resource authorization regressions (ADR-091 + ADR-092).

``GET /api/tasks/{task_id}/events`` must authenticate exactly one principal
lane, resolve the task through its durable ``ChatCompletionAttempt`` to a
canonical thread, and authorize that thread before any Redis event read.

The load-bearing property is ordering: a denied request performs **zero**
Redis event reads and cannot reveal whether foreign task-event data exists.

All credentials, tasks, threads, rooms, and event payloads here are
deterministic synthetic fixtures. No real account data is read or asserted.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import inspect
import json
import os
import tempfile
import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

# The route module performs import-time storage bootstrap.
os.environ.setdefault("STORAGE_BASE_PATH", os.path.join(tempfile.mkdtemp(prefix="task-evt-authz-"), "media"))
os.environ.setdefault("CODEXIFY_EMBEDDINGS_BACKEND", "mock")

from guardian.core import dependencies  # noqa: E402
from guardian.core import task_event_access  # noqa: E402
from guardian.core.auth import (  # noqa: E402
    ACCOUNT_SESSION_PURPOSE,
    OPERATOR_SESSION_PURPOSE,
    issue_session_token,
)
from guardian.core.dependencies import require_task_event_read_principal  # noqa: E402
from guardian.core.hosted_room_session import (  # noqa: E402
    HostedRoomGuestPrincipal,
    issue_guest_session_token,
)

# ADR-098 moved principal resolution for this surface onto the shared
# `require_task_event_read_principal` seam. These labels describe which lane a
# resolved principal belongs to; they are test-local evidence labels, not a
# production authorization constant.
ACCOUNT_LANE = "account"
GUEST_LANE = "hosted_room_guest"

ACCOUNT_A = "account-a@fixture.invalid"
ACCOUNT_B = "account-b@fixture.invalid"

THREAD_A = 1001
THREAD_B = 1002
THREAD_ROOM = 2001

TASK_A = "task-account-a"
TASK_B = "task-account-b"
TASK_ROOM = "task-room-one"
TASK_MISSING = "task-without-attempt"

SESSION_SECRET = "task-event-authz-session-secret"


# ── Credential fixtures ─────────────────────────────────────────────────


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _sign(payload: bytes) -> str:
    return _b64(hmac.new(SESSION_SECRET.encode(), payload, hashlib.sha256).digest())


def _account_token(subject: str, *, purpose: str | None, ttl_seconds: int = 3600) -> str:
    """Mint a signed session token, optionally without an explicit purpose."""
    claims = {
        "subject": subject,
        "exp": int(time.time()) + int(ttl_seconds),
        "nonce": "task-event-authz-fixture",
    }
    if purpose is not None:
        claims["purpose"] = purpose
    payload = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode()
    return f"{_b64(payload)}.{_sign(payload)}"


def _account_jwt(
    *,
    subject: str,
    purpose: str | None = ACCOUNT_SESSION_PURPOSE,
    exp: int | None = None,
    secret: str = SESSION_SECRET,
) -> str:
    """Mint an HS256 account-session JWT for the remote account lane.

    ADR-098 resolves this lane through `dependencies._remote_single_user_account_jwt_subject`,
    which accepts only a real HS256 JWT carrying `exp`, `sub`, and the account
    session purpose. A native two-part token is rejected there and falls through
    to a non-multi-user scope, where cross-account ownership is not enforced.

    The native `_account_token` above stays in use for the mixed-lane and
    wrong-purpose rejection tests, which assert credential-class rejection
    before any account identity is resolved.
    """
    jwt = pytest.importorskip("jwt")
    claims = {"sub": subject, "exp": exp or int(time.time()) + 120}
    if purpose is not None:
        claims["purpose"] = purpose
    return jwt.encode(claims, secret, algorithm="HS256")


@pytest.fixture(autouse=True)
def remote_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every case at the remote multi-principal boundary ADR-092 governs."""
    monkeypatch.setattr(dependencies, "is_private_preview", lambda: False)
    monkeypatch.setattr(dependencies, "_multi_user_mode_enabled", lambda: False)
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", SESSION_SECRET)
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.delenv("GUARDIAN_EXPOSURE_MODE", raising=False)


# ── Request / durable-state fakes ───────────────────────────────────────


def _request(
    *,
    bearer: str | None = None,
    guest: str | None = None,
    x_api_key: str | None = None,
    guardian_key: str | None = None,
    gc_session: str | None = None,
    path: str = "/api/tasks/t/events",
) -> Request:
    cookies: list[str] = []
    if guest:
        cookies.append(f"codexify_hosted_room_session={guest}")
    if gc_session:
        cookies.append(f"gc_session={gc_session}")
    if cookies:
        cookies.append("Cookie")
    cookie_value = "; ".join(c for c in cookies if c != "Cookie")

    raw: list[tuple[bytes, bytes]] = []
    if bearer:
        raw.append((b"authorization", f"Bearer {bearer}".encode()))
    if x_api_key:
        raw.append((b"x-api-key", x_api_key.encode()))
    if guardian_key:
        raw.append((b"x-guardian-key", guardian_key.encode()))
    if cookie_value:
        raw.append((b"cookie", cookie_value.encode()))

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": raw,
            "query_string": b"",
        },
        receive=receive,
    )


class _FakeChatlogDB:
    """Minimal canonical chat store: thread lookup only."""

    def __init__(self, threads: dict[int, dict]):
        self._threads = threads

    def get_chat_thread(self, thread_id: int):
        return self._threads.get(int(thread_id))


ATTEMPTS = {
    TASK_A: {"backend_task_id": TASK_A, "thread_id": THREAD_A},
    TASK_B: {"backend_task_id": TASK_B, "thread_id": THREAD_B},
    TASK_ROOM: {"backend_task_id": TASK_ROOM, "thread_id": THREAD_ROOM},
}
# Threads are owned by their accounts; the room thread is not account-owned.
THREADS = {
    THREAD_A: {"id": THREAD_A, "user_id": ACCOUNT_A},
    THREAD_B: {"id": THREAD_B, "user_id": ACCOUNT_B},
    THREAD_ROOM: {"id": THREAD_ROOM, "user_id": "room-owner-account"},
}


def _fake_attempts(_chatlog_db, backend_task_id: str):
    return ATTEMPTS.get(backend_task_id)


@pytest.fixture(autouse=True)
def durable_binding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bind task_id -> canonical thread through the durable attempt only."""
    monkeypatch.setattr(
        task_event_access, "get_chat_completion_attempt_by_task_id", _fake_attempts
    )


def _chatlog() -> _FakeChatlogDB:
    return _FakeChatlogDB(THREADS)


def _authorize(task_id: str, request: Request, chatlog_db=None):
    """Authenticate exactly one principal lane, then authorize durable lineage.

    Mirrors the route: `require_task_event_read_principal` resolves the lane
    (rejecting mixed lanes before any resource lookup), and
    `authorize_task_event_read` resolves the durable attempt to its canonical
    thread. A denial therefore raises before any thread or Redis access.
    """
    principal = require_task_event_read_principal(
        request,
        x_api_key=request.headers.get("X-API-Key"),
        authorization=request.headers.get("Authorization"),
        gc_session=request.cookies.get("gc_session"),
    )
    access = task_event_access.authorize_task_event_read(
        task_id,
        principal,
        chatlog_db=_chatlog() if chatlog_db is None else chatlog_db,
    )
    return SimpleNamespace(
        task_id=task_id,
        thread_id=access.thread_id,
        principal=principal,
        principal_kind=(
            GUEST_LANE
            if isinstance(principal, HostedRoomGuestPrincipal)
            else ACCOUNT_LANE
        ),
    )


def _guest_token(
    *,
    room_id: str = "room-one",
    participant_id: str = "participant-one",
    invitation_id: str = "invitation-one",
    ttl_seconds: int = 3600,
) -> str:
    token, _ = issue_guest_session_token(
        room_id=room_id,
        room_slug="room-one-slug",
        participant_id=participant_id,
        invitation_id=invitation_id,
        ttl_seconds=ttl_seconds,
    )
    return token


class _Room:
    def __init__(self, room_id: str, backing_thread_id: int, status: str = "active"):
        self.id = room_id
        self.backing_thread_id = backing_thread_id
        self.status = status


class _Participant:
    def __init__(
        self,
        participant_id: str,
        room_id: str,
        invitation_id: str,
        state: str = "active",
    ):
        self.id = participant_id
        self.room_id = room_id
        self.invitation_id = invitation_id
        self.state = state
        self.kind = "human"
        self.role = "member"


class _Invite:
    def __init__(self, invitation_id: str, status: str = "accepted"):
        self.id = invitation_id
        self.status = status
        self.expires_at = None


class _GuestSession:
    def __init__(self, rooms, participants, invites):
        self._rooms = rooms
        self._participants = participants
        self._invites = invites

    def get(self, model, pk):
        name = getattr(model, "__name__", "")
        table = {
            "HostedRoom": self._rooms,
            "HostedRoomParticipant": self._participants,
            "HostedRoomInvite": self._invites,
        }.get(name)
        if table is None:
            return None
        return table.get(pk)


class _GuestDB:
    def __init__(self, session: _GuestSession):
        self._session = session

    def get_session(self):
        session = self._session

        class _Ctx:
            def __enter__(self_inner):
                return session

            def __exit__(self_inner, *exc):
                return False

        return _Ctx()


def _install_guest_db(
    monkeypatch: pytest.MonkeyPatch,
    *,
    room_status: str = "active",
    participant_state: str = "active",
) -> None:
    session = _GuestSession(
        rooms={
            "room-one": _Room("room-one", THREAD_ROOM, status=room_status),
            "room-two": _Room("room-two", THREAD_A, status=room_status),
        },
        participants={
            "participant-one": _Participant(
                "participant-one", "room-one", "invitation-one", state=participant_state
            ),
        },
        invites={"invitation-one": _Invite("invitation-one")},
    )
    monkeypatch.setattr(
        task_event_access, "load_guardian_db_from_env", lambda: _GuestDB(session)
    )


def _redis_probe(monkeypatch: pytest.MonkeyPatch, events=None):
    """Count task_events.read_events_bounded calls so denial can be proven zero-read."""
    calls: list[tuple] = []

    def _read_events(task_id, last_id, **kwargs):
        calls.append((task_id, last_id))
        return list(events or [])

    import guardian.queue.task_events as real_task_events

    monkeypatch.setattr(real_task_events, "read_events_bounded", _read_events)
    return calls


# ── Authentication / credential-class rejection ─────────────────────────


def test_anonymous_request_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _redis_probe(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_A, _request())
    assert exc.value.status_code == 401
    assert calls == []


def test_malformed_session_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _redis_probe(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_A, _request(bearer="not.a-real-signed-token"))
    assert exc.value.status_code == 401
    assert calls == []


def test_expired_account_session_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _redis_probe(monkeypatch)
    expired = _account_token(ACCOUNT_A, purpose=ACCOUNT_SESSION_PURPOSE, ttl_seconds=-60)
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_A, _request(bearer=expired))
    assert exc.value.status_code == 401
    assert calls == []


def test_purpose_less_legacy_credential_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    """A validly signed, unexpired legacy token carries no account authority."""
    calls = _redis_probe(monkeypatch)
    legacy = _account_token(ACCOUNT_A, purpose=None)
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_A, _request(bearer=legacy))
    assert exc.value.status_code == 401
    assert calls == []


def test_operator_session_denied_as_account(monkeypatch: pytest.MonkeyPatch) -> None:
    """Operator authority is not user task-stream authority."""
    calls = _redis_probe(monkeypatch)
    operator, _ = issue_session_token(
        subject="operator@fixture.invalid", purpose=OPERATOR_SESSION_PURPOSE
    )
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_A, _request(bearer=operator))
    assert exc.value.status_code == 401
    assert calls == []


def test_static_api_key_denied_in_remote_posture(monkeypatch: pytest.MonkeyPatch) -> None:
    """A raw Guardian key is operator-lane material on this route, not account."""
    calls = _redis_probe(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_A, _request(x_api_key="static-guardian-key"))
    assert exc.value.status_code == 401
    assert calls == []


def test_raw_guardian_key_denied_in_remote_posture(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _redis_probe(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_A, _request(guardian_key="static-guardian-key"))
    assert exc.value.status_code == 401
    assert calls == []


def test_wrong_purpose_guest_token_denied_in_account_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A guest credential cannot become an account principal."""
    calls = _redis_probe(monkeypatch)
    guest = _guest_token()
    with pytest.raises(HTTPException) as exc:
        # Presented as a bearer account selector rather than the guest cookie.
        _authorize(TASK_A, _request(bearer=guest))
    assert exc.value.status_code == 401
    assert calls == []


# ── Mixed-lane rejection (ADR-092) ──────────────────────────────────────


def _mixed(exc: HTTPException) -> None:
    assert exc.value.status_code == 400
    assert exc.value.detail["error"] == "mixed_principal_credentials"


def test_mixed_account_and_guest_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _redis_probe(monkeypatch)
    _install_guest_db(monkeypatch)
    account, _ = issue_session_token(subject=ACCOUNT_A, purpose=ACCOUNT_SESSION_PURPOSE)
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_ROOM, _request(bearer=account, guest=_guest_token()))
    _mixed(exc)
    assert calls == []


def test_mixed_account_and_operator_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _redis_probe(monkeypatch)
    account, _ = issue_session_token(subject=ACCOUNT_A, purpose=ACCOUNT_SESSION_PURPOSE)
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_A, _request(bearer=account, x_api_key="static-guardian-key"))
    _mixed(exc)
    assert calls == []


def test_mixed_account_and_operator_session_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _redis_probe(monkeypatch)
    account, _ = issue_session_token(subject=ACCOUNT_A, purpose=ACCOUNT_SESSION_PURPOSE)
    operator, _ = issue_session_token(
        subject="operator@fixture.invalid", purpose=OPERATOR_SESSION_PURPOSE
    )
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_A, _request(bearer=account, gc_session=operator))
    _mixed(exc)
    assert calls == []


def test_mixed_guest_with_invalid_signed_material_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guest selector plus malformed signed material is still mixed."""
    calls = _redis_probe(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_ROOM, _request(bearer="garbage-selector", guest=_guest_token()))
    _mixed(exc)
    assert calls == []


# ── Durable lineage + account isolation ─────────────────────────────────


def test_account_a_may_read_own_task_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    """Positive control for the two denials below.

    The owner passes the very same ownership check that denies a foreign
    account. A non-multi-user principal would clear it vacuously and make the
    cross-account denials meaningless, so the resolved scope is asserted too.
    """
    calls = _redis_probe(monkeypatch)
    access = _authorize(TASK_A, _request(bearer=_account_jwt(subject=ACCOUNT_A)))
    assert access.thread_id == THREAD_A
    assert access.principal_kind == ACCOUNT_LANE
    assert access.principal.multi_user_enabled is True
    assert access.principal.account_id == ACCOUNT_A
    # Authorization alone must not consume events.
    assert calls == []


def test_account_b_cannot_read_account_a_task_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _redis_probe(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_A, _request(bearer=_account_jwt(subject=ACCOUNT_B)))
    assert exc.value.status_code == 403
    assert calls == []


def test_account_a_cannot_read_account_b_task_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _redis_probe(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_B, _request(bearer=_account_jwt(subject=ACCOUNT_A)))
    assert exc.value.status_code == 403
    assert calls == []


def test_unknown_thread_denied_without_leaking_ownership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _redis_probe(monkeypatch)
    token = _account_jwt(subject=ACCOUNT_A)
    with pytest.raises(HTTPException) as exc:
        # Durable attempt exists; canonical thread does not.
        _authorize("task-with-missing-thread", _request(bearer=token))
    assert exc.value.status_code == 404
    assert calls == []


def test_missing_durable_attempt_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """No durable ChatCompletionAttempt means no authority, not a guess."""
    calls = _redis_probe(monkeypatch)
    token = _account_jwt(subject=ACCOUNT_A)
    with pytest.raises(HTTPException) as missing:
        _authorize(TASK_MISSING, _request(bearer=token))
    assert missing.value.status_code == 404
    assert calls == []

    # The current contract is a single non-disclosing 404 string. "No durable
    # attempt" must be indistinguishable from "no such task", so a caller cannot
    # probe which task ids or thread lineage exist.
    with pytest.raises(HTTPException) as unknown:
        _authorize("task-that-never-existed", _request(bearer=token))
    assert unknown.value.status_code == missing.value.status_code
    assert unknown.value.detail == missing.value.detail


def test_missing_attempt_denied_before_thread_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Redis-derived ownership inference is never attempted."""
    token = _account_jwt(subject=ACCOUNT_A)
    seen: list[int] = []

    class _Tripwire(_FakeChatlogDB):
        def get_chat_thread(self, thread_id: int):
            seen.append(int(thread_id))
            return super().get_chat_thread(thread_id)

    with pytest.raises(HTTPException):
        _authorize(TASK_MISSING, _request(bearer=token), _Tripwire(THREADS))
    assert seen == []


# ── Hosted Room guest isolation ─────────────────────────────────────────


def test_same_room_guest_may_read_room_backing_thread_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _redis_probe(monkeypatch)
    _install_guest_db(monkeypatch)
    access = _authorize(TASK_ROOM, _request(guest=_guest_token()))
    assert access.thread_id == THREAD_ROOM
    assert access.principal_kind == GUEST_LANE
    assert calls == []


def test_wrong_room_guest_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    """A guest of another room may not read this room's task."""
    calls = _redis_probe(monkeypatch)
    _install_guest_db(monkeypatch)
    wrong_room_guest = _guest_token(room_id="room-two", participant_id="participant-one")
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_ROOM, _request(guest=wrong_room_guest))
    assert exc.value.status_code in {401, 404}
    assert calls == []


def test_guest_may_not_read_account_owned_task(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _redis_probe(monkeypatch)
    _install_guest_db(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_A, _request(guest=_guest_token()))
    assert exc.value.status_code == 401
    assert calls == []


def test_removed_guest_authority_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _redis_probe(monkeypatch)
    _install_guest_db(monkeypatch, participant_state="removed")
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_ROOM, _request(guest=_guest_token()))
    assert exc.value.status_code == 401
    assert calls == []


def test_inactive_room_guest_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _redis_probe(monkeypatch)
    _install_guest_db(monkeypatch, room_status="closed")
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_ROOM, _request(guest=_guest_token()))
    assert exc.value.status_code == 401
    assert calls == []


def test_expired_guest_session_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _redis_probe(monkeypatch)
    _install_guest_db(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_ROOM, _request(guest=_guest_token(ttl_seconds=-60)))
    assert exc.value.status_code == 401
    assert calls == []


def test_revoked_invitation_guest_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _redis_probe(monkeypatch)
    session = _GuestSession(
        rooms={"room-one": _Room("room-one", THREAD_ROOM)},
        participants={
            "participant-one": _Participant("participant-one", "room-one", "invitation-one")
        },
        invites={"invitation-one": _Invite("invitation-one", status="revoked")},
    )
    monkeypatch.setattr(
        task_event_access, "load_guardian_db_from_env", lambda: _GuestDB(session)
    )
    with pytest.raises(HTTPException) as exc:
        _authorize(TASK_ROOM, _request(guest=_guest_token()))
    assert exc.value.status_code == 401
    assert calls == []


# ── Route wiring and SSE transport compatibility ───────────────────────


@pytest.fixture(scope="module")
def guardian_api_module():
    import guardian.guardian_api as module

    return module


async def _stream(module, request, task_id, last_id_query="0-0", last_event_id=None):
    # Resolve the principal the way the route's dependency does, then hand it
    # to the route explicitly. Calling the route function directly bypasses
    # FastAPI's dependency injection, and the route still performs its own
    # durable-lineage authorization before any Redis read.
    principal = require_task_event_read_principal(
        request,
        x_api_key=request.headers.get("X-API-Key"),
        authorization=request.headers.get("Authorization"),
        gc_session=request.cookies.get("gc_session"),
    )
    response = await module.stream_task_events(
        request, task_id, last_id_query, last_event_id, principal=principal
    )
    chunks: list[str] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk if isinstance(chunk, str) else chunk.decode())
    return "".join(chunks)


def _install_route_events(monkeypatch: pytest.MonkeyPatch, module, events):
    calls: list[tuple] = []

    def _read_events(task_id, last_id, **kwargs):
        calls.append((task_id, last_id))
        return list(events)

    monkeypatch.setattr(module, "chatlog_db", _chatlog())
    monkeypatch.setattr(module.task_events, "read_events_bounded", _read_events)
    return calls


def test_route_no_longer_depends_on_generic_api_key() -> None:
    """The generic require_api_key seam is no longer this route's authority."""
    import guardian.guardian_api as module

    params = inspect.signature(module.stream_task_events).parameters
    assert "api_key" not in params
    source = inspect.getsource(module.stream_task_events)
    assert "require_api_key" not in source
    assert "authorize_task_event_read" in source


def test_authorized_request_preserves_sse_framing(
    monkeypatch: pytest.MonkeyPatch, guardian_api_module
) -> None:
    module = guardian_api_module
    calls = _install_route_events(
        monkeypatch,
        module,
        [("1-0", {"type": "task.completed", "data": {"marker": "synthetic-complete"}})],
    )
    token = _account_jwt(subject=ACCOUNT_A)
    body = asyncio.run(_stream(module, _request(bearer=token), TASK_A))

    assert body.startswith("retry: 3000\n\n")
    assert "id: 1-0\n" in body
    assert "event: task.completed\n" in body
    assert "synthetic-complete" in body
    # The terminal event ends the stream.
    assert calls == [(TASK_A, "0-0")]


def test_last_event_id_resume_starts_from_requested_cursor(
    monkeypatch: pytest.MonkeyPatch, guardian_api_module
) -> None:
    module = guardian_api_module
    calls = _install_route_events(
        monkeypatch,
        module,
        [("9-4", {"type": "task.completed", "data": {"marker": "resumed"}})],
    )
    token = _account_jwt(subject=ACCOUNT_A)
    body = asyncio.run(
        _stream(module, _request(bearer=token), TASK_A, last_event_id="5-2")
    )

    assert calls == [(TASK_A, "5-2")]
    assert "id: 9-4\n" in body


def test_malformed_cursor_is_normalized(
    monkeypatch: pytest.MonkeyPatch, guardian_api_module
) -> None:
    module = guardian_api_module
    calls = _install_route_events(
        monkeypatch,
        module,
        [("1-0", {"type": "task.completed", "data": {"marker": "normalized"}})],
    )
    token = _account_jwt(subject=ACCOUNT_A)
    asyncio.run(_stream(module, _request(bearer=token), TASK_A, last_id_query="garbage"))
    assert calls == [(TASK_A, "0-0")]


def test_cross_account_route_request_performs_zero_redis_reads(
    monkeypatch: pytest.MonkeyPatch, guardian_api_module
) -> None:
    module = guardian_api_module
    calls = _install_route_events(
        monkeypatch,
        module,
        [("1-0", {"type": "task.completed", "data": {"marker": "account-a-secret"}})],
    )
    token = _account_jwt(subject=ACCOUNT_B)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(_stream(module, _request(bearer=token), TASK_A))
    assert exc.value.status_code == 403
    # No StreamingResponse, no retry frame, no event data, no Redis read.
    assert calls == []


def test_missing_attempt_route_request_performs_zero_redis_reads(
    monkeypatch: pytest.MonkeyPatch, guardian_api_module
) -> None:
    module = guardian_api_module
    calls = _install_route_events(
        monkeypatch,
        module,
        [("1-0", {"type": "task.completed", "data": {"marker": "unreachable"}})],
    )
    token = _account_jwt(subject=ACCOUNT_A)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(_stream(module, _request(bearer=token), TASK_MISSING))
    assert exc.value.status_code == 404
    assert calls == []


def test_anonymous_route_request_performs_zero_redis_reads(
    monkeypatch: pytest.MonkeyPatch, guardian_api_module
) -> None:
    module = guardian_api_module
    calls = _install_route_events(
        monkeypatch,
        module,
        [("1-0", {"type": "task.completed", "data": {"marker": "unreachable"}})],
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(_stream(module, _request(), TASK_A))
    assert exc.value.status_code == 401
    assert calls == []