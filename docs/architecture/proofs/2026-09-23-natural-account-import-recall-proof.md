# Fresh natural account import-to-recall proof — 2026-09-23

## Classification

**`IMPORT_TRANSPORT_FAILED` — first failed boundary: rendered UI → account-import job creation.** A fresh Chromium session selected a newly generated synthetic OpenAI export folder through Settings → Data → Import ChatGPT history → Import account data → OpenAI (ChatGPT) → Choose Folder. The browser received HTTP 500 from `POST /api/imports/openai-account` and rendered “Account import failed — Internal Server Error.” PostgreSQL rejected the attempted job insert because the request resolved `user_id=You`, while the new database contained canonical user `local` and no user `You`. No job was committed. This proof stopped without another import submission, service restart, manual embedding action, or chat completion.

The requested natural embedding and recall chain was **not reached**. This result does not contradict the preceding controlled isolated worker replay, which manually reconstructed verified source rows into its proof-owned store. It does not establish whether an untouched, successfully committed import would automatically become searchable.

## Frozen source and fresh topology

- Evaluated checkout: clean local `main` at `2ccaf8174654a38004c7b9c9924609a4b94a5840`; `git merge-base --is-ancestor 2ccaf8174654a38004c7b9c9924609a4b94a5840 HEAD` exited 0. Docker context: `desktop-linux`.
- Fresh Compose project: `codexify_natural_import_recall_20260923`. The exact command prefix was `docker compose --env-file /Volumes/Dev_SSD/Codexify-main/.env --project-directory /Volumes/Dev_SSD/Codexify-main -p codexify_natural_import_recall_20260923 -f /Volumes/Dev_SSD/Codexify-main/docker-compose.yml -f /Volumes/Dev_SSD/Codexify-main/docker-compose.whooshd-smoke.yml -f /private/tmp/codexify-natural-import-recall-20260923/compose.override.yml`. The explicit Whoosh'd smoke layer preserved the local-only provider route; the repository development and private-preview overrides were not included.
- Before creation, all three exact requested Docker volume names were absent. At `2026-09-23T19:14:26Z`, Docker created `codexify_natural_import_recall_20260923_pg`, `codexify_natural_import_recall_20260923_chroma`, and `codexify_natural_import_recall_20260923_imports`. Each uses the local driver without driver options and has labels for the Compose project, `purpose=natural-account-import-recall-proof`, and `proof.created_date=2026-09-23`. Only this proof project's containers attached to them.
- The temporary override declares the three volumes external by exact engine name. Rendered configuration and actual `docker inspect` mounts agree: `db` uses the new PostgreSQL volume; `backend`, `worker-chat-embed`, and `worker-chat` share the new Chroma volume at `/app/.chroma` with `nocopy: true`; `backend` and `worker-account-import` share the new imports volume at `/app/data/imports`. The resolved vector backend is `chroma`, collection `codexify_vault_supported`, path `/app/.chroma`, and model `/models/bge-large-en-v1.5`. No started proof service mounted the shared host `.chroma`, prior proof volume, default-stack PostgreSQL data, or private-preview storage.
- Started only `db`, `redis`, `migrator`, `backend`, `worker-account-import`, `worker-chat-embed`, `worker-chat`, and `frontend`. Migrator exited 0; database revision was `a8d4c2f6b1e9`. PostgreSQL, Redis, and backend were healthy; frontend origin `http://127.0.0.1:5184/` and backend origin `http://127.0.0.1:8894/health` returned HTTP 200. Local Whoosh'd health and `/v1/models` returned HTTP 200, with `local-chat` present. The new database's existing General Project was ID 1, owner `local`.
- Before import, read-only vector inspection in both backend and chat worker returned exact parity: one deterministic `system-doc:builtin-help` record (`source=builtin_help_asset`) and no new source ID, new marker, or prior probe marker. No fixture vector was inserted manually.

## Synthetic export and browser attempt

The new export was derived from the previously successful canonical OpenAI fixture structure, with a new conversation identity, title, message identities, and marker contents. It was kept only in the authorized temporary directory.

| Fixture field | Value |
| --- | --- |
| Relative path | `openai-export/conversations.json` |
| File count / bytes | 1 / 1,007 |
| File SHA-256 | `42ead7ae23cb404ba8349e76fb1163be7cad0a73085d02ebe7a10b3c68d048e3` |
| Source conversation | `axis-natural-import-recall-20260923-02` |
| Source messages | `axis-natural-user-message-20260923-02`, `axis-natural-assistant-message-20260923-02` |
| Bodies | New synthetic user and assistant markers specified by the task; never committed |

