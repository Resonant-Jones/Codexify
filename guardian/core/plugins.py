"""Centralized plugin loading helpers for runtime and manifest-based plugins."""

from __future__ import annotations

import logging
from threading import Lock
from urllib.parse import urlparse

from guardian.plugin_loader import plugin_loader as _runtime_plugin_loader
from guardian.plugins.plugin_loader import (
    load_all_manifests as _load_manifest_plugins,
)
from guardian.plugins.plugin_manifest import PluginManifest

logger = logging.getLogger(__name__)

_RUNTIME_LOADER_LOCK = Lock()
_ALLOWED_ENTRYPOINT_SCHEMES = {"http", "https"}


def get_runtime_plugin_loader():
    """Return the singleton runtime plugin loader instance."""
    return _runtime_plugin_loader


def load_runtime_plugins():
    """
    Load runtime plugins through a single guarded entrypoint.

    Loader invocation is idempotent for non-empty registries to avoid
    accidental duplicate initialization across call sites.
    """
    loader = get_runtime_plugin_loader()
    with _RUNTIME_LOADER_LOCK:
        if not getattr(loader, "plugins", {}):
            loader.load_all_plugins()
    return loader


def _has_safe_entrypoint(manifest: PluginManifest) -> bool:
    parsed = urlparse(manifest.entrypoint)
    return parsed.scheme in _ALLOWED_ENTRYPOINT_SCHEMES and bool(parsed.netloc)


def list_plugin_manifests() -> list[PluginManifest]:
    """Load plugin manifests with dedupe and basic entrypoint validation."""
    manifests = _load_manifest_plugins()
    filtered: list[PluginManifest] = []
    seen_ids: set[str] = set()

    for manifest in manifests:
        if manifest.id in seen_ids:
            logger.warning(
                "[plugins] duplicate plugin id skipped: %s", manifest.id
            )
            continue
        if not _has_safe_entrypoint(manifest):
            logger.warning(
                "[plugins] unsafe plugin entrypoint skipped: %s (%s)",
                manifest.id,
                manifest.entrypoint,
            )
            continue
        seen_ids.add(manifest.id)
        filtered.append(manifest)

    return filtered


def get_plugin_manifest_by_id(plugin_id: str) -> PluginManifest | None:
    """Return a plugin manifest by id from the centralized manifest list."""
    for manifest in list_plugin_manifests():
        if manifest.id == plugin_id:
            return manifest
    return None


def get_plugin_manifest_by_capability(
    capability: str,
) -> PluginManifest | None:
    """Return the first plugin manifest declaring the requested capability."""
    wanted = capability.strip().lower()
    if not wanted:
        return None

    for manifest in list_plugin_manifests():
        capabilities = {
            cap.strip().lower() for cap in (manifest.capabilities or []) if cap
        }
        if wanted in capabilities:
            return manifest

    return None


__all__ = [
    "get_plugin_manifest_by_capability",
    "get_plugin_manifest_by_id",
    "get_runtime_plugin_loader",
    "list_plugin_manifests",
    "load_runtime_plugins",
]
