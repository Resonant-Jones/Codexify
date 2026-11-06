#!/usr/bin/env bash
#
# Build the disposable git repository used by the Codexify delegated-coding
# proof.
#
# The fixture repository is a throwaway working tree that a delegated coding
# task may be dispatched against. It is never the operator's real Codexify
# checkout. The script is deliberately conservative:
#
#   * it never deletes anything,
#   * it refuses to run against a non-empty target directory,
#   * it never writes global git configuration (identity is passed inline),
#   * it never touches a path outside the target directory.
#
# Usage:
#   scripts/ops/build_cxf_delegation_fixture.sh [target_directory]
#
set -euo pipefail

DEFAULT_TARGET="/Volumes/Dev_SSD/Codexify-main/.worktrees/feat-auto-20261105-c8c1dc20/.cxf_fixture/delegate-fixture"
TARGET="${1:-$DEFAULT_TARGET}"

FIXTURE_GIT_EMAIL="fixture@example.invalid"
FIXTURE_GIT_NAME="fixture"
CANARY_FILE="canary_marker.txt"
CANARY_CONTENT="canary-ok"

log() { printf '%s\n' "$*"; }
fail() { printf 'cxf-fixture: %s\n' "$*" >&2; }

# --- target guards ----------------------------------------------------------

if [ -e "$TARGET" ] && [ ! -d "$TARGET" ]; then
    fail "target exists and is not a directory: $TARGET"
    exit 2
fi

if [ -d "$TARGET" ]; then
    if [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
        fail "refusing to run: target directory is not empty: $TARGET"
        fail "nothing was created and nothing was deleted; use an empty directory."
        exit 3
    fi
else
    mkdir -p "$TARGET"
fi

ABS_TARGET="$(cd "$TARGET" && pwd -P)"

# --- repository construction ------------------------------------------------

git -C "$ABS_TARGET" -c init.defaultBranch=main init --quiet
log "git init: $ABS_TARGET"

printf '%s\n' "$CANARY_CONTENT" > "$ABS_TARGET/$CANARY_FILE"

git -C "$ABS_TARGET" add "$CANARY_FILE"

git -C "$ABS_TARGET" \
    -c "user.email=$FIXTURE_GIT_EMAIL" \
    -c "user.name=$FIXTURE_GIT_NAME" \
    -c commit.gpgsign=false \
    commit --quiet -m "fixture: canary marker"

TOPLEVEL="$(git -C "$ABS_TARGET" rev-parse --show-toplevel)"
HEAD_SHA="$(git -C "$ABS_TARGET" rev-parse HEAD)"

log "target: $ABS_TARGET"
log "top_level: $TOPLEVEL"
log "head: $HEAD_SHA"
