from datetime import datetime, timezone

from guardian.core import pgdb


class _FakeThreadCursor:
    def __init__(self, rows):
        self.rows = rows
        self.itersize = 0
        self.executed = []

    def execute(self, query, params):
        self.executed.append((query, params))

    def __iter__(self):
        return iter(self.rows)

    def close(self):
        return None


class _FakeMessageCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params):
        self.executed.append((query, params))

    def fetchall(self):
        return list(self.rows)


class _FakeConnection:
    def __init__(self, thread_rows, message_rows):
        self.thread_cursor = _FakeThreadCursor(thread_rows)
        self.message_cursor = _FakeMessageCursor(message_rows)
        self.closed = False
        self.rolled_back = False

    def cursor(self, name=None):
        if name is None:
            return self.message_cursor
        return self.thread_cursor

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_fetch_imported_chatgpt_threads_for_user_normalizes_rows(monkeypatch):
    now = datetime.now(timezone.utc)
    fake_conn = _FakeConnection(
        thread_rows=[
            {
                "id": 12,
                "user_id": "u1",
                "title": "Imported",
                "summary": "",
                "project_id": 9,
                "parent_id": None,
                "archived_at": None,
                "metadata": '{"import_source":"chatgpt","source_thread_id":"abc"}',
                "created_at": now,
                "updated_at": now,
                "project_name": "Imports",
            }
        ],
        message_rows=[],
    )

    monkeypatch.setattr(pgdb, "_resolve_dsn", lambda: "postgresql://test")
    monkeypatch.setattr(pgdb.psycopg, "connect", lambda *a, **k: fake_conn)

    rows = list(
        pgdb.fetch_imported_chatgpt_threads_for_user(
            "u1",
            project_id=9,
        )
    )

    assert len(rows) == 1
    assert rows[0]["id"] == 12
    assert rows[0]["project_name"] == "Imports"
    assert rows[0]["metadata"]["import_source"] == "chatgpt"

    executed = fake_conn.thread_cursor.executed
    assert executed
    assert executed[0][1][0] == "u1"
    assert executed[0][1][1] == 9


def test_fetch_imported_chatgpt_messages_for_thread_normalizes_rows(
    monkeypatch,
):
    now = datetime.now(timezone.utc)
    fake_conn = _FakeConnection(
        thread_rows=[],
        message_rows=[
            {
                "id": 100,
                "thread_id": 12,
                "role": "user",
                "content": "Hello",
                "kind": "chat",
                "event_at": now,
                "created_at": now,
                "extra_meta": '{"source_thread_id":"abc","source_message_id":"m1"}',
            }
        ],
    )

    monkeypatch.setattr(pgdb, "_resolve_dsn", lambda: "postgresql://test")
    monkeypatch.setattr(pgdb.psycopg, "connect", lambda *a, **k: fake_conn)

    rows = pgdb.fetch_imported_chatgpt_messages_for_thread(12)

    assert len(rows) == 1
    assert rows[0]["id"] == 100
    assert rows[0]["extra_meta"]["source_message_id"] == "m1"
    assert isinstance(rows[0]["event_at"], str)

    executed = fake_conn.message_cursor.executed
    assert executed
    assert executed[0][1] == (12,)
