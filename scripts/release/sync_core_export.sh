#!/usr/bin/env bash
#
# sync_core_export.sh
# -------------------
# Sync the active Codexify core source from the parent repo into the sibling
# Publishing_Portal/Core/ target directory.
#
# This is a local-only source-mirror workflow. It does not publish remotely.
# The Publishing_Portal owns its own Git history and must not be tracked by
# the parent Codexify repo.
#
# Default invocation:
#   bash scripts/release/sync_core_export.sh
#
# Options:
#   --target <path>   Override the default target (default: ../Publishing_Portal/Core)
#   --dry-run         Print what would be copied without changing the target
#   --commit          After a successful sync, commit Core/ inside Publishing_Portal
#
# The script must be run from the Codexify repo root.

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_TARGET="../Publishing_Portal/Core"
DRY_RUN=false
DO_COMMIT=false
TARGET=""

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      shift
      if [[ $# -eq 0 ]]; then
        echo "ERROR: --target requires a path argument" >&2
        exit 1
      fi
      TARGET="$1"
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --commit)
      DO_COMMIT=true
      shift
      ;;
    *)
      echo "ERROR: Unknown option: $1" >&2
      echo "Usage: $0 [--target <path>] [--dry-run] [--commit]" >&2
      exit 1
      ;;
  esac
done

# Apply default target if not overridden
if [[ -z "$TARGET" ]]; then
  TARGET="$DEFAULT_TARGET"
fi

# Resolve to absolute path for clarity in messages
TARGET_ABS="$(cd "$(dirname "$TARGET")" 2>/dev/null && pwd)/$(basename "$TARGET")" || TARGET_ABS="$TARGET"

# ---------------------------------------------------------------------------
# Validate we are running from the Codexify repo root
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# We check relative to REPO_ROOT, but the guard is that the CWD is the repo root.
REQUIRED_MARKERS=("guardian" "frontend" "docker-compose.yml" ".git")
MISSING_MARKERS=()
for marker in "${REQUIRED_MARKERS[@]}"; do
  if [[ ! -e "$REPO_ROOT/$marker" ]]; then
    MISSING_MARKERS+=("$marker")
  fi
done

# Also ensure we're actually IN the repo root, not just pointing at it
if [[ "$(pwd)" != "$REPO_ROOT" ]]; then
  echo "ERROR: This script must be run from the Codexify repo root: $REPO_ROOT" >&2
  echo "Current directory: $(pwd)" >&2
  exit 1
fi

