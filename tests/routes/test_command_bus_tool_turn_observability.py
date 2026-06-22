"""Tests for tool-turn observability readback route."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import command_bus


def _install_fake_loopback(monkeypatch) -> None:
    class _FakeResponse:
        status_code = 200; headers = {"content-type": "application/json"}
        @property
        def text(self) -> str: return '{"ok": true}'
        def json(self) -> dict[str, bool]: return {"ok": True}
    class _FakeAsyncClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, **kw): return _FakeResponse()
    monkeypatch.setenv("GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999")
    monkeypatch.setattr("guardian.command_bus.loopback_http_adapter.httpx.AsyncClient", _FakeAsyncClient)


class _FakeChatDB:
    def __init__(self, messages: dict[int, dict[str, Any]] | None = None):
        self._messages = messages or {}

    def get_message(self, message_id: int) -> Any | None:
        return self._messages.get(message_id)


class _FakeMessage:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def _build_client(monkeypatch) -> tuple[TestClient, _FakeChatDB, Any]:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "1")
    command_bus.configure_db(None)
    _install_fake_loopback(monkeypatch)

    chat_db = _FakeChatDB()
    monkeypatch.setattr(command_bus, "_chat_db", chat_db)

    app = FastAPI()
    @app.get("/health", operation_id="health_check")
    def health(): return {"ok": True}
    app.include_router(command_bus.router)
    return TestClient(app), chat_db, command_bus._store


def _make_assistant_msg(msg_id: int, extra_meta: dict[str, Any] | None = None) -> _FakeMessage:
    return _FakeMessage(id=msg_id, role="assistant", extra_meta=extra_meta or {})


def _tool_turn_meta(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    base = {
        "messageId": "msg-1",
        "requestId": "req-1",
        "toolTurnId": "tt-1",
        "toolTurnState": "completed",
        "loopStopReason": "tool_turn_completed",
        "commandRunId": "run-1",
    }
    if overrides:
        base.update(overrides)
    return base


class TestToolTurnObservabilityRoute:
    def test_missing_message_returns_404(self, monkeypatch) -> None:
        client, chat_db, store = _build_client(monkeypatch)
        resp = client.get("/api/guardian/commands/tool-turns/99999/observability", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 404

    def test_non_assistant_returns_400(self, monkeypatch) -> None:
        client, chat_db, store = _build_client(monkeypatch)
        chat_db._messages[1] = _FakeMessage(id=1, role="user", extra_meta={})
        resp = client.get("/api/guardian/commands/tool-turns/1/observability", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 400

    def test_no_tool_turn_metadata_returns_safe_null_model(self, monkeypatch) -> None:
        client, chat_db, store = _build_client(monkeypatch)
        chat_db._messages[1] = _make_assistant_msg(1, {})
        resp = client.get("/api/guardian/commands/tool-turns/1/observability", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["tool_turn_id"] is None
        assert body["command_run_id"] is None
        assert body["evidence_durability"] == "unknown"

    def test_returns_tool_turn_metadata_from_extra_meta(self, monkeypatch) -> None:
        client, chat_db, store = _build_client(monkeypatch)
        chat_db._messages[1] = _make_assistant_msg(1, _tool_turn_meta())
        resp = client.get("/api/guardian/commands/tool-turns/1/observability", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["tool_turn_id"] == "tt-1"
        assert body["tool_turn_state"] == "completed"
        assert body["loop_stop_reason"] == "tool_turn_completed"
        assert body["command_run_id"] == "run-1"

    def test_enriches_from_command_run(self, monkeypatch) -> None:
        client, chat_db, store = _build_client(monkeypatch)
        chat_db._messages[1] = _make_assistant_msg(1, _tool_turn_meta())
        store._mem_runs["run-1"] = {
            "run_id": "run-1",
            "command_id": "op::health_health_get",
            "status": "completed",
            "result_json": {"body": {"status": "ok"}},
            "error_text": None,
            "created_at": "2026-01-01T00:00:00Z",
        }
        resp = client.get("/api/guardian/commands/tool-turns/1/observability", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["command_id"] == "op::health_health_get"
        assert body["command_status"] == "completed"
        assert body["command_result_summary"] == "ok"

    def test_missing_command_run_still_returns_metadata(self, monkeypatch) -> None:
        client, chat_db, store = _build_client(monkeypatch)
        chat_db._messages[1] = _make_assistant_msg(1, _tool_turn_meta({"commandRunId": "run-missing"}))
        resp = client.get("/api/guardian/commands/tool-turns/1/observability", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["tool_turn_id"] == "tt-1"
        assert body["command_run_id"] == "run-missing"

    def test_does_not_expose_raw_result_json(self, monkeypatch) -> None:
        client, chat_db, store = _build_client(monkeypatch)
        chat_db._messages[1] = _make_assistant_msg(1, _tool_turn_meta())
        store._mem_runs["run-1"] = {
            "run_id": "run-1",
            "result_json": {"body": {"raw_args": "SECRET", "password": "hunter2"}},
        }
        resp = client.get("/api/guardian/commands/tool-turns/1/observability", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        body = resp.json()
        summary = str(body.get("command_result_summary", "")).lower()
        assert "secret" not in summary
        assert "hunter2" not in summary
        # redaction_summary may contain "raw_args_rendered" as a key — that's safe metadata
        assert body["redaction_summary"]["raw_args_rendered"] is False

    def test_response_includes_redaction_summary(self, monkeypatch) -> None:
        client, chat_db, store = _build_client(monkeypatch)
        chat_db._messages[1] = _make_assistant_msg(1, _tool_turn_meta())
        resp = client.get("/api/guardian/commands/tool-turns/1/observability", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        body = resp.json()
        rs = body.get("redaction_summary", {})
        assert rs["raw_args_rendered"] is False
        assert rs["secrets_rendered"] is False
