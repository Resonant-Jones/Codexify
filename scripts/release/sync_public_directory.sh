#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${ROOT_DIR}/Public-Directory"
TARGET_DIR="${1:-}"

if [[ -z "${TARGET_DIR}" ]]; then
  echo "Usage: $0 /path/to/fresh-repo"
  exit 1
fi

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "Public-Directory is missing. Run: make public-export"
  exit 1
fi

if [[ ! -d "${TARGET_DIR}/.git" ]]; then
  echo "Target directory is not a git repository: ${TARGET_DIR}"
  exit 1
fi

mkdir -p "${TARGET_DIR}"

# Mirror the curated snapshot into the public repo without touching git history.
rsync -a --delete --exclude='.git/' "${SOURCE_DIR}/" "${TARGET_DIR}/"
echo "Synced public portal tree to: ${TARGET_DIR}"
