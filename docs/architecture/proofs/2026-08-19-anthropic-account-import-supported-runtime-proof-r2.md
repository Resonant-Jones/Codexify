# Anthropic Account Import — Supported Runtime Proof R2 (2026-08-19)

## Result

**PASS**

The real Anthropic account export completed the full supported runtime chain —
rendered Web UI → `source_system="anthropic"` → durable account-import job →
Redis → `worker-account-import` → Anthropic adapter → canonical Claude writer →
durable committed-count accounting → terminal `completed` → PostgreSQL — and the
durable job counters now agree exactly with the persisted canonical truth.

## Lineage

- Branch: `codex/wire-anthropic-import-adapter`
- Pre-proof HEAD: `ec2814539b25bed2ff27b7436916e5aa2abbc759` (the accounting repair commit; HEAD itself)
- Accounting repair ancestry: `git merge-base --is-ancestor ec2814539… HEAD` → success
- First proof ancestry: `git merge-base --is-ancestor 608f483bf… HEAD` → success
- Worktree cleanliness: clean before and after the proof; only this receipt was added.
- Repair diff confirmed present in lineage: adapter `messages_imported` preservation, provider-neutral `record_committed_conversation_totals` seam, worker crediting before `complete_job`, and the 82-test regression additions (verified via `git show --stat ec2814539`).

## Runtime identity

- Compose project: `codexify_anthropic_import_proof_r2_20260819` (fresh disposable project; fresh volumes; distinct from `codexify`, `codexify_tester`, `codexify-audit`)
- Compose files:
  - `docker-compose.yml` (canonical base, unmodified)
  - `/private/tmp/codexify-anthropic-proof-r2.override.yml` (ephemeral external override, never committed; `!override` port remaps to 127.0.0.1:5544/7476/7689/8890/5180 and the documented supported local Beta posture pins: `v1-local-core-web-mcp`, `GUARDIAN_AUTH_MODE=local`, `GUARDIAN_EXPOSURE_MODE=local_safe`, `LLM_PROVIDER=local`, local-only flags, blessed `whooshd-mlx` gateway contract; frontend `VITE_GUARDIAN_API_BASE=""` same-origin proxy + `VITE_GUARDIAN_AUTH_MODE=local`)
  - `--env-file .env.tester` (operator-owned, unmodified)
- Tester-overlay re-check: the `config --services` resolution with `docker-compose.tester.yml` succeeds, but the overlay remains non-instantiable in isolation — the `tailscale-codexify-test` sidecar's `127.0.0.1:5174` binding is still held by the live `codexify_tester` project (verified with `lsof` before startup), and the sidecar is a single-instance tailnet identity. Same documented fallback as the first proof: base compose + unique project + ephemeral external override. No live project mutated.
- Services started: `db redis neo4j graph-init migrator model-prep backend frontend worker-account-import`
- Final states: db/redis/neo4j healthy; graph-init/migrator/model-prep exited 0; backend healthy; frontend serving; `worker-account-import` running with `RestartCount=0` before, during, and after the job.
- Migration head (isolated DB): `1c0a2b3c4d5e`; `chat_threads.origin_system` column present.
- Endpoints: backend `http://127.0.0.1:8890`, frontend `http://127.0.0.1:5180`.
- Worker boot evidence: `[account-import] worker started queue=codexify:queue:account-import recovered=0` at 23:39:33Z (before submission).

## Export identity (safe structural metadata only)

