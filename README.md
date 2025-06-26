# 🧠 Threadspace

A next-generation AI operating system designed to host recursive, persistent AI agents with self-awareness and dynamic capabilities.

## 🌟 Overview

Threadspace is not just another application framework—it's a complete operating environment for AI agents. Built with self-awareness and extensibility at its core, it provides:

- 🤖 **Persistent Agent Architecture**: Long-running AI agents with distinct roles and capabilities
- 🔄 **Dynamic Memory Management**: Sophisticated memory systems for context retention and pattern recognition
- 🔌 **Plugin System**: Extensible architecture for adding new capabilities at runtime
- 🛡️ **Guardian OS**: Core system management and health monitoring
- 📚 **Codex Integration**: Structured knowledge management and retrieval
- 🧪 **Self-Awareness**: Built-in epistemic uncertainty handling and capability tracking

## 🏗️ Architecture

```
Threadspace
├── GuardianOS (Core System)
│   ├── Thread Manager
│   ├── Plugin System
│   └── Memory Management
├── MetaCognition Layer
│   ├── Epistemic Self-Check
│   ├── Codex Awareness
│   └── Agent Registry
└── Subsystems
    ├── Vestige (Archival Memory)
    ├── Axis (Stable Compass)
    └── Echoform (Resonance Tracker)
```

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/threadspace/threadspace.git
cd threadspace

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### Basic Usage

```python
from guardian.system_init import threadspace

# Initialize the system
if threadspace.initialize():
    # System is ready for use
    status = threadspace.get_system_status()
    print(f"System Status: {status['health_status']}")
```

## 🔧 Core Components

### 1. Guardian OS

The core system management layer:
- Thread lifecycle management
- Health monitoring
- Resource allocation
- Plugin management

### 2. MetaCognition Engine

Handles system self-awareness:
- Knowledge state tracking
- Capability assessment
- Decision confidence evaluation
- Memory pattern recognition

### 3. Plugin System

Extensible architecture for adding capabilities:
- Dynamic loading/unloading
- Sandboxed execution
- Health monitoring
- Auto-documentation

### 4. Memory Management

Sophisticated memory handling:
- Long-term storage
- Pattern recognition
- Context awareness
- Relationship tracking

## 🔌 Plugin Development

Create new plugins to extend system capabilities:

```python
# plugins/my_plugin/main.py
def init_plugin():
    """Initialize plugin."""
    return True

def get_metadata():
    """Return plugin metadata."""
    return {
        "name": "my_plugin",
        "version": "1.0.0",
        "description": "Example plugin",
        "author": "Your Name",
        "dependencies": [],
        "capabilities": ["example_capability"]
    }
```

## 🛠️ Development

### Setting Up Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/
```

### Code Style

We use:
- Black for code formatting
- isort for import sorting
- mypy for type checking
- flake8 for linting

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- [Internal Architecture](docs/INTERNAL_DOCS.md)
- [Plugin Development Guide](docs/plugin_development.md)
- [API Reference](docs/api_reference.md)

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=guardian tests/

# Run specific test file
pytest tests/test_system_integration.py
```

## 🔒 Security

Security considerations:
- Plugin sandboxing
- Thread isolation
- Memory protection
- Access control

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Special thanks to:
- The Threadspace Core Team
- All contributors and community members
- Open source projects that made this possible

---

Built with ❤️ by the Threadspace Team
