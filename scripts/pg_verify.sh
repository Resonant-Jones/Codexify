#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="$ROOT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing .env file. Run scripts/pg_bootstrap.sh first." >&2
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "psql not found. Install libpq (e.g. 'brew install libpq && brew link --force libpq' on macOS)." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is not defined in .env" >&2
  exit 1
fi

echo "DSN: $DATABASE_URL"
psql "$DATABASE_URL" -c "\\dt"
psql "$DATABASE_URL" -c "select now(), current_database(), current_user;"
