from __future__ import annotations

from copy import deepcopy

from guardian.core import pgdb


class _FakeCursor:
    def __init__(self, executed: list[tuple[str, object | None]]) -> None:
        self.executed = executed

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        return []


class _FakeTransaction:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def __init__(self, snapshot: dict[str, list[dict[str, object]]]) -> None:
        self.snapshot = deepcopy(snapshot)
        self.executed: list[tuple[str, object | None]] = []
        self.transaction_entered = False
        self.closed = False

    def cursor(self):
        return _FakeCursor(self.executed)

    def transaction(self):
        self.transaction_entered = True
        return _FakeTransaction()

    def close(self):
        self.closed = True


def test_iter_account_export_payloads_for_user_uses_one_snapshot(
    monkeypatch,
):
    live_rows = {
        "chat_threads": [
            {"id": 1, "title": "Thread A"},
        ],
        "chat_messages": [
            {"id": 10, "thread_id": 1, "content": "before"},
        ],
    }
    connections: list[_FakeConnection] = []

    def fake_connect(*args, **kwargs):
        _ = args, kwargs
        conn = _FakeConnection(live_rows)
        connections.append(conn)
        return conn

    def _reader(key: str):
        def _read(user_id: str, *, conn=None):
            assert user_id == "user-123"
            assert conn is connections[0]
            return list(conn.snapshot[key])

        return _read

    monkeypatch.setattr(pgdb, "_resolve_dsn", lambda: "postgresql://test")
    monkeypatch.setattr(pgdb.psycopg, "connect", fake_connect)
    monkeypatch.setattr(
        pgdb,
        "PAYLOAD_ORDER",
        (
            (
                "chat_threads",
                "entities/chat_threads.json",
                "fetch_account_export_chat_threads_for_user",
            ),
            (
                "chat_messages",
                "entities/chat_messages.json",
                "fetch_account_export_chat_messages_for_user",
            ),
        ),
    )
    monkeypatch.setattr(
        pgdb,
        "fetch_account_export_chat_threads_for_user",
        _reader("chat_threads"),
    )
    monkeypatch.setattr(
        pgdb,
        "fetch_account_export_chat_messages_for_user",
        _reader("chat_messages"),
    )

    iterator = pgdb.iter_account_export_payloads_for_user("user-123")
    first_family, first_path, first_rows = next(iterator)

    assert first_family == "chat_threads"
    assert first_path == "entities/chat_threads.json"
    assert first_rows == [{"id": 1, "title": "Thread A"}]

    live_rows["chat_threads"].append({"id": 2, "title": "Thread B"})
    live_rows["chat_messages"].append(
        {"id": 11, "thread_id": 2, "content": "after"}
    )

    remaining = list(iterator)

    assert remaining == [
        (
            "chat_messages",
            "entities/chat_messages.json",
            [{"id": 10, "thread_id": 1, "content": "before"}],
        )
    ]

    assert len(connections) == 1
    assert connections[0].transaction_entered is True
    assert connections[0].closed is True
    assert connections[0].executed[0][0] == (
        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
    )
