# Guardian Plugin System

This directory contains plugins that extend the Guardian system's functionality.

## Plugin Structure

Each plugin must live in its own directory:
```
plugin_name/
├── plugin.json    # Plugin metadata and configuration
├── main.py        # Main plugin implementation
└── tests/         # Plugin tests
```

The `plugin.json` should contain metadata:
```json
{
  "last_updated": "2025-07-03T03:27:30.965439",
  "active_plugins": {},
  "disabled_plugins": {}
}
```

## Plugin Interface

Each plugin must inherit from `PluginBase` and implement the following:
- `name(self) -> str`: Return the plugin's name.
- `run(self, *args, **kwargs)`: Execute the plugin logic.

### Example

```python
from plugins.plugin_interface import PluginBase

class HelloWorldPlugin(PluginBase):
    def name(self):
        return "HelloWorld"

    def run(self, *args, **kwargs):
        print("Hello, world!")
```

## Loading Plugins at Runtime

The loader system detects and runs all valid plugins dynamically:
```python
from plugins.loader import load_plugins

for plugin in load_plugins():
    print(f"Running {plugin.name()} plugin...")
    plugin.run()
```

## Ledger

This file acts as a living contract. Keep it up to date when plugins are created, removed, or deprecated.

Known plugins:
- HelloWorldPlugin (example)
- [Add your plugin metadata here]