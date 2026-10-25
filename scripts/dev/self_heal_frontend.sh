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

LFS_POINTER_MARKER="https://git-lfs.github.com/spec/v1"

echo "📦 Frontend self-heal starting..."

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

# True (0) when the file holds a Git LFS pointer rather than real content.
is_lfs_pointer() {
  grep -q "${LFS_POINTER_MARKER}" "$1" 2>/dev/null
}

# Validate a candidate restoration for one artifact kind.
#
#   json      a package manifest; must parse as a JSON object
#   workspace the pnpm workspace file; must declare a non-empty package list
#   lockfile  the pnpm lockfile; must carry a version and an importer map
#
# Exits non-zero for empty content, for an unresolved LFS pointer, and for
# malformed content, so an unusable candidate can never replace a good file.
validate_candidate() {
  local file="$1"
  local kind="$2"

  python3 -c '
import json, re, sys

path, kind = sys.argv[1], sys.argv[2]
marker = "https://git-lfs.github.com/spec/v1"

try:
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
except OSError:
    sys.exit(1)

if not text.strip():
    sys.exit(1)
if marker in text:
    sys.exit(1)

if kind == "json":
    try:
        data = json.loads(text)
    except ValueError:
        sys.exit(1)
    sys.exit(0 if isinstance(data, dict) else 1)

required = {
    "workspace": ("packages:",),
    "lockfile": ("lockfileVersion:", "importers:"),
}[kind]
for entry in required:
    if not re.search(r"(?m)^" + re.escape(entry), text):
        sys.exit(1)

try:
    import yaml
except ImportError:
    sys.exit(0)

try:
    data = yaml.safe_load(text)
except Exception:
    sys.exit(1)
if not isinstance(data, dict):
    sys.exit(1)
if kind == "workspace":
    packages = data.get("packages")
    if not isinstance(packages, list) or not packages:
        sys.exit(1)
elif "lockfileVersion" not in data or "importers" not in data:
    sys.exit(1)
sys.exit(0)
' "$file" "$kind" >/dev/null 2>&1
}

