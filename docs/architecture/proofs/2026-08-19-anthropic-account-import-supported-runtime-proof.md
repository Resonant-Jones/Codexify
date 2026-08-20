# Anthropic Account Import — Supported Runtime Proof (2026-08-19)

## Status

**BLOCKED**

A real Anthropic account export completed the supported Web → job → Redis queue →
worker → PostgreSQL persistence chain, but the durable account-import job reached
terminal `failed` (not `completed`). The first blocking boundary is a worker
bookkeeping defect in the Anthropic dispatch branch (see "First Blocking
Boundary" below). Per task invariants, the defect is recorded, not repaired.

## Orientation (workspace identity)

- Worktree: `/Volumes/Dev_SSD/Codexify-main` (canonical Tester root, bind-mounted by Compose)
- Branch: `codex/wire-anthropic-import-adapter`
- Pre-proof HEAD: `140b9766c2681320f0f7962924c7773edc978926` (the rendered-UI proof commit)
- Dirty state: clean before and after the proof (`git status --short` empty; only the receipt commit follows)
- Live probes: backend `GET /health` 200 (`release_hold=true`, `supported_profile.v1-local-core-web-mcp` valid, `selected_provider=local`); all account-import routes registered in OpenAPI (`/api/imports/openai-account`, `/files`, `/commit`, `/{job_id}`, `/retry`, `/account/metadata`); frontend HTTP 200 on the proof origin.

## Source identity

- Branch: `codex/wire-anthropic-import-adapter`
- HEAD: `140b9766c2681320f0f7962924c7773edc978926`
- Ancestry: `140b9766c` is HEAD itself; `c3cc44ecbb7800e7216cd2f76bed9a39f0b2712b` is an ancestor (both `git merge-base --is-ancestor` checks returned success).
- Worktree cleanliness: clean pre-proof and post-proof (only the receipt commit adds content).
- Compose source correspondence: containers bind-mount the Tester root at HEAD `140b9766c`; the backend/migrator image `codexify-backend-runtime:latest` (built 2026-08-19T16:55Z) carries a migration tree byte-identical to the host tree (diff = `__pycache__` only), including `1c0a2b3c4d5e_add_chat_threads_origin_system.py`.

## Runtime identity

- Compose project: `codexify_anthropic_import_proof_20260819` (disposable; fresh volumes; distinct from `codexify`, `codexify_tester`, `codexify-audit`)
- Compose files:
  - `docker-compose.yml` (canonical base, unmodified, at HEAD)
  - `/private/tmp/codexify-anthropic-proof.override.yml` — ephemeral EXTERNAL override, never committed, no repo file modified. Contents: port remaps (`!override`) and supported-posture pins (see below).
  - `--env-file .env.tester` (operator-owned, unmodified)
- Tester-overlay fallback rationale: the mandated topology resolution with `docker-compose.tester.yml` succeeds (`config --services` lists all required services), but the overlay is not usable as a second isolated Web runtime on this host: the frontend runs only inside the `tailscale-codexify-test` sidecar network namespace, and that sidecar publishes `127.0.0.1:5174`, which is already bound by the live `codexify_tester` project; a second sidecar would collide on port and tailnet identity (`TAILSCALE_TEST_HOSTNAME`/auth key are single-instance). The task forbids mutating another running Compose project. Fallback per spec: the repository's documented supported local Compose configuration (`docker-compose.yml`) under the unique proof project name.
- Override pins (documented supported local Beta posture, matching the running audit backend's known-good boot combination): backend `CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp`, `GUARDIAN_AUTH_MODE=local`, `GUARDIAN_EXPOSURE_MODE=local_safe`, `LLM_PROVIDER=local`, `ALLOW_CLOUD_PROVIDERS=false`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `CODEXIFY_EGRESS_ALLOWLIST=""`, blessed local gateway contract (`LOCAL_RUNTIME_PRESET=whooshd-mlx`, `LOCAL_COMPAT_FIRST=true`, `LOCAL_PROVIDER_DISPLAY_NAME="Whoosh'd"`, `LOCAL_PROVIDER_VENDOR=whooshd`); frontend `VITE_GUARDIAN_API_BASE=""` (same-origin Vite proxy) + `VITE_GUARDIAN_AUTH_MODE=local`.
- Services started: `db redis neo4j graph-init migrator model-prep backend frontend worker-account-import`
- Final service states before teardown: `db` healthy, `redis` healthy, `neo4j` healthy, `graph-init` exited 0, `migrator` exited 0, `model-prep` exited 0, `backend` healthy (restarted once after env pin, healthy on pristine source), `frontend` up (Vite dev on 5173 in-container), `worker-account-import` up, `RestartCount=0`.
- Migration head (isolated DB): `1c0a2b3c4d5e`; `chat_threads.origin_system` column present (CHECK-constrained per `guardian/conversation_origin.py`).
- Endpoints: backend `http://127.0.0.1:8890`; frontend `http://127.0.0.1:5180`.
- Worker identity: container `codexify_anthropic_import_proof_20260819-worker-account-import-1`, entrypoint `python -m guardian.workers.account_import_worker`, boot log `[account-import] worker started queue=codexify:queue:account-import recovered=0` at 22:10:36Z.
- Startup diagnosis note: the first backend boot exited (3) with redacted logs; the documented log-safety bypass (`install_safe_logging` no-op) was applied temporarily to surface `LLMConfigError` (missing blessed local-gateway contract), the override was corrected, and the bypass was reverted byte-identically (blob SHA-256 `1cc41f21ea583ca3cf7866db45f7f15c312c0ffe667c7b74020886c0c81ba89f` == HEAD blob) before the final backend restart. The final runtime ran on pristine HEAD source.

## Export identity (safe structural metadata only)

- Operator-selected source: directory at `/Volumes/Dev_SSD/anthropic-export` (mode `drwx------`)
- Form: directory (6 files, 7,180,973 bytes)
- Filenames (structure identification only): `conversations.json` (6,566,116 B), `memories.json` (23,343 B), `users.json` (170 B), `projects/019a1d7f-aa06-73c4-b0db-6bbd4f9103af.json` (19,419 B), `projects/019a5c57-4700-7406-b9bb-2b9720926b65.json` (571,556 B), `projects/019b33d4-a874-75ca-a19f-c4d32fe2d2e0.json` (369 B)
- Structural classification: `conversations.json` = top-level list of 65 records, each with keys `(account, chat_messages, created_at, name, summary, updated_at, uuid)`, 65/65 carry `chat_messages` lists (length 0–146); `projects/*.json` = single dicts (project metadata, no `chat_messages`); `memories.json`/`users.json` = single-record lists (no `chat_messages`). No message content read or recorded.
- SHA-256 per file (recorded at intake and re-verified after the run — identical, source untouched):
  - `conversations.json` `e47d81c1b0eea38b78d36b6e38a8ff6bc21b9c4c70f211c5128033f39811ed98`
  - `memories.json` `82688c2c5c613af35494cf17ec8eb50c1cee82c6b380a5251a3f2728235d1e6c`
  - `users.json` `a86aa4608a1d9a01fd0643d02471e4347da15dacd8d2ccd72dc4d093179eaae8`
  - `projects/019a1d7f-…` `5372030d65ff79f1f78561f95b7b1bc93791b865193d0477cf0fa0fd196f3dee`
  - `projects/019a5c57-…` `b33bbc3f615638be31c364fdf05dc171189ee3a379d5cc29638f99ca920c31bf`
  - `projects/019b33d4-…` `3826010ba920ed8ee643d9e7da705e102e05b8e9c5f880b38a409d0fd8326318`
- Intake gate: PASS — the export is structurally compatible with the adapter's `anthropic_legacy` detection (chat_messages-bearing records) and with the modal's folder interaction. No converter built.

## UI evidence (rendered Web)

- Origin: rendered frontend at `http://127.0.0.1:5180`, Settings → Data → "Import ChatGPT history" → modal "Import account data".
- Both source options observed in the rendered modal: `OpenAI (ChatGPT)` and `Anthropic (Claude)` (radio inputs with `data-testid=account-import-source-openai|anthropic`).
- Anthropic selected: radio `anthropic` checked (verified in DOM before submission); browser sent `source_system: "anthropic"` only.
- Normal Web upload path: folder interaction via the rendered "Choose Folder" control and the OS folder chooser (operated manually per spec — browser automation cannot populate `webkitdirectory` inputs; explicitly permitted, does not invalidate the proof). The folder `/Volumes/Dev_SSD/anthropic-export` was selected; 6 files enumerated client-side with relative paths.
- Job ID created: `2cc3cf45-917b-43c9-97f9-0028c4aba1be` (captured from the browser network response for `POST /api/imports/openai-account` and confirmed from the durable DB row).

## Durable job evidence

- job_id: `2cc3cf45-917b-43c9-97f9-0028c4aba1be`
- user_id: `local` (single-user identity carried by the Web `X-User-Id` header)
- `source_system`: exactly `anthropic`
- Lifecycle states observed (browser poll + DB): `receiving` (create) → `receiving` (6/6 files staged, 7,180,973 bytes) → `queued` (commit; `source_export_fingerprint=09ceb8d7772f574f6c0c20d4be9892cfb19e6bc556c02e86077de1a646347513`) → `running` (started 22:58:15.503Z) → **`failed`** (completed_at 22:58:32.796Z)
- Final error: `code=account_import_no_committed_entities`, message "The export finished processing, but no canonical entities were committed."
- Durable `source_summary`: `conversations_discovered=65`, `conversations_accepted=65`, `conversations_skipped=0`, `conversations_failed=0`, `conversation_transactions_committed=true`
- Job counters at terminal: `imported_thread_count=0`, `imported_message_count=0`, `imported_media_count=0` — see First Blocking Boundary.

## Worker evidence

- Running before the job: booted 22:10:34Z, `[account-import] worker started queue=codexify:queue:account-import recovered=0` (no unrelated queued work).
- Job consumed: `running` state set at 22:58:15.503Z by the worker's `mark_running`; Redis queue `codexify:queue:account-import` (project-scoped Redis).
- Anthropic dispatch observed: worker logs show the canonical Claude writer's embedding handoff for the job (49 batches × 16 items = 784 messages, `queued_count=16 failed_count=0 failure_class=none` per batch), then `[account-import] worker failed job_id=<redacted> exception_type=AccountImportError failure_class=runtime` (the `complete_job` failure; no conversation content in logs).
- No crash/restart: `RestartCount=0`, container remained `running` through and after the job.

## PostgreSQL evidence (isolated proof DB, user scope `local`)

Baseline (before submission):

| surface | count |
|---|---|
| alembic head | `1c0a2b3c4d5e` |
| `chat_threads.origin_system` column | present (1) |
| `chat_threads` total | 0 |
| `chat_messages` total | 0 |
| anthropic-origin threads | 0 |
| account-import jobs | 0 |

After terminal `failed` (readback 1, direct read-only psql):

| surface | count |
|---|---|
| anthropic-origin threads | **63** |
| origin distribution | `anthropic=63`, `codexify=0`, `openai=0`, `NULL=0` |
| messages on anthropic threads | **784** |
| distinct importing users | 1 (`local`) |
| imported thread provenance metadata | `metadata->>'import_source'='claude'` on 63/63 |

Second independent readback (separate psql invocation after terminal completion): identical — 63 threads, 784 messages, distribution `anthropic=63`, 1 distinct user. Postgres is the authority; no in-process or API-payload dependence.

## Negative persistence checks (post-import counts, isolated DB)

| surface | count | verdict |
|---|---|---|
| `projects` | 2 — `General` (backend default) + `Imports` (canonical writer's import container) | PASS: no `projects/*.json` record became a Project entity (3 project files → 0 project rows) |
| `memory_entries` | 0 | PASS: `memories.json` created no memory state |
| `personal_facts` / `personal_fact_evidence` | 3 / 74 | OBSERVED: all 74 evidence rows link via `source_message_id` to messages in anthropic-origin threads — conversation-derived fact-candidate extraction by the pre-existing canonical Claude writer (same behavior as ChatGPT imports), NOT `memories.json` ingestion |
| `user_profiles` | 0 | PASS: `users.json` created no persona/account identity state |
| `media_assets`, `uploaded_images`, `generated_images`, `uploaded_documents`, `generated_documents`, `thread_documents`, `project_document_links` | 0 each | PASS: no fabricated media/document assets |

Limitation stated: pre-import baseline counts for non-thread tables were not captured (only threads/messages/jobs); attribution above is by row identity/lineage (canonical container project, evidence→imported-message links), which the schema supports. Nothing beyond that is claimed.

## UI completion (terminal state)

The rendered modal reached a terminal state and remained functional: it rendered "Account import failed — The export finished processing, but no canonical entities were committed." with a "Review failure details" disclosure, and the coordinator persisted `{jobId: 2cc3cf45-…, status: "failed", sourceSystem: "anthropic"}`. No screenshot committed.

## Invariants

1. One importer — PASS: no new route/queue/worker/job table/writer; single queue `codexify:queue:account-import`, single `openai_account_import_jobs` table.
2. Explicit source authority — PASS: job created with exactly `source_system="anthropic"`.
3. Backend provenance authority — PASS: browser never sends `origin_system` (api.ts rejects any response carrying it); persisted origin produced by backend canonicalization (`import_source="claude"` → `origin_system="anthropic"`).
4. Canonical durable lineage — PASS: 63/63 imported threads read back `origin_system="anthropic"`.
5. Isolated proof runtime — PASS: unique disposable Compose project, fresh volumes, `recovered=0`, zero jobs/threads at baseline; no unrelated queued work consumed.
6. Source immutability — PASS: per-file SHA-256 identical before/after; source directory untouched; staged copy removed at teardown.
7. Private-data minimization — PASS: no conversation text captured; receipt carries counts/IDs/hashes/statuses only.
8. No false capability expansion — PASS: no Projects/memories/users/media claims; boundaries recorded as observed (see Negative checks).
9. No repair smuggling — PASS: the proven defect is recorded as the blocking boundary and NOT fixed in this task.
10. No release widening — PASS: no current-state/release change.

## Acceptance criteria

1. Ancestry of both Web proof commits in HEAD — PASS
2. Focused regressions — PASS (50 passed, 1 skipped: `test_chat_thread_origin_system_migration` skips without a live admin DB; environmental)
3. Unique disposable Compose runtime — PASS
4. Real Postgres and Redis — PASS
5. `worker-account-import` actually running — PASS
6. Export initiated through rendered Web UI — PASS (folder interaction, manual OS chooser step)
7. UI selection Anthropic — PASS
8. Persisted job `source_system="anthropic"` — PASS
9. Redis-backed worker execution consumes the job — PASS
10. Job reaches durable terminal `completed` — **FAIL (terminal `failed`)**
11. ≥1 imported anthropic-origin thread — PASS (63)
12. ≥1 persisted message on those threads — PASS (784)
13. Every proof-scoped imported thread `origin_system="anthropic"` — PASS (63/63)
14. Imported rows belong to the importing user — PASS (1 user, `local`)
15. Second independent Postgres readback reproduces counts — PASS
16. No second importer/queue/worker/route/persistence path introduced — PASS
17. Export not modified or committed — PASS
18. No private content in the receipt — PASS
19. Unsupported Projects/memory/profile/media semantics not claimed — PASS
20. No release/current-state claim widened — PASS

## First blocking boundary (required — status BLOCKED)

`guardian/workers/account_import_worker.py` (Anthropic branch, lines ~198–228) invokes the canonical writer (`import_anthropic_export_path` → `ingest_claude_export`, which durably commits threads/messages and returns `threads_imported=63`) and calls `service.record_source_summary(...)` + `service.complete_job(...)` **without first recording the committed thread/message counts onto the durable job** (the OpenAI branch does this via `record_conversation_batch`; the Anthropic branch has no equivalent). `complete_job` (`guardian/services/openai_account_import.py:1210–1223`) derives `committed_entity_count` exclusively from `job.imported_thread_count + imported_message_count + imported_media_count` (plus `checkpoint.canonical_duplicate_count`); with all counters 0 it raises `account_import_no_committed_entities`, which the worker's catch-all persists as terminal `failed`.

Observed consequence on the real export: 63 anthropic-origin threads and 784 messages committed to Postgres (`origin_system="anthropic"`, user `local`), while the durable job reports `failed` with zero tracked entities — a false-negative terminal verdict that violates the account-export-restore-contract's intent (a `completed` result must follow committed canonical writes whose bounded counts are known; here they were known to the adapter result and not propagated).

Not repaired in this task (invariant 9).

## ADR impact

- Governing ADRs: **ADR-001** (Queue-Based Completion Acceptance Model), **ADR-005** (Runtime Mode and Account Boundary Invariants), **ADR-069** (Codexify Beta Runtime Support Boundary); normative contract `account-export-restore-contract.md` (canonical conversation origin + background account-import completion semantics).
- Verdict: **Aligned with existing ADR(s); no architecture change.** The runtime exercised only already-accepted implementation; the blocker is a worker bookkeeping defect within the accepted seam, not an accepted-invariant conflict.

## Documentation follow-through

- Proof artifact created: this file (the only tracked change).
- `00-current-state.md`: unchanged.
- No release promotion made; no release/current-state claim widened.
- Deferred next slice (BLOCKED variant, exactly one): **Repair the first proven runtime blocker in a separate atomic task before repeating the Anthropic runtime proof.**

## Teardown

- Project verified (`codexify_anthropic_import_proof_20260819`) and torn down with the exact same files: `docker compose --env-file .env.tester -p codexify_anthropic_import_proof_20260819 -f docker-compose.yml -f /private/tmp/codexify-anthropic-proof.override.yml down -v`. Only proof-project volumes/network removed; `codexify`, `codexify_tester`, `codexify-audit`, `codexify_private_preview` untouched.
- Proof job's staged private bytes removed from the shared staging root (only the job-scoped directory); other projects' staging directories untouched.
- Source export untouched.
