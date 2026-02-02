from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest

from guardian.core import event_bus
from guardian.graph import capability_index as ci
from prompts import get_guardian_system_prompt


@pytest.fixture(autouse=True)
def _reset_capability_state():
    event_bus.reset()
    ci.reset_capability_event_cache()


@dataclass
class _StubPlugin:
    name: str
    metadata: dict[str, Any]
    enabled: bool = True


class _StubPluginLoader:
    def __init__(self, plugins: list[_StubPlugin] | None = None) -> None:
        self.plugins = {p.name: p for p in (plugins or [])}


class _StubConnectorStore:
    def __init__(self, configs: list[dict[str, Any]] | None = None) -> None:
        self._configs = configs or []

    def list_connector_configs(self):
        return list(self._configs)


def test_capability_index_collects_active_items():
    plugins = _StubPluginLoader(
        [
            _StubPlugin(
                name="hello_world",
                metadata={
                    "name": "hello_world",
                    "description": "Hello World Plugin",
                    "version": "1.0.0",
                    "capabilities": ["hello"],
                    "help_triggers": ["hello"],
                },
            )
        ]
    )
    connectors = _StubConnectorStore(
        [
            {
                "id": 1,
                "name": "github",
                "type": "github",
                "created_at": "2026-01-14T06:12:02Z",
            }
        ]
    )

    ci.record_capability_event(
        "plugin.installed",
        name="hello_world",
        display_name="Hello World Plugin",
        version="1.0.0",
        capabilities=["hello"],
        help_triggers=["hello"],
    )
    ci.record_capability_event(
        "connector.installed",
        name="github",
        display_name="GitHub",
        timestamp="2026-01-14T06:12:02Z",
        capabilities=["github"],
    )
    ci.record_capability_event(
        "mcp.installed",
        name="filesystem",
        display_name="Filesystem MCP",
        capabilities=["fs"],
    )

    index = ci.get_capability_index(
        plugin_loader=plugins,
        connector_source=connectors,
        core_capabilities=[{"id": "chat"}],
    )

    assert any(item["id"] == "hello_world" for item in index["plugins"])
    assert any(item["id"] == "github" for item in index["connectors"])
    assert any(item["id"] == "filesystem" for item in index["mcps"])
    assert index["core"] == [{"id": "chat"}]


def test_removed_items_are_not_active():
    ci.record_capability_event(
        "plugin.installed", name="temp_plugin", timestamp="2026-01-14T01:00:00Z"
    )
    ci.record_capability_event(
        "plugin.removed", name="temp_plugin", timestamp="2026-01-14T02:00:00Z"
    )

    index = ci.get_capability_index(core_capabilities=[])
    assert all(item["id"] != "temp_plugin" for item in index["plugins"])

    history = ci.query_capability_events("temp_plugin")
    assert history[-1]["payload"]["removed_at"] == "2026-01-14T02:00:00Z"


def test_history_is_iso_sorted():
    ci.record_capability_event(
        "connector.installed",
        name="hist_test",
        timestamp="2026-01-01T00:00:00Z",
    )
    ci.record_capability_event(
        "connector.removed",
        name="hist_test",
        timestamp="2026-01-02T00:00:00Z",
    )

    events = ci.query_capability_events("hist_test")
    timeline = [
        ev["payload"].get("installed_at") or ev["payload"].get("removed_at")
        for ev in events
    ]
    assert timeline == ["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"]
    assert all("T" in ts and ts.endswith("Z") for ts in timeline)


def test_prompt_includes_capabilities_only_when_provided():
    base_prompt = get_guardian_system_prompt("user-1", "normal")
    assert "Capability Index (installed" not in base_prompt

    capability_index = {
        "core": [{"id": "chat", "triggers": ["chat"], "help": "Chat freely"}],
        "plugins": [{"id": "hello_world", "triggers": ["hello"]}],
        "connectors": [],
        "mcps": [],
    }
    prompt_with_index = get_guardian_system_prompt(
        "user-1", "normal", capability_index=capability_index
    )
    assert "Capability Index (installed" in prompt_with_index
    assert "hello_world" in prompt_with_index
