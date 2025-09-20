# Threadspace Makefile

.PHONY: all install dev-install test clean lint lint-fix lint-fix-unsafe format check docs build

# Python executable
PYTHON      := python3
PIP         := pip3

# Directories
SRC_DIR     := guardian
TEST_DIR    := tests
DOCS_DIR    := docs
BUILD_DIR   := build
DIST_DIR    := dist
VENV_DIR    := venv

# ────────────────────────────────
# Lint / format settings
# Lint / format settings
LINE_LENGTH := 88                # keep aligned with Black
RUFF_IGNORE := E203              # ignore the Black‑conflict rule
# Ruff ≥0.1 switched to --ignore (extend-ignore deprecated)
RUFF_ARGS   := --line-length=$(LINE_LENGTH) --ignore=$(RUFF_IGNORE)
# ────────────────────────────────

# Files
REQUIREMENTS        := requirements.txt
TEST_REQUIREMENTS   := requirements-test.txt
DEV_REQUIREMENTS    := requirements-dev.txt

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
	rm -rf $(BUILD_DIR) $(DIST_DIR) *.egg-info .pytest_cache .coverage $(TEST_REPORT_DIR)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run linting
lint:
	ruff check $(RUFF_ARGS) $(SRC_DIR) $(TEST_DIR)
	mypy $(SRC_DIR) $(TEST_DIR)

# Auto-fix linting issues using Ruff
lint-fix:
	ruff check --fix $(RUFF_ARGS) $(SRC_DIR) $(TEST_DIR)

# Auto‑fix linting issues, including “unsafe” fixes (may delete code)
lint-fix-unsafe:
	ruff check --fix --unsafe-fixes $(RUFF_ARGS) $(SRC_DIR) $(TEST_DIR)

# Format code
format:
	black -l $(LINE_LENGTH) $(SRC_DIR) $(TEST_DIR)
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

# Initialize plugin with scaffold
init-plugin:
	@if [ -z "$(name)" ]; then \
		read -p "Enter plugin name: " plugin_name; \
	else \
		plugin_name="$(name)"; \
	fi; \
	mkdir -p plugins/$$plugin_name; \
	printf '{\n  "name": "%s",\n  "version": "0.1.0",\n  "description": "New plugin",\n  "author": "Guardian Team",\n  "dependencies": [],\n  "capabilities": []\n}' "$$plugin_name" > plugins/$$plugin_name/plugin.json; \
	printf 'def init_plugin():\n    return True\n\ndef get_metadata():\n    return {}\n\ndef run(**kwargs):\n    return {"status": "success"}\n' > plugins/$$plugin_name/main.py; \
	echo "Plugin $$plugin_name initialized with scaffold"

# Query memory logs
logs:
	@if [ -z "$(hours)" ]; then \
		hours=24; \
	fi; \
	guardianctl query-memory --last $(hours)

# Run specific plugin
plugin:
	@if [ -z "$(name)" ]; then \
		echo "Usage: make plugin name=<plugin_name>"; \
		exit 1; \
	fi; \
	guardianctl run-plugin $(name) $(args)

# List all plugins
plugins:
	guardianctl list-plugins

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
	@grep -E '^[a-zA-Z_-]+:.*?##' $(firstword $(MAKEFILE_LIST)) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

# Development requirements file
requirements-dev.txt:
	@echo "black>=23.0.0"          > $@
	@echo "isort>=5.12.0"          >> $@
	@echo "mypy>=1.0.0"            >> $@
	@echo "flake8>=6.0.0"          >> $@
	@echo "ruff>=0.4.0"            >> $@
	@echo "pytest>=7.0.0"          >> $@
	@echo "pytest-cov>=4.1.0"      >> $@
	@echo "pytest-asyncio>=0.21.0" >> $@
	@echo "pre-commit>=3.3.0"      >> $@
	@echo "mkdocs>=1.4.0"          >> $@
	@echo "mkdocs-material>=9.1.0" >> $@
	@echo "twine>=4.0.0"           >> $@

# Test requirements file
requirements-test.txt:
	@echo "pytest>=7.0.0"          > $@
	@echo "pytest-cov>=4.1.0"      >> $@
	@echo "pytest-asyncio>=0.21.0" >> $@

# Initialize pre-commit configuration
.pre-commit-config.yaml:
	@echo "repos:"                        >  $@
	@echo "- repo: https://github.com/psf/black" >> $@
	@echo "  rev: 23.0.0"                >> $@
	@echo "  hooks:"                     >> $@
	@echo "    - id: black"              >> $@
	@echo "- repo: https://github.com/pycqa/isort" >> $@
	@echo "  rev: 5.12.0"                >> $@
	@echo "  hooks:"                     >> $@
	@echo "    - id: isort"              >> $@
	@echo "- repo: https://github.com/pycqa/flake8" >> $@
	@echo "  rev: 6.0.0"                 >> $@
	@echo "  hooks:"                     >> $@
	@echo "    - id: flake8"             >> $@

# Initialize project structure
init: venv requirements-dev.txt requirements-test.txt .pre-commit-config.yaml
	@mkdir -p $(SRC_DIR) $(TEST_DIR) $(DOCS_DIR) plugins
	@echo "Project structure initialized"