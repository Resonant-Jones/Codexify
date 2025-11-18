#!/usr/bin/env bash
set -euo pipefail

# --- sensible defaults pulled from DATABASE_URL ---
: "${PGHOST:=127.0.0.1}"
: "${PGPORT:=$(echo "${DATABASE_URL:-}" | sed -n 's/.*:\([0-9][0-9]*\)\/.*/\1/p')}"
: "${PGUSER:=guardian}"
: "${PGDATABASE:=guardian}"
# --------------------------------------------------

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DEFAULT_CONTAINER="guardian-pg"
DEFAULT_DSN="postgresql://codexify:codexify@localhost:5432/Codexify"
ENV_FILE="$ROOT_DIR/.env"
MIGRATIONS_DIR="migrations"
ALT_MIGRATIONS_DIR="db/migrations"
INIT_SQL="sql/init.sql"

GREEN="\033[32m"
RED="\033[31m"
YELLOW="\033[33m"
BLUE="\033[34m"
BOLD="\033[1m"
RESET="\033[0m"
CHECK="${GREEN}✓${RESET}"
CROSS="${RED}✗${RESET}"
WARN="${YELLOW}!${RESET}"
STEP_ICON="${BLUE}•${RESET}"

cleanup() {
  local exit_code=$?
  if [[ $exit_code -ne 0 ]]; then
    printf "%b %s (exit %d)\n" "$CROSS" "Bootstrap failed" "$exit_code" >&2
  fi
}
trap cleanup EXIT

log_step() { printf "%b %s\n" "$STEP_ICON" "$1"; }
log_ok() { printf "%b %s\n" "$CHECK" "$1"; }
log_warn() { printf "%b %s\n" "$WARN" "$1"; }
log_fail() { printf "%b %s\n" "$CROSS" "$1" >&2; }

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

require_command() {
  local cmd="$1"; shift
  if ! command_exists "$cmd"; then
    log_fail "$cmd not found. $*"
    exit 1
  fi
}

require_command docker "Install Docker Desktop or the Docker CLI."
require_command psql "Install psql (e.g. 'brew install libpq && brew link --force libpq' on macOS)."
require_command python3 "Install Python 3 to manage .env updates."

if ! docker info >/dev/null 2>&1; then
  log_fail "Docker daemon is not running. Start Docker and rerun."
  exit 1
fi

log_step "Ensuring Postgres container is running"
PG_CONTAINER="$DEFAULT_CONTAINER"

# Detect the superuser configured for the running container
SUPERUSER="$(docker exec "$PG_CONTAINER" printenv POSTGRES_USER 2>/dev/null || true)"
[[ -z "$SUPERUSER" ]] && SUPERUSER=postgres

container_exists() {
  docker ps -a --format '{{.Names}} {{.State}}' | awk -v name="$1" '$1==name {print $2}'
}

container_state=$(container_exists "$DEFAULT_CONTAINER")

if [[ -n "$container_state" ]]; then
  if [[ "$container_state" != "running" ]]; then
    if docker start "$DEFAULT_CONTAINER" >/dev/null; then
      log_ok "Started existing container $DEFAULT_CONTAINER"
    else
      log_fail "Failed to start container $DEFAULT_CONTAINER"
      exit 1
    fi
  else
    log_ok "Container $DEFAULT_CONTAINER already running"
  fi
else
  existing_on_port=$(docker ps --format '{{.Names}} {{.Ports}}' | awk '/(0\.0\.0\.0|:::)*:5432->/{print $1}' | head -n1)
  if [[ -n "$existing_on_port" ]]; then
    PG_CONTAINER="$existing_on_port"
    log_warn "Reusing running container $existing_on_port already bound to localhost:5432"
  else
    if command_exists lsof && lsof -iTCP:5432 -sTCP:LISTEN >/dev/null 2>&1; then
      log_fail "Port 5432 already in use by a local process. Stop it or change the mapping."
      exit 1
    fi
    log_step "Starting new postgres:16 container as $DEFAULT_CONTAINER"
    if docker run -d --name "$DEFAULT_CONTAINER" \
      -e POSTGRES_PASSWORD=postgres \
      -p 5432:5432 \
      -v guardian-pgdata:/var/lib/postgresql/data \
      postgres:16 >/dev/null; then
      log_ok "Container $DEFAULT_CONTAINER started"
    else
      log_fail "Failed to start container $DEFAULT_CONTAINER"
      exit 1
    fi
  fi
fi

wait_for_pg() {
  local attempts=0
  while true; do
    # use the requested credentials (defaults already set at top of script)
    if docker exec "$PG_CONTAINER" psql -U "$PGUSER" -d "${PGDATABASE:-$POSTGRES_DB}" -tAc 'SELECT 1' >/dev/null 2>&1; then
      return 0
    fi
    attempts=$((attempts + 1))
    if (( attempts > 30 )); then
      log_fail "Postgres in $PG_CONTAINER did not become ready."
      return 1
    fi
    sleep 1
  done
}

