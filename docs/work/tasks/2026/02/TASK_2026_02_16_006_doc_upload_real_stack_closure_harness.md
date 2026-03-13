Preflight: git status --porcelain -uall must be empty

If preflight is not empty, STOP and run exactly:
- git status --porcelain -uall
- git stash push -u -m "preflight-TASK-2026-02-16-006"
- git status --porcelain -uall

# TASK-2026-02-16-006  Doc-upload real-stack closure harness + runbook
- Risk: MED
- Findings: FINDING-2026-02-16-003
- Allowed files:
  - scripts/validate_doc_upload_embedding.sh
  - docs/reference/guardian/doc_upload_embedding_validation.md
  - tests/routes/test_media_routes.py
  - guardian/routes/media.py
  - guardian/routes/documents.py
  - docs/work/reports/mvp-core-loop-closure-matrix.md
- Dependencies/Prereqs:
  - command -v docker
  - command -v curl
  - command -v jq
  - command -v pytest
  - test -n "${GUARDIAN_API_KEY:-}"
  - docker compose up -d db redis backend worker-document-embed
- Command checklist:
  1. pytest -q tests/routes/test_media_routes.py::TestUploadDedupeAndResolve::test_upload_document_enqueues_embedding_with_asset_metadata
  2. Update doc-upload validator script to enforce non-proxy API-key upload and backend list/read verification.
  3. Update doc-upload runbook with one deterministic authenticated flow.
  4. bash scripts/validate_doc_upload_embedding.sh
  5. curl -s -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/api/threads/1/documents
- Scope guard:
  - git diff --name-only
  - If any changed file is outside Allowed files, STOP and run exactly:
    - git restore --staged --worktree -- .
    - git clean -fd
    - git status --porcelain -uall
- Expected outputs:
  - Doc-upload validator exits 0 and proves persistence visibility.
  - Runbook matches exact executable sequence.
- Rollback / cleanup commands:
  - git restore --staged --worktree -- scripts/validate_doc_upload_embedding.sh docs/reference/guardian/doc_upload_embedding_validation.md tests/routes/test_media_routes.py guardian/routes/media.py guardian/routes/documents.py docs/work/reports/mvp-core-loop-closure-matrix.md
  - git status --porcelain -uall