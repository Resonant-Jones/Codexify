import json
import os
import shutil
import unittest
from pathlib import Path

from guardian.plugin_loader import PluginLoader


class TestPluginLoader(unittest.TestCase):
    def setUp(self):
        self.plugin_dir = Path("tests/test_plugins")  # Use a dedicated test directory
        self.plugin_loader = PluginLoader()
        self.plugin_loader.plugin_dir = self.plugin_dir
        self.manifest_path = self.plugin_dir / "plugin_manifest.json"
        # Create test plugin directory and manifest
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w") as f:
            json.dump({}, f)

    def tearDown(self):
        # Clean up test plugin directory
        if self.plugin_dir.exists():
            shutil.rmtree(self.plugin_dir)

    def test_update_manifest(self):
        # Create a dummy plugin directory and metadata
        dummy_plugin_path = self.plugin_dir / "dummy_plugin"
        dummy_plugin_path.mkdir()
        metadata = {
            "name": "dummy_plugin",
            "version": "0.1.0",
            "description": "Dummy plugin for testing",
            "author": "Test Author",
            "dependencies": [],
            "capabilities": [],
        }
        with open(dummy_plugin_path / "plugin.json", "w") as f:
            json.dump(metadata, f)

        # Load the dummy plugin
        plugin = self.plugin_loader.load_plugin(dummy_plugin_path)
        self.assertIsNotNone(plugin)
        if plugin:
            self.plugin_loader.plugins[plugin.name] = plugin

        # Update the manifest
        self.plugin_loader.update_manifest()

        # Check manifest content
        with open(self.manifest_path, "r") as f:
            manifest = json.load(f)

        self.assertIn("active_plugins", manifest)
        self.assertIn("disabled_plugins", manifest)
        self.assertIn("dummy_plugin", manifest["active_plugins"])


if __name__ == "__main__":
    unittest.main()
