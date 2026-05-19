# Codexify Makefile

.PHONY: all install dev-install test clean lint lint-fix lint-fix-unsafe format check docs docs-diagram-freshness docs-diagram-freshness-strict docs-diagram-freshness-auto docs-diagram-watch docs-diagram-regenerate build check-pytest dossier-collab desktop-dev desktop-build daily-audit morning-audit evening-audit audit-risk audit-gates audit-gates-pre-merge audit-gates-pre-release audit-full audit-traps audit-ritual-weekly audit-ritual-monthly audit-ritual-quarterly heartbeat heartbeat-review heartbeat-stage heartbeat-inspect heartbeat-outbox heartbeat-full generate-marketing generate-marketing-automation public-export public-sync

# Python executable
PYTHON      ?= python
PIP         ?= pip

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
check-pytest:
	@$(PYTHON) -m pytest --version >/dev/null 2>&1 || ( \
		echo "pytest is missing. Install with:"; \
		echo "  $(PYTHON) -m pip install -r requirements.txt"; \
		echo "or"; \
		echo "  $(PYTHON) -m pip install pytest"; \
		exit 1; \
	)

test: check-pytest
	@mkdir -p $(TEST_REPORT_DIR)
	$(PYTHON) -m pytest -q guardian/tests tests

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
	$(PYTHON) scripts/validate_docs.py
	$(PYTHON) scripts/check_diagram_freshness.py

docs-diagram-freshness:
	$(PYTHON) scripts/check_diagram_freshness.py

docs-diagram-freshness-strict:
	$(PYTHON) scripts/check_diagram_freshness.py --strict

docs-diagram-freshness-auto:
	$(PYTHON) scripts/check_diagram_freshness.py --auto-regenerate --regenerate-cmd "make docs-diagram-regenerate"

docs-diagram-watch:
	$(PYTHON) scripts/check_diagram_freshness.py --watch --regenerate-cmd "make docs-diagram-regenerate"

docs-diagram-regenerate:
	@echo "No repo-local diagram generator is configured yet."
	@echo "Replace target docs-diagram-regenerate with your generation command."

# Serve documentation locally
docs-serve:
	@echo "No repo-local docs server is configured."
	@exit 1

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

# Start Tauri desktop shell against frontend/src + external backend
desktop-dev:
	pnpm --dir frontend/src install
	cd src-tauri && cargo tauri dev

# Build frontend and package desktop bundle locally (manual release gate)
desktop-build:
	pnpm --dir frontend/src install
	pnpm --dir frontend/src build
	cd src-tauri && cargo tauri build

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

# Generate the daily audit record
daily-audit:
	$(PYTHON) scripts/daily_audit.py

# Generate the morning audit record
morning-audit:
	$(PYTHON) scripts/daily_audit.py --phase morning

# Generate the evening audit record
evening-audit:
	$(PYTHON) scripts/daily_audit.py --phase evening

# Generate draft marketing artifacts from canonical truth sources.
# Usage: make generate-marketing args="--campaign-id CAMPAIGN_2026_05_11 --audience local-first-builders --channels website,social,community --mode draft"
generate-marketing:
	$(PYTHON) scripts/marketing/generate_marketing.py $(args)

# Automation wrapper for draft-only marketing generation.
# Usage: make generate-marketing-automation args="--date 2026-05-12 --campaign-suffix MARKETING_V1 --audience local-first-builders --channels website,social,community --mode draft"
generate-marketing-automation:
	$(PYTHON) scripts/marketing/run_marketing_automation.py $(args)

# ────────────────────────────────
# Regression Prevention Audit Infrastructure
#
# Rationale:
# - Separate from daily-audit which tracks repo activity
# - Focuses on risk matrix and regression gates
# - Report-only by default; --enforce for CI gates
# ────────────────────────────────

# Generate risk matrix report
audit-risk:
	$(PYTHON) scripts/audit/risk_matrix.py

# Check all regression gates
audit-gates:
	$(PYTHON) scripts/audit/regression_gates.py

# Check pre-merge gate only
audit-gates-pre-merge:
	$(PYTHON) scripts/audit/regression_gates.py --gate pre-merge

