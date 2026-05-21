#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="${1:-${ROOT_DIR}/../Publishing Portal}"
COMMIT_MESSAGE="${2:-Publish current Codexify snapshot}"

if [[ ! -d "${TARGET_DIR}" ]]; then
  echo "Target directory does not exist: ${TARGET_DIR}"
  exit 1
fi

if [[ ! -d "${TARGET_DIR}/.git" ]]; then
  echo "Target directory is not a git repository: ${TARGET_DIR}"
  exit 1
fi

if [[ -n "$(git -C "${TARGET_DIR}" status --porcelain)" ]]; then
  echo "Target repo has local changes. Commit, stash, or clean it before publishing."
  git -C "${TARGET_DIR}" status --short
  exit 1
fi

bash "${ROOT_DIR}/scripts/release/export_public_directory.sh"

git -C "${TARGET_DIR}" fetch origin main
git -C "${TARGET_DIR}" switch main
git -C "${TARGET_DIR}" pull --ff-only origin main

bash "${ROOT_DIR}/scripts/release/sync_public_directory.sh" "${TARGET_DIR}"

if [[ -n "$(git -C "${TARGET_DIR}" status --porcelain)" ]]; then
  git -C "${TARGET_DIR}" add -A
  if git -C "${TARGET_DIR}" diff --cached --quiet; then
    echo "No public snapshot changes to commit."
  else
    git -C "${TARGET_DIR}" commit -m "${COMMIT_MESSAGE}"
    git -C "${TARGET_DIR}" push origin main
  fi
else
  echo "No public snapshot changes detected."
fi