log_step "Waiting for Postgres to become ready"
wait_for_pg || exit 1
log_ok "Postgres is ready"

log_step "Ensuring .env exists"
if [[ ! -f "$ENV_FILE" ]]; then
  printf "# Guardian backend local environment\n" > "$ENV_FILE"
  log_ok "Created .env"
else
  log_ok ".env already present"
fi

update_env_file() {
  python3 - "$ENV_FILE" "$DEFAULT_DSN" <<'PY'
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
default_dsn = sys.argv[2]
placeholder_values = {"", "your-database-url", "YOUR-DATABASE-URL", "YOUR_DATABASE_URL", "postgres://user:pass@localhost:5432/dbname"}
if not env_path.exists():
    raise SystemExit("env file missing")
content = env_path.read_text().splitlines()
entries = {}
for idx, line in enumerate(content):
    if line.strip().startswith('#') or '=' not in line:
        continue
    key, value = line.split('=', 1)
    entries[key] = (idx, value)

def ensure_line(key, value):
    if key in entries:
        idx, _ = entries[key]
        content[idx] = f"{key}={value}"
    else:
        content.append(f"{key}={value}")

if 'DATABASE_URL' in entries:
    idx, val = entries['DATABASE_URL']
    current = val.strip()
    if current in placeholder_values:
        content[idx] = f"DATABASE_URL={default_dsn}"
        current = default_dsn
else:
    ensure_line('DATABASE_URL', default_dsn)
    current = default_dsn

if 'DATABASE_URL' not in entries:
    entries['DATABASE_URL'] = (len(content) - 1, default_dsn)

if 'DATABASE_URL' in entries:
    idx, val = entries['DATABASE_URL']
    current = content[idx].split('=',1)[1]
else:
    current = default_dsn

if 'GUARDIAN_DB_URL' in entries:
    g_idx, g_val = entries['GUARDIAN_DB_URL']
    if content[g_idx].split('=', 1)[1] != current:
        content[g_idx] = f"GUARDIAN_DB_URL={current}"

text = "\n".join(content)
if not text.endswith('\n'):
    text += '\n'
env_path.write_text(text)
PY
}

log_step "Ensuring DATABASE_URL in .env is set"
update_env_file
log_ok ".env configured"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${DATABASE_URL:-}" ]]; then
  log_fail "DATABASE_URL is not set in .env"
  exit 1
fi

log_step "Ensuring role 'guardian' exists"
docker exec -i "$PG_CONTAINER" psql -U "$SUPERUSER" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'guardian') THEN
    CREATE ROLE guardian LOGIN PASSWORD 'guardian';
  END IF;
END$$;
SQL
log_ok "Role 'guardian' ready"

log_step "Ensuring database 'guardian' exists"
docker exec -i "$PG_CONTAINER" psql -U "$SUPERUSER" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'guardian') THEN
    CREATE DATABASE guardian OWNER guardian;
  END IF;
END$$;
SQL
log_ok "Database 'guardian' ready"

apply_sql_file() {
  local file="$1"
  if [[ -f "$file" ]]; then
    log_step "Applying $(basename "$file")"
    if psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$file" >/dev/null; then
      log_ok "Applied $(basename "$file")"
    else
      log_fail "Failed to apply $(basename "$file")"
      exit 1
    fi
  fi
}

SQL_APPLIED=false
if [[ -f "$INIT_SQL" ]]; then
  apply_sql_file "$INIT_SQL"
  SQL_APPLIED=true
fi

apply_migrations_in_dir() {
  local dir="$1"
  local applied=0
  if [[ -d "$dir" ]]; then
    shopt -s nullglob
    for file in "$dir"/*.sql; do
      SQL_APPLIED=true
      apply_sql_file "$file"
      applied=1
    done
    shopt -u nullglob
    if [[ $applied -eq 0 ]]; then
      log_warn "No SQL files in $dir"
    fi
  fi
}

if [[ -d "$MIGRATIONS_DIR" ]]; then
  apply_migrations_in_dir "$MIGRATIONS_DIR"
elif [[ -d "$ALT_MIGRATIONS_DIR" ]]; then
  apply_migrations_in_dir "$ALT_MIGRATIONS_DIR"
else
  log_warn "No migrations directory found; relying on API to create tables."
fi

log_step "Verifying tables"
table_list="$(psql "$DATABASE_URL" -Atc "\\dt" || true)"
if [[ -n "$table_list" ]]; then
  printf "%s\n" "$table_list" | sed -n '1,50p'
  log_ok "Table listing complete"
else
  log_warn "No tables yet—start the API once to auto-init the schema."
fi

printf "\nNext steps:\n"
printf "  1. Start API: uvicorn guardian.guardian_api:app --reload --port 8000\n"
printf "  2. Start frontend: npm run dev (in the frontend folder)\n"

log_ok "Postgres bootstrap complete"
