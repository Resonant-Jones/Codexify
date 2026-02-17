#!/usr/bin/env bash
# Aggregate deterministic harness for MVP core loops.
set -euo pipefail

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log "FAIL: required command '$1' not found"
    exit 1
  fi
}

usage() {
  cat <<'USAGE'
Usage: bash scripts/validate_core_loops.sh [--dry-run]

Runs deterministic pytest selectors for MVP core loops in a fixed order.
Options:
  --dry-run   Print selectors without executing pytest.
USAGE
}

main() {
  local dry_run=0
  if [[ "${1:-}" == "--dry-run" ]]; then
    dry_run=1
  elif [[ -n "${1:-}" ]]; then
    usage
    exit 2
  fi

  require_cmd bash
  require_cmd pytest

  export GUARDIAN_API_KEY="${GUARDIAN_API_KEY:-test}"
  export OPENAI_API_KEY="${OPENAI_API_KEY:-dummy}"
  export LLM_PROVIDER="${LLM_PROVIDER:-local}"

  local -a loops=(
    "rag"
    "migration"
    "doc-upload"
    "image-gallery"
    "image-gen"
    "doc-gen"
  )
  local -a selectors=(
    "tests/integration/test_rag_integration_loop.py::test_rag_integration_memory_loop"
    "tests/routes/test_migration_routes.py::test_migration_route_executes_real_ingest_and_embeds"
    "tests/routes/test_media_routes.py::TestUploadDedupeAndResolve::test_upload_document_enqueues_embedding_with_asset_metadata"
    "tests/routes/test_media_routes.py::TestUploadDedupeAndResolve::test_list_images_generated_tag_returns_generated"
    "tests/routes/test_media_routes.py::TestImageGeneration::test_generate_image_success"
    "guardian/tests/test_document_gen_persist_and_link.py::test_document_generate_persists_and_links"
  )

  local pass_count=0
  local fail_count=0

  log "Starting MVP core loop harness"

  local i
  for i in "${!loops[@]}"; do
    local loop_name="${loops[$i]}"
    local selector="${selectors[$i]}"

    if (( dry_run == 1 )); then
      log "PASS [dry-run] ${loop_name}: ${selector}"
      ((pass_count += 1))
      continue
    fi

    log "RUN ${loop_name}: ${selector}"
    if pytest -q "$selector"; then
      log "PASS ${loop_name}: ${selector}"
      ((pass_count += 1))
    else
      log "FAIL ${loop_name}: ${selector}"
      ((fail_count += 1))
    fi
  done

  if (( fail_count > 0 )); then
    log "FAIL: core loop harness completed with ${fail_count} failing selector(s) and ${pass_count} passing selector(s)"
    exit 1
  fi

  log "PASS: core loop harness completed with ${pass_count} passing selector(s)"
}

main "$@"
