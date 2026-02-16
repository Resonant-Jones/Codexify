# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_MVP_CORE_LOOP_CLOSURE
- Task ID: 007
- Title: Deterministic doc-gen closure via backend retrieval after reload
- Finding: FINDING-2026-02-10-009
- Risk: MED

## Allowed Files
- guardian/tests/test_document_gen_persist_and_link.py
- guardian/tests/test_document_gen_pipeline.py
- guardian/routes/documents.py
- frontend/src/App.tsx
- frontend/src/tests/playwright/doc_gen_reload_persistence.spec.ts

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
4. test -n ${AI_BACKEND:-} || { echo 'Missing AI_BACKEND'; exit 1; }
5. test -n ${DATABASE_URL:-} || { echo 'Missing DATABASE_URL'; exit 1; }
6. rg -n 'thread_id is required|/api/documents/generate|cfy:documents:add' guardian/routes/documents.py frontend/src/App.tsx
7. pytest guardian/tests/test_document_gen_persist_and_link.py guardian/tests/test_document_gen_pipeline.py -q
8. cd frontend && npx playwright test src/tests/playwright/doc_gen_reload_persistence.spec.ts
9. for f in $(git diff --name-only); do case $f in guardian/tests/test_document_gen_persist_and_link.py|guardian/tests/test_document_gen_pipeline.py|guardian/routes/documents.py|frontend/src/App.tsx|frontend/src/tests/playwright/doc_gen_reload_persistence.spec.ts) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- Deterministic test proves generate -> persist -> thread-link -> backend retrieval after reload.
- Authenticated non-proxy behavior remains valid.
- Pipeline and persistence tests pass alongside reload assertion.

## Rollback / Cleanup
- git restore --staged guardian/tests/test_document_gen_persist_and_link.py guardian/tests/test_document_gen_pipeline.py guardian/routes/documents.py frontend/src/App.tsx frontend/src/tests/playwright/doc_gen_reload_persistence.spec.ts || true
- git restore guardian/tests/test_document_gen_persist_and_link.py guardian/tests/test_document_gen_pipeline.py guardian/routes/documents.py frontend/src/App.tsx frontend/src/tests/playwright/doc_gen_reload_persistence.spec.ts || true
- rm -f frontend/src/tests/playwright/doc_gen_reload_persistence.spec.ts

## Dependencies / Prereqs
- command -v git >/dev/null
- command -v rg >/dev/null
- command -v pytest >/dev/null
- command -v npx >/dev/null
- test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
- test -n ${AI_BACKEND:-} || { echo 'Missing AI_BACKEND'; exit 1; }
- test -n ${DATABASE_URL:-} || { echo 'Missing DATABASE_URL'; exit 1; }


---

# Task 007 — Tooling/Docs: Deterministic Doc-Upload + Embed Validation Artifact (FINDING-2026-02-16-006)

Preflight: git status --porcelain -uall must be empty

## STOP Conditions
1) If preflight is not empty, STOP and run:
- `git status --porcelain -uall`
- `git restore --staged --worktree -- .`
- `git clean -fd`

2) If any out-of-scope files appear at any point, STOP and run:
- `git status --porcelain -uall`
- `git restore --staged --worktree -- .`
- `git clean -fd`

## Finding
- ID: `FINDING-2026-02-16-006`
- Severity: `INFO` (map to task risk: LOW)
- Title: Core loop status: doc-upload (upload → persist → list → embed queue)

## Outcome (must be observable)
- A deterministic validation artifact exists (doc/script) that validates:
  1) Upload returns a usable `src_url` in the same runtime
  2) `/api/media/documents` lists the uploaded document
  3) `embedding_status` transitions to `ready` with `worker-document-embed` running

## Allowed Files (strict)
- `docs/**/*.md`
- `scripts/**/*.sh`
- `scripts/**/*.py`

## Dependencies / Prereqs (deterministic checks)
- `docker --version`
- `docker compose version`

## Command Checklist
1) Preflight:
- `git status --porcelain -uall`

2) Implement artifact using audit-suggested commands:
- Include:
  - `docker compose up -d db redis backend worker-document-embed`
  - `curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" -F "file=@test.txt" -F "project_id=1" -F "thread_id=1" http://localhost:8888/api/media/upload/document`
  - `curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" "http://localhost:8888/api/media/documents?limit=5"`
