"""Account-bound readback regression tests; no provider or network calls."""
import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from guardian.routes import command_bus


@pytest.fixture
def readback(monkeypatch):
    store = SimpleNamespace(get_run=Mock(return_value={"run_id": "run-a", "auth_subject": "account-a", "result_json": {"private": "a"}}))
    db = SimpleNamespace(
        get_message=Mock(return_value=SimpleNamespace(thread_id=7, role="assistant", extra_meta={"commandRunId": "run-a"})),
        get_chat_thread=Mock(return_value={"id": 7, "user_id": "account-a"}),
    )
    monkeypatch.setattr(command_bus, "_store", store)
    monkeypatch.setattr(command_bus, "_chat_db", db)
    return store, db


@pytest.mark.parametrize("owner", ["account-b", None, "", "operator"])
def test_run_rejects_foreign_or_missing_owner(readback, owner):
    store, _ = readback
    store.get_run.return_value["auth_subject"] = owner
    with pytest.raises(HTTPException) as exc:
        asyncio.run(command_bus.get_run("run-a", "account-a"))
    assert exc.value.status_code == 403


def test_owner_can_read_run(readback):
    assert asyncio.run(command_bus.get_run("run-a", "account-a"))["result_json"] == {"private": "a"}


@pytest.mark.parametrize("thread", [None, {}, {"user_id": "account-b"}, {"user_id": "operator"}, {"user_id": None}])
def test_observability_checks_thread_before_metadata(readback, thread):
    store, db = readback
    db.get_chat_thread.return_value = thread
    # Neither metadata claims nor message authorship substitutes for thread ownership.
    db.get_message.return_value.extra_meta["account_id"] = "account-a"
    with pytest.raises(HTTPException) as exc:
        asyncio.run(command_bus.get_tool_turn_observability("1", "account-a"))
    assert exc.value.status_code == 403
    store.get_run.assert_not_called()


@pytest.mark.parametrize("owner", ["account-b", "operator", None, ""])
def test_owned_message_cannot_link_foreign_run(readback, owner):
    store, _ = readback
    store.get_run.return_value["auth_subject"] = owner
    with pytest.raises(HTTPException) as exc:
        asyncio.run(command_bus.get_tool_turn_observability("1", "account-a"))
    assert exc.value.status_code == 403


def test_owned_message_and_run_readable(readback):
    result = asyncio.run(command_bus.get_tool_turn_observability("1", "account-a"))
    assert result["command_run_id"] == "run-a"
    readback[1].get_chat_thread.assert_called_once_with(7)


def test_missing_thread_link_fails_closed(readback):
    store, db = readback
    db.get_message.return_value.thread_id = None
    with pytest.raises(HTTPException) as exc:
        asyncio.run(command_bus.get_tool_turn_observability("1", "account-a"))
    assert exc.value.status_code == 403
    db.get_chat_thread.assert_not_called()
    store.get_run.assert_not_called()


def test_missing_run_preserves_owned_message_only(readback):
    readback[0].get_run.return_value = None
    result = asyncio.run(command_bus.get_tool_turn_observability("1", "account-a"))
    assert result["command_run_id"] == "run-a"
    assert result["command_result_summary"] is None
