#!/usr/bin/env bash
# Deterministic Beta-1 verification gate (non-docker).
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

main() {
  require_cmd pytest
  require_cmd pnpm

  export GUARDIAN_API_KEY="${GUARDIAN_API_KEY:-test-api-key}"
  export ENABLE_CONNECTOR_WORKER="${ENABLE_CONNECTOR_WORKER:-0}"
  export CODEXIFY_EMBEDDINGS_BACKEND="${CODEXIFY_EMBEDDINGS_BACKEND:-mock}"

  local -a selectors=(
    "tests/core/test_beta_router_quarantine.py::test_beta_core_only_quarantines_non_core_routers"
    "tests/routes/test_chat_routes.py::TestChatCompletePost::test_complete_groq_error"
    "tests/routes/test_chat_routes.py::TestChatCompletePost::test_complete_turn_lock_error_returns_structured_503"
    "tests/routes/test_metrics.py::test_health_chat_endpoint"
    "tests/routes/test_migration_routes.py::test_migration_route_executes_real_ingest_and_embeds"
    "tests/routes/test_media_routes.py::TestUploadDedupeAndResolve::test_upload_document_enqueues_embedding_with_asset_metadata"
    "tests/routes/test_media_routes.py::TestMediaQuarantine::test_generate_image_quarantined_in_beta_core_mode"
    "tests/routes/test_media_routes.py::TestMediaQuarantine::test_tts_quarantined_when_disabled"
  )

  log "Running Beta-1 pytest gate selectors"
  local selector
  for selector in "${selectors[@]}"; do
    log "RUN pytest -q $selector"
    pytest -q "$selector"
  done

  log "Running Beta-1 frontend completion-signal checks"
  pnpm --dir frontend/src exec vitest run \
    features/chat/__tests__/GuardianChat.offline-banner.test.tsx \
    test/chatClient.completePayload.test.ts

  log "PASS: Beta-1 deterministic core gate"
}

main "$@"