if [[ ${#MISSING_MARKERS[@]} -gt 0 ]]; then
  echo "ERROR: Required repo-root markers missing:" >&2
  for m in "${MISSING_MARKERS[@]}"; do
    echo "  - $m" >&2
  done
  echo "This script must be run from the Codexify repo root." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Validate the portal repo exists
# ---------------------------------------------------------------------------
PORTAL_REPO_DIR=""
if [[ "$TARGET" == "$DEFAULT_TARGET" ]]; then
  PORTAL_REPO_DIR="$REPO_ROOT/../Publishing_Portal"
else
  # For custom targets, check the parent of the target for .git
  PORTAL_REPO_DIR="$(dirname "$(cd "$(dirname "$TARGET")" 2>/dev/null && pwd || echo "$(dirname "$TARGET")")")"
fi

PORTAL_GIT="$PORTAL_REPO_DIR/.git"
if [[ ! -e "$PORTAL_GIT" ]]; then
  echo "ERROR: Publishing Portal repo not found at: $PORTAL_GIT" >&2
  echo "The sibling Publishing_Portal/ directory must exist and contain its own .git." >&2
  echo "Expected location: $PORTAL_REPO_DIR" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Source roots and files to include (when present)
# ---------------------------------------------------------------------------
INCLUDE_ROOTS=(
  "backend"
  "guardian"
  "frontend"
  "src-tauri"
  "config"
  "scripts"
  "tests"
)

INCLUDE_FILES=(
  "alembic.ini"
  "docker-compose.yml"
  "Dockerfile"
  "Makefile"
  "package.json"
  "pnpm-lock.yaml"
  "pyproject.toml"
  "requirements.txt"
  "requirements-dev.txt"
  ".env.example"
  ".env.template"
  "README.md"
  "AUTHORIZATION.md"
)

INCLUDE_DOCS_SUBSET=(
  "docs/architecture"
  "docs/release"
  "docs/dev"
  "docs/tasks"
  "docs/Campaign"
)

# ---------------------------------------------------------------------------
# Exclusion patterns for rsync
# ---------------------------------------------------------------------------
EXCLUDE_PATTERNS=(
  ".git/"
  ".env"
  ".env.*"
  "node_modules/"
  ".venv/"
  "venv/"
  "__pycache__/"
  ".pytest_cache/"
  ".mypy_cache/"
  ".ruff_cache/"
  ".cache/"
  "dist/"
  "build/"
  "coverage/"
  ".DS_Store"
  "*.log"
  "*.db"
  "*.sqlite"
  "tmp/"
  "scratch/"
  "Publishing_Portal/"
  "Codexify-Beta/"
  "releases/Codexify-Beta/"
  "docs/Marketing/generated/"
  "docs/audits/daily/"
  "docs/audits/latest.json"
  "docs/audits/latest.md"
)

# ---------------------------------------------------------------------------
# Check rsync availability
# ---------------------------------------------------------------------------
if ! command -v rsync &>/dev/null; then
  echo "ERROR: rsync is required but not available on this system." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Source repo metadata for the manifest
# ---------------------------------------------------------------------------
SOURCE_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
SOURCE_COMMIT="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")"
SOURCE_DIRTY="false"
if ! git -C "$REPO_ROOT" diff-index --quiet HEAD -- 2>/dev/null; then
  SOURCE_DIRTY="true"
fi

# ---------------------------------------------------------------------------
# Build rsync arguments
# ---------------------------------------------------------------------------
RSYNC_ARGS=()
RSYNC_ARGS+=("-a")          # archive mode
RSYNC_ARGS+=("--delete")    # delete files in target not present in source

if [[ "$DRY_RUN" == "true" ]]; then
  RSYNC_ARGS+=("--dry-run")
  RSYNC_ARGS+=("-v")        # verbose for dry-run so user can see what would happen
fi

# Include rules must come BEFORE exclude rules in rsync.
# .env.example and .env.template are excluded by the ".env.*" pattern;
# we re-include them explicitly by placing include rules first.
RSYNC_ARGS+=("--include=.env.example")
RSYNC_ARGS+=("--include=.env.template")

# Add exclude patterns
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
  RSYNC_ARGS+=("--exclude=$pattern")
done

# ---------------------------------------------------------------------------
# Display configuration
# ---------------------------------------------------------------------------
echo "=== Codexify Core Export Sync ==="
echo "Source repo: $REPO_ROOT"
echo "Branch:      $SOURCE_BRANCH"
echo "Commit:      $SOURCE_COMMIT"
echo "Dirty:       $SOURCE_DIRTY"
echo "Target:      $TARGET_ABS"
echo "Portal repo: $PORTAL_REPO_DIR"
echo "Mode:        $([ "$DRY_RUN" = "true" ] && echo "DRY RUN" || echo "LIVE")"
echo "Commit:      $([ "$DO_COMMIT" = "true" ] && echo "YES" || echo "NO")"
echo ""

# ---------------------------------------------------------------------------
# Create target directory if needed (not in dry-run)
# ---------------------------------------------------------------------------
if [[ "$DRY_RUN" == "false" ]]; then
  mkdir -p "$TARGET"
fi

# ---------------------------------------------------------------------------
# Sync each source root and file
# ---------------------------------------------------------------------------
SYNCED_COUNT=0
SKIPPED_COUNT=0

echo "--- Syncing source roots ---"
for root in "${INCLUDE_ROOTS[@]}"; do
  if [[ -d "$REPO_ROOT/$root" ]]; then
    echo "  + $root/"
    if [[ "$DRY_RUN" == "false" ]]; then
      rsync "${RSYNC_ARGS[@]}" "$REPO_ROOT/$root/" "$TARGET/$root/"
    else
      rsync "${RSYNC_ARGS[@]}" "$REPO_ROOT/$root/" "$TARGET/$root/" 2>&1 || true
    fi
    ((SYNCED_COUNT++)) || true
  else
    echo "  - $root/ (not present, skipping)"
    ((SKIPPED_COUNT++)) || true
  fi
done

echo ""
echo "--- Syncing root files ---"
for file in "${INCLUDE_FILES[@]}"; do
  if [[ -f "$REPO_ROOT/$file" ]]; then
    echo "  + $file"
    if [[ "$DRY_RUN" == "false" ]]; then
      rsync "${RSYNC_ARGS[@]}" "$REPO_ROOT/$file" "$TARGET/$file"
    else
      rsync "${RSYNC_ARGS[@]}" "$REPO_ROOT/$file" "$TARGET/$file" 2>&1 || true
    fi
    ((SYNCED_COUNT++)) || true
  else
    echo "  - $file (not present, skipping)"
    ((SKIPPED_COUNT++)) || true
  fi
done

echo ""
echo "--- Syncing curated docs ---"
for doc_dir in "${INCLUDE_DOCS_SUBSET[@]}"; do
  if [[ -d "$REPO_ROOT/$doc_dir" ]]; then
    echo "  + $doc_dir/"
    if [[ "$DRY_RUN" == "false" ]]; then
      mkdir -p "$TARGET/$doc_dir"
      rsync "${RSYNC_ARGS[@]}" "$REPO_ROOT/$doc_dir/" "$TARGET/$doc_dir/"
    else
      rsync "${RSYNC_ARGS[@]}" "$REPO_ROOT/$doc_dir/" "$TARGET/$doc_dir/" 2>&1 || true
    fi
    ((SYNCED_COUNT++)) || true
  else
    echo "  - $doc_dir/ (not present, skipping)"
    ((SKIPPED_COUNT++)) || true
  fi
done

# ---------------------------------------------------------------------------
# Clean up any stale doc dirs in target that we no longer sync
# (rsync --delete handles files within synced dirs, but we need to remove
#  docs directories we no longer include in the subset)
# Only in live mode, and only remove docs/ subdirs we used to sync but don't anymore.
# We handle this by syncing a minimal empty structure, then removing anything
# under docs/ that isn't in the approved subset. This is safe because we ONLY
# remove subdirectories we created ourselves in the target.
if [[ "$DRY_RUN" == "false" ]] && [[ -d "$TARGET/docs" ]]; then
  KNOWN_DOC_DIRS=()
  for doc_dir in "${INCLUDE_DOCS_SUBSET[@]}"; do
    KNOWN_DOC_DIRS+=("$(basename "$doc_dir")")
  done
  for existing in "$TARGET/docs"/*/; do
    [[ -d "$existing" ]] || continue
    dir_name="$(basename "$existing")"
    allowed=false
    for known in "${KNOWN_DOC_DIRS[@]}"; do
      if [[ "$dir_name" == "$known" ]]; then
        allowed=true
        break
      fi
    done
    if [[ "$allowed" == "false" ]]; then
      echo "  Removing stale doc dir from target: docs/$dir_name/"
      rm -rf "$existing"
    fi
  done
fi

# ---------------------------------------------------------------------------
# Generate manifest (in live mode only)
# ---------------------------------------------------------------------------
if [[ "$DRY_RUN" == "false" ]]; then
  GENERATED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

  # Build included_roots array for the manifest (only directories that exist)
  MANIFEST_ROOTS="["
  first=true
  for root in "${INCLUDE_ROOTS[@]}"; do
    if [[ -d "$REPO_ROOT/$root" ]]; then
      if [[ "$first" == "false" ]]; then MANIFEST_ROOTS+=", "; fi
      MANIFEST_ROOTS+="\"$root\""
      first=false
    fi
  done
  for file in "${INCLUDE_FILES[@]}"; do
    if [[ -f "$REPO_ROOT/$file" ]]; then
      if [[ "$first" == "false" ]]; then MANIFEST_ROOTS+=", "; fi
      MANIFEST_ROOTS+="\"$file\""
      first=false
    fi
  done
  for doc_dir in "${INCLUDE_DOCS_SUBSET[@]}"; do
    if [[ -d "$REPO_ROOT/$doc_dir" ]]; then
      if [[ "$first" == "false" ]]; then MANIFEST_ROOTS+=", "; fi
      MANIFEST_ROOTS+="\"$doc_dir\""
      first=false
    fi
  done
  MANIFEST_ROOTS+="]"

  # Build excluded_patterns array
  MANIFEST_EXCLUDES="["
  first=true
  for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    if [[ "$first" == "false" ]]; then MANIFEST_EXCLUDES+=", "; fi
    MANIFEST_EXCLUDES+="\"$pattern\""
    first=false
  done
  MANIFEST_EXCLUDES+="]"

  MANIFEST_PATH="$TARGET/CORE_EXPORT_MANIFEST.json"
  cat > "$MANIFEST_PATH" <<MANIFEST_EOF
{
  "export_kind": "codexify_core_source_mirror",
  "generated_at": "$GENERATED_AT",
  "source_branch": "$SOURCE_BRANCH",
  "source_commit": "$SOURCE_COMMIT",
  "source_repo_path": "$REPO_ROOT",
  "target_path": "$TARGET_ABS",
  "source_dirty": $SOURCE_DIRTY,
  "included_roots": $MANIFEST_ROOTS,
  "excluded_patterns": $MANIFEST_EXCLUDES,
  "do_not_edit_notice": "Publishing_Portal/Core/ is generated output. The source of truth is the parent Codexify repo. Do not edit files here as the canonical source."
}
MANIFEST_EOF

  echo ""
  echo "--- Manifest ---"
  echo "Written: $MANIFEST_PATH"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=== Sync Complete ==="
echo "Synced:  $SYNCED_COUNT"
echo "Skipped: $SKIPPED_COUNT"
echo "Target:  $TARGET_ABS"
echo "Mode:    $([ "$DRY_RUN" = "true" ] && echo "DRY RUN (no changes made)" || echo "LIVE")"

# ---------------------------------------------------------------------------
# Commit inside Publishing_Portal if requested
# ---------------------------------------------------------------------------
if [[ "$DO_COMMIT" == "true" ]] && [[ "$DRY_RUN" == "false" ]]; then
  echo ""
  echo "--- Committing in Publishing_Portal ---"

  PORTAL_ROOT="$PORTAL_REPO_DIR"
  CORE_REL="$(realpath --relative-to="$PORTAL_ROOT" "$TARGET_ABS" 2>/dev/null || echo "Core")"

  # Stage only Core/
  git -C "$PORTAL_ROOT" add "$CORE_REL" 2>&1

  # Check if there are changes to commit
  if git -C "$PORTAL_ROOT" diff --cached --quiet 2>/dev/null; then
    echo "No changes to commit in Publishing_Portal (Core/ is already up to date)."
  else
    git -C "$PORTAL_ROOT" commit -m "Refresh Codexify core mirror" 2>&1
    echo "Committed: Refresh Codexify core mirror"
    echo "Commit hash: $(git -C "$PORTAL_ROOT" rev-parse --short HEAD)"
  fi

  echo "NOTE: The sync workflow does not push. To publish, push manually from inside Publishing_Portal."
fi

echo ""
echo "Done."
