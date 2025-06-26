# Plugin Development Guide

## 📚 Table of Contents
- [Overview](#overview)
- [Plugin Architecture](#plugin-architecture)
- [Creating a Plugin](#creating-a-plugin)
- [Plugin Interface](#plugin-interface)
- [Plugin Configuration](#plugin-configuration)
- [Best Practices](#best-practices)
- [Testing](#testing)
- [Distribution](#distribution)
- [Examples](#examples)

## 🌟 Overview

Threadspace's plugin system allows extending the system's functionality through modular, self-contained plugins. This guide covers everything you need to know to create, test, and distribute plugins.

## 🏗️ Plugin Architecture

### Core Concepts

```
plugin/
├── plugin.json         # Plugin metadata and configuration
├── main.py            # Plugin implementation
├── README.md          # Plugin documentation
└── tests/             # Plugin tests
    └── test_plugin.py # Test suite
```

### Integration Points

- Memory System
- Thread Management
- Event System
- Configuration System
- Health Monitoring

## 🛠️ Creating a Plugin

### 1. Initialize Plugin Structure

```bash
make init-plugin
# Enter plugin name when prompted
```

### 2. Define Plugin Metadata

```json
{
    "name": "my_plugin",
    "version": "1.0.0",
    "description": "Plugin description",
    "author": "Your Name",
    "dependencies": [],
    "capabilities": [
        "capability_1",
        "capability_2"
    ],
    "config": {
        "enabled": true,
        "setting_1": "value_1"
    }
}
```

### 3. Implement Plugin Interface

```python
def init_plugin() -> bool:
    """Initialize the plugin."""
    try:
        # Initialization logic
        return True
    except Exception as e:
        logger.error(f"Plugin initialization failed: {e}")
        return False

def cleanup() -> bool:
    """Clean up plugin resources."""
    try:
        # Cleanup logic
        return True
    except Exception as e:
        logger.error(f"Plugin cleanup failed: {e}")
        return False

def get_metadata() -> Dict[str, Any]:
    """Return plugin metadata."""
    try:
        plugin_dir = Path(__file__).parent
        with open(plugin_dir / 'plugin.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load metadata: {e}")
        return {}

def health_check() -> Dict[str, Any]:
    """Return plugin health status."""
    return {
        'status': 'healthy',
        'message': 'Plugin is running normally',
        'metrics': {
            'metric_1': 'value_1'
        }
    }
```

## 🔌 Plugin Interface

### Required Methods

| Method | Description | Return Type |
|--------|-------------|-------------|
| `init_plugin()` | Initialize plugin | `bool` |
| `get_metadata()` | Get plugin metadata | `Dict[str, Any]` |

### Optional Methods

| Method | Description | Return Type |
|--------|-------------|-------------|
| `cleanup()` | Clean up resources | `bool` |
| `health_check()` | Check plugin health | `Dict[str, Any]` |

## ⚙️ Plugin Configuration

### Configuration File Structure

```json
{
    "config": {
        "enabled": true,
        "interval": 300,
        "log_level": "INFO",
        "features": {
            "feature_1": true,
            "feature_2": false
        }
    }
}
```

### Configuration Access

```python
def get_config() -> Dict[str, Any]:
    """Get plugin configuration."""
    plugin_dir = Path(__file__).parent
    with open(plugin_dir / 'plugin.json', 'r') as f:
        data = json.load(f)
    return data.get('config', {})
```

## 🎯 Best Practices

### 1. Error Handling

```python
try:
    # Operation that might fail
    result = perform_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    # Proper error recovery
```

### 2. Logging

```python
import logging

logger = logging.getLogger(__name__)

def plugin_operation():
    logger.info("Starting operation")
    try:
        # Operation logic
        logger.debug("Operation details")
    except Exception as e:
        logger.error(f"Operation failed: {e}")
```

### 3. Resource Management

```python
class PluginResource:
    def __init__(self):
        self.initialized = False
    
    def __enter__(self):
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
```

### 4. Thread Safety

```python
from threading import Lock

class ThreadSafePlugin:
    def __init__(self):
        self.lock = Lock()
        self.shared_resource = {}
    
    def update_resource(self, key, value):
        with self.lock:
            self.shared_resource[key] = value
```

## 🧪 Testing

### 1. Test Structure

```python
import unittest

class TestMyPlugin(unittest.TestCase):
    def setUp(self):
        """Set up test resources."""
        self.plugin = MyPlugin()
    
    def tearDown(self):
        """Clean up test resources."""
        self.plugin.cleanup()
    
    def test_plugin_initialization(self):
        """Test plugin initialization."""
        self.assertTrue(self.plugin.init_plugin())
```

### 2. Test Coverage

```bash
pytest --cov=my_plugin tests/
```

## 📦 Distribution

### 1. Package Structure

```
my_plugin/
├── setup.py
├── README.md
├── LICENSE
├── my_plugin/
│   ├── __init__.py
│   ├── plugin.json
│   └── main.py
└── tests/
    └── test_plugin.py
```

### 2. Setup Script

```python
from setuptools import setup, find_packages

setup(
    name="threadspace-plugin-name",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'dependency1>=1.0.0',
        'dependency2>=2.0.0'
    ]
)
```

## 📝 Examples

### Memory Analysis Plugin

```python
from guardian.codex_awareness import CodexAwareness

class MemoryAnalyzer:
    def __init__(self):
        self.codex = CodexAwareness()
    
    def analyze_memory(self, memory_id: str) -> Dict[str, Any]:
        """Analyze memory content."""
        try:
            memory = self.codex.query_memory(memory_id)
            # Analysis logic
            return {'status': 'success', 'analysis': results}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
```

### Pattern Recognition Plugin

```python
class PatternRecognizer:
    def __init__(self):
        self.patterns = []
    
    def recognize_patterns(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Recognize patterns in data."""
        patterns = []
        # Pattern recognition logic
        return patterns
```

## 🔍 Debugging

### 1. Debug Mode

```python
def enable_debug():
    """Enable debug logging."""
    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)
```

### 2. Debug Tools

```python
def debug_info() -> Dict[str, Any]:
    """Get debug information."""
    return {
        'status': self.status,
        'memory_usage': self.get_memory_usage(),
        'thread_count': self.get_thread_count(),
        'error_log': self.get_error_log()
    }
```

## 🔒 Security

### 1. Input Validation

```python
def validate_input(data: Dict[str, Any]) -> bool:
    """Validate plugin input."""
    required_fields = ['field1', 'field2']
    return all(field in data for field in required_fields)
```

### 2. Resource Limits

```python
def check_resource_limits(self) -> bool:
    """Check if plugin is within resource limits."""
    memory_usage = self.get_memory_usage()
    thread_count = self.get_thread_count()
    return (memory_usage < MAX_MEMORY and 
            thread_count < MAX_THREADS)
```

## 📚 Additional Resources

- [API Documentation](api_reference.md)
- [System Architecture](system_architecture.md)
- [Best Practices Guide](best_practices.md)
- [Security Guidelines](security_guidelines.md)

## 🤝 Support

For plugin development support:
- GitHub Issues
- Developer Forum
- Documentation
- Community Chat

---

Last Updated: [DATE]
Version: 1.0.0
