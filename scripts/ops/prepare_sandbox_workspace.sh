#!/usr/bin/env bash
#
# Prepare the workspace archive consumed by the hosted sandbox adapter.
#
# The coding worker and the Guardian backend share the
# `codexify_sandbox_workspaces` volume, mounted at
# `/app/.sandbox-workspaces` in both. The worker prepares the archive here;
# the adapter uploads it to the provider sandbox and verifies its digest
# inside the sandbox before extracting it.
#
# Run this inside the worker-coding container (or anywhere that can write the
# shared volume), then export the printed path as
# `CODEXIFY_SANDBOX_WORKSPACE_ARCHIVE` for the worker service.
#
# Usage: prepare_sandbox_workspace.sh [repo-root] [output-dir]

set -euo pipefail

REPO_ROOT="${1:-/app}"
OUT_DIR="${2:-${CODEXIFY_SANDBOX_WORKSPACE_DIR:-/app/.sandbox-workspaces}}"

if [[ ! -d "$REPO_ROOT" ]]; then
  echo "repo root not found: $REPO_ROOT" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"

WORKSPACE_ID="${CODEXIFY_SANDBOX_WORKSPACE_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
ARCHIVE="$OUT_DIR/${WORKSPACE_ID}.tar"

# The archive is the sandbox's workspace. VCS metadata, dependency trees and
# build output are excluded: the sandbox gets source, not a host snapshot.
tar \
  --exclude='./.git' \
  --exclude='./node_modules' \
  --exclude='*/node_modules' \
  --exclude='./.sandbox-workspaces' \
  --exclude='./data' \
  --exclude='./models' \
  --exclude='./.chroma' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  -cf "$ARCHIVE" \
  -C "$REPO_ROOT" .

# `sha256sum` is Linux-only; the operator's macOS host has `shasum -a 256`.
if command -v sha256sum >/dev/null 2>&1; then
  DIGEST="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
else
  DIGEST="$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')"
fi

echo "$ARCHIVE"
echo "digest: $DIGEST"
echo "bytes: $(wc -c < "$ARCHIVE" | tr -d ' ')"
