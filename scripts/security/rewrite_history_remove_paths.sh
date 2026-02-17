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

echo "Rewriting history to remove known secret-bearing paths..."

git filter-repo \
  --path guardian/secrets/client_secret_oauth.json \
  --path guardian/secrets/token.json \
  --invert-paths

echo "Done. Next manual steps:"
echo "1) Rotate/revoke affected credentials if not already done"
echo "2) Force-push rewritten refs"
echo "3) Invalidate old clones/caches"
