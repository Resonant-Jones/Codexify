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
    manifests: List[PluginManifest | None] = []
    manifest_indexes_by_id: dict[str, int] = {}
    duplicate_ids: set[str] = set()

    if not PLUGIN_DIR.exists():
        logger.warning(
            "[plugin_loader] Plugin directory not found: %s", PLUGIN_DIR
        )
        return []

    # Canonical discovery path only: <repo_root>/plugins/<plugin_id>/manifest.json
    for manifest_file in sorted(PLUGIN_DIR.glob("*/manifest.json")):
        try:
            with manifest_file.open() as f:
                data = json.load(f)
                manifest = PluginManifest(**data)
                existing_index = manifest_indexes_by_id.get(manifest.id)
                if existing_index is not None:
                    duplicate_ids.add(manifest.id)
                    manifests[existing_index] = None
                    logger.error(
                        "[plugin_loader] Duplicate plugin id rejected: %s "
                        "(conflict includes %s)",
                        manifest.id,
                        manifest_file,
                    )
                    continue
                manifest_indexes_by_id[manifest.id] = len(manifests)
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

    if duplicate_ids:
        logger.error(
            "[plugin_loader] Rejected duplicate plugin id(s): %s",
            ", ".join(sorted(duplicate_ids)),
        )

    loaded_manifests = [
        manifest for manifest in manifests if manifest is not None
    ]
    logger.info("[plugin_loader] Loaded %d plugin(s)", len(loaded_manifests))
    return loaded_manifests


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
