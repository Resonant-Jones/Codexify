#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

require_cmd() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    log "ERROR: '$name' not found in PATH"
    exit 1
  fi
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    log "ERROR: environment variable '$name' is required"
    exit 1
  fi
}

wait_for_backend() {
  local url="$1"
  local attempt=1
  local max_attempts=30
  until curl -fsS "$url" >/dev/null 2>&1; do
    if (( attempt >= max_attempts )); then
      log "ERROR: backend did not become healthy at $url"
      exit 1
    fi
    sleep 2
    ((attempt++))
  done
}

ensure_thread() {
  local thread_id="$1"
  local documents_url="$2"
  local status
  local tmp_file
  tmp_file=$(mktemp /tmp/doc_gen_docs.XXXXXX)
  status=$(curl -sS -o "$tmp_file" -w '%{http_code}' -H "X-API-Key: $GUARDIAN_API_KEY" "$documents_url" || true)
  case "$status" in
    200)
      log "Thread $thread_id exists; continuing"
      rm -f "$tmp_file"
      echo "$thread_id"
      ;;
    404)
      log "Thread $thread_id missing; creating via POST /api/threads"
      local payload
      payload=$(jq -n --arg title "Doc Gen Validation Thread" '{title:$title}')
      local response
      response=$(curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" -H "Content-Type: application/json" -d "$payload" "${API_ROOT}/api/threads")
      local new_id
      new_id=$(jq -r '.thread_id' <<<"$response")
      if [[ -z "$new_id" || "$new_id" == "null" ]]; then
        log "ERROR: thread creation response missing thread_id"
        exit 1
      fi
      log "Created thread $new_id for validation"
      rm -f "$tmp_file"
      echo "$new_id"
      ;;
    *)
      log "ERROR: Unexpected status $status from $documents_url"
      cat "$tmp_file" >&2
      rm -f "$tmp_file"
      exit 1
      ;;
  esac
}

assert_field() {
  local label="$1"
  local value="$2"
  if [[ -z "$value" || "$value" == "null" ]]; then
    log "ERROR: missing required field '$label'"
    exit 1
  fi
}

main() {
  require_cmd docker
  require_cmd jq
  require_cmd curl

  require_env GUARDIAN_API_KEY

  docker --version >/dev/null
  docker compose version >/dev/null

  API_ROOT=${API_ROOT:-http://localhost:8888}
  THREAD_ID=${THREAD_ID:-1}
  PROMPT=${PROMPT:-"Write a short audit note."}
  FORMAT=${FORMAT:-"markdown"}

  log "Starting db/redis/backend via docker compose"
  docker compose up -d db redis backend >/dev/null
  wait_for_backend "${API_ROOT}/health"

  THREAD_ID=$(ensure_thread "$THREAD_ID" "${API_ROOT}/api/threads/${THREAD_ID}/documents")
  export THREAD_ID

  log "Requesting document generation"
  local gen_payload
  gen_payload=$(jq -n \
    --argjson thread_id "$THREAD_ID" \
    --arg prompt "$PROMPT" \
    --arg format "$FORMAT" \
    '{thread_id:$thread_id,prompt:$prompt,format:$format}')

  local gen_response
  gen_response=$(curl -sS \
    -H "X-API-Key: $GUARDIAN_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$gen_payload" \
    "${API_ROOT}/api/documents/generate")

  local gen_ok
  gen_ok=$(jq -r '.ok' <<<"$gen_response")
  local document_id
  document_id=$(jq -r '.document_id' <<<"$gen_response")
  local content
  content=$(jq -r '.content' <<<"$gen_response")

  if [[ "$gen_ok" != "true" ]]; then
    log "ERROR: /api/documents/generate returned ok=$gen_ok"
    log "Response: $gen_response"
    exit 1
  fi

  assert_field document_id "$document_id"
  assert_field content "$content"
  log "Document generation succeeded with document_id=$document_id"

  log "Listing documents for thread $THREAD_ID"
  local docs_response
  docs_response=$(curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" "${API_ROOT}/api/threads/${THREAD_ID}/documents")
  local docs_ok
  docs_ok=$(jq -r '.ok' <<<"$docs_response")
  if [[ "$docs_ok" != "true" ]]; then
    log "ERROR: /api/threads/${THREAD_ID}/documents returned ok=$docs_ok"
    log "Response: $docs_response"
    exit 1
  fi

  local matched
  matched=$(jq --arg id "$document_id" -e '.documents | map(.id) | index($id)' <<<"$docs_response" >/dev/null && echo yes || echo no)
  if [[ "$matched" != "yes" ]]; then
    log "ERROR: Generated document_id=$document_id missing from thread listing"
    log "Response: $docs_response"
    exit 1
  fi

  local relation
  relation=$(jq -r --arg id "$document_id" '.documents[] | select(.id == $id) | .relation' <<<"$docs_response")
  assert_field relation "$relation"

  log "SUCCESS: doc-gen loop verified (document relation '$relation')"
}

main "$@"
