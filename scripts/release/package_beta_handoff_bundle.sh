#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

SOURCE_DIR="Codexify-Beta"
ARCHIVE_DIR="dist"
ARCHIVE_PATH="${ARCHIVE_DIR}/Codexify-Beta-WebUI-local-beta.zip"
STAGING_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "${STAGING_DIR}"
}

trap cleanup EXIT

mkdir -p "${ARCHIVE_DIR}"
rm -f "${ARCHIVE_PATH}"

mkdir -p "${STAGING_DIR}/${SOURCE_DIR}"
# The public handoff bundle stays minimal and excludes any local `.env`.
cp "${SOURCE_DIR}/AUTHORIZATION.md" "${STAGING_DIR}/${SOURCE_DIR}/AUTHORIZATION.md"
cp "${SOURCE_DIR}/docker-compose.yml" "${STAGING_DIR}/${SOURCE_DIR}/docker-compose.yml"
cp "${SOURCE_DIR}/.env.example" "${STAGING_DIR}/${SOURCE_DIR}/.env.example"
cp "${SOURCE_DIR}/README.md" "${STAGING_DIR}/${SOURCE_DIR}/README.md"

(
  cd "${STAGING_DIR}"
  zip -qr "${ROOT_DIR}/${ARCHIVE_PATH}" "${SOURCE_DIR}"
)

echo "[beta-package] archive: ${ARCHIVE_PATH}"
unzip -l "${ARCHIVE_PATH}"
