import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from guardian.plugins import plugin_loader
from guardian.plugins.plugin_loader import DuplicatePluginIdError
from guardian.plugins.plugin_manifest import PluginManifest


def _manifest_payload(
    plugin_id: str,
    *,
    base_url: str = "https://plugin.example",
    capabilities=None,
):
    return {
        "schema_version": "1.0",
        "id": plugin_id,
        "name": f"{plugin_id} plugin",
        "version": "1.2.3",
        "description": "test plugin",
        "base_url": base_url,
        "capabilities": capabilities or [{"id": "tts", "actions": ["speak"]}],
        "extensions": {"owner": "tests"},
    }


def _write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_accepts_valid_v1_manifest():
    manifest = PluginManifest(
        **_manifest_payload("voice", base_url="https://voice.example/")
    )
    assert manifest.schema_version == "1.0"
    assert manifest.base_url == "https://voice.example"
    assert manifest.operation_pairs == {("tts", "speak")}


@pytest.mark.parametrize(
    "base_url",
    [
        "ftp://voice.example",
        "ws://voice.example",
        "localhost:7101",
    ],
)
def test_rejects_non_http_base_url(base_url):
    with pytest.raises(ValidationError):
        PluginManifest(**_manifest_payload("voice", base_url=base_url))


@pytest.mark.parametrize(
    "base_url",
    [
        "https://voice.example/api",
        "https://voice.example/?x=1",
        "https://voice.example/#fragment",
    ],
)
def test_rejects_base_url_with_path_query_or_fragment(base_url):
    with pytest.raises(ValidationError):
        PluginManifest(**_manifest_payload("voice", base_url=base_url))


def test_rejects_duplicate_capability_action_pairs():
    with pytest.raises(ValidationError):
        PluginManifest(
            **_manifest_payload(
                "voice",
                capabilities=[
                    {"id": "tts", "actions": ["speak"]},
                    {"id": "tts", "actions": ["speak"]},
                ],
            )
        )


def test_discovery_lists_only_validated_manifests(tmp_path):
    plugins_root = tmp_path / "plugins"

    _write_manifest(
        plugins_root / "voice" / "manifest.json",
        _manifest_payload("voice", base_url="https://voice.example"),
    )
    invalid = _manifest_payload("broken", base_url="https://broken.example")
    invalid.pop("version")
    _write_manifest(plugins_root / "broken" / "manifest.json", invalid)

    manifests = plugin_loader.load_all_manifests(plugin_dir=plugins_root)
    assert [manifest.id for manifest in manifests] == ["voice"]


def test_discovery_rejects_duplicate_plugin_ids(tmp_path):
    plugins_root = tmp_path / "plugins"

    _write_manifest(
        plugins_root / "voice_a" / "manifest.json",
        _manifest_payload("shared"),
    )
    _write_manifest(
        plugins_root / "voice_b" / "manifest.json",
        _manifest_payload("shared"),
    )

    with pytest.raises(DuplicatePluginIdError):
        plugin_loader.load_all_manifests(plugin_dir=plugins_root)


def test_discovery_uses_canonical_path_only(tmp_path):
    plugins_root = tmp_path / "plugins"

    _write_manifest(
        plugins_root / "voice" / "manifest.json",
        _manifest_payload("voice"),
    )
    _write_manifest(
        plugins_root / "legacy" / "plugin_manifest.json",
        _manifest_payload("legacy"),
    )
    _write_manifest(
        plugins_root / "nested" / "child" / "manifest.json",
        _manifest_payload("nested"),
    )

    manifests = plugin_loader.load_all_manifests(plugin_dir=plugins_root)
    assert [manifest.id for manifest in manifests] == ["voice"]


def test_active_tts_manifest_is_valid_and_discoverable():
    manifest_path = (
        Path(__file__).resolve().parents[2]
        / "plugins"
        / "chatterbox"
        / "manifest.json"
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = PluginManifest(**payload)
    assert manifest.supports_operation("tts", "speak")

    discovered_ids = {item.id for item in plugin_loader.load_all_manifests()}
    assert "chatterbox" in discovered_ids


def test_active_tts_manifest_origin_matches_runtime_compose_mapping():
    repo_root = Path(__file__).resolve().parents[2]
    manifest_payload = json.loads(
        (repo_root / "plugins" / "chatterbox" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    manifest = PluginManifest(**manifest_payload)
    compose_text = (repo_root / "docker-compose.yml").read_text(
        encoding="utf-8"
    )
    backend_block = compose_text.split("  backend:\n", 1)[1].split(
        "\n  worker-warmup:\n", 1
    )[0]
    worker_chat_block = compose_text.split("  worker-chat:\n", 1)[1].split(
        "\n  worker-voice:\n", 1
    )[0]

    assert "tts:" in compose_text
    assert 'ports: ["8000:8000"]' in compose_text
    assert "- ./plugins:/app/plugins:ro" in backend_block
    assert "- ./plugins:/app/plugins:ro" in worker_chat_block
    assert "./plugins/chatterbox:/app/plugins/chatterbox:ro" not in compose_text
    assert (
        'CODEXIFY_ASSISTANT_MESSAGE_AUDIO_AUTOGENERATE: "true"'
        in worker_chat_block
    )
    assert manifest.base_url == "http://tts:8000"


def test_backend_runtime_image_and_worker_chat_runtime_keep_canonical_plugins():
    repo_root = Path(__file__).resolve().parents[2]
    dockerfile_text = (repo_root / "backend" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    compose_text = (repo_root / "docker-compose.yml").read_text(
        encoding="utf-8"
    )
    worker_chat_block = compose_text.split("  worker-chat:\n", 1)[1].split(
        "\n  worker-voice:\n", 1
    )[0]

    assert "COPY plugins /app/plugins" in dockerfile_text
    assert "worker-chat:" in compose_text
    assert "- ./plugins:/app/plugins:ro" in worker_chat_block
