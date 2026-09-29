# Fresh natural account import-to-recall proof R2 — 2026-09-23

## Classification

**`AUTOMATIC_EMBED_HANDOFF_FAILED` — first failed boundary: canonical imported messages → automatic import-embedding handoff.** The fresh rendered Settings flow created, uploaded, committed, and completed one account-import job under canonical owner `local`. PostgreSQL contains the expected imported Project, thread, and two messages. More than 120 seconds after materialization, both messages remained `embedding_status=pending`, neither embedding queue held work, the chat embedding worker recorded no processing, and both backend and chat worker still saw only the deterministic built-in Chroma record. No recall thread or completion was created. This receipt stops at that boundary and makes no retrieval, provider, answer, or persistence claim.

The account-import worker currently invokes the OpenAI conversation importer with `embedding_mode="defer"` (`guardian/workers/account_import_worker.py`). That code path is consistent with the observed missing handoff; the live result establishes that this job did not naturally reach embedding. No backfill, enqueue, status reset, service restart, or vector write was used to bridge it.

## Frozen source and isolated runtime

- Evaluated checkout: clean local `main` at `7eafe427391bd172b6dec00939ea0ea7d9c520cf`; `git merge-base --is-ancestor 7eafe427391bd172b6dec00939ea0ea7d9c520cf HEAD` passed before runtime construction. Docker context: `desktop-linux`. This is the committed browser identity repair. The prior failed proof and its volumes were not reused.
- Compose project: `codexify_natural_import_recall_r2_20260923`. The private wrapper `/private/tmp/codexify-natural-import-recall-r2-20260923/compose.sh` selects the repository base Compose file, explicitly adds `docker-compose.whooshd-smoke.yml`, and adds only the R2 temporary override. It does not load the repository development or private-preview override. The backend/worker image was built under the unique tag `codexify-backend-runtime:proof-r2-7eafe427` (manifest `sha256:64d8b979b5286b55503c76619d2dd6b2344426a17b62e52336dec5cfc4c2768c`).
- Before creation, the exact requested volume names were absent. The new local-driver volumes are `codexify_natural_import_recall_r2_20260923_pg`, `codexify_natural_import_recall_r2_20260923_chroma`, and `codexify_natural_import_recall_r2_20260923_imports`, each labeled with the R2 project, purpose, and creation date. Fresh Redis belonged to the same project.
- `compose.sh config --quiet` passed. The rendered JSON and actual `docker inspect` mounts agree: `db` uses R2 PostgreSQL; backend, `worker-chat-embed`, and `worker-chat` share R2 Chroma at `/app/.chroma` with `nocopy: true`; backend and `worker-account-import` share R2 import staging at `/app/data/imports`. Vector settings are `chroma`, `/app/.chroma`, collection `codexify_vault_supported`, model `/models/bge-large-en-v1.5`. No activated service mounted an earlier proof or default Chroma corpus.
- The normal migrator exited 0; database revision is `a8d4c2f6b1e9`. The fresh database began with user `local` and General Project `1|local`. Backend health, frontend, the three required workers, and local Whoosh'd `/v1/models` were reachable; logical `local-chat` was present. An initial Compose `up` encountered an already occupied Neo4j host port before any import; the required proof services were then started with the same frozen configuration and `--no-deps`. Neo4j was not needed for the exercised path. No service was restarted after import to provoke indexing.
- Before import, read-only VectorStore inspection from both backend and chat worker returned the exact same single record: `system-doc:builtin-help`, hash `49b815338b9bf67c7f5efda57d88a5a3a1db36ec97a6d587cd5e0feea81ce622`, source `builtin_help_asset`, namespace `system_docs:global`. The new source and markers, prior proof markers, and sentinel markers were absent. No fixture vector was seeded.

## Synthetic fixture and rendered browser import

The only submitted export was a new synthetic OpenAI folder in the authorized temporary directory.

| Field | Value |
| --- | --- |
| File | `/private/tmp/codexify-natural-import-recall-r2-20260923/fixture/openai-export/conversations.json` |
| File count / bytes | 1 / 1,010 |
| SHA-256 | `9842e58fc691299702d57069f0955bcccddf6214a2b93ff7f34a1ad7f815a95b` |
| Source conversation | `axis-natural-import-recall-20260923-03` |
| Title | `Axis Natural Import Recall Probe R2` |
| Source messages | `axis-natural-user-message-20260923-03`, `axis-natural-assistant-message-20260923-03` |
| Synthetic bodies | `CODEXIFY_NATURAL_IMPORT_USER_MARKER_20260923_C`, `CODEXIFY_NATURAL_IMPORT_ASSISTANT_MARKER_20260923_C` |