# Check pre-release gate only
audit-gates-pre-release:
	$(PYTHON) scripts/audit/regression_gates.py --gate pre-release

# Run full regression audit (risk matrix + gates)
audit-full:
	@echo "Running full regression audit..."
	$(PYTHON) scripts/audit/risk_matrix.py --delta
	$(PYTHON) scripts/audit/regression_gates.py
	@echo "Audit complete. Reports in docs/audits/regression/"

# ────────────────────────────────
# Pass 2: Heuristic Intelligence
#
# Rationale:
# - Trap detection for preventable patterns
# - Ritual automation for recurring reviews
# - All report-only by default
# ────────────────────────────────

# Detect preventable traps in changed files
audit-traps:
	$(PYTHON) scripts/audit/trap_detector.py

# Generate weekly ritual agenda
audit-ritual-weekly:
	$(PYTHON) scripts/audit/ritual.py --cadence weekly

# Generate monthly ritual agenda
audit-ritual-monthly:
	$(PYTHON) scripts/audit/ritual.py --cadence monthly

# Generate quarterly ritual agenda
audit-ritual-quarterly:
	$(PYTHON) scripts/audit/ritual.py --cadence quarterly

# ────────────────────────────────
# Heartbeat Orchestrator
#
# Runs Beta Release Sentinel (always), Daily Dev Blog ingestion,
# and Resonant Constructs Daily Insight generator in one pass.
#
# Usage:
#   make heartbeat DATE=2026-05-14 DEV_BLOG_SOURCE=docs/Website/dev-blog/README.md INSIGHT_SOURCE=docs/ResonantConstructs/daily-insights/README.md FORCE=1
#
#   make heartbeat   # defaults to today, skips dev-blog and insight unless sources provided
# ────────────────────────────────
heartbeat:
	@DATE="$${DATE:-$$(date +%Y-%m-%d)}"; \
	CMD="$(PYTHON) scripts/content/run_heartbeat_orchestrator.py --date $$DATE"; \
	if [ -n "$${DEV_BLOG_SOURCE:-}" ]; then \
		CMD="$$CMD --dev-blog-source $$DEV_BLOG_SOURCE"; \
	else \
		CMD="$$CMD --skip-dev-blog"; \
	fi; \
	if [ -n "$${INSIGHT_SOURCE:-}" ]; then \
		for src in $$INSIGHT_SOURCE; do \
			CMD="$$CMD --insight-source $$src"; \
		done; \
	else \
		CMD="$$CMD --skip-daily-insight"; \
	fi; \
	if [ "$${FORCE:-}" = "1" ]; then \
		CMD="$$CMD --force"; \
	fi; \
	echo "Running: $$CMD"; \
	$$CMD

# Review a heartbeat run report for the given date.
#
# Usage:
#   make heartbeat-review DATE=2026-05-14
#   make heartbeat-review DATE=2026-05-14 STRICT=1
#   make heartbeat-review   # defaults to today
heartbeat-review:
	@DATE="$${DATE:-$$(date +%Y-%m-%d)}"; \
	CMD="$(PYTHON) scripts/content/review_heartbeat_run.py --date $$DATE"; \
	if [ "$${STRICT:-}" = "1" ]; then \
		CMD="$$CMD --strict"; \
	fi; \
	$$CMD

# Stage heartbeat artifacts into a flat outbox directory.
#
# Usage:
#   make heartbeat-stage DATE=2026-05-14
#   make heartbeat-stage DATE=2026-05-14 FORCE=1
#   make heartbeat-stage   # defaults to today
heartbeat-stage:
	@DATE="$${DATE:-$$(date +%Y-%m-%d)}"; \
	CMD="$(PYTHON) scripts/content/stage_heartbeat_outbox.py --date $$DATE"; \
	if [ "$${FORCE:-}" = "1" ]; then \
		CMD="$$CMD --force"; \
	fi; \
	$$CMD

