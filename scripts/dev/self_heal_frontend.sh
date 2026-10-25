#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"

# The canonical dependency authority is the root pnpm workspace.
# `frontend/` is a script hub, not an install root, and `frontend/src/package.json`
# is the application manifest.
ROOT_PKG_JSON="$REPO_ROOT/package.json"
ROOT_WORKSPACE="$REPO_ROOT/pnpm-workspace.yaml"
ROOT_LOCKFILE="$REPO_ROOT/pnpm-lock.yaml"
APP_PKG_JSON="$REPO_ROOT/frontend/src/package.json"
HUB_PKG_JSON="$REPO_ROOT/frontend/package.json"

BASE_REF="${SELF_HEAL_BASE_REF:-origin/main}"
BASE_REMOTE="${BASE_REF%%/*}"
BASE_BRANCH="${BASE_REF#*/}"

echo "📦 Frontend self-heal starting..."

# Restore a tracked file from the base ref.
#
# Every `*.json` file in this repository is tracked by Git LFS, so a plain
# `git show <ref>:<path>` writes the LFS *pointer* rather than the real file.
# Restoring that pointer produces a manifest that cannot be parsed and that
# pnpm silently ignores, which is exactly the failure this script exists to
# repair. Smudge the pointer so the actual content lands on disk.
restore_from_base() {
  local path="$1"
  local target="$2"
  local tmp real

  tmp="$(mktemp "${target}.heal.XXXXXX")"
  real="$(mktemp "${target}.lfs.XXXXXX")"

  if ! git show "${BASE_REF}:${path}" > "$tmp" 2>/dev/null; then
    rm -f "$tmp" "$real"
    echo "ℹ️  ${BASE_REF} has no ${path}; leaving ${target} as-is."
    return 1
  fi

  if grep -q "https://git-lfs.github.com/spec/v1" "$tmp" 2>/dev/null; then
    if ! git lfs smudge < "$tmp" > "$real" 2>/dev/null || [ ! -s "$real" ]; then
      # The LFS object is not cached locally yet; fetch it and retry once.
      git lfs pull "$BASE_REMOTE" "$BASE_BRANCH" --include="$path" >/dev/null 2>&1 || true
      git lfs smudge < "$tmp" > "$real" 2>/dev/null || true
    fi
    if [ -s "$real" ]; then
      cat "$real" > "$target"
      rm -f "$tmp" "$real"
      echo "✅ Restored ${target} from ${BASE_REF} (Git LFS content)."
      return 0
    fi
    rm -f "$tmp" "$real"
    echo "❌ Could not materialize the Git LFS object for ${path}."
    return 1
  fi

  cat "$tmp" > "$target"
  rm -f "$tmp" "$real"
  echo "✅ Restored ${target} from ${BASE_REF}."
}

# True (0) when the file is missing, is an LFS pointer, or (for JSON) does not
# parse. A pointer check alone is not enough: a truncated or hand-edited
# manifest is just as broken as a pointer.
needs_restore() {
  local path="$1"

  if [ ! -f "$path" ]; then
    return 0
  fi
  if grep -q "https://git-lfs.github.com/spec/v1" "$path" 2>/dev/null; then
    return 0
  fi
  case "$path" in
    *.json)
      python3 -c 'import json,sys; json.load(open(sys.argv[1], encoding="utf-8"))' \
        "$path" >/dev/null 2>&1 || return 0
      ;;
  esac
  return 1
}

# 1) Canonical manifests: root workspace + application manifest + script hub.
for entry in \
  "package.json:${ROOT_PKG_JSON}" \
  "pnpm-workspace.yaml:${ROOT_WORKSPACE}" \
  "frontend/src/package.json:${APP_PKG_JSON}" \
  "frontend/package.json:${HUB_PKG_JSON}"
do
  path="${entry%%:*}"
  target="${entry#*:}"
  if needs_restore "$target"; then
    echo "⚠️  ${target} missing or unhealthy. Restoring from ${BASE_REF}..."
    restore_from_base "$path" "$target" || true
  else
    echo "✅ ${target} looks sane."
  fi
done

# 2) The root lockfile is the only lockfile. Heal it if it is missing or broken.
if needs_restore "$ROOT_LOCKFILE"; then
  echo "⚠️  ${ROOT_LOCKFILE} missing or unhealthy. Restoring from ${BASE_REF}..."
  restore_from_base "pnpm-lock.yaml" "$ROOT_LOCKFILE" || true
else
  echo "✅ pnpm-lock.yaml present."
fi

# 3) Reinstall dependencies from the canonical workspace root.
echo "📥 Running pnpm install at the workspace root..."
cd "$REPO_ROOT"

if ! pnpm install --frozen-lockfile; then
  echo "⚠️  Frozen install failed; refreshing the canonical lockfile from the manifests..."
  pnpm install
fi

echo "✅ Frontend self-heal complete."
