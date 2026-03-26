#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

BASE="${GUARDIAN_API_BASE:-http://127.0.0.1:8888}"
OUT_DIR="docs/audits/supported_path"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_FILE="$OUT_DIR/supported_path_$TS.json"
POLL_SECONDS="${SUPPORTED_PATH_POLL_SECONDS:-2}"
POLL_ATTEMPTS="${SUPPORTED_PATH_POLL_ATTEMPTS:-30}"

mkdir -p "$OUT_DIR"

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

wait_for_backend() {
  local attempt
  for attempt in $(seq 1 "$POLL_ATTEMPTS"); do
    if curl -fsS "$BASE/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$POLL_SECONDS"
  done
  return 1
}

poll_for_assistant_message() {
  local thread_id="$1"
  local prior_count="$2"
  local attempt
  local messages assistant_count

  for attempt in $(seq 1 "$POLL_ATTEMPTS"); do
    messages="$(curl -fsS -H "X-API-Key: $GUARDIAN_API_KEY" \
      "$BASE/api/chat/$thread_id/messages")"
    assistant_count="$(jq '[.messages[] | select(.role == "assistant")] | length' <<<"$messages")"

    if (( assistant_count > prior_count )); then
      jq -r '[.messages[] | select(.role == "assistant") | .content] | last // empty' <<<"$messages"
      return 0
    fi

    sleep "$POLL_SECONDS"
  done

  return 1
}

poll_for_document_status() {
  local thread_id="$1"
  local document_id="$2"
  local attempt
  local docs status

  for attempt in $(seq 1 "$POLL_ATTEMPTS"); do
    docs="$(curl -fsS -H "X-API-Key: $GUARDIAN_API_KEY" \
      "$BASE/api/media/documents?thread_id=$thread_id&limit=20")"
    status="$(jq -r --arg doc_id "$document_id" \
      '.documents[] | select(.id == $doc_id) | .embedding_status' <<<"$docs")"

    if [[ "$status" == "ready" ]]; then
      return 0
    fi

    if [[ "$status" == "failed" ]]; then
      fail "Embedding reported failed for document $document_id"
    fi

    sleep "$POLL_SECONDS"
  done

  return 1
}

require_cmd docker
require_cmd curl
require_cmd jq

log "INFO: Starting supported-path proof run at $TS"

if [[ -z "${GUARDIAN_API_KEY:-}" ]]; then
  fail "GUARDIAN_API_KEY not set"
fi

if [[ ! -f README.md ]]; then
  fail "README.md not found at repo root"
fi

log "INFO: Booting compose services"
docker compose up -d db redis backend worker-chat worker-document-embed >/dev/null

log "INFO: Waiting for backend health at $BASE/health"
wait_for_backend || fail "Backend health check did not become ready"

JSON_HEADERS=(-H "X-API-Key: $GUARDIAN_API_KEY" -H "Content-Type: application/json")
AUTH_HEADER=(-H "X-API-Key: $GUARDIAN_API_KEY")

log "INFO: Creating thread"
THREAD="$(curl -fsS "${JSON_HEADERS[@]}" -X POST "$BASE/api/chat/threads" -d '{}')"
THREAD_ID="$(jq -r '.id // .thread.id // empty' <<<"$THREAD")"

if [[ -z "$THREAD_ID" || "$THREAD_ID" == "null" ]]; then
  fail "Thread creation failed"
fi

log "OK: Thread created: $THREAD_ID"

log "INFO: Posting deterministic completion prompt"
MSG="$(curl -fsS "${JSON_HEADERS[@]}" -X POST "$BASE/api/chat/$THREAD_ID/messages" \
  -d '{"role":"user","content":"Reply with exactly: supported-path-proof"}')"

if ! jq -e '.ok == true' >/dev/null <<<"$MSG"; then
  fail "Message post failed"
fi

log "OK: Message posted"

INITIAL_ASSISTANT_COUNT=0
log "INFO: Triggering completion"
COMPLETE="$(curl -fsS "${JSON_HEADERS[@]}" -X POST "$BASE/api/chat/$THREAD_ID/complete" -d '{}')"
TASK_ID="$(jq -r '.task_id // empty' <<<"$COMPLETE")"

if [[ -z "$TASK_ID" || "$TASK_ID" == "null" ]]; then
  fail "Completion enqueue failed"
fi

