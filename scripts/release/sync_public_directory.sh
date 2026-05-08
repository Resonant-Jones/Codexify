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

mkdir -p "${TARGET_DIR}"
cp -R "${SOURCE_DIR}/." "${TARGET_DIR}/"
echo "Synced public portal tree to: ${TARGET_DIR}"
