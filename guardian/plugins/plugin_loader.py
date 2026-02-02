"""
Plugin Loader
~~~~~~~~~~~~~

Loads plugin manifests from the plugins directory. Each plugin is expected
to have a manifest.json file in its subdirectory.
"""

import json
import logging
from pathlib import Path
from typing import List

from .plugin_manifest import PluginManifest

logger = logging.getLogger(__name__)

# Plugin directory at project root
PLUGIN_DIR = Path(__file__).parent.parent.parent / "plugins"


def load_all_manifests() -> List[PluginManifest]:
    """
    Load all plugin manifests from the plugins directory.

    Scans the plugins directory for subdirectories containing manifest.json
    files and parses them into PluginManifest objects.

    Returns:
        List of validated PluginManifest objects
    """
    manifests: List[PluginManifest] = []

    if not PLUGIN_DIR.exists():
        logger.warning(
            "[plugin_loader] Plugin directory not found: %s", PLUGIN_DIR
        )
        return manifests

    for manifest_file in PLUGIN_DIR.glob("*/manifest.json"):
        try:
            with manifest_file.open() as f:
                data = json.load(f)
                manifest = PluginManifest(**data)
                manifests.append(manifest)
                logger.debug(
                    "[plugin_loader] Loaded plugin: %s (%s)",
                    manifest.name,
                    manifest.id,
                )
        except json.JSONDecodeError as e:
            logger.error(
                "[plugin_loader] Invalid JSON in %s: %s", manifest_file, e
            )
        except Exception as e:
            logger.error(
                "[plugin_loader] Failed to load manifest %s: %s",
                manifest_file,
                e,
            )

    logger.info("[plugin_loader] Loaded %d plugin(s)", len(manifests))
    return manifests


def get_plugin_by_id(plugin_id: str) -> PluginManifest | None:
    """
    Get a specific plugin manifest by ID.

    Args:
        plugin_id: The unique plugin identifier

    Returns:
        PluginManifest if found, None otherwise
    """
    for manifest in load_all_manifests():
        if manifest.id == plugin_id:
            return manifest
    return None