# Inspect a staged heartbeat outbox directory.
#
# Usage:
#   make heartbeat-inspect DATE=2026-05-14
#   make heartbeat-inspect   # defaults to today
heartbeat-inspect:
	@DATE="$${DATE:-$$(date +%Y-%m-%d)}"; \
	$(PYTHON) scripts/content/inspect_heartbeat_outbox.py --date $$DATE

# Inspect a staged heartbeat outbox directory (alias).
#
# Usage:
#   make heartbeat-outbox DATE=2026-05-14
#   make heartbeat-outbox DATE=2026-05-14 STRICT=1
#   make heartbeat-outbox   # defaults to today
heartbeat-outbox:
	@DATE="$${DATE:-$$(date +%Y-%m-%d)}"; \
	CMD="$(PYTHON) scripts/content/inspect_heartbeat_outbox.py --date $$DATE"; \
	if [ "$${STRICT:-}" = "1" ]; then \
		CMD="$$CMD --strict"; \
	fi; \
	$$CMD

# Full end-to-end heartbeat pipeline: run, review, stage, inspect.
# Stops on the first failed step.
#
# Usage:
#   make heartbeat-full DEV_BLOG_SOURCE=docs/Website/dev-blog/README.md INSIGHT_SOURCE="docs/ResonantConstructs/daily-insights/README.md" FORCE=1
#   make heartbeat-full   # beta-only (dev-blog and insight auto-skipped)
#   make heartbeat-full STRICT=1   # strict review and inspection
#
# Pass-through variables:
#   DATE             -> all four child targets
#   DEV_BLOG_SOURCE  -> heartbeat
#   INSIGHT_SOURCE   -> heartbeat
#   FORCE=1          -> heartbeat, heartbeat-stage
#   STRICT=1         -> heartbeat-review, heartbeat-outbox
heartbeat-full:
	@echo "=== Heartbeat Full Pipeline ==="
	@echo "Step 1/4: heartbeat"
	@$(MAKE) heartbeat || { echo "ERROR: heartbeat failed"; exit 1; }
	@echo "Step 2/4: heartbeat-review"
	@$(MAKE) heartbeat-review || { echo "ERROR: heartbeat-review failed"; exit 1; }
	@echo "Step 3/4: heartbeat-stage"
	@$(MAKE) heartbeat-stage || { echo "ERROR: heartbeat-stage failed"; exit 1; }
	@echo "Step 4/4: heartbeat-outbox"
	@$(MAKE) heartbeat-outbox || { echo "ERROR: heartbeat-outbox failed"; exit 1; }
	@echo "=== Heartbeat Full Pipeline Complete ==="

# Build the public portal staging tree
public-export:
	bash scripts/release/export_public_directory.sh

# Sync the public portal staging tree into a fresh repo path: make public-sync target=/path/to/repo
public-sync:
	@if [ -z "$(target)" ]; then \
		echo "Usage: make public-sync target=/path/to/fresh-repo"; \
		exit 1; \
	fi
	bash scripts/release/sync_public_directory.sh "$(target)"

# Publish the current snapshot into the public repo and push origin/main
public-publish:
	@if [ -z "$(target)" ]; then \
		echo "Usage: make public-publish target=/path/to/public-repo [message=...]"; \
		exit 1; \
	fi
	bash scripts/release/publish_public_portal.sh "$(target)" "$(message)"

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

# Generate codemap snapshot artifact for CI maintenance workflow
codemap:
	@set -eu; \
	python guardian/codemap/generate_codemap.py; \
	target="$${CODEMAP_PATH:-artifacts/codemap/codemap-$$(date -u +%Y%m%d-%H%M%S).json}"; \
	mkdir -p "$$(dirname "$$target")"; \
	cp guardian/codemap/codemap.json "$$target"; \
	echo "Codemap snapshot written to $$target"

