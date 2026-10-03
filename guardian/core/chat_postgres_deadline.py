"""ADR-087 query bounds for worker-owned PgDB operations.

This scope bounds native connection/query polling and pool waiting, not DNS
resolution or remote commit acknowledgement. It never creates a budget.
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
from psycopg.conninfo import conninfo_to_dict, timeout_from_conninfo
from sqlalchemy.pool import QueuePool
from sqlalchemy.util import queue as pool_queue

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


class AcceptedDeadlineQueue(pool_queue.Queue):
    """Clip each pool borrower without changing the pool's shared timeout."""

    def get(self, block=True, timeout=None):
        budget = _budget.get()
        if budget is None:
            return super().get(block, timeout)
        # SQLAlchemy's queue uses an RLock. Hold it through the post-admission
        # check so an expired borrower can restore the entry before another
        # thread fills the slot. No connection has been checked out yet.
        while not self.mutex.acquire(timeout=budget.remaining()):
            budget.remaining()
        try:
            remaining = budget.remaining()
            clipped = remaining if timeout is None else min(timeout, remaining)
            try:
                item = super().get(block, clipped)
            except pool_queue.Empty:
                budget.remaining()
                raise
            try:
                budget.remaining()
            except (AcceptedChatTaskDeadlineExceeded, ValueError):
                self._put(item)
                self.not_empty.notify()
                raise
            return item
        finally:
            self.mutex.release()


class AcceptedDeadlineQueuePool(QueuePool):
    """Keep normal QueuePool capacity/reset semantics with scoped queue waits."""

    _queue_class = AcceptedDeadlineQueue


class AcceptedDeadlineConnection(psycopg.Connection):
    """Close native query I/O on parent expiry, without background workers."""

    @classmethod
    def _connect_gen(cls, conninfo="", **kwargs):
        # Driver 3.2 passes its timeout into this generator; 3.3 applies it in
        # the outer wait_conn. Retain the driver's policy and final connection
        # setup without copying connect() or changing library-global waiting.
        gen = super()._connect_gen(conninfo, **kwargs)
        budget = _budget.get()
        if budget is None:
            return (yield from gen)
        result = None
        try:
            budget.remaining()
            policy = kwargs.get("timeout")
            if policy is None:
                policy = timeout_from_conninfo(conninfo_to_dict(conninfo))
            policy_end = time.monotonic() + policy if policy > 0 else None
            try:
                with selectors.DefaultSelector() as selector:
                    fd, wanted = next(gen)
                    while True:
                        remaining = budget.remaining()
                        if policy_end is not None:
                            policy_remaining = policy_end - time.monotonic()
                            if policy_remaining <= 0:
                                raise psycopg.errors.ConnectionTimeout(
                                    "connection timeout expired"
                                )
                            remaining = min(remaining, policy_remaining)
                        mask = 0
                        if wanted & waiting.WAIT_R:
                            mask |= selectors.EVENT_READ
                        if wanted & waiting.WAIT_W:
                            mask |= selectors.EVENT_WRITE
                        if not mask:
                            raise RuntimeError(
                                "PostgreSQL connection yielded no I/O interest"
                            )
                        # The native connect generator may replace its socket,
                        # even reusing the same descriptor. Remove registration
                        # before advancing it, as the driver wait_conn does.
                        selector.register(fd, mask)
                        ready = 0
                        try:
                            for _key, events in selector.select(remaining):
                                if events & selectors.EVENT_READ:
                                    ready |= waiting.READY_R
                                if events & selectors.EVENT_WRITE:
                                    ready |= waiting.READY_W
                        finally:
                            selector.unregister(fd)
                        budget.remaining()
                        if policy_end is not None and time.monotonic() >= policy_end:
                            raise psycopg.errors.ConnectionTimeout(
                                "connection timeout expired"
                            )
                        fd, wanted = gen.send(ready)
            except StopIteration as completed:
                result = completed.value
            budget.remaining()
            return result
        except BaseException:
            if result is not None:
                result.close()
            raise
        finally:
            # Closing the suspended native generator releases its partial
            # PGconn/socket. No background connection operation survives.
            gen.close()

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
    connection = AcceptedDeadlineConnection.connect(dsn, **kwargs)
    if budget is not None:
        try:
            budget.remaining()
        except (AcceptedChatTaskDeadlineExceeded, ValueError):
            connection.close()
            raise
    return connection


def accepted_postgres_queries_active() -> bool:
    return _budget.get() is not None
