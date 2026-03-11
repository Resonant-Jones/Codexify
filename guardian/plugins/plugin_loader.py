"""Canonical manifest discovery for service plugins."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from .plugin_manifest import PluginManifest

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO_ROOT / "plugins"


class PluginDiscoveryError(Exception):
    """Raised when manifest discovery fails deterministically."""


class DuplicatePluginIdError(PluginDiscoveryError):
    """Raised when duplicate plugin ids are discovered."""


def _manifest_files(plugin_dir: Path = PLUGIN_DIR) -> list[Path]:
    return sorted(plugin_dir.glob("*/manifest.json"))


def load_all_manifests(plugin_dir: Path = PLUGIN_DIR) -> list[PluginManifest]:
    """Load and validate canonical v1 manifests from plugins/*/manifest.json."""
    manifests: list[PluginManifest] = []
    seen_manifest_by_id: dict[str, Path] = {}

    if not plugin_dir.exists():
        return manifests

    for manifest_file in _manifest_files(plugin_dir):
        try:
            with manifest_file.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            manifest = PluginManifest.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning(
                "[plugin_loader] skipping invalid manifest %s: %s",
                manifest_file,
                exc,
            )
            continue

        existing = seen_manifest_by_id.get(manifest.id)
        if existing is not None:
            message = (
                f"duplicate plugin id '{manifest.id}' in "
                f"{existing} and {manifest_file}"
            )
            raise DuplicatePluginIdError(message)

        seen_manifest_by_id[manifest.id] = manifest_file
        manifests.append(manifest)

    return manifests


def get_plugin_by_id(
    plugin_id: str, plugin_dir: Path = PLUGIN_DIR
) -> PluginManifest | None:
    """Get a manifest by plugin id from canonical manifest discovery."""
    for manifest in load_all_manifests(plugin_dir=plugin_dir):
        if manifest.id == plugin_id:
            return manifest
    return None
