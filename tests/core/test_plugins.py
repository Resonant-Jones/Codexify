from guardian.core import plugins as core_plugins
from guardian.plugins.plugin_manifest import PluginManifest


class DummyRuntimeLoader:
    def __init__(self, plugins=None):
        self.plugins = plugins or {}
        self.load_calls = 0

    def load_all_plugins(self):
        self.load_calls += 1
        self.plugins["loaded"] = object()


def _manifest(
    plugin_id: str,
    *,
    entrypoint: str,
    capabilities: list[str] | None = None,
) -> PluginManifest:
    return PluginManifest(
        id=plugin_id,
        name=plugin_id,
        entrypoint=entrypoint,
        permissions=[],
        capabilities=capabilities or [],
    )


def test_load_runtime_plugins_loads_once_when_empty(monkeypatch):
    loader = DummyRuntimeLoader()
    monkeypatch.setattr(
        core_plugins,
        "get_runtime_plugin_loader",
        lambda: loader,
    )

    loaded = core_plugins.load_runtime_plugins()

    assert loaded is loader
    assert loader.load_calls == 1


def test_load_runtime_plugins_skips_reload_when_registry_present(monkeypatch):
    loader = DummyRuntimeLoader(plugins={"existing": object()})
    monkeypatch.setattr(
        core_plugins,
        "get_runtime_plugin_loader",
        lambda: loader,
    )

    loaded = core_plugins.load_runtime_plugins()

    assert loaded is loader
    assert loader.load_calls == 0


def test_list_plugin_manifests_filters_duplicate_ids_and_unsafe_entrypoints(
    monkeypatch,
):
    manifests = [
        _manifest(
            "tts_plugin",
            entrypoint="http://localhost:7101",
            capabilities=["tts"],
        ),
        _manifest(
            "tts_plugin",
            entrypoint="https://example.invalid",
            capabilities=["tts"],
        ),
        _manifest("unsafe_plugin", entrypoint="file:///tmp/plugin"),
        _manifest("safe_plugin", entrypoint="https://localhost:7201"),
    ]

    monkeypatch.setattr(
        core_plugins,
        "_load_manifest_plugins",
        lambda: manifests,
    )

    filtered = core_plugins.list_plugin_manifests()

    assert [manifest.id for manifest in filtered] == [
        "tts_plugin",
        "safe_plugin",
    ]


def test_get_plugin_manifest_by_capability_is_case_insensitive(monkeypatch):
    manifests = [
        _manifest(
            "non_tts",
            entrypoint="https://localhost:7000",
            capabilities=["vision"],
        ),
        _manifest(
            "voice",
            entrypoint="https://localhost:7101",
            capabilities=["TTS", "audio"],
        ),
    ]
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: manifests
    )

    manifest = core_plugins.get_plugin_manifest_by_capability("tts")

    assert manifest is not None
    assert manifest.id == "voice"
    assert core_plugins.get_plugin_manifest_by_capability("missing") is None
