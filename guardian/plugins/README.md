# Guardian Plugin System

This directory contains plugins that extend the Guardian system's functionality.

## Plugin Structure

Each plugin should be contained in its own directory with the following structure:

```
plugin_name/
├── plugin.json    # Plugin metadata and configuration
├── main.py        # Main plugin implementation
└── tests/         # Plugin tests
    └── test_plugin.py
```

## Plugin Manifest

The plugin.json file should contain:

```json
{
<<<<<<< HEAD
  "last_updated": "2025-06-26T03:54:26.170870",
=======
  "last_updated": "2025-06-26T05:38:05.365713",
>>>>>>> 7f93d0c (✅ Add event-loop-safe global rate limiter system with Safe Mode config + test suite)
  "active_plugins": {},
  "disabled_plugins": {}
}
```

## Plugin Development

See `docs/plugin_development.md` for detailed plugin development guidelines.