The fresh named Playwright browser session opened the isolated frontend, selected Settings → Data → Import ChatGPT history, confirmed OpenAI (ChatGPT) was selected, clicked Choose Folder, and supplied the generated `openai-export` directory through the real file chooser. The rendered modal then displayed one selected file and the failure message. Its console recorded HTTP 500 at `/api/imports/openai-account`. Backend logging correlated the failed request as `req_b65ba7c3891043daaa58e4d2d6ef0581` with `IntegrityError`. PostgreSQL's error named `openai_account_import_jobs_user_id_fkey` and reported missing `user_id=You`. This occurred during job creation, before upload or commit could be established.

Read-only database checks found zero account-import jobs, zero canonical threads/messages with the new source conversation ID, one `users.id=local`, and zero `users.id=You`. The account-import, import-embedding, and chat queues each had depth zero. The account-import and embedding workers recorded no processing of this source. Backend Chroma remained identical to its pre-import one-record inventory. No job ID, staged manifest, imported Project/thread/message ID, or terminal import counters exist for this attempt.

The observed identity path is specific: the fresh UI defaults `userName` to “You”; the import modal passes `userName` to the coordinator; the API helper sends a nonempty value as `X-User-Id`; the backend reported its local header override enabled and canonical single-user ID `local`. The PostgreSQL foreign-key error confirms the resolved job owner was `You`. This is a code-path explanation corroborated by live request/database evidence, not proof of behavior in other profiles. The earlier staging proof used a different retained browser/runtime context and is not evidence that this fresh identity path succeeds.

## Unreached stages and validation

| Stage | Result |
| --- | --- |
| Fresh isolated Postgres, Redis, Chroma, import staging, migrations, mounts, local provider | Passed live topology checks |
| Rendered folder selection | Passed; one synthetic file selected |
| Account-import job create | **Failed HTTP 500**; no durable job |
| Upload, commit, account-import worker materialization | Not reached |
| Automatic embedding handoff, worker consumption, vector parity for imported rows | Not reached; no source rows existed |
| Fresh General recall, worker retrieval, provider capture, answer, durable assistant readback | Not attempted; zero completions |
| Project-mode negative control | Not applicable without imported evidence or a recall thread |

Validation commands and evidence levels:

- Exact fresh Compose prefix `config --quiet` and `config --format json`: passed. A private resolved JSON render was checked for the three explicit volumes, loopback ports, vector settings, and absence of inherited Chroma binds. This is configuration proof; actual mounts were separately checked with `docker inspect`.
- `docker wait codexify_natural_import_recall_20260923-migrator-1`: exit 0; read-only `alembic_version` query returned `a8d4c2f6b1e9`. This proves migration completion in the fresh database.
- `compose.sh exec -T backend python - < inspect_vector.py` and the matching `worker-chat` command: before import, exact one-record parity and marker absence passed. After the failed attempt, backend inspection matched its before snapshot exactly. This is live vector observation, not automatic embedding proof.
- Browser CLI commands `open`, `snapshot`, `click`, and `upload` in the fresh `natural_import_20260923` session: rendered UI path reached folder selection and the HTTP 500 failure. The CLI's documented `network` command was unavailable in the installed version; the browser console, backend request log, PostgreSQL constraint log, and read-only database/queue checks establish the failed boundary without a second submission.
- `.venv/bin/python -m pytest -v tests/workers/test_account_import_worker.py tests/migration/test_openai_export_conversation_import.py`: 30 passed. These are test proof for import code, not a live job result.
- `.venv/bin/python -m pytest -v tests/core/test_context_broker_source_mode.py tests/core/test_context_broker_depth.py tests/core/test_retrieval_user_isolation_and_widening.py tests/context/test_retrieval_scope_boundaries.py`: 53 passed. These are policy regression tests; retrieval was not executed in this proof.
- `git diff --check -- docs/architecture/proofs/2026-09-23-natural-account-import-recall-proof.md`: passed after staging via the stronger staged diff check.

## Closeout and next prerequisite

All proof project services were stopped; the migrator had already exited 0. The three proof volumes, stopped containers, temporary Compose overlay, fixture, browser snapshots, and sanitized diagnostics remain under the authorized temporary directory or Docker project for review. The browser session was closed. Default-stack and private-preview containers remained running; no command reconfigured or stopped them. No production source, test, ADR, contract, current-state, or release-claim file changed. No manual vector insertion, embedding enqueue/retry/backfill, status reset, or restart was used to bridge the failed boundary.

**One next corrective task:** reconcile the local account-import request identity so a fresh browser display name cannot become an unauthorized/nonexistent canonical job owner when local debug header override is enabled; cover that exact fresh-browser job-create path before rerunning a new natural import-to-recall proof. This receipt does not implement that correction or classify automatic embedding.

**ADR impact:** no ADR change; ADR-067 and ADR-081 remain governing. **Documentation follow-through:** this proof artifact only. **Current-state change:** none. **Release-claim change:** none.
