#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.webui-runtime.yml}"
WEBUI_IMAGE_REGISTRY="${CODEXIFY_WEBUI_IMAGE_REGISTRY:-ghcr.io/resonant-jones}"
WEBUI_IMAGE_TAG="${CODEXIFY_WEBUI_IMAGE_TAG:-local-beta}"
RUNTIME_IMAGE_REGISTRY="${CODEXIFY_IMAGE_REGISTRY:-ghcr.io/resonant-jones}"
RUNTIME_IMAGE_TAG="${CODEXIFY_IMAGE_TAG:-local-beta}"

WEBUI_IMAGE="${WEBUI_IMAGE_REGISTRY}/codexify-webui:${WEBUI_IMAGE_TAG}"
RUNTIME_IMAGE="${RUNTIME_IMAGE_REGISTRY}/codexify-runtime:${RUNTIME_IMAGE_TAG}"

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

  echo "[webui-runtime] timed out waiting for ${label}" >&2
  return 1
}

check_frontend_html() {
  local response
  response="$(curl -fsS http://localhost:3000)"
  printf '%s' "${response}" | grep -qi '<html'
}

check_backend_health() {
  curl -fsS http://localhost:8888/health | jq -e '.status == "ok"' >/dev/null
  curl -fsS http://localhost:8888/health/chat | jq -e '.status == "healthy" and .ok == true' >/dev/null
  curl -fsS http://localhost:8888/api/health/llm | jq -e '.status == "ok"' >/dev/null
}

echo "[webui-runtime] rendering compose config..."
config_output="$(compose config)"

printf '%s\n' "${config_output}" | grep -F "${WEBUI_IMAGE}" >/dev/null
printf '%s\n' "${config_output}" | grep -F "${RUNTIME_IMAGE}" >/dev/null
printf '%s\n' "${config_output}" | grep -F "frontend:" >/dev/null
printf '%s\n' "${config_output}" | grep -F "backend:" >/dev/null
printf '%s\n' "${config_output}" | grep -F 'published: "3000"' >/dev/null
printf '%s\n' "${config_output}" | grep -F 'target: 80' >/dev/null

echo "[webui-runtime] building frontend image..."
compose build frontend

docker image inspect "${WEBUI_IMAGE}" >/dev/null

echo "[webui-runtime] starting webui bundle..."
compose up -d

echo "[webui-runtime] compose status:"
compose ps

echo "[webui-runtime] waiting for backend health and browser HTML..."
wait_for "backend health" 60 check_backend_health
wait_for "frontend html" 60 check_frontend_html

echo "[webui-runtime] bundle validation complete"
