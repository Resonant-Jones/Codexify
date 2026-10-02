from __future__ import annotations

import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from guardian.core import dependencies
from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    OPERATOR_SESSION_PURPOSE,
    issue_session_token,
)
from guardian.core.dependencies import RequestUserScope, require_task_event_read_principal
from guardian.core.hosted_room_session import issue_guest_session_token
from guardian.db.models import HostedRoom, HostedRoomInvite, HostedRoomParticipant
from guardian.queue import task_events


@pytest.fixture
def task_event_client(monkeypatch):
    from guardian import guardian_api

    db = Mock()
    db.get_chat_thread.side_effect = lambda thread_id: {
        "id": thread_id,
        "user_id": "account-owner" if thread_id == 19 else "account-a",
    }
    attempts = {
        "backend-task-a": {"backend_task_id": "backend-task-a", "request_id": "request-a", "thread_id": 7},
        "backend-task-room": {"backend_task_id": "backend-task-room", "request_id": "request-room", "thread_id": 19},
    }
    attempt_lookup = Mock(side_effect=lambda _db, task_id: attempts.get(task_id))
    monkeypatch.setattr(guardian_api, "chatlog_db", db)
    monkeypatch.setattr(
        "guardian.core.task_event_access.get_chat_completion_attempt_by_task_id",
        attempt_lookup,
    )
    redis_read = Mock(
        return_value=[
            (
                "1-0",
                {
                    "type": "task.completed",
                    "data": {
                        "text": "private generated output",
                        "thread_id": 19,
                        "turn_id": "turn-secret",
                    },
                },
            )
        ]
    )
    monkeypatch.setattr(task_events, "read_events", redis_read)

    from guardian.guardian_api import app

    previous_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[require_task_event_read_principal] = lambda: RequestUserScope(
        user_id="account-a",
        account_id="account-a",
        multi_user_enabled=True,
    )
    client = TestClient(app)
    yield client, db, attempt_lookup, redis_read, attempts
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous_overrides)


