# Contributing to Threadspace

Thank you for your interest in contributing to Threadspace! This guide will help you get started with development and understand our workflow.

## 🔧 Development Setup

### Prerequisites

- Python 3.8 or higher
- pip
- make
- git

### Initial Setup

1. Clone the repository:
```bash
git clone https://github.com/threadspace/threadspace.git
cd threadspace
```

2. Create and activate virtual environment:
```bash
make venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:
```bash
make dev-install
```

This will:
- Install all required packages
- Set up pre-commit hooks
- Initialize the development environment

## 🚀 Development Workflow

### 1. Create a New Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or modifications

### 2. Development Cycle

1. Make your changes
2. Run tests:
```bash
make test
```

3. Check code quality:
```bash
make check
```

This will:
- Format code with black and isort
- Run linting with flake8
- Run type checking with mypy
- Execute tests

4. Run the system:
```bash
make run
```

### 3. Pre-commit Hooks

We use pre-commit hooks to ensure code quality. They run automatically on commit, checking:
- Code formatting (black, isort)
- Linting (flake8)
- Type checking (mypy)
- Security checks (bandit)
- Test execution

To run hooks manually:
```bash
pre-commit run --all-files
```

## 🏗️ Project Structure

```
threadspace/
├── guardian/               # Core system components
│   ├── agents/            # Agent implementations
│   ├── config/           # System configuration
│   └── threads/          # Thread management
├── plugins/               # Plugin system
│   ├── memory_analyzer/   # Memory analysis plugin
│   └── pattern_analyzer/  # Pattern recognition plugin
├── tests/                 # Test suite
├── docs/                  # Documentation
└── scripts/               # Utility scripts
```

## 🧪 Testing

### Running Tests

- Run all tests:
```bash
make test
```

- Run with coverage:
```bash
make test-coverage
```

- Run specific test:
```bash
pytest tests/test_specific.py
```

### Writing Tests

1. Create test files in the `tests/` directory
2. Follow the naming convention: `test_*.py`
3. Use pytest fixtures for common setup
4. Include both unit and integration tests
5. Aim for high coverage

## 📝 Documentation

### Building Docs

```bash
make docs
```

### Serving Docs Locally

```bash
make docs-serve
```

### Documentation Standards

1. All public APIs must have docstrings
2. Follow Google docstring format
3. Include examples in docstrings
4. Keep documentation up to date with code changes

## 🔌 Plugin Development

### Creating a New Plugin

1. Initialize plugin structure:
```bash
make init-plugin
```

2. Implement required interface:
- `init_plugin()`
- `get_metadata()`
- `cleanup()` (optional)
- `health_check()` (optional)

3. Add plugin configuration in `plugin.json`

### Plugin Guidelines

1. Follow single responsibility principle
2. Implement proper error handling
3. Include comprehensive logging
4. Add plugin-specific tests
5. Document all functionality

## 🐛 Bug Reports

1. Check existing issues first
2. Use the bug report template
3. Include:
   - System information
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant logs

## 🎯 Feature Requests

1. Use the feature request template
2. Clearly describe the problem and solution
3. Include implementation details if possible
4. Consider impact on existing functionality

## 📊 Code Review Process

1. Create a pull request
2. Fill out the PR template
3. Ensure all checks pass
4. Request review from maintainers
5. Address feedback
6. Update documentation if needed

## 🔄 Release Process

1. Update version in `setup.py`
2. Update CHANGELOG.md
3. Create release branch
4. Run full test suite
5. Create release tag
6. Build and publish:
```bash
make build
make upload
```

## 🤝 Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

## 📜 License

By contributing, you agree that your contributions will be licensed under the project's MIT License.

## 🆘 Getting Help

- Create an issue for bugs
- Discuss features in discussions
- Join our community chat
- Contact maintainers directly

## 🎉 Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to Threadspace! Your efforts help make this project better for everyone.
