# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_MVP_CORE_LOOP_CLOSURE
- Task ID: 006
- Title: Fix document generation endpoint contract drift in tests
- Finding: FINDING-2026-02-10-010
- Risk: MED

## Allowed Files
- guardian/tests/test_document_gen_endpoint.py
- guardian/routes/documents.py

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. rg -n 'thread_id|/api/documents/generate' guardian/tests/test_document_gen_endpoint.py guardian/routes/documents.py
4. pytest guardian/tests/test_document_gen_endpoint.py -q
5. for f in $(git diff --name-only); do case $f in guardian/tests/test_document_gen_endpoint.py|guardian/routes/documents.py) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- Success test cases include required thread_id.
- Negative test explicitly asserts 400 when thread_id is missing.
- Endpoint contract tests pass.

## Rollback / Cleanup
- git restore --staged guardian/tests/test_document_gen_endpoint.py guardian/routes/documents.py || true
- git restore guardian/tests/test_document_gen_endpoint.py guardian/routes/documents.py || true

## Dependencies / Prereqs
- command -v git >/dev/null
- command -v rg >/dev/null
- command -v pytest >/dev/null


---

# Task 006 — Tooling/Docs: Deterministic RAG Loop Validation Artifact (FINDING-2026-02-16-003)

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
- ID: `FINDING-2026-02-16-003`
- Severity: `WARN` (map to task risk: LOW)
- Title: RAG loop uses async queue; needs deterministic validation path

## Outcome (must be observable)
- A deterministic validation artifact exists (docs and/or a small script) that validates:
  1) `docker compose` brings up `redis`, `backend`, and `worker-chat`
  2) `/chat/{thread_id}/complete` triggers an assistant message visible via messages endpoint
  3) RAG trace is retrievable via `/api/chat/debug/rag-trace/{thread_id}/latest` (or documented equivalent)

## Allowed Files (strict)
- `docs/**/*.md`
- `scripts/**/*.sh`
- `scripts/**/*.py`
- `frontend/src/tests/playwright/**/*.ts`
- `frontend/src/tests/playwright/**/*.tsx`

## Dependencies / Prereqs (deterministic checks)
- `docker --version`
- `docker compose version`

## Command Checklist
1) Preflight:
- `git status --porcelain -uall`

2) Implement artifact:
- Add a short doc page and/or script that runs the audit-suggested commands, including:
  - `docker compose up -d db redis backend worker-chat`
  - OpenAPI grep for `threads`, `complete`, `rag-trace`
  - Example `curl` calls showing required headers (e.g., `X-API-Key: $GUARDIAN_API_KEY`)
- Ensure the artifact is deterministic: clear prerequisites, explicit endpoints, expected responses.

3) Verify commands are present and runnable:
- `docker compose up -d db redis backend worker-chat`
- `curl -sS http://localhost:8888/openapi.json | rg -n "\/api\/chat\/threads|\/chat\/\{thread_id\}\/complete|\/api\/chat\/debug\/rag-trace"`

4) Scope check:
- `git status --porcelain -uall`

## Expected Outputs (success signals)
- The repo contains a single clear validation recipe (doc/script) for the RAG loop.
- The artifact explicitly states what constitutes “pass” (assistant message appears; trace endpoint returns a record).
- `git status --porcelain -uall` shows modifications only within Allowed Files.

## Rollback / Cleanup Commands
- `git restore --source=HEAD --staged --worktree -- docs`
- `git restore --source=HEAD --staged --worktree -- scripts`
- `git restore --source=HEAD --staged --worktree -- frontend/src/tests/playwright`
- `git clean -fd`


## Runner Receipt (Start)

- Campaign: CAMPAIGN_2026_02_16_COMPILED_AUDIT

- Task ID: 006

- Head before: 58a7f6e9d18622c53ab1724ce3388141cb83c9ce
