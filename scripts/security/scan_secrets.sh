#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

if command -v pre-commit >/dev/null 2>&1; then
  echo "[scan] pre-commit run --all-files"
  pre-commit run --all-files
else
  echo "[scan] pre-commit not installed; skipping"
fi

if command -v gitleaks >/dev/null 2>&1; then
  echo "[scan] gitleaks dir (working tree)"
  gitleaks dir . --exit-code 1
  echo "[scan] gitleaks git (full history / all refs)"
  gitleaks git . --log-opts="--all" --exit-code 1
else
  echo "[scan] gitleaks not installed"
  exit 1
fi
