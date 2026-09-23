"""The runtime context window selects the newest rows, then restores chronology."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import MethodType

import pytest

from guardian.context.broker import ContextBroker
from guardian.core import chat_completion_service
from guardian.core.pgdb import PgDB
from guardian.tasks.types import ChatCompletionTask
from tests.core.test_chat_completion_service_latest_turn_regression import (
    _seed_completion_service,
)


class _Cursor:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.selected: list[dict[str, object]] = []

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | list[object]) -> None:
        assert "FROM chat_messages" in query
        assert params[0] == 1
        newest_first = "ORDER BY created_at DESC, id DESC" in query
        oldest_first = "ORDER BY created_at ASC, id ASC" in query
        assert newest_first or oldest_first
        ordered = sorted(
            self.rows,
            key=lambda row: (row["created_at"], row["id"]),
            reverse=newest_first,
        )
        limit = int(params[1] if newest_first else params[-2])
        offset = 0 if newest_first else int(params[-1])
        self.selected = ordered[offset : offset + limit]

    def fetchall(self) -> list[dict[str, object]]:
        return self.selected


class _Connection:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def cursor(self) -> _Cursor:
        return _Cursor(self.rows)


def _chatlog(message_count: int) -> PgDB:
    # Exercise PgDB's actual SQL construction and row-order normalization.
    # The cursor evaluates that SQL's ordering and limit against seeded rows.
    start = datetime(2026, 9, 23)
    rows: list[dict[str, object]] = [
        {
            "id": message_id,
            "thread_id": 1,
            "role": "user" if message_id % 2 else "assistant",
            "content": f"message {message_id}",
            # Adjacent rows tie on timestamp; id must break the tie.
            "created_at": start + timedelta(seconds=message_id // 2),
        }
        for message_id in range(1, message_count + 1)
    ]
    db = object.__new__(PgDB)
    db._connect = lambda: _Connection(rows)
    db.get_chat_thread = MethodType(
        lambda _self, _thread_id: {"id": 1, "user_id": "user-1", "project_id": 42},
        db,
    )
    return db


@pytest.mark.parametrize(
    ("message_count", "expected_first"),
    [(10, 1), (50, 1), (55, 6)],
)
def test_postgres_recent_window_is_newest_and_chronological(
    message_count: int, expected_first: int
) -> None:
    db = _chatlog(message_count)
    assert [row["id"] for row in db.recent_messages(1, limit=50)] == list(
        range(expected_first, message_count + 1)
    )
    # Transcript pagination keeps its existing oldest-first contract.
    assert [row["id"] for row in db.list_messages(1, limit=3, offset=0)] == [
        1,
        2,
        3,
    ]


@pytest.mark.asyncio
async def test_completion_keeps_latest_target_and_excludes_oldest_overflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_completion_service(monkeypatch, messages=[])
    monkeypatch.setattr(chat_completion_service.dependencies, "chatlog_db", _chatlog(55))
    task = ChatCompletionTask(
        user_id="user-1",
        thread_id=1,
        provider="local",
        latest_turn_message_id=55,
        max_context=50,
    )

    messages, _, _, bundle, _ = await chat_completion_service.build_messages_for_llm(
        task
    )

    assert bundle["_completion_assembly"]["latest_turn"]["id"] == 55
    assert [item["id"] for item in bundle["_completion_assembly"]["history"]] == list(
        range(6, 55)
    )
    assert [item["content"] for item in messages[-50:]] == [
        f"message {message_id}" for message_id in range(6, 56)
    ]
    assert [item["content"] for item in messages if item["role"] == "user"] == [
        f"message {message_id}" for message_id in range(7, 56, 2)
    ]
    assert captured["query"] == "message 55"


@pytest.mark.asyncio
async def test_context_broker_uses_newest_six_in_chronological_order() -> None:
    broker = ContextBroker(chatlog_db=_chatlog(10), vector_store=None)
    assert [row["id"] for row in await broker._fetch_messages(1, 6, user_id="user-1")] == [
        5,
        6,
        7,
        8,
        9,
        10,
    ]
