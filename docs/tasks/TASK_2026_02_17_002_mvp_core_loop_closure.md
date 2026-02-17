# CAMPAIGN_2026_02_17_MVP_CORE_LOOP_CLOSURE

## Campaign Metadata
- campaign_id: CAMPAIGN_2026_02_17_MVP_CORE_LOOP_CLOSURE
- campaign_slug: mvp-core-loop-closure
- campaign_doc_path: docs/Campaign/<RUNNER_DETERMINES>.md
- source_findings: FINDING-2026-02-17-003, 004, 005, 006, 007, 008, 010
- objective: Close non-deterministic loop-validation gaps by aligning validators/docs to runtime contracts, adding missing migration validation assets, and wiring an aggregate harness into CI.

## Tasks

### Task 001
- task_id: 001
- task_title: Add migration loop validator + runbook with real-stack persistence criteria
- risk: MED
- task_artifact_path: docs/tasks/<RUNNER_DETERMINES>.md
- allowed_files:
  - scripts/verification/validate_migration_loop.sh
  - docs/guardian/migration_loop_validation.md
  - tests/routes/test_migration_routes.py
- command_checklist:
  1. Preflight: git status --porcelain -uall must be empty
  2. test -z "$(git status --porcelain -uall)" || { echo "STOP: dirty tree"; echo "Cleanup: git stash push -u -m preflight-CAMPAIGN_2026_02_17_MVP_CORE_LOOP_CLOSURE-001"; exit 1; }
  3. rg -n "upload-chatgpt-export|Depends\\(require_api_key\\)" guardian/routes/migration.py
  4. rg -n "test_migration_route_executes_real_ingest_and_embeds|monkeypatch.setattr" tests/routes/test_migration_routes.py
  5. rg --files scripts docs/guardian | rg -i "migration.*(validation|loop)" || true
  6. violations="$(git diff --name-only | rg -v '^(scripts/verification/validate_migration_loop\\.sh|docs/guardian/migration_loop_validation\\.md|tests/routes/test_migration_routes\\.py)$' || true)"; test -z "$violations" || { echo "STOP: out-of-scope files detected"; printf '%s\n' "$violations"; echo "Cleanup: git restore --staged $violations && git restore $violations"; exit 1; }
  7. bash scripts/verification/validate_migration_loop.sh
  8. pytest -q tests/routes/test_migration_routes.py::test_migration_route_executes_real_ingest_and_embeds
- expected_outputs:
  - migration validator script exists and exits 0 with explicit PASS/FAIL output
  - migration runbook exists and documents deterministic authenticated flow
  - targeted migration test passes with real-stack persistence assertions
- rollback_commands:
  - git restore scripts/verification/validate_migration_loop.sh docs/guardian/migration_loop_validation.md tests/routes/test_migration_routes.py
- dependencies:
  - command -v bash >/dev/null
  - command -v pytest >/dev/null
  - docker compose ps >/dev/null
  - test -n "${GUARDIAN_API_KEY:-}" || { echo "STOP: GUARDIAN_API_KEY required"; exit 1; }

### Task 002
- task_id: 002
- task_title: Align doc-upload validator + runbook with current API contract
- risk: MED
- task_artifact_path: docs/tasks/<RUNNER_DETERMINES>.md
- allowed_files:
  - scripts/validate_doc_upload_embedding.sh
  - docs/guardian/doc_upload_embedding_validation.md
- command_checklist:
  1. Preflight: git status --porcelain -uall must be empty
  2. test -z "$(git status --porcelain -uall)" || { echo "STOP: dirty tree"; echo "Cleanup: git stash push -u -m preflight-CAMPAIGN_2026_02_17_MVP_CORE_LOOP_CLOSURE-002"; exit 1; }
  3. rg -n "class DocumentUploadResponse|@router.get\\(\\\"/documents\\\"|\\\"documents\\\"" guardian/routes/media.py
  4. rg -n "project_id|items|embedding_status" scripts/validate_doc_upload_embedding.sh docs/guardian/doc_upload_embedding_validation.md
  5. violations="$(git diff --name-only | rg -v '^(scripts/validate_doc_upload_embedding\\.sh|docs/guardian/doc_upload_embedding_validation\\.md)$' || true)"; test -z "$violations" || { echo "STOP: out-of-scope files detected"; printf '%s\n' "$violations"; echo "Cleanup: git restore --staged $violations && git restore $violations"; exit 1; }
  6. bash scripts/validate_doc_upload_embedding.sh
- expected_outputs:
  - validator references current payload shape (documents key, no project_id dependency)
  - runbook examples match validator and route behavior
  - validation script exits 0 on success path
- rollback_commands:
  - git restore scripts/validate_doc_upload_embedding.sh docs/guardian/doc_upload_embedding_validation.md
- dependencies:
  - command -v bash >/dev/null
  - test -n "${GUARDIAN_API_KEY:-}" || { echo "STOP: GUARDIAN_API_KEY required"; exit 1; }
  - docker compose ps >/dev/null

