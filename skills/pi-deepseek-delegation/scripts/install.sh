#!/usr/bin/env bash
set -euo pipefail

# Canonical installer for the pi-deepseek-delegation skill.
# Reads from the canonical source directory (where this script lives).
# Installs to ~/.codex/skills/pi-deepseek-delegation/ by default.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_TARGET="$HOME/.codex/skills/pi-deepseek-delegation"
TARGET="${PI_DEEPSEEK_SKILL_TARGET:-$DEFAULT_TARGET}"
ACTION=""
DRY_RUN=0
DEV_OVERRIDE=0

DEPLOYABLE=(
  "SKILL.md"
  "agents/openai.yaml"
  "scripts/pi_deepseek_delegate.sh"
  "references/setup.md"
  "references/delegation-contract.md"
)

usage() {
  cat <<'USAGE'
Usage:
  install.sh --install       Install the skill from source to deployment target.
  install.sh --check         Compare source against installed copy.
  install.sh --uninstall     Remove installed skill files.
  install.sh --dry-run       Show what --install would do without changing anything.

Options:
  --target DIR               Override deployment target (default: ~/.codex/skills/pi-deepseek-delegation)
  --dev                      Allow installation from a dirty or non-git source.
  -h, --help

Environment:
  PI_DEEPSEEK_SKILL_TARGET   Override default deployment target.
USAGE
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

is_git_worktree() {
  git -C "$SKILL_ROOT" rev-parse --show-toplevel >/dev/null 2>&1
}

is_clean() {
  local changes
  changes="$(git -C "$SKILL_ROOT" status --porcelain -- . 2>/dev/null || true)"
  [[ -z "$changes" ]]
}

shasum_file() {
  local file="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file" | awk '{print $1}'
  else
    python3 -c "import hashlib; print(hashlib.sha256(open('$file','rb').read()).hexdigest())"
  fi
}

generate_manifest() {
  local base_dir="$1"
  local file
  for file in "${DEPLOYABLE[@]}"; do
    local full_path="$base_dir/$file"
    if [[ -f "$full_path" ]]; then
      printf '%s %s\n' "$(shasum_file "$full_path")" "$file"
    fi
  done
}

check_source_valid() {
  if ! is_git_worktree; then
    printf 'invalid_source: not a git worktree\n'
    return 1
  fi
  if [[ $DEV_OVERRIDE -eq 1 ]]; then
    return 0
  fi
  if ! is_clean; then
    printf 'invalid_source: working tree is dirty (use --dev to override)\n'
    return 1
  fi
  return 0
}

do_check() {
  if ! check_source_valid; then
    exit 1
  fi

  if [[ ! -d "$TARGET" ]]; then
    printf 'not_installed\n'
    exit 0
  fi

  local source_manifest installed_manifest
  source_manifest="$(generate_manifest "$SKILL_ROOT")"
  installed_manifest="$(generate_manifest "$TARGET")"

  if [[ "$source_manifest" == "$installed_manifest" ]]; then
    printf 'installed_current\n'
    exit 0
  else
    printf 'installed_drifted\n'
    # Show diff for diagnostics
    diff <(printf '%s\n' "$source_manifest") <(printf '%s\n' "$installed_manifest") || true
    exit 4
  fi
}

do_install() {
  if ! check_source_valid; then
    exit 1
  fi

  # Guard against path traversal
  if [[ "$TARGET" != /* ]]; then
    fail "TARGET must be an absolute path: $TARGET"
  fi
  if [[ "$TARGET" == *".."* ]]; then
    fail "TARGET must not contain '..' components: $TARGET"
  fi

  local source_manifest
  source_manifest="$(generate_manifest "$SKILL_ROOT")"

  if [[ $DRY_RUN -eq 1 ]]; then
    printf 'Would install %d files from %s to %s\n' "${#DEPLOYABLE[@]}" "$SKILL_ROOT" "$TARGET"
    local file
    for file in "${DEPLOYABLE[@]}"; do
      printf '  %s\n' "$file"
    done
    return
  fi

  # Atomic install: write to temp directory, then rename
  local tmp_dir
  tmp_dir="$(mktemp -d /tmp/pi-deepseek-install.XXXXXX)"
  trap 'rm -rf "$tmp_dir"' EXIT

  local file src dst dst_dir
  for file in "${DEPLOYABLE[@]}"; do
    src="$SKILL_ROOT/$file"
    dst="$tmp_dir/$file"
    dst_dir="$(dirname "$dst")"
    if [[ -f "$src" ]]; then
      mkdir -p "$dst_dir"
      cp "$src" "$dst"
      # Preserve executable bit
      if [[ -x "$src" ]]; then
        chmod +x "$dst"
      fi
    fi
  done

  # Verify manifest matches before deploying
  local tmp_manifest
  tmp_manifest="$(generate_manifest "$tmp_dir")"
  if [[ "$source_manifest" != "$tmp_manifest" ]]; then
    fail 'Manifest mismatch after staging; install aborted'
  fi

  # Remove old target and rename tmp into place
  if [[ -d "$TARGET" ]]; then
    rm -rf "${TARGET}.bak" 2>/dev/null || true
    mv "$TARGET" "${TARGET}.bak" 2>/dev/null || true
  fi

  mkdir -p "$(dirname "$TARGET")"
  mv "$tmp_dir" "$TARGET"
  rm -rf "${TARGET}.bak" 2>/dev/null || true
  trap '' EXIT

  printf 'installed_current\n'
}

do_uninstall() {
  if [[ ! -d "$TARGET" ]]; then
    printf 'not_installed\n'
    return
  fi

  if [[ $DRY_RUN -eq 1 ]]; then
    printf 'Would remove %s\n' "$TARGET"
    return
  fi

  # Only remove files we own, then the directory if empty
  local file
  for file in "${DEPLOYABLE[@]}"; do
    local f="$TARGET/$file"
    if [[ -f "$f" ]]; then
      rm -f "$f"
    fi
  done

  # Remove empty directories bottom-up (only within the target tree)
  find "$TARGET" -type d -empty -delete 2>/dev/null || true

  # If TARGET itself is now empty, remove it
  if [[ -d "$TARGET" ]] && [[ -z "$(ls -A "$TARGET" 2>/dev/null)" ]]; then
    rmdir "$TARGET" 2>/dev/null || true
  fi

  printf 'uninstalled\n'
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --install)
      ACTION="install"
      shift
      ;;
    --check)
      ACTION="check"
      shift
      ;;
    --uninstall)
      ACTION="uninstall"
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --target)
      [[ $# -ge 2 ]] || fail "--target requires a value"
      TARGET="$2"
      shift 2
      ;;
    --dev)
      DEV_OVERRIDE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
done

if [[ -z "$ACTION" ]]; then
  fail "an action is required: --install, --check, or --uninstall"
fi

case "$ACTION" in
  check)    do_check ;;
  install)  do_install ;;
  uninstall) do_uninstall ;;
esac