log "OK: Completion accepted: $TASK_ID"
log "INFO: Waiting for assistant completion"
ASSISTANT="$(poll_for_assistant_message "$THREAD_ID" "$INITIAL_ASSISTANT_COUNT")" \
  || fail "Assistant response not found for initial completion"

if [[ -z "$ASSISTANT" || "$ASSISTANT" == "null" ]]; then
  fail "Assistant response was empty for initial completion"
fi

log "OK: Assistant response received"

log "INFO: Uploading README.md as proof document"
DOC="$(curl -fsS "${AUTH_HEADER[@]}" -X POST "$BASE/api/media/upload/document" \
  -F "file=@README.md" \
  -F "thread_id=$THREAD_ID")"
DOC_ID="$(jq -r '.id // .document.id // empty' <<<"$DOC")"

if [[ -z "$DOC_ID" || "$DOC_ID" == "null" ]]; then
  fail "Document upload failed"
fi

log "OK: Document uploaded: $DOC_ID"
log "INFO: Waiting for embedding readiness"
poll_for_document_status "$THREAD_ID" "$DOC_ID" \
  || fail "Embedding did not reach ready state"

log "OK: Embedding ready"

log "INFO: Posting retrieval probe"
RETRIEVAL_MSG="$(curl -fsS "${JSON_HEADERS[@]}" -X POST "$BASE/api/chat/$THREAD_ID/messages" \
  -d '{"role":"user","content":"Use the uploaded README to summarize this repository in one sentence."}')"

if ! jq -e '.ok == true' >/dev/null <<<"$RETRIEVAL_MSG"; then
  fail "Retrieval message post failed"
fi

log "OK: Retrieval message posted"

PRE_RETRIEVAL_ASSISTANT_COUNT="$(curl -fsS "${AUTH_HEADER[@]}" \
  "$BASE/api/chat/$THREAD_ID/messages" \
  | jq '[.messages[] | select(.role == "assistant")] | length')"

log "INFO: Triggering retrieval completion"
RETRIEVAL_COMPLETE="$(curl -fsS "${JSON_HEADERS[@]}" -X POST "$BASE/api/chat/$THREAD_ID/complete" -d '{}')"
RETRIEVAL_TASK_ID="$(jq -r '.task_id // empty' <<<"$RETRIEVAL_COMPLETE")"

if [[ -z "$RETRIEVAL_TASK_ID" || "$RETRIEVAL_TASK_ID" == "null" ]]; then
  fail "Retrieval completion enqueue failed"
fi

log "OK: Retrieval completion accepted: $RETRIEVAL_TASK_ID"
log "INFO: Waiting for retrieval assistant response"
RETRIEVAL_ASSISTANT="$(poll_for_assistant_message "$THREAD_ID" "$PRE_RETRIEVAL_ASSISTANT_COUNT")" \
  || fail "Assistant response not found for retrieval completion"

if [[ -z "$RETRIEVAL_ASSISTANT" || "$RETRIEVAL_ASSISTANT" == "null" ]]; then
  fail "Assistant response was empty for retrieval completion"
fi

log "OK: Retrieval assistant response received"

log "INFO: Fetching latest RAG trace"
TRACE="$(curl -fsS "${AUTH_HEADER[@]}" "$BASE/api/chat/debug/rag-trace/$THREAD_ID/latest")"
DOC_COUNT="$(jq '.documents | length' <<<"$TRACE")"

if (( DOC_COUNT == 0 )); then
  fail "Retrieval returned no documents"
fi

log "OK: Retrieval returned $DOC_COUNT documents"

jq -n \
  --arg timestamp "$TS" \
  --arg thread_id "$THREAD_ID" \
  --arg task_id "$TASK_ID" \
  --arg retrieval_task_id "$RETRIEVAL_TASK_ID" \
  --arg assistant "$ASSISTANT" \
  --arg retrieval_assistant "$RETRIEVAL_ASSISTANT" \
  --arg document_id "$DOC_ID" \
  --arg retrieved_documents "$DOC_COUNT" \
  '{
    timestamp: $timestamp,
    thread_id: $thread_id,
    task_id: $task_id,
    retrieval_task_id: $retrieval_task_id,
    assistant: $assistant,
    retrieval_assistant: $retrieval_assistant,
    document_id: $document_id,
    retrieved_documents: ($retrieved_documents | tonumber)
  }' >"$OUT_FILE"

log "SUCCESS: Supported-path proof complete"
log "ARTIFACT: $OUT_FILE"
