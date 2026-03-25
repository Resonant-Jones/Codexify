# Supported Path Proof Refresh - 2026-03-25

## Goal
Refresh the live supported-path proof on `main` for the beta-critical text loop after the prompt assembly, retrieval injection, document linkage, and worker compatibility repairs.

## Environment
- Date: 2026-03-25
- Branch tested: `main`
- Runtime commit under test: `43ab90f016dd8d09c85902e0d1ad50b02fc5dd6e`
- Runtime services used: `backend`, `worker-chat`, `worker-document-embed`, `db`, `redis`, `neo4j`
- Frontend service was running, but browser UI validation was not available in this environment because Playwright Chrome was missing.
- Completion path used the live backend/worker stack and resolved through Groq-backed model selection in the backend provider catalog.

## Exact Commands Run
- `docker compose up -d --force-recreate backend worker-chat worker-document-embed`
- `docker compose ps backend worker-chat worker-document-embed db redis neo4j frontend`
- `docker compose exec -T backend python - <<'PY' ...` for:
  - a clean thread creation and completion probe
  - persona save/status checks and an explicit `system_override` completion probe
  - document upload, embedding readiness, thread linkage, and retrieval probe
  - direct reads from the task event stream for payload summaries
- `pytest -v`
- `pnpm test`

## Validation Results

### 1. Thread Creation + Completion
- PASS.
- Fresh thread: `4`
- Task id: `15c4192f-6436-4215-a6e9-a7380a27f7d5`
- Assistant reply persisted: `Hello! How can I help you today?`
- Task-event payload summary:
  - `has_system_prompt: true`
  - `message_count: 2`
  - `persona_or_imprint_present: false`
  - `retrieval_injected: false`
- Regression note:
  - I did not observe duplicate context injection in the diagnostics for this run.

### 2. Persona Continuity
- PARTIAL.
- A persona/system prompt was saved for a fresh project and is visible in `GET /api/imprint/status?project_id=2`:
  - `persona.id: 4`
  - `system_prompt_meta.segments_present.persona: true`
- Fresh thread used for the explicit override probe: `11`
- Task id: `5ebad457-7290-4837-b579-013cc4ecdf9c`
- When the persona text was injected explicitly as `system_override`, the runtime honored it:
  - assistant reply: `PERSONA-ORCHID Hello! How can I assist you today?`
  - task-event payload summary showed `has_user_system_override: true`
- However, the stored persona path itself still did not surface `persona_or_imprint_present: true` in the completion payload summary.
- Conclusion:
  - The runtime can consume the persona text when it is explicitly injected.
  - Automatic Settings-to-completion persona binding is not yet proven end to end.

### 3. Document Upload + Retrieval
- PASS.
- Thread: `9`
- Uploaded document: `audit-proof.txt`
- Uploaded content included:
  - `Project codename: DOC-EMBER-718.`
  - `The answer to the retrieval question is DOC-EMBER-718.`
- Upload response started with `embedding_status: pending`.
- `GET /api/media/documents?thread_id=9` eventually reached `embedding_status: ready`.
- Thread/project linkage was explicit:
  - `GET /api/threads/9/documents` returned the document with relation `attached`
  - `GET /api/media/documents?thread_id=9` showed `project_id: 1` and `thread_id: 9`
- Retrieval answer reflected the uploaded content:
  - assistant reply: `The project codename mentioned in the uploaded document is DOC-EMBER-718.`
- Task id: `994aa9a0-94a9-4630-9d85-c4ef505f97f8`
- Task-event payload summary:
  - `linked_document_count: 2`
  - `linked_document_injected: true`
  - `retrieval_injected: true`
  - `message_count: 2`

### 4. Thread/Project Linked Document Scope
- PASS.
- The uploaded document was linked into the correct thread/project scope, not merely stored:
  - project-scoped media listing showed the expected `project_id`
  - thread-scoped document listing returned `attached`
  - retrieval diagnostics reported linked-document injection

### 5. Regression Guard
- PASS, with inference.
- The payload summaries remained consistent with a single system prompt slot and no obvious duplicate context injection.
- Inference: the runtime still behaves like a single-system-message assembler, but the raw assembled prompt is not directly emitted in the diagnostics, so this is based on the event summaries.

### 6. Known Exclusions
- Out of scope for this proof:
  - image/multimodal proof
  - unrelated Obsidian failures
- If those remain failing, they should stay separated from the supported text-path proof.

## Test Results

### `pytest -v`
- Result: FAILED
- Summary: `952 passed, 15 skipped, 33 xfailed, 11 xpassed, 2 failed`
- The two failures are unrelated Obsidian tests:
  - `tests/obsidian/test_file_lifecycle.py::test_obsidian_file_lifecycle_prune`
  - `tests/obsidian/test_ingest_idempotency.py::test_obsidian_ingest_idempotency`
- These were excluded from the supported-path proof result.

### `pnpm test`
- Result: FAILED
- Frontend Vitest stopped on a JSX parse error in `frontend/src/features/chat/GuardianChat.tsx`:
  - `The character ">" is not valid inside a JSX element`
  - `Expected "}" but found ";"` near lines `2591-2594`
- This is a separate frontend regression and not part of the supported-path proof path.

## Result Matrix
| Segment | Result | Notes |
| --- | --- | --- |
| Thread creation + completion | PASS | Clean completion returned and persisted |
| Persona continuity | PARTIAL | Saved persona visible in status, but automatic propagation is not yet proven |
| Document upload + retrieval | PASS | Embedding reached ready and retrieval returned the expected grounded answer |
| Linked document scope | PASS | Thread/project linkage was explicit and diagnostics reported injection truthfully |
| Regression guard | PASS | No obvious duplicate context injection in diagnostics |
| `pytest -v` | FAILED | Unrelated Obsidian failures |
| `pnpm test` | FAILED | Existing JSX parse error in `GuardianChat.tsx` |

## Conclusion
- Core beta-critical text-loop behavior is proven on `main` for clean completion and document-grounded retrieval.
- The beta-critical text path is **not fully proven** on `main` because automatic saved-persona propagation from Settings is still unproven.
- The runtime can honor the persona text when injected explicitly as `system_override`, but the saved-persona binding path still needs repair.

## Remaining Blockers
- Beta-blocking
  - Automatic Settings persona propagation into the chat completion payload and assistant behavior is not yet proven.
- Non-blocking follow-up
  - `pnpm test` fails on the JSX parse error in `frontend/src/features/chat/GuardianChat.tsx`.
- Unrelated pre-existing failures
  - The two Obsidian tests listed above fail independently of this proof.