def test_owner_can_subscribe_and_existing_sse_payload_is_preserved(task_event_client):
    client, _db, lookup, redis_read, _attempts = task_event_client

    response = client.get(
        "/api/tasks/backend-task-a/events",
        headers={"Last-Event-ID": "5-9"},
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: task.completed" in response.text
    assert "private generated output" in response.text
    assert "turn-secret" in response.text
    lookup.assert_called_once()
    assert lookup.call_args.args[1] == "backend-task-a"
    redis_read.assert_called_once()
    assert redis_read.call_args.args[1] == "5-9"


def test_cross_account_denial_precedes_redis_and_discloses_no_event(task_event_client):
    client, _db, _lookup, redis_read, _attempts = task_event_client
    client.app.dependency_overrides[require_task_event_read_principal] = lambda: RequestUserScope(
        user_id="account-b",
        account_id="account-b",
        multi_user_enabled=True,
    )

    response = client.get(
        "/api/tasks/backend-task-a/events?last_id=8-2",
        headers={"Last-Event-ID": "9-1"},
    )

    assert response.status_code == 403
    assert "private generated output" not in response.text
    assert "turn-secret" not in response.text
    assert "thread_id" not in response.text
    redis_read.assert_not_called()


def test_hosted_room_owner_account_can_read_its_backing_thread_task(
    task_event_client
):
    client, _db, _lookup, redis_read, _attempts = task_event_client
    client.app.dependency_overrides[require_task_event_read_principal] = lambda: RequestUserScope(
        user_id="account-owner",
        account_id="account-owner",
        multi_user_enabled=True,
    )

    response = client.get("/api/tasks/backend-task-room/events")

    assert response.status_code == 200
    assert "private generated output" in response.text
    redis_read.assert_called_once()


@pytest.mark.parametrize("task_id", ["unknown-backend-id", "request-a"])
def test_unknown_or_request_id_path_fails_before_redis(task_event_client, task_id):
    client, _db, lookup, redis_read, _attempts = task_event_client

    response = client.get(f"/api/tasks/{task_id}/events")

    assert response.status_code == 404
    assert "private generated output" not in response.text
    assert lookup.call_args.args[1] == task_id
    redis_read.assert_not_called()


def test_redis_only_task_id_is_not_an_authorized_object(task_event_client):
    client, _db, _lookup, redis_read, _attempts = task_event_client
    # The mocked Redis transport has a secret event available for every key;
    # without the durable mapping, the route must not ask it for that event.

    response = client.get("/api/tasks/redis-only-task/events")

    assert response.status_code == 404
    assert "private generated output" not in response.text
    redis_read.assert_not_called()


@pytest.mark.parametrize("operator_selector", ["cookie", "raw-key"])
def test_account_jwt_mix_is_denied_before_attempt_or_redis(
    task_event_client, monkeypatch, operator_selector
):
    from tests.identity.test_mixed_principal_boundary import (
        API_KEY,
        _assert_mixed,
        _configure_remote,
        _presence_token,
    )

    client, db, lookup, redis_read, _attempts = task_event_client
    _configure_remote(monkeypatch)
    token = _presence_token(b'{"purpose":"account_session","exp":0}', jwt=True)
    headers = {"Authorization": f"Bearer {token}", "X-API-Key": ""}
    cookies = {}
    if operator_selector == "cookie":
        operator, _ = issue_session_token(
            subject="operator", purpose=OPERATOR_SESSION_PURPOSE, ttl_seconds=-60
        )
        cookies["gc_session"] = operator
    else:
        headers["X-API-Key"] = API_KEY
    client.app.dependency_overrides.pop(require_task_event_read_principal)
    response = client.get(
        "/api/tasks/backend-task-a/events", headers=headers, cookies=cookies
    )
    _assert_mixed(response)
    lookup.assert_not_called()
    db.get_chat_thread.assert_not_called()
    redis_read.assert_not_called()


class _RoomSession:
    def __init__(self, *, participant_state: str = "active", room_id: str = "room-a"):
        self.room = SimpleNamespace(
            id="room-a",
            backing_thread_id=19,
            owner_account_id="account-owner",
            status="active",
        )
        self.participant = SimpleNamespace(
            id="guest-a",
            room_id=room_id,
            state=participant_state,
            kind="human",
            role="member",
            invitation_id="invite-a",
        )
        self.invite = SimpleNamespace(id="invite-a", status="accepted", expires_at=None)

    def get(self, model, key):
        records = {
            (HostedRoom, "room-a"): self.room,
            (HostedRoomParticipant, "guest-a"): self.participant,
            (HostedRoomInvite, "invite-a"): self.invite,
        }
        return records.get((model, key))


@pytest.mark.parametrize(
    "auth_mode,supplemental_auth", [("local", False), ("local", True), ("remote", False)]
)
def test_eligible_room_guest_reads_same_room_attempt_without_becoming_owner(
    task_event_client, monkeypatch, auth_mode, supplemental_auth
):
    client, _db, _lookup, redis_read, _attempts = task_event_client
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "inert-task-event-test-secret")
    token, _ = issue_guest_session_token(
        room_id="room-a",
        room_slug="room-a",
        participant_id="guest-a",
        invitation_id="invite-a",
    )
    guest_session = _RoomSession()
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", auth_mode)
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")

    @contextmanager
    def room_db_session():
        yield guest_session

    monkeypatch.setattr(
        "guardian.core.task_event_access.load_guardian_db_from_env",
        lambda: SimpleNamespace(get_session=room_db_session),
    )
    client.app.dependency_overrides.pop(require_task_event_read_principal)

    response = client.get(
        "/api/tasks/backend-task-room/events",
        cookies={"codexify_hosted_room_session": token},
        headers={
            "X-API-Key": "",
            **({"Authorization": "Bearer local-supplemental-material"}
               if supplemental_auth else {}),
        },
    )

    assert response.status_code == 200
    assert "private generated output" in response.text
    assert guest_session.room.owner_account_id == "account-owner"
    assert guest_session.participant.id == "guest-a"
    redis_read.assert_called_once()


def test_inactive_room_guest_is_denied_before_redis(task_event_client, monkeypatch):
    client, _db, _lookup, redis_read, _attempts = task_event_client
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "inert-task-event-test-secret")
    token, _ = issue_guest_session_token(
        room_id="room-a",
        room_slug="room-a",
        participant_id="guest-a",
        invitation_id="invite-a",
    )

    @contextmanager
    def room_db_session():
        yield _RoomSession(participant_state="removed")

    monkeypatch.setattr(
        "guardian.core.task_event_access.load_guardian_db_from_env",
        lambda: SimpleNamespace(get_session=room_db_session),
    )
    client.app.dependency_overrides.pop(require_task_event_read_principal)

    response = client.get(
        "/api/tasks/backend-task-room/events",
        cookies={"codexify_hosted_room_session": token},
    )

    assert response.status_code == 401, response.text
    assert "private generated output" not in response.text
    redis_read.assert_not_called()


def test_wrong_room_guest_and_thread_mismatch_are_denied_before_redis(
    task_event_client, monkeypatch
):
    client, _db, _lookup, redis_read, _attempts = task_event_client
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "inert-task-event-test-secret")

    @contextmanager
    def room_db_session():
        yield _RoomSession()

    monkeypatch.setattr(
        "guardian.core.task_event_access.load_guardian_db_from_env",
        lambda: SimpleNamespace(get_session=room_db_session),
    )
    client.app.dependency_overrides.pop(require_task_event_read_principal)

    wrong_room_token, _ = issue_guest_session_token(
        room_id="room-b",
        room_slug="room-b",
        participant_id="guest-a",
        invitation_id="invite-a",
    )
    wrong_room_response = client.get(
        "/api/tasks/backend-task-room/events",
        cookies={"codexify_hosted_room_session": wrong_room_token},
    )
    assert wrong_room_response.status_code == 401
    redis_read.assert_not_called()

    same_room_token, _ = issue_guest_session_token(
        room_id="room-a",
        room_slug="room-a",
        participant_id="guest-a",
        invitation_id="invite-a",
    )
    wrong_thread_response = client.get(
        "/api/tasks/backend-task-a/events",
        cookies={"codexify_hosted_room_session": same_room_token},
    )
    assert wrong_thread_response.status_code == 401
    assert "private generated output" not in wrong_thread_response.text
    redis_read.assert_not_called()


