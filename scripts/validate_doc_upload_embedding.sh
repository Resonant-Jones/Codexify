#!/usr/bin/env bash
# File: scripts/validate_doc_upload_embedding.sh
# Purpose: deterministically validate doc upload, listing, and embedding worker readiness (Task 007).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )/.." && pwd)"
cd "$ROOT_DIR"

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

fail() {
  log "FAIL: $*"
  exit 1
}

require_clean_tree() {
  if [[ -n $(git status --porcelain -uall) ]]; then
    git status --porcelain -uall
    fail "Repo is dirty. Clean the tree before running validation."
  fi
}

json_field() {
  local file=$1
  local expr=$2
  python3 - "$file" "$expr" <<'PY'
import json, sys
path, expr = sys.argv[1:3]
try:
    data = json.load(open(path))
except json.JSONDecodeError as exc:
    print(f"JSON decode error: {exc}")
    sys.exit(2)
parts = expr.split('.')
node = data
for part in parts:
    if isinstance(node, list):
        try:
            idx = int(part)
        except ValueError:
            print(f"Expected numeric index for list access in '{expr}'")
            sys.exit(3)
        if idx >= len(node):
            print(f"List index {idx} out of range for '{expr}'")
            sys.exit(3)
        node = node[idx]
    else:
        if part not in node:
            print(f"Missing field '{part}' while resolving '{expr}'")
            sys.exit(3)
        node = node[part]
print(node)
PY
}

ensure_worker_running() {
  local output
  if output=$(docker compose ps worker-document-embed --format json 2>/dev/null); then
    python3 - <<'PY' "$output" || exit 1
import json, sys
text = sys.argv[1]
services = json.loads(text)
if not services:
    print('worker-document-embed missing from compose ps output')
    sys.exit(1)
state = services[0].get('State', {}).get('Status') or services[0].get('State')
if not state:
    print('Unable to read worker state from compose json output')
    sys.exit(1)
print(f"worker-document-embed state: {state}")
if state.lower() != 'running':
    sys.exit(1)
PY
  else
    docker compose ps worker-document-embed | tee /tmp/worker_status.txt
    if ! grep -qi running /tmp/worker_status.txt; then
      fail "worker-document-embed is not running"
    fi
  fi
}

clean_temp() {
  for path in "$@"; do
    [[ -n "${path:-}" ]] && rm -f "$path"
  done
}

main() {
  require_clean_tree

  command -v docker >/dev/null || fail "docker not installed"
  command -v curl >/dev/null || fail "curl not installed"
  command -v python3 >/dev/null || fail "python3 not installed"

  [[ -n ${GUARDIAN_API_KEY:-} ]] || fail "GUARDIAN_API_KEY is not set"

  local upload_file="$ROOT_DIR/test.txt"
  [[ -f "$upload_file" ]] || fail "Payload file $upload_file not found"

  local api_base="${API_BASE:-http://localhost:8888}"
  local upload_endpoint="$api_base/api/media/upload/document"
  local list_endpoint="$api_base/api/media/documents?limit=5"

  log "Starting compose services"
  docker compose up -d db redis backend worker-document-embed >/dev/null
  ensure_worker_running || fail "worker-document-embed container not running after compose up"

  log "Uploading $upload_file"
  local upload_json list_json
  local TMP_FILES=()
  upload_json=$(mktemp)
  TMP_FILES+=("$upload_json")
  trap 'clean_temp "${TMP_FILES[@]}"' EXIT
  curl -sS \
    -H "X-API-Key: $GUARDIAN_API_KEY" \
    -F "file=@${upload_file}" \
    -F "project_id=${PROJECT_ID:-1}" \
    -F "thread_id=${THREAD_ID:-1}" \
    "$upload_endpoint" >"$upload_json"

  local doc_id src_url embed_status project_id
  doc_id=$(json_field "$upload_json" id) || fail "Upload response missing id"
  src_url=$(json_field "$upload_json" src_url) || fail "Upload response missing src_url"
  embed_status=$(json_field "$upload_json" embedding_status) || fail "Upload response missing embedding_status"
  project_id=$(json_field "$upload_json" project_id) || fail "Upload response missing project_id"

  [[ "$doc_id" =~ ^[0-9]+$ ]] || fail "id '$doc_id' is not numeric"
  local expected_media_prefix="${api_base%/}/media/"
  case "$src_url" in
    ${expected_media_prefix}*|http://localhost:8888/media/*) ;;
    *) fail "Unexpected src_url '$src_url'" ;;
  esac
  [[ "$project_id" == "${PROJECT_ID:-1}" ]] || fail "project_id mismatch"

  case "$embed_status" in
    pending|processing) ;;
    *) fail "Unexpected initial embedding_status '$embed_status'" ;;
  esac

  log "Upload OK (id=$doc_id status=$embed_status)"

  local poll_attempt=1
  local max_attempts=12
  local found_status=""
  list_json=$(mktemp)
  TMP_FILES+=("$list_json")

  while (( poll_attempt <= max_attempts )); do
    curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" "$list_endpoint" >"$list_json"
    ensure_worker_running || fail "worker-document-embed exited during polling"
    found_status=$(python3 - "$list_json" "$doc_id" <<'PY'
import json, sys
path, target_id = sys.argv[1], int(sys.argv[2])
data = json.load(open(path))
items = data.get('items')
if items is None and isinstance(data, list):
    items = data
if items is None:
    print('NO_ITEMS')
    sys.exit(0)
for item in items:
    if item.get('id') == target_id:
        print(item.get('embedding_status', ''))
        break
else:
    print('NOT_FOUND')
PY
)
    case "$found_status" in
      ready)
        log "Embedding finished (attempt $poll_attempt)"
        break
      failed)
        fail "Embedding worker reported failed"
        ;;
      NOT_FOUND)
        log "Document not found in listing (attempt $poll_attempt)"
        ;;
      NO_ITEMS)
        log "Listing response missing 'items' (attempt $poll_attempt)"
        ;;
      *)
        log "Embedding status still '$found_status' (attempt $poll_attempt)"
        ;;
    esac
    (( poll_attempt++ ))
    sleep 5
  done

  if [[ "$found_status" != "ready" ]]; then
    fail "Embedding status never became ready"
  fi

  log "PASS: doc upload + embedding validation completed"
}

main "$@"
