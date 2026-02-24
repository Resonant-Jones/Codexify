#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${1:-$ROOT_DIR/.env}"

is_sourced() {
  [[ "${BASH_SOURCE[0]}" != "$0" ]]
}

fail() {
  echo "$1" >&2
  if is_sourced; then
    return 1
  fi
  exit 1
}

if [[ ! -f "$ENV_FILE" ]]; then
  fail "env file not found: $ENV_FILE"
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${GUARDIAN_API_KEY:-}" ]]; then
  fail "GUARDIAN_API_KEY is missing after loading $ENV_FILE"
fi

if [[ "${PRINT_GUARDIAN_API_KEY:-0}" == "1" ]]; then
  printf '%s\n' "$GUARDIAN_API_KEY"
else
  echo "GUARDIAN_API_KEY loaded into current shell environment."
fi