# Clean codemap snapshots
codemap-clean:
	@ls -1t artifacts/codemap/*.json 2>/dev/null | tail -n +$$((KEEP + 1)) | xargs -r rm -f

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

# ────────────────────────────────
# Docker Compose shortcuts
#
# Rationale:
# - Keep everything attached to the repo (not your machine), using --env-file.
# - Provide a quick “rendered config” view (config --no-interpolate) to verify
#   variables are filling as expected and secrets aren’t accidentally inlined.
#
# Notes:
# - `make logs` is already taken (Guardian memory logs), so Docker logs are `dlogs`.
# - If you don’t have a separate prod env file yet, create `.env.prod` later.
# ────────────────────────────────

COMPOSE   ?= docker compose
DEV_ENV   ?= .env
PROD_ENV  ?= .env.prod

.PHONY: up down restart ps dlogs cfg cfgredact cfgsec \
	up-prod down-prod restart-prod ps-prod dlogs-prod cfg-prod cfgredact-prod cfgsec-prod

# Dev (defaults to .env)
up:
	$(COMPOSE) --env-file $(DEV_ENV) up -d --build

down:
	$(COMPOSE) --env-file $(DEV_ENV) down

restart:
	$(COMPOSE) --env-file $(DEV_ENV) restart

ps:
	$(COMPOSE) --env-file $(DEV_ENV) ps

dlogs:
	$(COMPOSE) --env-file $(DEV_ENV) logs -f --tail=200

# Build shareable collaborator dossier (technical teaser profile)
dossier-collab:
	bash scripts/docs/build_collab_dossier.sh --profile $${PROFILE:-technical-teaser}

# Render the fully merged compose (WITHOUT interpolating ${...} from env/shell)
cfg:
	$(COMPOSE) --env-file $(DEV_ENV) config --no-interpolate

# Render the fully merged compose with secrets redacted (handy for screenshots/PRs)
cfgredact:
	$(COMPOSE) --env-file $(DEV_ENV) config --no-interpolate | sed -E 's/^([[:space:]]*NEO4J_PASS:[[:space:]]+).*/\1<redacted>/'

# - Should NOT hardcode NEO4J_PASS as a literal in docker-compose.yml
cfgsec:
	@$(COMPOSE) --env-file $(DEV_ENV) config --no-interpolate | rg -n 'bolt://.*@' || true
	@rg -n '^[[:space:]]*NEO4J_PASS:[[:space:]]+[^$$]' docker-compose.yml || true
	@echo "[cfgsec] NOTE: It's normal for 'docker compose config' to show resolved env values (including NEO4J_PASS). This check only flags (a) credentials embedded in bolt:// URLs and (b) hardcoded NEO4J_PASS literals in docker-compose.yml."

# Prod (defaults to .env.prod)
up-prod:
	$(COMPOSE) --env-file $(PROD_ENV) up -d --build

down-prod:
	$(COMPOSE) --env-file $(PROD_ENV) down

restart-prod:
	$(COMPOSE) --env-file $(PROD_ENV) restart

ps-prod:
	$(COMPOSE) --env-file $(PROD_ENV) ps

dlogs-prod:
	$(COMPOSE) --env-file $(PROD_ENV) logs -f --tail=200

cfg-prod:
	$(COMPOSE) --env-file $(PROD_ENV) config --no-interpolate

# Render the fully merged compose (prod) with secrets redacted
cfgredact-prod:
	@test -f $(PROD_ENV) || { echo "[cfgredact-prod] NOTE: $(PROD_ENV) not found; skipping compose config check"; exit 0; }
	$(COMPOSE) --env-file $(PROD_ENV) config --no-interpolate | sed -E 's/^([[:space:]]*NEO4J_PASS:[[:space:]]+).*/\1<redacted>/'

cfgsec-prod:
	@test -f $(PROD_ENV) || { echo "[cfgsec-prod] NOTE: $(PROD_ENV) not found; skipping compose config check"; exit 0; }
	@$(COMPOSE) --env-file $(PROD_ENV) config --no-interpolate | rg -n 'bolt://.*@' || true
	@rg -n '^[[:space:]]*NEO4J_PASS:[[:space:]]+[^$$]' docker-compose.yml || true
	@echo "[cfgsec-prod] NOTE: It's normal for 'docker compose config' to show resolved env values (including NEO4J_PASS). This check only flags (a) credentials embedded in bolt:// URLs and (b) hardcoded NEO4J_PASS literals in docker-compose.yml."