# Permission bits of the destination, or nothing when it does not exist.
mode_of() {
  local target="$1"

  [ -e "$target" ] || return 0
  stat -c '%a' "$target" 2>/dev/null || stat -f '%Lp' "$target" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# Restoration
# ---------------------------------------------------------------------------

# Materialize an LFS pointer into the output file.
#
# git-lfs can copy the pointer to stdout unchanged and still exit zero: with
# GIT_LFS_SKIP_SMUDGE=1 the pointer is passed through verbatim, and a failed
# download can leave partial output behind. A non-empty result is therefore
# never evidence of success. One bounded fetch-and-retry is allowed, and the
# result must validate before it is accepted.
materialize_lfs() {
  local pointer="$1"
  local out="$2"
  local kind="$3"
  local path="$4"

  if git lfs smudge < "$pointer" > "$out" 2>/dev/null; then
    if validate_candidate "$out" "$kind"; then
      return 0
    fi
  fi

  # The object may not be cached locally yet. One bounded fetch, one retry.
  git lfs pull "$BASE_REMOTE" "$BASE_BRANCH" --include="$path" >/dev/null 2>&1 || true
  if git lfs smudge < "$pointer" > "$out" 2>/dev/null; then
    if validate_candidate "$out" "$kind"; then
      return 0
    fi
  fi

  return 1
}

# Restore one tracked artifact from the base ref.
#
# The destination is replaced only after the candidate has been validated, and
# the replacement is a same-filesystem rename so the destination is never
# observed half-written. If anything fails, the destination keeps its original
# bytes.
restore_from_base() {
  local path="$1"
  local target="$2"
  local kind="$3"
  local raw candidate target_mode

  if [ ! -d "$(dirname "$target")" ]; then
    echo "❌ Cannot restore ${path}: $(dirname "$target") does not exist." >&2
    return 1
  fi

  raw="$(mktemp "${target}.heal.raw.XXXXXX")"
  candidate="$(mktemp "${target}.heal.candidate.XXXXXX")"

  if ! git show "${BASE_REF}:${path}" > "$raw" 2>/dev/null; then
    rm -f "$raw" "$candidate" 2>/dev/null || true
    echo "❌ Could not read ${path} from ${BASE_REF}." >&2
    return 1
  fi

  if is_lfs_pointer "$raw"; then
    if ! materialize_lfs "$raw" "$candidate" "$kind" "$path"; then
      rm -f "$raw" "$candidate" 2>/dev/null || true
      echo "❌ Could not materialize the Git LFS object for ${path} from ${BASE_REF}." >&2
      return 1
    fi
  else
    cat "$raw" > "$candidate"
  fi

  if ! validate_candidate "$candidate" "$kind"; then
    rm -f "$raw" "$candidate" 2>/dev/null || true
    echo "❌ Restored content for ${path} did not pass validation; ${target} was left untouched." >&2
    return 1
  fi

  # The atomic replace swaps in a new inode, so carry the destination's
  # permission bits across; mktemp creates the candidate as 0600.
  target_mode="$(mode_of "$target")"
  if [ -n "$target_mode" ]; then
    chmod "$target_mode" "$candidate" 2>/dev/null || true
  fi

  # The candidate sits next to the destination, so this is an atomic rename on
  # the same filesystem rather than a copy that could truncate the target.
  if ! mv -f "$candidate" "$target"; then
    rm -f "$raw" "$candidate" 2>/dev/null || true
    echo "❌ Could not replace ${target}; the original file was left untouched." >&2
    return 1
  fi

  rm -f "$raw" 2>/dev/null || true
  echo "✅ Restored ${target} from ${BASE_REF}."
}

# True (0) when the destination is missing or does not pass validation.
needs_restore() {
  local target="$1"
  local kind="$2"

  [ -f "$target" ] || return 0
  validate_candidate "$target" "$kind" || return 0
  return 1
}

# Restore one artifact when it is missing or unhealthy.
restore_artifact() {
  local path="$1"
  local target="$2"
  local kind="$3"

  if needs_restore "$target" "$kind"; then
    echo "⚠️  ${target} missing or unhealthy. Restoring from ${BASE_REF}..."
    if ! restore_from_base "$path" "$target" "$kind"; then
      echo "❌ Self-heal aborted: ${target} could not be restored. The original file was left untouched and no installation was attempted." >&2
      return 1
    fi
  else
    echo "✅ ${target} looks sane."
  fi
}

# ---------------------------------------------------------------------------
# 1) Canonical manifests, workspace, and lockfile
# ---------------------------------------------------------------------------

restore_artifact "package.json" "$ROOT_PKG_JSON" "json" || exit 1
restore_artifact "pnpm-workspace.yaml" "$ROOT_WORKSPACE" "workspace" || exit 1
restore_artifact "frontend/src/package.json" "$APP_PKG_JSON" "json" || exit 1
restore_artifact "frontend/package.json" "$HUB_PKG_JSON" "json" || exit 1
restore_artifact "pnpm-lock.yaml" "$ROOT_LOCKFILE" "lockfile" || exit 1

# ---------------------------------------------------------------------------
# 2) Install from the canonical workspace root
# ---------------------------------------------------------------------------

echo "📥 Running pnpm install at the workspace root..."
cd "$REPO_ROOT"

# A frozen install is the only safe self-heal outcome: it fails instead of
# rewriting the canonical lockfile, so dependency resolution can never change
# during a restorative operation.
if ! pnpm install --frozen-lockfile; then
  echo "❌ Frozen installation failed." >&2
  echo "   The canonical lockfile was not modified." >&2
  echo "   A frozen install failure means the manifests and pnpm-lock.yaml disagree, or the install environment is broken." >&2
  echo "   Regenerating the lockfile is a separate, explicitly authorized maintenance operation; self-heal does not do it." >&2
  exit 1
fi

echo "✅ Frontend self-heal complete."
