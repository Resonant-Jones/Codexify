# Daily Audit — 2026-03-25

## Live Proof Refresh
- Date: 2026-03-25
- Branch tested: `main`
- Runtime refreshed with: `docker compose up -d --force-recreate backend worker-chat worker-document-embed`
- Services used: `backend`, `worker-chat`, `worker-document-embed`, `db`, `redis`, `neo4j`
- Frontend service was up, but browser UI proof was not available in this environment because Playwright Chrome was missing; validation used the live backend/worker API path directly.
- Runtime commit under test: `43ab90f016dd8d09c85902e0d1ad50b02fc5dd6e`

## Commands Run
- `docker compose up -d --force-recreate backend worker-chat worker-document-embed`
- `docker compose ps backend worker-chat worker-document-embed`
- `docker compose exec -T backend python - <<'PY' ...` to validate a clean chat completion on Groq-backed `moonshotai/kimi-k2-instruct-0905`
- `docker compose exec -T backend python - <<'PY' ...` to validate persona save + status + explicit `system_override` behavior on a fresh project
- `docker compose exec -T backend python - <<'PY' ...` to validate document upload, embedding readiness, thread linkage, and retrieval
- `docker compose exec -T backend python - <<'PY' ...` to read `task.completed` events directly from the task-event stream
- `pytest -v`
- `pnpm test`

## Proof Results

### 1. Clean thread creation + completion
- PASS.
- Thread `4` created cleanly and completed on Groq (`task_id=15c4192f-6436-4215-a6e9-a7380a27f7d5`).
- Assistant reply persisted: `Hello! How can I help you today?`
- Task-event payload summary:
  - `has_system_prompt: true`
  - `message_count: 2`
  - `persona_or_imprint_present: false`
  - `retrieval_injected: false`

### 2. Persona continuity
- PARTIAL.
- A persona/system prompt was saved and is visible in `GET /api/imprint/status` for a fresh project:
  - `persona.id: 4`
  - `system_prompt_meta.segments_present.persona: true`
- The direct completion path did not automatically report persona presence in `payload_summary`:
  - `persona_or_imprint_present: false`
  - the plain greeting path stayed generic
- When the same persona text was supplied explicitly as `system_override`, the runtime honored it:
  - thread `11`
  - assistant reply: `PERSONA-ORCHID Hello! How can I assist you today?`
  - task-event payload summary showed `has_user_system_override: true`
- Conclusion: the model can honor the saved text, but automatic Settings-to-completion persona propagation is still not proven end-to-end.

### 3. Document upload + retrieval
- PASS.
- Uploaded `audit-proof.txt` into thread `9`.
- Upload response initially showed `embedding_status: pending`, then thread-scoped listing reached `embedding_status: ready`.
- Thread/project linkage was explicit:
  - `GET /api/threads/9/documents` returned the document with relation `attached`
  - `GET /api/media/documents?thread_id=9` showed the same doc with `project_id: 1` and `thread_id: 9`
- Retrieval answer reflected the document content:
  - assistant reply: `The project codename mentioned in the uploaded document is DOC-EMBER-718.`
- Task-event payload summary:
  - `linked_document_count: 2`
  - `linked_document_injected: true`
  - `retrieval_injected: true`

## Test Results

### `pytest -v`
- Result: FAILED
- Summary: `952 passed, 15 skipped, 33 xfailed, 11 xpassed, 2 failed`
- The two failures are in Obsidian ingestion tests:
  - `tests/obsidian/test_file_lifecycle.py::test_obsidian_file_lifecycle_prune`
  - `tests/obsidian/test_ingest_idempotency.py::test_obsidian_ingest_idempotency`
- These are unrelated to the supported text-loop proof and were excluded from the proof pass/fail.

### `pnpm test`
- Result: FAILED
- Frontend Vitest stopped on a syntax parse error in `frontend/src/features/chat/GuardianChat.tsx`:
  - `The character ">" is not valid inside a JSX element`
  - `Expected "}" but found ";"` near lines `2591-2594`
- This is a separate frontend regression and not part of the proof path, but it blocks a clean frontend test run.

## Conclusion
- Core text-loop runtime is proven for clean thread completion and document-grounded retrieval on `main`.
- Automatic saved-persona propagation is **not fully proven** on `main` because the completion payload summary still reports `persona_or_imprint_present: false` for the stored persona path.
- The same persona text is honored when passed explicitly as `system_override`, so the runtime can consume the prompt content, but the Settings binding remains the blocker.

## Remaining Blockers
- **Beta-blocking**
  - Automatic Settings persona propagation into the chat completion payload/assistant behavior is not yet proven.
- **Non-blocking follow-up**
  - `pnpm test` fails on a JSX parse error in `frontend/src/features/chat/GuardianChat.tsx`.
- **Unrelated pre-existing failures**
  - `pytest -v` fails only on the two Obsidian tests listed above.
