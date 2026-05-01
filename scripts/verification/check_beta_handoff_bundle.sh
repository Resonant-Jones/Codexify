#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

COMPOSE_FILE="Codexify-Beta/docker-compose.yml"
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
  docker compose -f "${COMPOSE_FILE}" "$@"
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

check_backend_health() {
  curl -fsS http://localhost:8888/health | jq -e '.status == "ok"' >/dev/null
  curl -fsS http://localhost:8888/health/chat | jq -e '.status == "healthy" and .ok == true' >/dev/null
  curl -fsS http://localhost:8888/api/health/llm | jq -e '.status == "ok"' >/dev/null
}

check_frontend_http() {
  curl -fsSI http://localhost:3000 | grep -q '200 OK'
}

echo "[beta-handoff] clearing GHCR credentials..."
if [ ! -f Codexify-Beta/.env ]; then
  cp Codexify-Beta/.env.example Codexify-Beta/.env
  TEMP_ENV_CREATED=1
fi

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

echo "[beta-handoff] pulling bundle images through compose..."
compose pull

echo "[beta-handoff] starting bundle..."
compose up -d

echo "[beta-handoff] compose status:"
compose ps

echo "[beta-handoff] waiting for backend and frontend..."
wait_for "backend health" 60 check_backend_health
wait_for "frontend http" 60 check_frontend_http

echo "[beta-handoff] bundle validation complete"
