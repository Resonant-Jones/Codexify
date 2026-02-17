#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log "ERROR: '$1' not found in PATH"
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

check_provider_keys() {
  local provider
  provider="$(printf '%s' "${LLM_PROVIDER}" | tr '[:upper:]' '[:lower:]')"
  case "$provider" in
    openai)
      require_env OPENAI_API_KEY
      ;;
    groq)
      require_env GROQ_API_KEY
      ;;
    local)
      ;;
    *)
      log "ERROR: Unsupported LLM_PROVIDER '$LLM_PROVIDER' (expected local/openai/groq)"
      exit 1
      ;;
  esac
}

curl_json() {
  local url="$1"
  curl -fsS -H "X-API-Key: $GUARDIAN_API_KEY" "$url"
}

fetch_gallery() {
  curl_json "${API_ROOT}/api/media/images?limit=${GALLERY_LIMIT}"
}

wait_for_backend() {
  local max_attempts=30
  local attempt=1
  until curl -fsS "${API_ROOT}/health" >/dev/null 2>&1; do
    if (( attempt >= max_attempts )); then
      log "ERROR: backend not healthy at ${API_ROOT} after $max_attempts attempts"
      exit 1
    fi
    sleep 2
    ((attempt++))
  done
}

assert_images_array_present() {
  local json="$1"
  if ! jq -e '.images and (.images | type == "array")' <<<"$json" >/dev/null; then
    log "ERROR: missing 'images' array in gallery response"
    exit 1
  fi
}

count_images_by_source() {
  local json="$1"
  local source="$2"
  jq -r --arg source "$source" '[.images[] | select((.source_tag // "uploaded") == $source)] | length' <<<"$json"
}

assert_generated_id_present() {
  local json="$1"
  local target_id="$2"
  if ! jq -e --arg id "$target_id" '[.images[] | select((.source_tag // "uploaded") == "generated") | .id | tostring] | index($id)' <<<"$json" >/dev/null; then
    log "ERROR: generated id $target_id missing from refreshed gallery response"
    exit 1
  fi
}

validate_src_url() {
  local src_url="$1"
  local tmp_file
  tmp_file=$(mktemp /tmp/image_validation.XXXXXX)
  curl -fsS -o "$tmp_file" "$src_url"
  local size
  size=$(wc -c < "$tmp_file")
  rm -f "$tmp_file"
  if (( size <= 0 )); then
    log "ERROR: downloaded asset size is 0 bytes; /media proxy likely unhealthy"
    exit 1
  fi
  log "Fetched ${size} bytes from ${src_url}"
}

main() {
  require_cmd docker
  require_cmd curl
  require_cmd jq

  require_env GUARDIAN_API_KEY
  require_env LLM_PROVIDER
  check_provider_keys

  API_ROOT=${API_ROOT:-http://localhost:8888}
  GALLERY_LIMIT=${GALLERY_LIMIT:-20}
  GEN_PROMPT=${GEN_PROMPT:-"audit test image"}
  GEN_MODEL=${GEN_MODEL:-"dall-e-3"}
  GEN_PROJECT_ID=${GEN_PROJECT_ID:-1}
  GEN_THREAD_ID=${GEN_THREAD_ID:-1}
  GEN_USER_ID=${GEN_USER_ID:-"default"}

  log "Starting db/redis/backend via docker compose"
  docker compose up -d db redis backend >/dev/null
  wait_for_backend
  log "Backend healthy at ${API_ROOT}"

  log "Fetching gallery baseline"
  baseline_json=$(fetch_gallery)
  assert_images_array_present "$baseline_json"
  baseline_uploaded=$(count_images_by_source "$baseline_json" "uploaded")
  baseline_generated=$(count_images_by_source "$baseline_json" "generated")
  log "Baseline uploaded=${baseline_uploaded} generated=${baseline_generated}"

  log "Requesting deterministic image generation"
  gen_payload=$(jq -n \
    --arg prompt "$GEN_PROMPT" \
    --arg model "$GEN_MODEL" \
    --argjson project_id "$GEN_PROJECT_ID" \
    --argjson thread_id "$GEN_THREAD_ID" \
    --arg user_id "$GEN_USER_ID" '{prompt:$prompt,model:$model,project_id:$project_id,thread_id:$thread_id,user_id:$user_id}')

  gen_response=$(curl -fsS -H "X-API-Key: $GUARDIAN_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$gen_payload" \
    "${API_ROOT}/api/media/generate/image")

  gen_id=$(jq -r '.id' <<<"$gen_response")
  gen_src=$(jq -r '.src_url' <<<"$gen_response")
  gen_prompt=$(jq -r '.prompt' <<<"$gen_response")
  gen_model=$(jq -r '.model' <<<"$gen_response")
  gen_created=$(jq -r '.created_at' <<<"$gen_response")

  [[ -n "$gen_id" && "$gen_id" != "null" ]] || { log "ERROR: generation response missing 'id'"; exit 1; }
  [[ -n "$gen_src" && "$gen_src" != "null" ]] || { log "ERROR: generation response missing 'src_url'"; exit 1; }
  [[ -n "$gen_prompt" && "$gen_prompt" != "null" ]] || { log "ERROR: generation response missing 'prompt'"; exit 1; }
  [[ -n "$gen_model" && "$gen_model" != "null" ]] || { log "ERROR: generation response missing 'model'"; exit 1; }
  [[ -n "$gen_created" && "$gen_created" != "null" ]] || { log "ERROR: generation response missing 'created_at'"; exit 1; }

  log "Generated image id=$gen_id model=$gen_model created_at=$gen_created"

  log "Refreshing gallery after generation"
  refreshed_json=$(fetch_gallery)
  assert_images_array_present "$refreshed_json"
  refreshed_generated=$(count_images_by_source "$refreshed_json" "generated")
  assert_generated_id_present "$refreshed_json" "$gen_id"

  if (( refreshed_generated < baseline_generated )); then
    log "ERROR: generated image count regressed (${baseline_generated} -> ${refreshed_generated})"
    exit 1
  fi

  log "Validating /media fetchability"
  validate_src_url "$gen_src"

  log "SUCCESS: gallery + generation loop verified"
}

main "$@"
