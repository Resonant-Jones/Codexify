from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from guardian.account_observability.schemas import HeartbeatRequest
from guardian.routes import account_observability as routes


def _request(headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/account-observability/heartbeat",
            "headers": headers or [],
        }
    )


def test_guest_subject_comes_only_from_server_issued_cookie() -> None:
    guest_id = str(uuid4())
    assert routes._resolve_subject(
        _request(),
        authorization=None,
        gc_session=None,
        x_api_key=None,
        guest_id_cookie=guest_id,
    ) == (None, guest_id)


def test_invalid_guest_cookie_is_rejected() -> None:
    with pytest.raises(HTTPException) as exc_info:
        routes._resolve_subject(
            _request(),
            authorization=None,
            gc_session=None,
            x_api_key=None,
            guest_id_cookie="client-chosen-id",
        )
    assert exc_info.value.status_code == 401


def test_heartbeat_payload_rejects_analytics_dimensions() -> None:
    with pytest.raises(ValueError):
        HeartbeatRequest.model_validate({"route": "/workspace"})


def test_heartbeat_route_returns_only_bounded_lease_ack(monkeypatch) -> None:
    class _Session:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def commit(self) -> None:
            pass

    class _Database:
        def get_session(self):
            return _Session()

    monkeypatch.setattr(
        routes,
        "_resolve_subject",
        lambda *_args, **_kwargs: ("account-1", None),
    )
    monkeypatch.setattr(routes, "_get_db", lambda: _Database())
    monkeypatch.setattr(
        routes,
        "record_heartbeat",
        lambda *_args, **_kwargs: SimpleNamespace(
            active=True,
            active_window_seconds=300,
            idle_expiry_seconds=1800,
            server_time="2026-07-28T12:00:00Z",
        ),
    )

    response = routes.heartbeat(HeartbeatRequest(), _request())
    assert response.active is True
    assert response.active_window_seconds == 300
    assert response.idle_expiry_seconds == 1800
    assert not hasattr(response, "presence_session_id")
