#!/usr/bin/env bash
set -euo pipefail

# WARNING:
# This operation rewrites git history and is destructive.
# Run only after credential rotation and team communication.

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

if ! command -v git-filter-repo >/dev/null 2>&1; then
  echo "git-filter-repo is required. Install it first."
  exit 1
fi

BASELINE_PRE_REWRITE="${BASELINE_PRE_REWRITE:-$(git rev-parse --short origin/main 2>/dev/null || git rev-parse --short HEAD)}"
REPLACEMENTS_FILE="${REPLACEMENTS_FILE:-scripts/security/filter-repo-replacements.txt}"

echo "Rewriting all local branch/tag refs."
echo "Pre-rewrite baseline: ${BASELINE_PRE_REWRITE}"

FILTER_ARGS=(
  --force
  --refs refs/heads/*
  --refs refs/tags/*
  --path-glob '**/token.json'
  --path-glob '**/client_secret*.json'
  --path-glob '**/credentials.json'
  --path-glob 'secrets/**'
  --invert-paths
)

if [[ -f "${REPLACEMENTS_FILE}" ]]; then
  FILTER_ARGS+=(--replace-text "${REPLACEMENTS_FILE}")
else
  echo "Replacement file not found (${REPLACEMENTS_FILE}); continuing without --replace-text."
fi

git filter-repo "${FILTER_ARGS[@]}"

echo
echo "Rewrite complete."
echo "Next steps:"
echo "1) git push --force --all origin"
echo "2) git push --force --tags origin"
echo "3) Create SECURITY-REWRITE-NOTICE.md with baseline ${BASELINE_PRE_REWRITE} and post-rewrite commit hash"
echo "4) Invalidate old clones and CI caches"