- Define expected response fields and explicit pass/fail criteria.
- Note prerequisite that `/media` URLs must be fetchable (blocked by/depends on Task 003 outcome).

3) Basic sanity check route exists:
- `curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" "http://localhost:8888/api/media/documents?limit=5" || true`

4) Scope check:
- `git status --porcelain -uall`

## Expected Outputs (success signals)
- The repo contains a deterministic doc/script for doc-upload validation.
- The artifact includes explicit prerequisites, headers, and expected JSON fields.
- `git status --porcelain -uall` shows modifications only within Allowed Files.

## Rollback / Cleanup Commands
- `git restore --source=HEAD --staged --worktree -- docs`
- `git restore --source=HEAD --staged --worktree -- scripts`
- `git clean -fd`


## Runner Receipt (Start)

- Campaign: CAMPAIGN_2026_02_16_COMPILED_AUDIT

- Task ID: 007

- Head before: 48f76d608b558d485345997629226127fa31eeac


## Completion Summary (Runner)

- Status: success

- Summary: **Task 007 Artifact**
- Documented the deterministic validation procedure in `docs/guardian/doc_upload_embedding_validation.md:1-87`, including prerequisite checks, the audit-specified docker/curl commands, the mandated `curl … || true` route sanity check, and an explicit pass/fail matrix covering upload, listing, embedding, and worker health.
- Added `scripts/validate_doc_upload_embedding.sh:1-199`, an executable validator that enforces a clean git tree, boots `db redis backend worker-document-embed`, issues the audited upload/list calls, asserts JSON fields (id/src_url/embedding_status/project_id), polls `/api/media/documents` until `embedding_status` becomes `ready`, and fails fast if the worker exits or returns `failed`.

Execution notes
- Ran the required `curl -sS … /api/media/documents?limit=5 || true`; it failed to connect because nothing is listening on `localhost:8888` yet, which is expected until the stack is running.
- Didn’t run the new validator (needs a live backend, GUARDIAN_API_KEY, and compose services); run `./scripts/validate_doc_upload_embedding.sh` once those are available to confirm the loop.

Next steps
1. Export `GUARDIAN_API_KEY`, start docker compose, and run the validator to capture a PASS log for the audit trail.
2. If `/media` URLs remain unreachable, note the block in the operator log per the doc and coordinate with Task 003 owners.

- Implementation commit hash: 910cb682009f3249051406c4741c39ad99a8d9ec

- Receipt update commit hash: 80115d93844754c1471ca637c77d6c22a2ae46ea

- Tests ran: (none)

<details>
<summary>Structured task_result.json</summary>

```json
{
  "status": "success",
  "summary": "**Task 007 Artifact**\n- Documented the deterministic validation procedure in `docs/guardian/doc_upload_embedding_validation.md:1-87`, including prerequisite checks, the audit-specified docker/curl commands, the mandated `curl \u2026 || true` route sanity check, and an explicit pass/fail matrix covering upload, listing, embedding, and worker health.\n- Added `scripts/validate_doc_upload_embedding.sh:1-199`, an executable validator that enforces a clean git tree, boots `db redis backend worker-document-embed`, issues the audited upload/list calls, asserts JSON fields (id/src_url/embedding_status/project_id), polls `/api/media/documents` until `embedding_status` becomes `ready`, and fails fast if the worker exits or returns `failed`.\n\nExecution notes\n- Ran the required `curl -sS \u2026 /api/media/documents?limit=5 || true`; it failed to connect because nothing is listening on `localhost:8888` yet, which is expected until the stack is running.\n- Didn\u2019t run the new validator (needs a live backend, GUARDIAN_API_KEY, and compose services); run `./scripts/validate_doc_upload_embedding.sh` once those are available to confirm the loop.\n\nNext steps\n1. Export `GUARDIAN_API_KEY`, start docker compose, and run the validator to capture a PASS log for the audit trail.\n2. If `/media` URLs remain unreachable, note the block in the operator log per the doc and coordinate with Task 003 owners.",
  "tests_ran": [],
  "commit_hash": "910cb682009f3249051406c4741c39ad99a8d9ec",
  "implementation_commit_hash": "910cb682009f3249051406c4741c39ad99a8d9ec",
  "receipt_update_commit_hash": "80115d93844754c1471ca637c77d6c22a2ae46ea",
  "notes": ""
}
```

</details>
