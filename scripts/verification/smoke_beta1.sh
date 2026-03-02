#!/usr/bin/env bash
# Beta-1 docker smoke (target runtime <= 10 minutes).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

fail() {
  log "FAIL: $*"
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

probe_http_status() {
  local method="$1"
  local path="$2"
  local data_json="${3:-}"
  local -a curl_args

  curl_args=(
    --silent
    --show-error
    --output /tmp/beta1_smoke_body.json
    --write-out '%{http_code}'
    -X "$method"
  )
  if [[ -n "${GUARDIAN_API_KEY:-}" ]]; then
    curl_args+=(-H "X-API-Key: ${GUARDIAN_API_KEY}")
  fi
  if [[ -n "$data_json" ]]; then
    curl_args+=(-H "Content-Type: application/json" --data "$data_json")
  fi

  curl "${curl_args[@]}" "${API_BASE}${path}"
}

probe_expect_404() {
  local method="$1"
  local path="$2"
  local data_json="${3:-}"
  local status
  local url="${API_BASE}${path}"

  status="$(probe_http_status "$method" "$path" "$data_json")"
  [[ "$status" == "404" ]] || {
    cat /tmp/beta1_smoke_body.json || true
    fail "Route appears mounted: method=${method} url=${url} expected_status=404 actual_status=${status}"
  }
}

probe_expect_not_mounted() {
  probe_expect_404 "$@"
}

assert_not_status() {
  local disallowed="$1"
  local method="$2"
  local path="$3"
  local data_json="${4:-}"
  local status
  local url="${API_BASE}${path}"

  status="$(probe_http_status "$method" "$path" "$data_json")"
  [[ "$status" != "$disallowed" ]] || {
    cat /tmp/beta1_smoke_body.json || true
    fail "Probe failed: method=${method} url=${url} expected_status!=${disallowed} actual_status=${status}"
  }
}

wait_for_completion_service_ready() {
  local start_ts="$1"
  local now elapsed
  while true; do
    curl -fsS "${API_BASE}/health/chat" > /tmp/beta1_health_chat.json
    if python3 - <<'PY' /tmp/beta1_health_chat.json
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
completion = payload.get("completion_service") or {}
if bool(completion.get("ok")):
    raise SystemExit(0)
raise SystemExit(1)
PY
    then
      return 0
    fi
    now="$(date +%s)"
    elapsed=$((now - start_ts))
    (( elapsed <= SMOKE_TIMEOUT_SECONDS )) || return 1
    sleep 2
  done
}

main() {
  require_cmd docker
  require_cmd curl
  require_cmd python3

  [[ -n ${GUARDIAN_API_KEY:-} ]] || fail "GUARDIAN_API_KEY is required"

  API_BASE="${API_BASE:-http://localhost:8888}"
  SMOKE_TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-600}"
  SOURCE_ENV_FILE="${BETA_ENV_SOURCE_FILE:-.env}"
  [[ -f "$SOURCE_ENV_FILE" ]] || fail "Missing env file: ${SOURCE_ENV_FILE}"

  local start_ts now elapsed beta_core_env
  start_ts="$(date +%s)"
  trap 'rm -f /tmp/beta1_smoke_body.json /tmp/beta1_health_chat.json' EXIT

  log "Starting Beta-1 smoke services"
  docker compose --env-file "$SOURCE_ENV_FILE" up -d --force-recreate db redis backend worker-chat worker-document-embed >/dev/null

  log "Waiting for backend health"
  while ! curl -fsS "${API_BASE}/health" >/dev/null 2>&1; do
    now="$(date +%s)"
    elapsed=$((now - start_ts))
    (( elapsed <= SMOKE_TIMEOUT_SECONDS )) || fail "Timed out waiting for /health"
    sleep 2
  done

  beta_core_env="$(
    docker compose --env-file "$SOURCE_ENV_FILE" exec -T backend sh -lc 'printf "%s" "${CODEXIFY_BETA_CORE_ONLY:-}"'
  )"
  if [[ "$beta_core_env" != "1" && "$beta_core_env" != "true" && "$beta_core_env" != "TRUE" ]]; then
    fail "Backend CODEXIFY_BETA_CORE_ONLY is not enabled. Set CODEXIFY_BETA_CORE_ONLY=true in ${SOURCE_ENV_FILE}."
  fi

  log "Waiting for /health/chat completion service readiness"
  wait_for_completion_service_ready "$start_ts" || {
    python3 - <<'PY' /tmp/beta1_health_chat.json || true
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
print(payload.get("completion_service"))
PY
    docker compose --env-file "$SOURCE_ENV_FILE" logs --tail=120 worker-chat || true
    fail "completion service did not become healthy in time"
  }

  log "Checking Beta-1 quarantined routes"
  probe_expect_not_mounted "GET" "/api/connectors"
  probe_expect_not_mounted "GET" "/api/guardian/commands/manifest"
  probe_expect_not_mounted "GET" "/api/cron/jobs"
  probe_expect_not_mounted "GET" "/api/tools/manifest"
  probe_expect_not_mounted "POST" "/api/media/generate/image" '{"prompt":"smoke"}'
  probe_expect_not_mounted "POST" "/api/media/tts/synthesize" '{"text":"smoke"}'

  log "Checking Beta-1 core routes remain mounted"
  assert_not_status "404" "GET" "/api/chat/threads"
  assert_not_status "404" "POST" "/api/upload-chatgpt-export"
  assert_not_status "404" "GET" "/api/media/documents"

  now="$(date +%s)"
  elapsed=$((now - start_ts))
  (( elapsed <= SMOKE_TIMEOUT_SECONDS )) || fail "Smoke exceeded ${SMOKE_TIMEOUT_SECONDS}s"

  log "PASS: Beta-1 smoke completed in ${elapsed}s"
}

main "$@"
