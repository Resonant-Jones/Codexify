# 🔌 Threadspace Plugin System

This directory contains all active plugins for the Threadspace system. The plugin manifest is automatically updated as plugins are added or removed.

## 📋 Current Plugin Manifest

> ⚠️ This section is automatically maintained by the system. Manual edits will be overwritten.

```json
{
  "last_updated": "",
  "active_plugins": {},
  "disabled_plugins": {}
}
```

## 🔧 Plugin Architecture

Plugins in Threadspace follow a standardized interface that enables dynamic loading and seamless integration with the core system. Each plugin must implement:

### Required Interface

```python
def init_plugin() -> bool:
    """Initialize the plugin and its resources."""
    pass

def get_metadata() -> dict:
    """
    Return plugin metadata.
    
    Returns:
        {
            "name": str,            # Plugin name
            "version": str,         # Semantic version
            "description": str,     # Plugin description
            "author": str,          # Author information
            "dependencies": list,   # Required dependencies
            "capabilities": list    # Provided capabilities
        }
    """
    pass
```

### Optional Interface

```python
def cleanup() -> bool:
    """Cleanup resources when plugin is disabled."""
    pass

def health_check() -> dict:
    """
    Return plugin health status.
    
    Returns:
        {
            "status": str,         # "healthy" | "warning" | "error"
            "message": str,        # Status description
            "metrics": dict        # Optional performance metrics
        }
    """
    pass
```

## 🚀 Plugin Development

To create a new plugin:

1. Create a new directory under `plugins/` with your plugin name
2. Implement the required interface methods
3. Add a `plugin.json` file with metadata
4. Optional: Add documentation in a `README.md` file

### Example Plugin Structure

```
plugins/
  my_plugin/
    __init__.py
    plugin.json
    README.md
    main.py
```

### Example plugin.json

```json
{
  "name": "my_plugin",
  "version": "1.0.0",
  "description": "Example plugin description",
  "author": "Your Name",
  "dependencies": [],
  "capabilities": ["example_capability"],
  "config": {
    "enabled": true,
    "setting1": "value1"
  }
}
```

## 🔒 Security

Plugins are sandboxed and have limited access to system resources. They:
- Can only access their own configuration and data directory
- Must declare required permissions in their metadata
- Are monitored for resource usage and health

## 🔄 Auto-Update Process

The plugin manifest is automatically updated when:
- New plugins are added to the system
- Existing plugins are removed or disabled
- Plugin configurations are modified
- Plugin health status changes

The update process:
1. Scans the plugins directory for changes
2. Validates plugin interfaces and metadata
3. Updates the manifest in this README
4. Logs changes to the system journal

## 🎯 Best Practices

1. **Initialization**
   - Perform resource allocation in `init_plugin()`
   - Handle initialization failures gracefully
   - Log initialization steps

2. **Error Handling**
   - Use try/except blocks for robust operation
   - Report errors through the health check interface
   - Clean up resources on error

3. **Configuration**
   - Use the plugin.json for configuration
   - Support runtime configuration updates
   - Validate configuration values

4. **Documentation**
   - Maintain clear documentation
   - Document configuration options
   - Provide usage examples

5. **Testing**
   - Include unit tests
   - Test initialization and cleanup
   - Verify error handling

## 📝 Plugin Guidelines

1. **Naming**
   - Use lowercase with underscores
   - Be descriptive but concise
   - Avoid generic names

2. **Dependencies**
   - Minimize external dependencies
   - Document all requirements
   - Version dependencies appropriately

3. **Performance**
   - Optimize resource usage
   - Implement efficient algorithms
   - Cache results when appropriate

4. **Maintenance**
   - Keep plugins updated
   - Monitor for deprecation
   - Respond to bug reports

## 🤝 Contributing

To contribute a plugin:

1. Fork the repository
2. Create your plugin following the guidelines
3. Test thoroughly
4. Submit a pull request

## 📚 Additional Resources

- [Plugin Development Guide](../docs/plugin_development.md)
- [API Documentation](../docs/api_reference.md)
- [Example Plugins](../examples/plugins/)

---

> 🔄 Last Updated: [timestamp]
> This document is automatically maintained by the Threadspace system.
