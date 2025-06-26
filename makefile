# Threadspace Makefile

.PHONY: all install dev-install test clean lint format check docs build

# Python executable
PYTHON := python3
PIP := pip3

# Directories
SRC_DIR := guardian
TEST_DIR := tests
DOCS_DIR := docs
BUILD_DIR := build
DIST_DIR := dist
VENV_DIR := venv

# Files
REQUIREMENTS := requirements.txt
TEST_REQUIREMENTS := requirements-test.txt
DEV_REQUIREMENTS := requirements-dev.txt

# Test report directory
TEST_REPORT_DIR := tests/reports

# Default target
all: install test

# Create virtual environment
venv:
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "Virtual environment created. Activate with 'source $(VENV_DIR)/bin/activate'"

# Install production dependencies
install:
	$(PIP) install -r $(REQUIREMENTS)
	$(PIP) install -e .

# Install development dependencies
dev-install: install
	$(PIP) install -r $(DEV_REQUIREMENTS)
	pre-commit install

# Run tests
test:
	@mkdir -p $(TEST_REPORT_DIR)
	$(PYTHON) $(TEST_DIR)/run_tests.py

# Run tests with coverage
test-coverage:
	@mkdir -p $(TEST_REPORT_DIR)
	pytest --cov=$(SRC_DIR) $(TEST_DIR) --cov-report=html:$(TEST_REPORT_DIR)/coverage

# Clean build artifacts and cache
clean:
	rm -rf $(BUILD_DIR)
	rm -rf $(DIST_DIR)
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf $(TEST_REPORT_DIR)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run linting
lint:
	flake8 $(SRC_DIR) $(TEST_DIR)
	mypy $(SRC_DIR) $(TEST_DIR)

# Format code
format:
	black $(SRC_DIR) $(TEST_DIR)
	isort $(SRC_DIR) $(TEST_DIR)

# Run all checks (format, lint, test)
check: format lint test

# Build documentation
docs:
	mkdocs build

# Serve documentation locally
docs-serve:
	mkdocs serve

# Build distribution packages
build: clean
	$(PYTHON) setup.py sdist bdist_wheel

# Upload to PyPI
upload: build
	twine upload dist/*

# Run the system
run:
	$(PYTHON) -m guardian.system_init

# Start development server
dev:
	$(PYTHON) -m guardian.system_init --debug

# Initialize plugin
init-plugin:
	@read -p "Enter plugin name: " plugin_name; \
	mkdir -p plugins/$$plugin_name; \
	cp plugins/README.md plugins/$$plugin_name/; \
	echo "Plugin $$plugin_name initialized"

# Health check
health:
	$(PYTHON) -m guardian.system_init --health-check

# Show system status
status:
	$(PYTHON) -m guardian.system_init --status

# Generate system report
report:
	@mkdir -p reports
	$(PYTHON) -m guardian.system_init --generate-report

# Help target
help:
	@echo "Threadspace Makefile commands:"
	@echo "  make install        - Install production dependencies"
	@echo "  make dev-install    - Install development dependencies"
	@echo "  make test          - Run tests"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make clean         - Clean build artifacts and cache"
	@echo "  make lint          - Run linting"
	@echo "  make format        - Format code"
	@echo "  make check         - Run all checks (format, lint, test)"
	@echo "  make docs          - Build documentation"
	@echo "  make docs-serve    - Serve documentation locally"
	@echo "  make build         - Build distribution packages"
	@echo "  make upload        - Upload to PyPI"
	@echo "  make run           - Run the system"
	@echo "  make dev           - Start development server"
	@echo "  make init-plugin   - Initialize new plugin"
	@echo "  make health        - Run system health check"
	@echo "  make status        - Show system status"
	@echo "  make report        - Generate system report"

# Development requirements file
requirements-dev.txt:
	@echo "black>=23.0.0" > requirements-dev.txt
	@echo "isort>=5.12.0" >> requirements-dev.txt
	@echo "mypy>=1.0.0" >> requirements-dev.txt
	@echo "flake8>=6.0.0" >> requirements-dev.txt
	@echo "pytest>=7.0.0" >> requirements-dev.txt
	@echo "pytest-cov>=4.1.0" >> requirements-dev.txt
	@echo "pytest-asyncio>=0.21.0" >> requirements-dev.txt
	@echo "pre-commit>=3.3.0" >> requirements-dev.txt
	@echo "mkdocs>=1.4.0" >> requirements-dev.txt
	@echo "mkdocs-material>=9.1.0" >> requirements-dev.txt
	@echo "twine>=4.0.0" >> requirements-dev.txt

# Test requirements file
requirements-test.txt:
	@echo "pytest>=7.0.0" > requirements-test.txt
	@echo "pytest-cov>=4.1.0" >> requirements-test.txt
	@echo "pytest-asyncio>=0.21.0" >> requirements-test.txt

# Initialize pre-commit configuration
.pre-commit-config.yaml:
	@echo "repos:" > .pre-commit-config.yaml
	@echo "- repo: https://github.com/psf/black" >> .pre-commit-config.yaml
	@echo "  rev: 23.0.0" >> .pre-commit-config.yaml
	@echo "  hooks:" >> .pre-commit-config.yaml
	@echo "    - id: black" >> .pre-commit-config.yaml
	@echo "- repo: https://github.com/pycqa/isort" >> .pre-commit-config.yaml
	@echo "  rev: 5.12.0" >> .pre-commit-config.yaml
	@echo "  hooks:" >> .pre-commit-config.yaml
	@echo "    - id: isort" >> .pre-commit-config.yaml
	@echo "- repo: https://github.com/pycqa/flake8" >> .pre-commit-config.yaml
	@echo "  rev: 6.0.0" >> .pre-commit-config.yaml
	@echo "  hooks:" >> .pre-commit-config.yaml
	@echo "    - id: flake8" >> .pre-commit-config.yaml

# Initialize project structure
init: venv requirements-dev.txt requirements-test.txt .pre-commit-config.yaml
	@mkdir -p $(SRC_DIR)
	@mkdir -p $(TEST_DIR)
	@mkdir -p $(DOCS_DIR)
	@mkdir -p plugins
	@echo "Project structure initialized"
