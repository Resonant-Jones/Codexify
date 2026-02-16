from __future__ import annotations

from typing import Any

from guardian.core import event_bus
from guardian.core.outbox import (
    normalize_outbox_tenant_id,
    parse_last_event_id,
    parse_outbox_batch_size,
    parse_outbox_poll_interval,
)


class _TenantAwareStore:
    def __init__(self, events: list[dict[str, Any]]) -> None:
        self.events = events
        self.calls: list[tuple[int, int, str | None]] = []

    def ensure_event_outbox(self) -> None:
        return None

    def list_events_after(
        self,
        last_id: int,
        limit: int = 100,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append((last_id, limit, tenant_id))
        rows = [event for event in self.events if int(event["id"]) > last_id]
        if tenant_id is not None:
            rows = [
                event for event in rows if event.get("tenant_id") == tenant_id
            ]
        return rows[:limit]


class _LegacyStore:
    def __init__(self, events: list[dict[str, Any]]) -> None:
        self.events = events
        self.calls: list[tuple[int, int]] = []

    def ensure_event_outbox(self) -> None:
        return None

    def list_events_after(
        self,
        last_id: int,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        self.calls.append((last_id, limit))
        rows = [event for event in self.events if int(event["id"]) > last_id]
        return rows[:limit]


class _AppendCaptureStore:
    def __init__(self) -> None:
        self.append_calls: list[tuple[str, dict[str, Any], str]] = []

    def ensure_event_outbox(self) -> None:
        return None

    def append_event(
        self,
        topic: str,
        payload: dict[str, Any],
        tenant_id: str = "default",
    ) -> None:
        self.append_calls.append((topic, payload, tenant_id))


def test_parse_outbox_poll_interval_bounds_and_defaults() -> None:
    assert parse_outbox_poll_interval(None) == 1.0
    assert parse_outbox_poll_interval("not-a-number") == 1.0
    assert parse_outbox_poll_interval("0") == 0.1
    assert parse_outbox_poll_interval("999") == 30.0


def test_parse_outbox_batch_size_bounds_and_defaults() -> None:
    assert parse_outbox_batch_size(None) == 100
    assert parse_outbox_batch_size("bad") == 100
    assert parse_outbox_batch_size("0") == 1
    assert parse_outbox_batch_size("99999") == 1000


def test_parse_last_event_id_prefers_header_and_non_negative() -> None:
    assert parse_last_event_id("17", 0) == 17
    assert parse_last_event_id(None, 12) == 12
    assert parse_last_event_id("-5", 99) == 0
    assert parse_last_event_id("bad", 99) == 0


def test_normalize_outbox_tenant_id_uses_default_on_empty() -> None:
    assert normalize_outbox_tenant_id("", default="tenant-x") == "tenant-x"
    assert normalize_outbox_tenant_id("  a  ") == "a"


def test_fetch_events_after_uses_tenant_aware_store_signature() -> None:
    store = _TenantAwareStore(
        [
            {"id": 1, "tenant_id": "default", "topic": "a"},
            {"id": 2, "tenant_id": "other", "topic": "b"},
        ]
    )

    event_bus.reset()
    event_bus.configure_event_store(store)
    try:
        events = event_bus.fetch_events_after(0, tenant_id="default")
    finally:
        event_bus.reset()

    assert [event["id"] for event in events] == [1]
    assert store.calls == [(0, 100, "default")]


def test_fetch_events_after_filters_tenant_for_legacy_store() -> None:
    store = _LegacyStore(
        [
            {"id": 1, "tenant_id": "default", "topic": "a"},
            {"id": 2, "tenant_id": "other", "topic": "b"},
            {"id": 3, "topic": "c"},
        ]
    )

    event_bus.reset()
    event_bus.configure_event_store(store)
    try:
        events = event_bus.fetch_events_after(0, tenant_id="default")
    finally:
        event_bus.reset()

    # Missing tenant_id values are treated as default in compatibility mode.
    assert [event["id"] for event in events] == [1, 3]
    assert store.calls == [(0, 100)]


def test_emit_event_normalizes_blank_tenant_id() -> None:
    store = _AppendCaptureStore()

    event_bus.reset()
    event_bus.configure_event_store(store)
    try:
        event_bus.emit_event("test.event", {"ok": True}, tenant_id="  ")
    finally:
        event_bus.reset()

    assert store.append_calls
    assert store.append_calls[0][2] == "default"
