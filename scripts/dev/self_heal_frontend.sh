#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
FRONTEND_DIR="$REPO_ROOT/frontend"
PKG_JSON="$FRONTEND_DIR/package.json"
LOCKFILE="$FRONTEND_DIR/pnpm-lock.yaml"

echo "📦 Frontend self-heal starting..."

# 1) Check package.json existence and sanity
if [ ! -f "$PKG_JSON" ]; then
  echo "⚠️  $PKG_JSON missing. Restoring from origin/main..."
  git show origin/main:frontend/package.json > "$PKG_JSON"
elif grep -q "https://git-lfs.github.com/spec/v1" "$PKG_JSON"; then
  echo "⚠️  $PKG_JSON appears to be a Git LFS pointer. Restoring from origin/main..."
  git show origin/main:frontend/package.json > "$PKG_JSON"
else
  echo "✅ package.json looks sane."
fi

# 2) Optionally heal lockfile if missing
if [ ! -f "$LOCKFILE" ]; then
  echo "⚠️  $LOCKFILE missing. Restoring from origin/main..."
  git show origin/main:frontend/pnpm-lock.yaml > "$LOCKFILE" || {
    echo "ℹ️  No lockfile in origin/main; will let pnpm recreate it."
  }
else
  echo "✅ pnpm-lock.yaml present."
fi

# 3) Reinstall dependencies
echo "📥 Running pnpm install..."
cd "$FRONTEND_DIR"
pnpm install

echo "✅ Frontend self-heal complete."
