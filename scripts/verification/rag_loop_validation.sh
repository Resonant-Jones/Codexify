#!/usr/bin/env bash
# Deterministic RAG loop validator.
# Brings up the async stack, triggers a completion, and asserts messages + trace materialize.
set -euo pipefail

say() {
  printf '\n[%s] %s\n' "$1" "$2"
}

fail() {
  printf '\n[FAIL] %s\n' "$1" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

normalize_url() {
  local raw="$1"
  if [[ "$raw" =~ ^https?:// ]]; then
    printf '%s' "$raw"
  else
    local base="${API_BASE%/}"
    raw="${raw#/}"
    printf '%s/%s' "$base" "$raw"
  fi
}

API_BASE="${GUARDIAN_API_BASE:-http://localhost:8888}"
API_KEY="${GUARDIAN_API_KEY:-}"
USER_ID="${GUARDIAN_USER_ID:-default}"
POLL_SECONDS="${GUARDIAN_RAG_POLL_SECONDS:-2}"
POLL_ATTEMPTS="${GUARDIAN_RAG_POLL_ATTEMPTS:-30}"
CURL_TIMEOUT="${GUARDIAN_RAG_CURL_TIMEOUT:-5}"
PROMPT_TEXT="${GUARDIAN_RAG_PROMPT:-RAG validation ping $(date -u +%Y-%m-%dT%H:%M:%SZ)}"
PROVIDER="${GUARDIAN_RAG_PROVIDER:-local}"
DEPTH_MODE="${GUARDIAN_RAG_DEPTH_MODE:-normal}"

say STEP "Preflight command availability"
require_cmd docker
require_cmd curl
require_cmd jq
require_cmd rg
require_cmd git

if [[ -z "$API_KEY" ]]; then
  fail "GUARDIAN_API_KEY is required. Export it before running this script."
fi

say STEP "Repo cleanliness"
if [[ -n "$(git status --porcelain -uall)" ]]; then
  fail "Working tree has uncommitted changes. Commit/stash before running."
fi

say STEP "docker compose up -d db redis backend worker-chat"
if ! docker compose up -d db redis backend worker-chat; then
  fail "Docker compose bring-up failed. Ensure Docker is running and you have permission to access the daemon."
fi

say STEP "Backend health at ${API_BASE}/health"
if ! curl -fsS --max-time "$CURL_TIMEOUT" "$API_BASE/health" >/dev/null; then
  fail "Backend health check failed at $API_BASE/health"
fi

say STEP "OpenAPI advertises threads, complete, rag-trace"
if ! curl -fsS --max-time "$CURL_TIMEOUT" "$API_BASE/openapi.json" \
  | rg -n '\/api\/chat\/threads|\/chat\/\{thread_id\}\/complete|\/api\/chat\/debug\/rag-trace' >/dev/null; then
  fail "OpenAPI contract is missing required endpoints"
fi

say STEP "Create chat thread"
create_resp=$(curl -fsS --max-time "$CURL_TIMEOUT" \
  -H "X-API-Key: $API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"title":"RAG validation","user_id":"'"$USER_ID"'"}' \
  "$API_BASE/api/chat/threads")
thread_id=$(jq -er '.id' <<<"$create_resp")
say INFO "thread_id=$thread_id"

say STEP "Post seed user message"
message_payload=$(jq -n --arg txt "$PROMPT_TEXT" --arg user "$USER_ID" '{role:"user", content:$txt, user_id:$user}')
if ! curl -fsS --max-time "$CURL_TIMEOUT" \
  -H "X-API-Key: $API_KEY" \
  -H 'Content-Type: application/json' \
  -d "$message_payload" \
  "$API_BASE/api/chat/$thread_id/messages" >/dev/null; then
  fail "Failed to post user message"
fi

say STEP "Enqueue async completion"
completion_body=$(jq -n --arg provider "$PROVIDER" --arg depth "$DEPTH_MODE" '{provider:$provider, depth_mode:$depth}')
complete_resp=$(curl -fsS --max-time "$CURL_TIMEOUT" \
  -H "X-API-Key: $API_KEY" \
  -H 'Content-Type: application/json' \
  -d "$completion_body" \
  "$API_BASE/api/chat/$thread_id/complete")

task_id=$(jq -er '.task_id' <<<"$complete_resp")
messages_url=$(normalize_url "$(jq -er '.messages_url' <<<"$complete_resp")")
trace_url=$(normalize_url "$(jq -er '.trace_url' <<<"$complete_resp")")
say INFO "task_id=$task_id"

say STEP "Poll messages for assistant response"
assistant_json=""
for attempt in $(seq 1 "$POLL_ATTEMPTS"); do
  if resp=$(curl -fsS --max-time "$CURL_TIMEOUT" -H "X-API-Key: $API_KEY" "$messages_url" 2>/dev/null); then
    candidate=$(jq -c '[.messages[] | select(.role=="assistant")] | last // empty' <<<"$resp")
    if [[ -n "$candidate" && "$candidate" != "null" && "$candidate" != "" ]]; then
      assistant_json="$candidate"
      break
    fi
  fi
  sleep "$POLL_SECONDS"
done

if [[ -z "$assistant_json" || "$assistant_json" == "null" ]]; then
  fail "Assistant message never materialized within $((POLL_SECONDS * POLL_ATTEMPTS))s"
fi
assistant_id=$(jq -r '.id' <<<"$assistant_json")
say PASS "Assistant reply persisted (message_id=$assistant_id)"

say STEP "Poll rag trace endpoint for populated documents/graph"
trace_json=""
for attempt in $(seq 1 "$POLL_ATTEMPTS"); do
  if resp=$(curl -fsS --max-time "$CURL_TIMEOUT" -H "X-API-Key: $API_KEY" "$trace_url" 2>/dev/null); then
    docs=$(jq '.documents | length' <<<"$resp") || docs=0
    graph=$(jq '.graph | length' <<<"$resp") || graph=0
    if (( docs > 0 || graph > 0 )); then
      trace_json="$resp"
      break
    fi
  fi
  sleep "$POLL_SECONDS"
done

if [[ -z "$trace_json" ]]; then
  fail "RAG trace never returned populated documents/graph within $((POLL_SECONDS * POLL_ATTEMPTS))s"
fi
doc_count=$(jq '.documents | length' <<<"$trace_json")
graph_count=$(jq '.graph | length' <<<"$trace_json")
say PASS "RAG trace available (documents=$doc_count, graph=$graph_count)"

say PASS "Async RAG completion loop validated (task_id=$task_id, thread_id=$thread_id)"
