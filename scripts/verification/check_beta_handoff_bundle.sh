#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

COMPOSE_FILE="Codexify-Beta/docker-compose.yml"
COMPOSE_PROJECT_NAME="codexify-beta"
ENV_EXAMPLE="Codexify-Beta/.env.example"
ARCHIVE_PATH="dist/Codexify-Beta-WebUI-local-beta.zip"
RUNTIME_IMAGE="ghcr.io/resonant-jones/codexify-runtime:local-beta"
WEBUI_IMAGE="ghcr.io/resonant-jones/codexify-webui:local-beta"
TEMP_ENV_CREATED=0

cleanup() {
  if [ "${TEMP_ENV_CREATED}" -eq 1 ]; then
    rm -f Codexify-Beta/.env
  fi
}

trap cleanup EXIT

compose() {
  docker compose -p "${COMPOSE_PROJECT_NAME}" -f "${COMPOSE_FILE}" "$@"
}

wait_for() {
  local label="$1"
  local attempts="${2:-60}"
  shift 2 || true

  local attempt
  for attempt in $(seq 1 "${attempts}"); do
    if "$@"; then
      return 0
    fi
    sleep 2
  done

  echo "[beta-handoff] timed out waiting for ${label}" >&2
  return 1
}

bootstrap_temp_api_keys() {
  if [ -z "${GUARDIAN_API_KEY:-}" ]; then
    GUARDIAN_API_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  fi

  if [ -z "${VITE_GUARDIAN_API_KEY:-}" ]; then
    VITE_GUARDIAN_API_KEY="${GUARDIAN_API_KEY}"
  fi

  export GUARDIAN_API_KEY VITE_GUARDIAN_API_KEY

  if [ "${TEMP_ENV_CREATED}" -eq 1 ]; then
    python3 - "${GUARDIAN_API_KEY}" <<'PY'
from pathlib import Path
import sys

path = Path("Codexify-Beta/.env")
api_key = sys.argv[1]
lines = path.read_text().splitlines()
updated = []

for line in lines:
    if line.startswith("GUARDIAN_API_KEY="):
        updated.append(f"GUARDIAN_API_KEY={api_key}")
    elif line.startswith("VITE_GUARDIAN_API_KEY="):
        updated.append(f"VITE_GUARDIAN_API_KEY={api_key}")
    else:
        updated.append(line)

path.write_text("\n".join(updated) + "\n")
PY
  fi
}

check_backend_health() {
  curl -fsS http://localhost:8888/health | jq -e '.status == "ok"' >/dev/null
  curl -fsS http://localhost:8888/health/chat | jq -e '.status == "healthy" and .ok == true' >/dev/null
  curl -fsS http://localhost:8888/api/health/llm | jq -e '.status == "ok"' >/dev/null
}

check_default_compose_contract() {
  local config_json
  config_json="$(compose config --format json)"

  printf '%s' "${config_json}" | jq -e '
    .services.backend.depends_on | keys_unsorted | sort
    == ["db", "migrator", "model-prep"]
  ' >/dev/null

  [ "$(grep -c 'profiles: \["graph"\]' "${COMPOSE_FILE}")" -eq 2 ]
  [ "$(grep -c 'pull_policy: never' "${COMPOSE_FILE}")" -eq 2 ]
}

check_env_example() {
  grep -Fx 'GUARDIAN_API_KEY=' "${ENV_EXAMPLE}" >/dev/null
  grep -Fx 'VITE_GUARDIAN_API_KEY=' "${ENV_EXAMPLE}" >/dev/null
  grep -Fx 'GUARDIAN_DEV_MODE=true' "${ENV_EXAMPLE}" >/dev/null

  local csp_line
  csp_line="$(grep -E '^GUARDIAN_CSP_POLICY=' "${ENV_EXAMPLE}" || true)"
  if [ -n "${csp_line}" ] && printf '%s' "${csp_line}" | grep -q ';'; then
    case "${csp_line}" in
      GUARDIAN_CSP_POLICY=\"*\") ;;
      *)
        echo "[beta-handoff] GUARDIAN_CSP_POLICY must be quoted when it contains semicolons" >&2
        return 1
        ;;
    esac
  fi
}

check_archive_contents() {
  [ -f "${ARCHIVE_PATH}" ] || return 0

  local archive_listing
  archive_listing="$(unzip -Z1 "${ARCHIVE_PATH}")"

  printf '%s\n' "${archive_listing}" | grep -Fx 'Codexify-Beta/README.md' >/dev/null
  printf '%s\n' "${archive_listing}" | grep -Fx 'Codexify-Beta/AUTHORIZATION.md' >/dev/null
  printf '%s\n' "${archive_listing}" | grep -Fx 'Codexify-Beta/docker-compose.yml' >/dev/null
  printf '%s\n' "${archive_listing}" | grep -Fx 'Codexify-Beta/.env.example' >/dev/null
  ! printf '%s\n' "${archive_listing}" | grep -Fx 'Codexify-Beta/.env' >/dev/null
}

check_default_runtime_is_graph_free() {
  local ps_json
  ps_json="$(compose ps --format json)"

  printf '%s' "${ps_json}" | jq -s -e '
    all(.[]; .Service != "neo4j" and .Service != "graph-init")
  ' >/dev/null
}

check_frontend_http() {
  curl -fsSI http://localhost:3000 | grep -q '200 OK'
}

echo "[beta-handoff] clearing GHCR credentials..."
if [ ! -f Codexify-Beta/.env ]; then
  cp Codexify-Beta/.env.example Codexify-Beta/.env
  TEMP_ENV_CREATED=1
fi

bootstrap_temp_api_keys

echo "[beta-handoff] clearing any prior beta compose state..."
compose down --remove-orphans || true

docker logout ghcr.io || true

echo "[beta-handoff] verifying anonymous registry pulls..."
docker pull "${RUNTIME_IMAGE}"
docker pull "${WEBUI_IMAGE}"

echo "[beta-handoff] rendering compose config..."
config_output="$(compose config)"
printf '%s\n' "${config_output}" | grep -F "${RUNTIME_IMAGE}" >/dev/null
printf '%s\n' "${config_output}" | grep -F "${WEBUI_IMAGE}" >/dev/null
printf '%s\n' "${config_output}" | grep -F 'published: "8888"' >/dev/null
printf '%s\n' "${config_output}" | grep -F 'published: "3000"' >/dev/null
check_default_compose_contract
check_env_example
check_archive_contents

echo "[beta-handoff] pulling bundle images through compose..."
compose pull --policy missing

echo "[beta-handoff] starting bundle..."
compose up -d

echo "[beta-handoff] compose status:"
compose ps
check_default_runtime_is_graph_free

echo "[beta-handoff] waiting for backend and frontend..."
wait_for "backend health" 60 check_backend_health
wait_for "frontend http" 60 check_frontend_http

echo "[beta-handoff] bundle validation complete"
