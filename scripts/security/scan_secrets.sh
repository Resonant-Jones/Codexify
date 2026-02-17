#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

echo "[scan] quick git grep checks"
PATTERNS=(
  "token.json"
  "client_secret"
  "refresh_token"
  "GUARDIAN_API_KEY"
)

for pat in "${PATTERNS[@]}"; do
  echo "[scan] pattern: $pat"
  git grep -n -I "$pat" -- . \
    ':(exclude)node_modules/*' \
    ':(exclude).venv/*' \
    ':(exclude).pnpm-store/*' || true
done

if command -v detect-secrets >/dev/null 2>&1; then
  echo "[scan] detect-secrets available"
  detect-secrets scan || true
else
  echo "[scan] detect-secrets not installed; skipping"
fi

if command -v gitleaks >/dev/null 2>&1; then
  echo "[scan] gitleaks available"
  gitleaks detect --no-git --source . || true
else
  echo "[scan] gitleaks not installed; skipping"
fi
