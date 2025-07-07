# Plugins Directory

This folder is reserved for dynamic plugins that can be added or modified by the assistant.

## Plugin Structure

Each plugin should define a class that inherits from `PluginBase` located in `plugin_interface.py`. It must implement the following methods:

- `name(self) -> str`: Return the plugin's name.
- `run(self, *args, **kwargs)`: Execute the plugin logic.

## Example Plugin

```python
from plugins.plugin_interface import PluginBase

class HelloWorldPlugin(PluginBase):
    def name(self):
        return "HelloWorld"

    def run(self, *args, **kwargs):
        print("Hello, world!")
```

Use `loader.py` to dynamically load and run all available plugins.
```python
from plugins.loader import load_plugins

for plugin in load_plugins():
    print(f"Running {plugin.name()} plugin...")
    plugin.run()
```
# Guardian Plugin System State

This file acts as a ledger of known plugin interfaces available to the Guardian LLM environment.

## Plugin Interface

All plugins must inherit from `PluginBase` and implement:

- `name(self) -> str`: Return the plugin's name.
- `run(self, *args, **kwargs)`: Execute the plugin logic.

## Example

```python
from plugins.plugin_interface import PluginBase

class HelloWorldPlugin(PluginBase):
    def name(self):
        return "HelloWorld"

    def run(self, *args, **kwargs):
        print("Hello, world!")
```

## Loaded at Runtime

The plugin loader system will detect and import all modules within the `plugins/` directory that follow this interface. These are made available to the assistant at runtime for invocation.

Loader logic:

```python
from plugins.loader import load_plugins

for plugin in load_plugins():
    print(f"Running {plugin.name()} plugin...")
    plugin.run()
```

## Purpose

This file should act as a living contract that is kept up to date by the assistant. If plugins are created, removed, or deprecated, the assistant should reflect those changes here.

## Known Plugins

- HelloWorldPlugin (example)
- [Add your plugin metadata here as they are built]