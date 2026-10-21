"""P1 regression: chat workers must dispatch through a durable Command Bus store.

Chat runs in its own process in the supported Compose topology, and only
`guardian_api` calls `command_bus_routes.configure_db`. Without the worker
doing the same, the store stays the in-memory module default: after a restart
or task redelivery the frozen tool-decision checkpoint is still durable, but
the matching CommandRun is gone, so the retry would mint a fresh run and
execute the command a second time.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from guardian.command_bus.store import CommandBusStore
from guardian.routes import command_bus as command_bus_routes
from guardian.workers import chat_worker


def test_worker_configures_durable_command_bus_store(monkeypatch: pytest.MonkeyPatch):
    sentinel = object()
    configured: list[object] = []

    monkeypatch.setattr(
        chat_worker, "load_guardian_db_from_env", lambda: sentinel
    )
    monkeypatch.setattr(
        command_bus_routes, "configure_db", lambda db: configured.append(db)
    )

    chat_worker._configure_durable_command_bus_store()

    assert configured == [sentinel]


def test_worker_refuses_to_start_without_a_durable_store(
    monkeypatch: pytest.MonkeyPatch,
):
    """Fail closed rather than silently dispatching through an in-memory store."""

    monkeypatch.setattr(chat_worker, "load_guardian_db_from_env", lambda: None)

    with pytest.raises(RuntimeError, match="durable_command_bus_store_unavailable"):
        chat_worker._configure_durable_command_bus_store()


def test_initialize_worker_wires_the_store_before_use(
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list[str] = []

    class _Db:
        pass

    db = _Db()
    monkeypatch.setattr(
        chat_worker.dependencies, "init_database", lambda: db
    )
    monkeypatch.setattr(
        chat_worker.dependencies, "init_services", lambda _db: calls.append("services")
    )
    monkeypatch.setattr(
        chat_worker,
        "_configure_durable_command_bus_store",
        lambda: calls.append("command_bus"),
    )
    monkeypatch.setattr(chat_worker, "_publish_worker_heartbeat", lambda *_a: None)
    monkeypatch.setattr(chat_worker.dependencies, "ENABLE_OUTBOX", False)

    chat_worker._initialize_worker()

    assert calls.index("command_bus") > calls.index("services")


def test_module_default_store_is_in_memory_until_configured():
    """Document why the worker must call configure_db explicitly."""

    assert isinstance(command_bus_routes._store, CommandBusStore)