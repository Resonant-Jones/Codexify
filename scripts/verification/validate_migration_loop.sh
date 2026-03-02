#!/usr/bin/env bash
# Deterministic migration loop validator.
# Verifies authenticated upload-chatgpt-export persists a thread and retrievable messages.
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

require_clean_tree() {
  if [[ -n $(git status --porcelain -uall) ]]; then
    git status --porcelain -uall
    fail "Working tree is dirty. Commit/stash before running migration validation."
  fi
}

wait_for_backend() {
  local attempts=30
  local n=1
  until curl -fsS "${API_BASE}/health" >/dev/null 2>&1; do
    if (( n >= attempts )); then
      fail "Backend health check failed at ${API_BASE}/health"
    fi
    sleep 2
    ((n++))
  done
}

latest_thread_id_by_title() {
  local json_file=$1
  local title=$2
  python3 - "$json_file" "$title" <<'PY'
import json
import sys

path, title = sys.argv[1], sys.argv[2]
data = json.load(open(path, encoding="utf-8"))
threads = data.get("threads")
if not isinstance(threads, list):
    sys.exit(2)
ids = []
for thread in threads:
    if not isinstance(thread, dict):
        continue
    if thread.get("title") != title:
        continue
    value = thread.get("id")
    try:
        ids.append(int(value))
    except (TypeError, ValueError):
        continue
if not ids:
    sys.exit(3)
print(max(ids))
PY
}

assert_messages_include_sentinel() {
  local json_file=$1
  local sentinel=$2
  python3 - "$json_file" "$sentinel" <<'PY'
import json
import sys

path, sentinel = sys.argv[1], sys.argv[2]
data = json.load(open(path, encoding="utf-8"))
messages = data.get("messages")
if not isinstance(messages, list):
    print("messages payload missing list")
    sys.exit(2)
if len(messages) < 2:
    print(f"expected at least 2 messages, got {len(messages)}")
    sys.exit(3)
for message in messages:
    if not isinstance(message, dict):
        continue
    content = str(message.get("content") or "")
    if sentinel in content:
        print("sentinel persisted")
        sys.exit(0)
print("sentinel not found")
sys.exit(4)
PY
}

main() {
  require_cmd git
  require_cmd docker
  require_cmd curl
  require_cmd jq
  require_cmd python3

  [[ -n ${GUARDIAN_API_KEY:-} ]] || fail "GUARDIAN_API_KEY is required"

  require_clean_tree

  API_BASE="${API_BASE:-http://localhost:8888}"
  local upload_endpoint="${API_BASE}/api/upload-chatgpt-export"
  local threads_endpoint="${API_BASE}/api/chat/threads"

  local run_id
  run_id="$(date -u '+%Y%m%dT%H%M%SZ')"
  local thread_title="Migration Validation ${run_id}"
  local sentinel="MIGRATION-LOOP-SENTINEL-${run_id}"

  local payload_file upload_json threads_json messages_json
  payload_file="$(mktemp)"
  upload_json="$(mktemp)"
  threads_json="$(mktemp)"
  messages_json="$(mktemp)"
  trap 'for f in "${payload_file:-}" "${upload_json:-}" "${threads_json:-}" "${messages_json:-}"; do [[ -n "$f" ]] && rm -f "$f"; done' EXIT

  cat >"$payload_file" <<JSON
[
  {
    "id": "migration-validation-${run_id}",
    "title": "${thread_title}",
    "current_node": "assistant-node",
    "mapping": {
      "user-node": {
        "id": "user-node",
        "parent": null,
        "children": ["assistant-node"],
        "message": {
          "author": {"role": "user"},
          "content": {"parts": ["${sentinel}"]},
          "create_time": 1
        }
      },
      "assistant-node": {
        "id": "assistant-node",
        "parent": "user-node",
        "children": [],
        "message": {
          "author": {"role": "assistant"},
          "content": {"parts": ["Migration validator acknowledgement."]},
          "create_time": 2
        }
      }
    }
  }
]
JSON

  log "Starting db/redis/backend via docker compose"
  docker compose up -d db redis backend >/dev/null

  wait_for_backend
  log "Backend healthy"

  log "Uploading migration payload"
  curl -fsS -H "X-API-Key: ${GUARDIAN_API_KEY}" -F "file=@${payload_file};type=application/json" "$upload_endpoint" >"$upload_json"

  local threads_imported messages_imported
  threads_imported="$(jq -r '.threads_imported' "$upload_json")"
  messages_imported="$(jq -r '.messages_imported' "$upload_json")"

  [[ "$threads_imported" == "1" ]] || fail "Expected threads_imported=1, got ${threads_imported}"
  [[ "$messages_imported" == "2" ]] || fail "Expected messages_imported=2, got ${messages_imported}"
  log "Upload response OK (threads_imported=${threads_imported}, messages_imported=${messages_imported})"

  log "Resolving imported thread in /api/chat/threads"
  curl -fsS -H "X-API-Key: ${GUARDIAN_API_KEY}" "$threads_endpoint" >"$threads_json"
  local thread_id
  thread_id="$(latest_thread_id_by_title "$threads_json" "$thread_title")" || fail "Imported thread '${thread_title}' not found in /api/chat/threads"

  log "Fetching persisted messages for thread_id=${thread_id}"
  curl -fsS -H "X-API-Key: ${GUARDIAN_API_KEY}" "${API_BASE}/api/chat/${thread_id}/messages?limit=20" >"$messages_json"
  assert_messages_include_sentinel "$messages_json" "$sentinel" >/dev/null || fail "Imported sentinel message was not persisted/retrievable"

  log "PASS: migration loop validated (thread_id=${thread_id}, sentinel=${sentinel})"
}

main "$@"