The first fresh Chromium CLI session closed before folder selection. PostgreSQL still contained zero account-import jobs, so the retry session was opened against the same untouched R2 runtime. It rendered Imprint with presentation name `You`, then navigated Settings → Data → Import ChatGPT history → Import account data, kept OpenAI (ChatGPT) selected, clicked Choose Folder, and supplied the folder through the actual file chooser. Folder selection automatically began the import; the modal showed one file and “Accepted — continuing in background.” Exactly one job was created.

The browser request inventory recorded HTTP 200 for `POST /api/imports/openai-account`, the job's `/files` upload, `/commit`, and two status reads. Sanitized browser request-header inspection found no `X-User-Id` on create, upload, commit, or status. The normal browser authentication/request configuration was left intact. The backend's existing request identity resolver assigned job owner `local`; no frontend `local` value was supplied. Job ID: `e1ba8b51-4699-4149-93aa-1221a79a5317`.

## Materialization and first failed handoff

The terminal job row is `completed`, owner `local`, source `openai`, with `total_file_count=1`, `uploaded_file_count=1`, `imported_thread_count=1`, `imported_message_count=2`, and duplicate/skipped/warning/failure counts all zero. Its checkpoint records the exact source conversation ID, one discovered and accepted conversation, and committed conversation transactions.

PostgreSQL reconciliation found Imports Project `2|local`, imported chat thread `1|local|project=2|origin_system=openai`, title `Axis Natural Import Recall Probe R2`, and source thread ID `axis-natural-import-recall-20260923-03`. Imported chat message IDs `1` (user) and `2` (assistant) belong to that thread and owner `local`; their provenance contains the expected respective source-message IDs and synthetic content. General Project `1|local` remains distinct. No other conversation was imported.

The account-import worker completed text materialization at `2026-09-23 21:46:53 UTC`. At `21:51 UTC`, more than four minutes later, both imported messages still had `extra_meta.embedding_status=pending` and null `embedded_at`. `LLEN codexify:queue:chat-import-embed` and `LLEN codexify:queue:chat-embed` were both zero. `worker-chat-embed` had no post-import processing log entry. Read-only post-import VectorStore inspection from both backend and `worker-chat` still returned only the same built-in record and no R2 source or marker. Thus the topology is shared, but there is **no imported vector parity to qualify** because no imported vectors exist.

| Boundary | Result |
| --- | --- |
| Fresh isolated topology, migration, canonical `local`, clean vectors | Passed live runtime checks |
| Rendered folder selection, create, upload, commit, status | Passed; browser HTTP 200 and no `X-User-Id` |
| Account-import worker and canonical PostgreSQL materialization | Passed; one conversation, two messages, zero job failures |
| Automatic import-embedding handoff and worker consumption | **Failed**; messages pending, both queues empty, no worker processing or vectors after the observation bound |
| Exact imported-vector parity, fresh General recall, semantic retrieval, provider injection, answer, persistence, Project-mode negative control | Not attempted after the first failed boundary; zero recall completions |

## Validation and closeout

- `pnpm --dir frontend/src exec vitest run features/imports/__tests__/accountImportCoordinator.ChatGPTImportModal.test.ts components/modals/__tests__/ChatGPTImportModal.test.tsx`: 2 files, 22 tests passed. This is focused frontend regression proof, not the live import outcome.
- `.venv/bin/python -m pytest -v tests/routes/test_migration_routes.py tests/workers/test_account_import_worker.py tests/migration/test_openai_export_conversation_import.py`: 58 passed. This is route/import test proof.
- `.venv/bin/python -m pytest -v tests/core/test_context_broker_source_mode.py tests/core/test_context_broker_depth.py tests/core/test_retrieval_user_isolation_and_widening.py tests/context/test_retrieval_scope_boundaries.py`: 53 passed. This is retrieval-policy test proof; no recall retrieval ran in R2.
- `git diff --check -- docs/architecture/proofs/2026-09-23-natural-account-import-recall-proof-r2.md`: passed. The proof file alone was staged and committed.

Only R2 proof services were stopped after observation. Its named PostgreSQL, Chroma, and import-staging volumes and temporary fixture/diagnostics were retained; no `docker compose down -v` was used. The prior failed proof runtime, default stack, private-preview state, source code, tests, ADRs, current-state, and release documentation were not changed. The Whoosh'd provider was reached for preflight only; no completion was submitted and no provider capture receipt was produced. No manual indexing, enqueue, backfill, status reset, or recovery bridge occurred.

**One next prerequisite:** establish and qualify an automatic post-materialization embedding handoff for background account-import jobs, then rerun this natural chain from another fresh isolated runtime. Do not treat a manual backfill or the earlier controlled replay as evidence of this missing handoff.

**ADR impact:** no ADR change; ADR-005, ADR-067, and ADR-081 remain governing. **Documentation follow-through:** this proof artifact only. **Current-state change:** none. **Release-claim change:** none.
