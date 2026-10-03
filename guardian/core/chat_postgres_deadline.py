"""ADR-087 query bounds for worker-owned PgDB operations.

This scope bounds native query polling, not DNS, connection establishment,
pool admission, or remote commit acknowledgement. It never creates a budget.
"""

from __future__ import annotations

import math
import selectors
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg
from psycopg import waiting

from guardian.tasks.chat_deadline import (
    AcceptedChatTaskDeadline,
    AcceptedChatTaskDeadlineExceeded,
)


@dataclass
class _QueryBudget:
    work_end: float
    terminal_end: float
    terminal: bool = False
    invalid: bool = False

    def remaining(self) -> float:
        if self.invalid:
            raise ValueError("accepted chat deadline snapshot is invalid")
        remaining = (
            self.terminal_end if self.terminal else self.work_end
        ) - time.monotonic()
        if remaining <= 0:
            error = AcceptedChatTaskDeadlineExceeded()
            if self.terminal:
                error.detail["message"] = (
                    "Accepted chat task terminal deadline exceeded."
                )
            raise error
        return remaining


_budget: ContextVar[_QueryBudget | None] = ContextVar(
    "chat_postgres_query_budget", default=None
)


@contextmanager
def accepted_postgres_query_scope(
    deadline: AcceptedChatTaskDeadline | None,
    *,
    now: datetime | None = None,
    monotonic_at_wall: float | None = None,
    invalid: bool = False,
):
    """Anchor both frozen timestamps once; child progress cannot refresh them."""
    value = None
    if deadline is not None:
        clock = time.monotonic() if monotonic_at_wall is None else monotonic_at_wall
        wall = now or datetime.now(timezone.utc)
        work = (deadline.work_deadline_at - wall).total_seconds()
        terminal = (deadline.terminal_deadline_at - wall).total_seconds()
        value = _QueryBudget(clock + work, clock + terminal, terminal=work <= 0)
    elif invalid:
        value = _QueryBudget(0, 0, invalid=True)
    token = _budget.set(value)
    try:
        yield
    finally:
        _budget.reset(token)


def use_postgres_terminal_budget() -> None:
    """Permit only terminal database work inside the original reserve."""
    value = _budget.get()
    if value is not None:
        value.terminal = True


class AcceptedDeadlineConnection(psycopg.Connection):
    """Close native query I/O on parent expiry, without background workers."""

    def wait(self, gen, interval=0.1):
        budget = _budget.get()
        if budget is None:
            return super().wait(gen, interval=interval)
        try:
            budget.remaining()
            try:
                with selectors.DefaultSelector() as selector:
                    wanted = next(gen)
                    while True:
                        mask = 0
                        if wanted & waiting.WAIT_R:
                            mask |= selectors.EVENT_READ
                        if wanted & waiting.WAIT_W:
                            mask |= selectors.EVENT_WRITE
                        if not mask:
                            raise RuntimeError(
                                "PostgreSQL query yielded no I/O interest"
                            )
                        if selector.get_map():
                            selector.modify(self.pgconn.socket, mask)
                        else:
                            selector.register(self.pgconn.socket, mask)
                        ready = 0
                        for _key, events in selector.select(budget.remaining()):
                            if events & selectors.EVENT_READ:
                                ready |= waiting.READY_R
                            if events & selectors.EVENT_WRITE:
                                ready |= waiting.READY_W
                        budget.remaining()
                        wanted = gen.send(ready)
            except StopIteration as completed:
                result = completed.value
            budget.remaining()
            return result
        except (AcceptedChatTaskDeadlineExceeded, ValueError):
            # PQfinish closes the socket. No five-second interrupt/cancel wait,
            # abandoned execution thread, or subsequent rollback can outlive it.
            self.close()
            gen.close()
            raise


class AcceptedDeadlineCursor(psycopg.Cursor):
    def _set_query_limits(self):
        budget = _budget.get()
        if budget is None:
            return None
        milliseconds = math.floor(budget.remaining() * 1000)
        if milliseconds < 1:
            # PostgreSQL's zero timeout means unbounded. Admit no statement
            # during the final fractional millisecond; classify only real expiry.
            while True:
                time.sleep(budget.remaining())
        if self.connection.autocommit:
            raise RuntimeError(
                "Accepted chat PostgreSQL queries require transaction-local limits"
            )
        # Use the base cursor to avoid recursive policy application. Preserve
        # stricter server/transaction limits; LOCAL prevents pooled-session leaks.
        with psycopg.Cursor(self.connection) as policy:
            policy.execute(
                """SELECT set_config(name,
                    LEAST(COALESCE(NULLIF(setting::bigint, 0), %s), %s)::text,
                    true)
                FROM pg_settings
                WHERE name IN ('statement_timeout', 'lock_timeout')""",
                (milliseconds, milliseconds),
                prepare=False,
            )
        budget.remaining()
        return budget

    def _deadline_after_server_timeout(self, budget):
        # PostgreSQL limits use integral milliseconds. If its deadline-clipped
        # limit arrives just before the parent, wait at most two milliseconds
        # for the actual parent expiry before assigning the canonical error.
        if budget is not None and budget.remaining() <= 0.002:
            while True:
                time.sleep(budget.remaining())

    def execute(self, query, params=None, *, prepare=None, binary=None):
        budget = self._set_query_limits()
        try:
            return super().execute(query, params, prepare=prepare, binary=binary)
        except (psycopg.errors.QueryCanceled, psycopg.errors.LockNotAvailable):
            self._deadline_after_server_timeout(budget)
            raise

    def executemany(self, query, params_seq, *, returning=False):
        budget = self._set_query_limits()
        try:
            return super().executemany(query, params_seq, returning=returning)
        except (psycopg.errors.QueryCanceled, psycopg.errors.LockNotAvailable):
            self._deadline_after_server_timeout(budget)
            raise


def connect_with_query_bounds(dsn: str, **kwargs):
    """Always use this class for ORM pools, including pre-existing connections."""
    budget = _budget.get()
    if budget is not None:
        budget.remaining()
    kwargs.setdefault("cursor_factory", AcceptedDeadlineCursor)
    return AcceptedDeadlineConnection.connect(dsn, **kwargs)


def accepted_postgres_queries_active() -> bool:
    return _budget.get() is not None
