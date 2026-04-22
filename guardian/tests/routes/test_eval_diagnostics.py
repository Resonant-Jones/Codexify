from __future__ import annotations

import pytest
from fastapi import HTTPException

from guardian.core.dependencies import RequestUserScope
from guardian.routes import chat as chat_routes


class _StubChatlogDB:
    def __init__(self, thread: dict[str, object]):
        self._thread = thread

    def get_chat_thread(self, thread_id: int):
        thread_id_value = self._thread.get("id")
        if isinstance(thread_id_value, int) and thread_id_value == thread_id:
            return dict(self._thread)
        return None


def test_eval_diagnostics_route_is_thread_scoped(monkeypatch) -> None:
    captured: dict[str, int] = {}

    def _fake_get_latest_eval_diagnostics(_db, *, thread_id: int):
        captured["thread_id"] = thread_id
        return {
            "thread_id": thread_id,
            "trace_snapshot": {"trace_snapshot_id": "snapshot-7"},
            "verdicts": [],
        }

    monkeypatch.setattr(
        chat_routes,
        "chatlog_db",
        _StubChatlogDB({"id": 7, "user_id": "local"}),
    )
    monkeypatch.setattr(
        chat_routes,
        "get_latest_eval_diagnostics",
        _fake_get_latest_eval_diagnostics,
    )

    scope = RequestUserScope(
        user_id="local",
        account_id="local",
        multi_user_enabled=True,
    )
    result = chat_routes.get_latest_eval_diagnostics_route(
        7,
        request_user_scope=scope,
    )
    assert result["thread_id"] == 7
    assert captured["thread_id"] == 7

    with pytest.raises(HTTPException) as exc_info:
        chat_routes.get_latest_eval_diagnostics_route(
            7,
            request_user_scope=RequestUserScope(
                user_id="other",
                account_id="other",
                multi_user_enabled=True,
            ),
        )
    assert exc_info.value.status_code == 403