### Task 003
- task_id: 003
- task_title: Align image gallery/image-gen validator + docs to runtime schema and add explicit auth assertion
- risk: MED
- task_artifact_path: docs/tasks/<RUNNER_DETERMINES>.md
- allowed_files:
  - scripts/validate_image_gallery.sh
  - docs/guardian/image_gallery_validation.md
  - tests/routes/test_media_routes.py
- command_checklist:
  1. Preflight: git status --porcelain -uall must be empty
  2. test -z "$(git status --porcelain -uall)" || { echo "STOP: dirty tree"; echo "Cleanup: git stash push -u -m preflight-CAMPAIGN_2026_02_17_MVP_CORE_LOOP_CLOSURE-003"; exit 1; }
  3. rg -n "@router.get\\(\\\"/images\\\"|\\\"images\\\"|count|class ImageGenerationResponse|return ImageGenerationResponse|tag" guardian/routes/media.py
  4. rg -n "items|tag|/api/media/images" scripts/validate_image_gallery.sh docs/guardian/image_gallery_validation.md
  5. violations="$(git diff --name-only | rg -v '^(scripts/validate_image_gallery\\.sh|docs/guardian/image_gallery_validation\\.md|tests/routes/test_media_routes\\.py)$' || true)"; test -z "$violations" || { echo "STOP: out-of-scope files detected"; printf '%s\n' "$violations"; echo "Cleanup: git restore --staged $violations && git restore $violations"; exit 1; }
  6. pytest -q tests/routes/test_media_routes.py::TestImageGeneration::test_generate_image_success tests/routes/test_media_routes.py::TestImageGeneration::test_generate_image_requires_api_key
  7. bash scripts/validate_image_gallery.sh
  8. if rg -n "\\bitems\\b|\\btag\\b" scripts/validate_image_gallery.sh docs/guardian/image_gallery_validation.md; then echo "STOP: legacy contract references remain"; exit 1; fi
- expected_outputs:
  - image validator and docs use images payload and canonical image-gen response fields
  - explicit unauthorized image-gen assertion exists and passes
  - validation script exits 0
- rollback_commands:
  - git restore scripts/validate_image_gallery.sh docs/guardian/image_gallery_validation.md tests/routes/test_media_routes.py
- dependencies:
  - command -v bash >/dev/null
  - command -v pytest >/dev/null
  - test -n "${GUARDIAN_API_KEY:-}" || { echo "STOP: GUARDIAN_API_KEY required"; exit 1; }
  - test -n "${OPENAI_API_KEY:-}" || { echo "STOP: OPENAI_API_KEY required"; exit 1; }
  - test -n "${LLM_PROVIDER:-}" || { echo "STOP: LLM_PROVIDER required"; exit 1; }

### Task 004
- task_id: 004
- task_title: Create aggregate core-loop harness and execute it in CI with matrix alignment
- risk: MED
- task_artifact_path: docs/tasks/<RUNNER_DETERMINES>.md
- allowed_files:
  - scripts/validate_core_loops.sh
  - .github/workflows/guardian-ci.yml
  - docs/reports/mvp-core-loop-closure-matrix.md
- command_checklist:
  1. Preflight: git status --porcelain -uall must be empty
  2. test -z "$(git status --porcelain -uall)" || { echo "STOP: dirty tree"; echo "Cleanup: git stash push -u -m preflight-CAMPAIGN_2026_02_17_MVP_CORE_LOOP_CLOSURE-004"; exit 1; }
  3. test -f scripts/validate_core_loops.sh && echo present || echo missing
  4. rg -n "PASS|validate_core_loops.sh" docs/reports/mvp-core-loop-closure-matrix.md
  5. rg -n "test_rag_integration_memory_loop|test_migration_route_executes_real_ingest_and_embeds|test_generate_image_success|test_document_generate_persists_and_links" .github/workflows/guardian-ci.yml
  6. test -f scripts/verification/validate_migration_loop.sh || { echo "STOP: Task 001 in this campaign must complete first"; exit 1; }
  7. violations="$(git diff --name-only | rg -v '^(scripts/validate_core_loops\\.sh|\\.github/workflows/guardian-ci\\.yml|docs/reports/mvp-core-loop-closure-matrix\\.md)$' || true)"; test -z "$violations" || { echo "STOP: out-of-scope files detected"; printf '%s\n' "$violations"; echo "Cleanup: git restore --staged $violations && git restore $violations"; exit 1; }
  8. bash scripts/validate_core_loops.sh
  9. rg -n "validate_core_loops.sh" .github/workflows/guardian-ci.yml docs/reports/mvp-core-loop-closure-matrix.md
- expected_outputs:
  - scripts/validate_core_loops.sh exists and runs declared loop selectors with deterministic pass/fail exit code
  - CI workflow runs aggregate harness
  - matrix references real harness/selectors instead of missing artifacts
- rollback_commands:
  - git restore scripts/validate_core_loops.sh .github/workflows/guardian-ci.yml docs/reports/mvp-core-loop-closure-matrix.md
- dependencies:
  - command -v bash >/dev/null
  - docker compose ps >/dev/null
  - test -n "${GUARDIAN_API_KEY:-}" || { echo "STOP: GUARDIAN_API_KEY required"; exit 1; }
