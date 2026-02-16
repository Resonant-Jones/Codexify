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
  case "${LLM_PROVIDER,,}" in
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
  local tag="$1"
  curl_json "${API_ROOT}/api/media/images?tag=${tag}&limit=${GALLERY_LIMIT}"
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

assert_count_gt_zero() {
  local json="$1"
  local tag="$2"
  local count
  count=$(jq '.items | length' <<<"$json")
  if [[ "$count" == "null" ]]; then
    log "ERROR: missing 'items' array in ${tag} response"
    exit 1
  fi
  if (( count == 0 )); then
    log "ERROR: ${tag} gallery returned zero items"
    exit 1
  fi
  log "${tag} gallery returned ${count} item(s)"
}

assert_id_present() {
  local json="$1"
  local target_id="$2"
  if ! jq -e --arg id "$target_id" '.items | map(.id | tostring) | index($id)' <<<"$json" >/dev/null; then
    log "ERROR: generated id $target_id missing from refreshed gallery"
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
    log "ERROR: downloaded asset size is 0 bytes — /media proxy likely unhealthy"
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
  GALLERY_LIMIT=${GALLERY_LIMIT:-5}
  GEN_PROMPT=${GEN_PROMPT:-"audit test image"}
  GEN_MODEL=${GEN_MODEL:-"dall-e-3"}
  GEN_PROJECT_ID=${GEN_PROJECT_ID:-1}
  GEN_THREAD_ID=${GEN_THREAD_ID:-1}
  GEN_USER_ID=${GEN_USER_ID:-"default"}

  log "Starting db/redis/backend via docker compose"
  docker compose up -d db redis backend >/dev/null
  wait_for_backend
  log "Backend healthy at ${API_ROOT}"

  log "Fetching uploaded gallery"
  uploaded_json=$(fetch_gallery "uploaded")
  assert_count_gt_zero "$uploaded_json" "uploaded"

  log "Fetching generated gallery (baseline)"
  generated_json=$(fetch_gallery "generated")
  baseline_count=$(jq '.items | length' <<<"$generated_json")
  log "Generated gallery baseline count: ${baseline_count:-0}"

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
  gen_tag=$(jq -r '.tag' <<<"$gen_response")

  if [[ -z "$gen_id" || "$gen_id" == "null" ]]; then
    log "ERROR: generation response missing 'id'"
    exit 1
  fi
  if [[ "$gen_tag" != "generated" ]]; then
    log "ERROR: generation response tag '$gen_tag' != 'generated'"
    exit 1
  fi
  if [[ -z "$gen_src" || "$gen_src" == "null" ]]; then
    log "ERROR: generation response missing 'src_url'"
    exit 1
  fi
  log "Generated image id=$gen_id tag=$gen_tag src_url=$gen_src"

  log "Refreshing generated gallery for new item"
  refreshed_json=$(fetch_gallery "generated")
  assert_count_gt_zero "$refreshed_json" "generated"
  assert_id_present "$refreshed_json" "$gen_id"

  log "Validating /media fetchability"
  validate_src_url "$gen_src"

  log "SUCCESS: gallery + generation loop verified (Task 008)"
}

main "$@"
