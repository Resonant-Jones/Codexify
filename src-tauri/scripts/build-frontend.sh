#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="${SCRIPT_DIR}/../../src"

if [ ! -f "${FRONTEND_DIR}/package.json" ]; then
  echo "[build-frontend] package.json not found at ${FRONTEND_DIR}" >&2
  exit 1
fi

echo "[build-frontend] Building frontend in ${FRONTEND_DIR}..."
cd "${FRONTEND_DIR}"
npm run build

