#!/usr/bin/env bash
set -euo pipefail

# Resolve to repository layout robustly: this script lives in src-tauri/scripts/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="${SCRIPT_DIR}/../../src"

if [ ! -f "${FRONTEND_DIR}/package.json" ]; then
  echo "[dev-frontend] package.json not found at ${FRONTEND_DIR}" >&2
  exit 1
fi

echo "[dev-frontend] Starting Vite dev server in ${FRONTEND_DIR}..."
cd "${FRONTEND_DIR}"
npm run dev

