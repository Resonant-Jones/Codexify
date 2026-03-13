Preflight: git status --porcelain -uall must be empty

If preflight is not empty, STOP and run exactly:
- git status --porcelain -uall
- git stash push -u -m "preflight-TASK-2026-02-16-012"
- git status --porcelain -uall

# TASK-2026-02-16-012  Doc-gen real-stack closure harness + runbook
- Risk: MED
- Findings: FINDING-2026-02-16-007
- Allowed files:
  - scripts/validate_doc_gen.sh
  - docs/reference/operator/ops/doc-gen-validation.md
  - guardian/tests/test_document_gen_persist_and_link.py
  - guardian/routes/documents.py
  - docs/work/reports/mvp-core-loop-closure-matrix.md
- Dependencies/Prereqs:
  - command -v docker
  - command -v curl
  - command -v jq
  - command -v pytest
  - test -n "${GUARDIAN_API_KEY:-}"
  - docker compose up -d db backend
- Command checklist:
  1. pytest -q guardian/tests/test_document_gen_persist_and_link.py::test_document_generate_persists_and_links
  2. Update doc-gen validator script to enforce authenticated non-proxy generation + backend retrieval checks.
  3. Update doc-gen runbook with exact deterministic commands and pass/fail gates.
  4. bash scripts/validate_doc_gen.sh
- Scope guard:
  - git diff --name-only
  - If any changed file is outside Allowed files, STOP and run exactly:
    - git restore --staged --worktree -- .
    - git clean -fd
    - git status --porcelain -uall
- Expected outputs:
  - Doc-gen closure is reproducible against local services.
  - Selector + script exit 0.
- Rollback / cleanup commands:
  - git restore --staged --worktree -- scripts/validate_doc_gen.sh docs/reference/operator/ops/doc-gen-validation.md guardian/tests/test_document_gen_persist_and_link.py guardian/routes/documents.py docs/work/reports/mvp-core-loop-closure-matrix.md
  - git status --porcelain -uall