- Operator-selected source: directory `/Volumes/Dev_SSD/anthropic-export` (generic path reference in this receipt)
- Form: directory; 6 files; 7,180,973 bytes
- Structural filenames: `conversations.json`, `memories.json`, `users.json`, `projects/019a1d7f-…json`, `projects/019a5c57-…json`, `projects/019b33d4-…json`
- Structure class (no content read): `conversations.json` = list of 65 records carrying `chat_messages`; `projects/*.json` = project-metadata dicts; `memories.json`/`users.json` = single-record lists
- Intake SHA-256 (identical to the first proof's recorded baseline):
  - `conversations.json` `e47d81c1b0eea38b78d36b6e38a8ff6bc21b9c4c70f211c5128033f39811ed98`
  - `memories.json` `82688c2c5c613af35494cf17ec8eb50c1cee82c6b380a5251a3f2728235d1e6c`
  - `users.json` `a86aa4608a1d9a01fd0643d02471e4347da15dacd8d2ccd72dc4d093179eaae8`
  - `projects/019a1d7f-…` `5372030d65ff79f1f78561f95b7b1bc93791b865193d0477cf0fa0fd196f3dee`
  - `projects/019a5c57-…` `b33bbc3f615638be31c364fdf05dc171189ee3a379d5cc29638f99ca920c31bf`
  - `projects/019b33d4-…` `3826010ba920ed8ee643d9e7da705e102e05b8e9c5f880b38a409d0fd8326318`

## Web evidence

- Rendered UI at `http://127.0.0.1:5180`, Settings → Data → "Import ChatGPT history" → "Import account data" modal.
- Rendered choices observed: `OpenAI (ChatGPT)` and `Anthropic (Claude)`.
- `Anthropic (Claude)` selected (radio `anthropic` checked, verified in DOM before submission).
- Source submitted through the normal rendered folder interaction ("Choose Folder" + OS file chooser; manual OS-picker operation permitted by the spec and required by the browser automation limitation).
- Created job ID: `c94e8387-839f-46a0-9083-aaba1ca8d18e` (captured from the browser network response for `POST /api/imports/openai-account` and confirmed from the durable DB row — not inferred from UI selection).

## Job lifecycle

- job_id: `c94e8387-839f-46a0-9083-aaba1ca8d18e`
- user_id: `local`
- `source_system`: exactly `anthropic` (durable row)
- Observed transitions (browser capture + durable row): `receiving` (create) → `receiving` (6/6 files staged, 7,180,973 bytes) → `queued` (commit) → `running` (worker pickup) → **`completed`** (terminal, 23:42:44Z)
- Terminal counters: `imported_thread_count=63`, `imported_message_count=784`, `imported_media_count=0`, `duplicate_count=0`, `skipped_count=0`, `warning_count=0`, `failure_count=0`
- `account_import_no_committed_entities`: **did not recur.**

## Accounting evidence

- Durable checkpoint (`openai_account_import_jobs.checkpoint`):
  - `source_summary`: `{conversations_discovered: 65, conversations_accepted: 65, conversations_skipped: 0, conversations_failed: 0, conversation_transactions_committed: true}`
  - `committed_conversation_totals`: `[{"key": "anthropic_conversations", "threads_imported": 63, "messages_imported": 784}]`
- The zero-counter defect is absent: `imported_thread_count=63`, `imported_message_count=784` at terminal (first proof: both 0).
- Consistency with PostgreSQL: `Jt = 63 = Pt`, `Jm = 784 = Pm` — exact equality, as required for this fresh isolated import.

## Worker evidence

- Worker was running before the job (booted 23:39:33Z, `recovered=0`).
- Job consumed: durable status moved to `running`; worker logs show the canonical Claude writer executing for the job at 23:42:44Z (embedding handoff, 49 batches × 16 items = 784 messages, `failed_count=0 failure_class=none` per batch).
- Durable accounting executed (checkpoint entry above); terminal classification followed (job `completed`).
- No `[account-import] worker failed …` line; no crash; `RestartCount=0`, container `running` throughout.

## Persistence evidence

Baseline (before submission): anthropic threads 0; total threads 0; total messages 0; jobs 0.

After terminal `completed` (readback 1):

| surface | value |
|---|---|
| anthropic-origin threads | **63** |
| origin distribution | `anthropic=63`, `codexify=0`, `openai=0`, `NULL=0` |
| messages on anthropic threads | **784** |
| distinct importing users | **1** (`local`) |
| imported provenance metadata | `metadata->>'import_source'='claude'` on 63/63 |

Second independent readback (separate psql invocation): identical — 63 threads, 784 messages, distribution `anthropic=63`, 1 distinct user.

## Source-vs-commit distinction

| surface | value |
|---|---|
| conversations discovered (source) | 65 |
| conversations accepted (source) | 65 |
| canonical threads committed (writer/durable) | 63 |
| canonical messages committed (writer/durable) | 784 |

Discovery (65) is not substituted for committed threads (63); the difference is the writer's legitimate skip of conversations with no importable messages, exactly as the first proof observed.

## Negative checks (pre/post, isolated DB)

| surface | baseline | post | verdict |
|---|---|---|---|
| `projects` | 1 (`General`) | 2 (`General`, `Imports`) | PASS — only the backend default and the canonical writer's import-container project exist; no Anthropic `projects/*.json` → Project entity |
| `memory_entries` | 0 | 0 | PASS — `memories.json` created no memory state |
| `user_profiles` | 0 | 0 | PASS — `users.json` created no persona/identity rows |
| `personal_facts` / `personal_fact_evidence` | 0 / 0 | 3 / 74 | OBSERVED — all 74 evidence rows link via `source_message_id` to messages in anthropic-origin threads: conversation-derived fact candidates from the pre-existing canonical Claude writer, NOT `memories.json` ingestion |
| media/document tables (`media_assets`, `uploaded_images`, `generated_images`, `uploaded_documents`, `generated_documents`, `thread_documents`, `project_document_links`) | 0 each | 0 each | PASS — no fabricated media/document rows |

## Export integrity

Per-file SHA-256 recomputed after the run: all six identical to the intake hashes (byte-for-byte unchanged). Staged private copy of the proof job removed from the shared staging root at teardown; unrelated staging directories untouched.

## UI terminal proof

Rendered modal reached terminal success: **"Import completed — Imported 63 threads, 784 messages, and 0 images. Duplicates: 0. Skipped: 0. Warnings: 0."** (operator-observed) and the coordinator persisted `{jobId: "c94e8387-…", status: "completed", sourceSystem: "anthropic"}`. No screenshot committed.

## Invariants

1. Rendered Web UI origin — PASS (modal interaction + network capture; not an API-only exercise)
2. `source_system` exactly `anthropic` — PASS (durable row)
3. Browser never assigns `origin_system` — PASS (client serializes only `source_system`; no origin field in any captured request)
4. PostgreSQL durable authority — PASS (direct read-only psql evidence; two independent readbacks)
5. Durable accounting agrees with persistence — PASS (`Jt=63=Pt`, `Jm=784=Pm`; checkpoint entry present)
6. Discovery ≠ committed — PASS (65 discovered vs 63 committed, recorded separately)
7. Job not manually repaired/edited — PASS (no row edits; terminal state produced by the runtime)
8. Export byte-for-byte unchanged — PASS (hash equality)
9. Isolated disposable runtime — PASS (fresh R2 project/volumes, no reuse of the first proof's volumes)
10. No unrelated runtime mutated — PASS (`codexify`/`codexify_tester`/`codexify-audit` untouched; verified before teardown and after)
11. No implementation fix authorized/performed — PASS (only the receipt is new; tree otherwise clean)
12. No release widening — PASS (no release/current-state claim)
13. Unsupported Projects/memory/users/media not inferred from conversation success — PASS (negative checks recorded as observed)
14. Historical BLOCKED receipt unchanged — PASS (not modified)

## ADR impact

`Aligned with existing ADR(s); no architecture change.` Governing anchors confirmed during pre-read: ADR-001 (Queue-Based Completion Acceptance Model), ADR-005 (Runtime Mode and Account Boundary Invariants), ADR-069 (Codexify Beta Runtime Support Boundary), and the `account-export-restore-contract.md` normative contract. This task exercises already-accepted architecture; no ADR added or superseded.

## Documentation follow-through

- Historical BLOCKED receipt (`2026-08-19-anthropic-account-import-supported-runtime-proof.md`) remains unchanged and remains historically correct at `608f483bf`.
- `00-current-state.md` unchanged.
- No release/support claim widened.
- With this PASS, the runtime evidence is now sufficient to make a separate support-posture reconciliation task eligible (deferred — see below).

## Teardown

- `PROOF_PROJECT=codexify_anthropic_import_proof_r2_20260819` printed and verified before teardown; torn down with the same files used to start it: `docker compose --env-file .env.tester -p codexify_anthropic_import_proof_r2_20260819 -f docker-compose.yml -f /private/tmp/codexify-anthropic-proof-r2.override.yml down -v`. Only proof-project volumes/network removed; all unrelated projects intact (20 containers unaffected).
- Proof job's staged private bytes removed (job-scoped directory only).
- Source export still present and unchanged afterward.