@pytest.mark.parametrize(
    "credential_kind,expected_status",
    [
        ("anonymous", 401),
        ("invalid_guest", 401),
        ("wrong_purpose_guest", 401),
        ("invalid_account", 401),
        ("operator", 401),
        ("operator_key", 401),
        ("mixed", 400),
    ],
)
def test_remote_auth_rejections_happen_before_attempt_lookup_or_redis(
    task_event_client, monkeypatch, credential_kind, expected_status
):
    client, _db, lookup, redis_read, _attempts = task_event_client
    client.app.dependency_overrides.pop(require_task_event_read_principal)
    monkeypatch.setattr(dependencies, "is_private_preview", lambda: True)
    monkeypatch.setattr(
        dependencies,
        "require_preview_principal",
        lambda _request: SimpleNamespace(email="account-a"),
    )
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "inert-task-event-test-secret")

    headers = {}
    cookies = {}
    if credential_kind == "operator":
        token, _ = issue_session_token(
            subject="operator", purpose=OPERATOR_SESSION_PURPOSE
        )
        headers["Authorization"] = f"Bearer {token}"
    elif credential_kind == "invalid_account":
        headers["Authorization"] = "Bearer invalid-account-token"
    elif credential_kind == "operator_key":
        headers["X-API-Key"] = "test-api-key"
    elif credential_kind == "mixed":
        token, _ = issue_session_token(
            subject="account-a", purpose=ACCOUNT_SESSION_PURPOSE
        )
        headers["Authorization"] = f"Bearer {token}"
        cookies["codexify_hosted_room_session"] = "malformed-guest-token"
    elif credential_kind == "invalid_guest":
        cookies["codexify_hosted_room_session"] = "malformed-guest-token"
    elif credential_kind == "wrong_purpose_guest":
        token, _ = issue_session_token(
            subject="account-a", purpose=ACCOUNT_SESSION_PURPOSE
        )
        cookies["codexify_hosted_room_session"] = token

    if credential_kind != "operator_key":
        headers["X-API-Key"] = ""
    response = client.get(
        "/api/tasks/backend-task-a/events", headers=headers, cookies=cookies
    )

    assert response.status_code == expected_status
    lookup.assert_not_called()
    redis_read.assert_not_called()


@pytest.mark.parametrize(
    "authenticated_account,expected_status",
    [("account-a", 200), ("account-b", 403)],
)
def test_remote_account_principal_cannot_be_overridden_by_user_header(
    task_event_client, monkeypatch, authenticated_account, expected_status
):
    client, _db, lookup, redis_read, _attempts = task_event_client
    client.app.dependency_overrides.pop(require_task_event_read_principal)
    monkeypatch.setattr(dependencies, "is_private_preview", lambda: True)
    monkeypatch.setattr(
        dependencies,
        "require_preview_principal",
        lambda _request: SimpleNamespace(email=authenticated_account),
    )
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "inert-task-event-test-secret")
    token, _ = issue_session_token(
        subject=authenticated_account,
        purpose=ACCOUNT_SESSION_PURPOSE,
    )

    response = client.get(
        "/api/tasks/backend-task-a/events",
        headers={
            "X-API-Key": "",
            "Authorization": f"Bearer {token}",
            "X-User-Id": "account-a",
        },
    )

    assert response.status_code == expected_status
    assert lookup.call_args.args[1] == "backend-task-a"
    if expected_status == 200:
        redis_read.assert_called_once()
    else:
        assert "private generated output" not in response.text
        redis_read.assert_not_called()


def test_durable_authorization_queries_run_outside_the_event_loop(
    task_event_client, monkeypatch
):
    from guardian import guardian_api

    client, _db, _lookup, redis_read, _attempts = task_event_client
    authorize = guardian_api.authorize_task_event_read
    off_loop_checks = []

    def off_loop_authorize(*args, **kwargs):
        with pytest.raises(RuntimeError, match="no running event loop"):
            asyncio.get_running_loop()
        off_loop_checks.append(True)
        return authorize(*args, **kwargs)

    monkeypatch.setattr(guardian_api, "authorize_task_event_read", off_loop_authorize)
    response = client.get("/api/tasks/backend-task-a/events")

    assert response.status_code == 200
    assert off_loop_checks == [True]
    redis_read.assert_called_once()
