"""The chat message write path keeps one transaction and one durable row."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from guardian.core.db import create_chat_message_with_metadata


class _FakeThread:
    def __init__(self, thread_id: int) -> None:
        self.id = thread_id
        self.user_id = "user-a"
        self.updated_at: Any = None
        self.last_interaction_at: Any = None


class _FakeQuery:
    def __init__(self, thread: _FakeThread) -> None:
        self._thread = thread

    def filter_by(self, **_kwargs: Any) -> "_FakeQuery":
        return self

    def one_or_none(self) -> _FakeThread:
        return self._thread


class _FakeSession:
    """A session that records the call order of the write path."""

    def __init__(
        self, thread: _FakeThread, calls: list[str], *, assign_id: bool
    ) -> None:
        self._thread = thread
        self._calls = calls
        self._assign_id = assign_id
        self._message: Any = None

    def query(self, _model: Any) -> _FakeQuery:
        return _FakeQuery(self._thread)

    def add(self, message: Any) -> None:
        self._message = message
        self._calls.append("add")

    def flush(self) -> None:
        self._calls.append("flush")
        if self._assign_id:
            self._message.id = 42

    def rollback(self) -> None:
        self._calls.append("rollback")


class _FakeChatlog:
    def __init__(self, calls: list[str], *, assign_id: bool) -> None:
        self._calls = calls
        self._assign_id = assign_id
        self.thread = _FakeThread(7)

    @contextmanager
    def _sa_session(self) -> Iterator[_FakeSession]:
        yield _FakeSession(self.thread, self._calls, assign_id=self._assign_id)

    def create_message(
        self, thread_id: int, role: str, content: str, *, extra_meta: dict[str, Any]
    ) -> int:
        self._calls.append("create_message")
        return 99


def test_assigned_id_keeps_the_single_transaction() -> None:
    calls: list[str] = []
    chatlog = _FakeChatlog(calls, assign_id=True)

    message_id = create_chat_message_with_metadata(
        chatlog, 7, "assistant", "hello", extra_meta={"kind": "chat"}
    )

    assert message_id == 42
    assert calls == ["add", "flush"]


def test_fallback_write_aborts_the_pending_transaction_first() -> None:
    """A second write must not run beside the transaction it would deadlock."""
    calls: list[str] = []
    chatlog = _FakeChatlog(calls, assign_id=False)

    message_id = create_chat_message_with_metadata(
        chatlog, 7, "assistant", "hello", extra_meta={"kind": "chat"}
    )

    assert message_id == 99
    assert calls == ["add", "flush", "rollback", "create_message"]
