import json

import pytest
from pydantic import ValidationError

from guardian.plugins import plugin_loader
from guardian.plugins.plugin_loader import DuplicatePluginIdError
from guardian.plugins.plugin_manifest import PluginManifest


def _write_manifest(base, plugin_dir, payload):
    path = base / plugin_dir
    path.mkdir(parents=True)
    with (path / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def test_accepts_valid_v1_manifest_and_normalizes_base_url():
    manifest = PluginManifest.model_validate(
        {
            "schema_version": "1.0",
            "id": "alpha",
            "name": "Alpha",
            "version": "1.2.3",
            "description": "desc",
            "base_url": "https://example.com/",
            "capabilities": [{"id": "chat", "actions": ["reply"]}],
            "extensions": {"x": True},
        }
    )

    assert manifest.base_url == "https://example.com"


@pytest.mark.parametrize(
    "base_url",
    ["ftp://example.com", "file:///tmp/nope", "wss://example.com"],
)
def test_rejects_non_http_base_url(base_url):
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(
            {
                "schema_version": "1.0",
                "id": "alpha",
                "name": "Alpha",
                "version": "1.2.3",
                "base_url": base_url,
                "capabilities": [{"id": "chat", "actions": ["reply"]}],
            }
        )


@pytest.mark.parametrize(
    "base_url",
    [
        "https://example.com/path",
        "https://example.com?x=1",
        "https://example.com#frag",
    ],
)
def test_rejects_base_url_with_path_query_or_fragment(base_url):
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(
            {
                "schema_version": "1.0",
                "id": "alpha",
                "name": "Alpha",
                "version": "1.2.3",
                "base_url": base_url,
                "capabilities": [{"id": "chat", "actions": ["reply"]}],
            }
        )


def test_rejects_duplicate_capability_action_pairs_within_manifest():
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(
            {
                "schema_version": "1.0",
                "id": "alpha",
                "name": "Alpha",
                "version": "1.2.3",
                "base_url": "https://example.com",
                "capabilities": [
                    {"id": "chat", "actions": ["reply", "reply"]}
                ],
            }
        )


def test_only_validated_manifests_are_listed_as_installed(tmp_path):
    _write_manifest(
        tmp_path,
        "good",
        {
            "schema_version": "1.0",
            "id": "good",
            "name": "Good",
            "version": "1.0.0",
            "base_url": "https://good.example",
            "capabilities": [{"id": "chat", "actions": ["reply"]}],
        },
    )
    _write_manifest(
        tmp_path,
        "bad",
        {
            "schema_version": "1.0",
            "id": "bad",
            "name": "Bad",
            "version": "1.0.0",
            "base_url": "ftp://bad.example",
            "capabilities": [{"id": "chat", "actions": ["reply"]}],
        },
    )

    manifests = plugin_loader.load_all_manifests(plugin_dir=tmp_path)

    assert [manifest.id for manifest in manifests] == ["good"]


def test_unhealthy_plugins_remain_installed_if_manifest_is_valid(tmp_path):
    _write_manifest(
        tmp_path,
        "good",
        {
            "schema_version": "1.0",
            "id": "good",
            "name": "Good",
            "version": "1.0.0",
            "base_url": "https://good.example",
            "capabilities": [{"id": "chat", "actions": ["reply"]}],
        },
    )

    manifests = plugin_loader.load_all_manifests(plugin_dir=tmp_path)

    assert len(manifests) == 1
    assert manifests[0].id == "good"


def test_canonical_discovery_uses_plugins_manifest_json_only(tmp_path):
    (tmp_path / "one").mkdir(parents=True)
    with (tmp_path / "one" / "plugin.json").open("w", encoding="utf-8") as handle:
        json.dump({}, handle)
    with (tmp_path / "one" / "manifest.yaml").open("w", encoding="utf-8") as handle:
        handle.write("id: no")

    _write_manifest(
        tmp_path,
        "two",
        {
            "schema_version": "1.0",
            "id": "two",
            "name": "Two",
            "version": "1.0.0",
            "base_url": "https://two.example",
            "capabilities": [{"id": "chat", "actions": ["reply"]}],
        },
    )

    manifests = plugin_loader.load_all_manifests(plugin_dir=tmp_path)

    assert [manifest.id for manifest in manifests] == ["two"]


def test_rejects_duplicate_plugin_ids_across_discovery(tmp_path):
    payload = {
        "schema_version": "1.0",
        "id": "dup",
        "name": "Dup",
        "version": "1.0.0",
        "base_url": "https://dup.example",
        "capabilities": [{"id": "chat", "actions": ["reply"]}],
    }
    _write_manifest(tmp_path, "one", payload)
    _write_manifest(tmp_path, "two", payload)

    with pytest.raises(DuplicatePluginIdError):
        plugin_loader.load_all_manifests(plugin_dir=tmp_path)
