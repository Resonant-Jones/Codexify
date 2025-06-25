.PHONY: test lint format check setup dev diagnose clean

ENV_FILE=.env

## Run tests with verbose output
test:
	pytest -v

## Lint Python files using flake8
lint:
	flake8 . --statistics --count --show-source --max-line-length=120

## Format code using black
format:
	black .

## Run linting and tests
check: lint test

## Install requirements
setup:
	@if [ -f requirements.txt ]; then \
		echo "Installing requirements..."; \
		pip install -r requirements.txt; \
	else \
		echo "No requirements.txt found."; \
	fi

## Start dev server with hot reload
dev:
	@echo "Starting FastAPI server with live reload..."
	@if [ -f $(ENV_FILE) ]; then \
		export $$(cat $(ENV_FILE) | xargs); \
	fi && \
	uvicorn guardian.main:app --reload --host 0.0.0.0 --port 8000

## Diagnose environment and dependencies
diagnose:
	@echo "Python version: $$(python --version)"
	@echo "Virtualenv: $$(which python)"
	@echo "Checking required tools..."
	@command -v uvicorn >/dev/null 2>&1 || { echo >&2 "Missing: uvicorn"; exit 1; }
	@command -v pytest >/dev/null 2>&1 || { echo >&2 "Missing: pytest"; exit 1; }
	@command -v flake8 >/dev/null 2>&1 || { echo >&2 "Missing: flake8"; exit 1; }
	@echo "All tools present."

## Clean Python cache files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -r {} +
