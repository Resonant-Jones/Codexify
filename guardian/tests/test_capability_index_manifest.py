from __future__ import annotations

from guardian.core import event_bus
from guardian.core import plugins as core_plugins
from guardian.graph import capability_index as ci
from guardian.plugins.plugin_manifest import PluginManifest


def _manifest(
    plugin_id: str = "tts_service",
    *,
    capabilities=None,
) -> PluginManifest:
    return PluginManifest(
        schema_version="1.0",
        id=plugin_id,
        name="TTS Service",
        version="1.0.0",
        base_url="https://tts.example",
        capabilities=capabilities
        or [{"id": "tts", "actions": ["speak", "voices"]}],
    )


def test_capability_index_reads_validated_manifest_plugins(monkeypatch):
    event_bus.reset()
    ci.reset_capability_event_cache()
    manifest = _manifest()
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )

    index = ci.get_capability_index(core_capabilities=[])

    assert len(index["plugins"]) == 1
    plugin = index["plugins"][0]
    assert plugin["id"] == "tts_service"
    assert plugin["display_name"] == "TTS Service"
    assert plugin["version"] == "1.0.0"
    assert plugin["capabilities"] == ["tts.speak", "tts.voices"]
    assert plugin["help_triggers"] == ["tts"]
    assert plugin["help_text_ref"] is None
    assert "installed_at" in plugin


def test_capability_index_ignores_legacy_runtime_plugin_loader(monkeypatch):
    event_bus.reset()
    ci.reset_capability_event_cache()
    monkeypatch.setattr(core_plugins, "list_plugin_manifests", lambda: [])

    class LegacyLoader:
        plugins = {
            "legacy_tts": type(
                "LegacyPlugin",
                (),
                {
                    "name": "legacy_tts",
                    "enabled": True,
                    "metadata": {"capabilities": ["tts"]},
                },
            )()
        }

    index = ci.get_capability_index(
        plugin_loader=LegacyLoader(),
        core_capabilities=[],
    )

    assert index["plugins"] == []


def test_capability_index_allows_explicit_manifest_source_override():
    event_bus.reset()
    ci.reset_capability_event_cache()
    index = ci.get_capability_index(
        plugin_loader=[_manifest("override_tts")],
        core_capabilities=[],
    )

    assert len(index["plugins"]) == 1
    assert index["plugins"][0]["id"] == "override_tts"
    assert index["plugins"][0]["capabilities"] == ["tts.speak", "tts.voices"]
