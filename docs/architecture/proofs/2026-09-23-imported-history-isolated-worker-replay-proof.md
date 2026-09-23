# Imported-history isolated worker replay proof — 2026-09-23

## Result and boundary

**PASS — controlled isolated worker path.** A new proof-owned Docker volume was initialized empty, then exactly two verified canonical OpenAI import messages were reconstructed through Codexify's local `VectorStore.add_texts()` implementation. The live backend and chat worker mounted that same volume and read the same imported record IDs and source text hashes. One fresh General-thread completion selected both records under `personal_knowledge` + `normal`, placed both synthetic markers in the actual local Whoosh'd request, and persisted an assistant answer containing the expected assistant marker. The task reached a `task.completed` event.

This proves the bounded, manually reconstructed fixture path only. It does not prove automatic import-to-index handoff, restart-free embedding, production recovery, shared-store repair, private-preview health, or release readiness. No production source or repository Compose file changed.

## Source, ownership, and resource gates

- Execution checkout: `/Volumes/Dev_SSD/Codexify-main`, clean `main` at `d91d621933f7c6a476d4985901e9e4eefd2bc72c` before this receipt. `git merge-base --is-ancestor d91d621933f7c6a476d4985901e9e4eefd2bc72c HEAD` passed. Docker context: `desktop-linux`.
- The retained project is `codexify_account_import_ui_probe_20260923`. Its PostgreSQL volume `codexify_account_import_ui_probe_20260923_pg_data` and database container carry that Compose project label; the database container mounts that exact volume. Port `5548` was not used as identity evidence.
- Exact Compose prefix, in order: `docker compose --env-file /Volumes/Dev_SSD/Codexify-main/.env --project-directory /Volumes/Dev_SSD/Codexify-main -p codexify_account_import_ui_probe_20260923 -f /Volumes/Dev_SSD/Codexify-main/docker-compose.yml -f /Volumes/Dev_SSD/Codexify-main/docker-compose.whooshd-smoke.yml -f /private/tmp/codexify-account-import-ui-staging-20260923/compose.override.yml -f /private/tmp/codexify-import-retrieval-probe-provider-20260923/compose.capture.override.yml`. This repeats the preceding parity receipt's explicitly evaluated environment file, project directory, file order, and project name.
- The requested volume did not exist at the baseline check. It was created as `codexify_account_import_ui_probe_20260923_chroma_isolated_v1` at `2026-09-23T18:28:36Z`, with Docker's local driver, no driver options, and labels `com.docker.compose.project=codexify_account_import_ui_probe_20260923`, `proof.task=2026-09-23-imported-history-isolated-worker-replay`, and `purpose=codexify-imported-history-isolated-worker-replay`. Docker reported no attached container before activation. Its only attached containers afterward were this proof's backend and chat worker. No non-probe consumer mounted it.
- The protected stopped-worker copy and manifest under `worker-store-parity/` were not opened for mutation. The existing shared host `.chroma` and default `codexify` services were not changed.

## Configuration and canonical reconstruction

The only temporary configuration edit was `/private/tmp/codexify-account-import-ui-staging-20260923/compose.override.yml`. It declares the named volume with `external: true` and replaces `/app/.chroma` mounts for `backend`, `worker-chat`, `worker-chat-embed`, `worker-document-embed`, optional `obsidian-ingest`, and optional `embedding-backfill` with the new volume and `volume.nocopy: true`. It pins `CODEXIFY_CHROMA_PATH=/app/.chroma`. The existing collection `codexify_vault_supported`, Chroma backend, and local `/models/bge-large-en-v1.5` embedding model were preserved. Optional ingest/backfill services remained stopped. The capture overlay was unchanged.

The exact prefix's `config --quiet` passed before and after the edit. Full `config --format json` renders were kept privately. A structured comparison removed only the new volume declaration, each scoped `/app/.chroma` mount, and each scoped `CODEXIFY_CHROMA_PATH` field; the remaining entire rendered model compared equal. A render with `--profile cli --profile backfill` also showed the named volume as the sole `/app/.chroma` mount for all six listed consumers. No started proof container retained the shared host `.chroma` bind. The old stopped `worker-chat-embed` container still carries its historical bind; it was not started or reconfigured.

The source gate used a read-only PostgreSQL transaction and selected by `chat_threads.metadata.source_thread_id`, then verified the one matching thread was ID 1, owner `local`, Project owner `local`, and `origin_system=openai`. Its only messages were canonical IDs 1 and 2, with the expected roles and source message identities. Their canonical content hashes matched the retained synthetic export (`conversations.json` SHA-256 `1e622bfe53114c77792523bfca96cde557975b1f7d21f0fc1f2384f49dbbf862`):

| Canonical message | Source identity suffix | Content SHA-256 |
| --- | --- | --- |
| 1, user | `axis-import-user-message-20260923-01` | `5927e6de547f2c3f1ddbc7cbbcb0492e266d46590a77fca5f1c1fc6b8e4844e3` |
| 2, assistant | `axis-import-assistant-message-20260923-01` | `cd13ccbb57ec79cb6e11b80dc69f93591413b46460b69e889df00013bde642c9` |

The empty target collection was observed before insertion. The temporary script used the trusted backend runtime, the existing import text/metadata sanitizers, and `VectorStore.add_texts()` to embed the two canonical bodies. It passed only allowlisted owner, thread, message, role, source, timestamp, and source classification fields into the index; it did not serialize raw messages or whole `extra_meta` dictionaries. Deterministic IDs were `isolated-import-message-1` and `isolated-import-message-2`. The script's resume path verifies exact records rather than reinserting them. No canonical row, job, lifecycle status, or queue item was reset or repaired. A first initialization attempt stopped before insertion because two Chroma clients used different settings; using Codexify's initialized collection in the temporary script resolved that local proof utility issue. The successful run inserted exactly two records.

Backend startup subsequently added one deterministic `system-doc:builtin-help` record (`source=builtin_help_asset`, namespace `system_docs:global`, hash `49b815338b9bf67c7f5efda57d88a5a3a1db36ec97a6d587cd5e0feea81ce622`). It contained neither synthetic marker. The two imported records remained the only reconstructed fixture records. Live backend and `worker-chat` inspection reported identical imported IDs, source identities, text hashes, vector path, collection, and model; both actual container mounts named the same Docker volume. The ordinary embedding queues were empty and `worker-chat-embed` stayed stopped.

## Single completion and independent observations

The retained failed probe's exact authored question was read from canonical message 3 and reused without printing its body. Its SHA-256 was `e9d5d6373fa268b9b682bb11b33b12ab6eb202f202326f1c7d8fea90cb92bf2a`; neither complete marker appeared in it. The normal message API created fresh native thread 4 in the existing General Project 1, owned by `local`, and authored user message 5. The normal completion API accepted **one** request with provider `local`, logical model `local-chat`, `source_mode=personal_knowledge`, and `depth_mode=normal`. Whoosh'd health and model-list preflight returned HTTP 200 and exposed `local-chat`; no cloud fallback was used.

| Correlation | Observed value |
| --- | --- |
| Task | `156f385b-52be-495e-87e6-a867185319cc` |
| Request | `req_7f3c15338e8843758285c7b28fd5588b` |
| Turn | `cacd9d0c-1343-4909-af7a-69cae1c6526e` |
| Attempt | `attempt_ce6c35156daf435ab0121f702bd7bba5` |
| Thread / user message / assistant message | `4` / `5` / `6` |
| Terminal event | `task.completed`, Redis stream event `1790188897639-0` |

1. **Worker retrieval:** the durable trace for this exact task reports retrieval executed, `semantic_count=2`, `widen_reason=explicit_personal_knowledge`, source/depth `personal_knowledge`/`normal`, and selected vector IDs `isolated-import-message-1` and `isolated-import-message-2`, both from canonical thread 1. The worker log independently recorded `semantic=2`.
2. **Context assembly:** the same trace contains two selected documents in user/assistant roles, and `semantic_injected=true`, `retrieval_injected=true`. This is a trace receipt for assembly, separate from provider observation.
3. **Actual provider input:** the pre-dispatch `requests.post()` hook on the real `worker-chat` captured the exact task/request/attempt IDs, model `local-chat`, `stream=true`, and both markers present in the provider system message. The provider user message contained neither. The hook delegated the request unchanged; its response receipt recorded Whoosh'd HTTP 200. Only structural fields, hashes, and presence booleans were retained in the scoped capture copy.
4. **Answer use:** the persisted assistant response contains the expected assistant marker; its entire answer SHA-256 equals the verified canonical assistant source hash above. The question and capture code supplied no marker text to the provider user message.
5. **Persistence and terminal truth:** read-only PostgreSQL joined `eval_trace_snapshots` for this task to canonical assistant message 6 in thread 4, owner `local`, role `assistant`. The trace reports accepted, attempted, executed, and completed. The task event stream separately reports `task.completed`. The source thread remains owned by `local`, both source messages remain `ready` with unchanged content hashes and source identities, and the original import job remains `completed` with 1 thread, 2 messages, and 0 failures.

The source is outside the General Project, so this is the governed same-user Personal Knowledge widening path. The provider capture proves input to the executed local request; durable readback proves the answer and state, rather than treating task acceptance or queue consumption as completion.

## Validation, closeout, and limits

- `python3 -m py_compile` on all three temporary scripts: passed.
- Exact `DC` prefix `config --quiet` and `config --format json` before/after: passed; scoped structured render comparison: equal after removing only authorized vector fields and volume declaration.
- Exact `DC` prefix with optional profiles `config --quiet` and `config --format json`: passed; all six Chroma consumers resolve to the isolated named volume with `nocopy`.
- `DC run --rm --no-deps -T --entrypoint python backend - < seed_from_canonical.py`: passed on the corrected temporary script, with two records inserted. Initial client-settings failure wrote no vectors.
- `DC exec -T backend python - < inspect_vector_parity.py` and the corresponding `worker-chat` command: passed with exact imported-record parity and separately inventoried built-in record.
- `DC exec -T backend python - < replay_completion.py`: submitted exactly one completion. The proof script's status-route poll returned 404 in this runtime and was interrupted after the worker had completed; it did not retry. Read-only task-event, trace, provider capture, and message readback then independently established the terminal result within the documented 780-second accepted-task budget.
- `.venv/bin/python -m pytest -v tests/core/test_context_broker_source_mode.py tests/core/test_context_broker_depth.py`: 46 passed. These policy tests support the unchanged source/depth behavior; the live receipts above establish the runtime path.
- `git diff --check -- docs/architecture/proofs/2026-09-23-imported-history-isolated-worker-replay-proof.md`: passed after this artifact was prepared.

The temporary scripts, private renders, parity outputs, provider capture copy, and replay receipts remain under `/private/tmp/codexify-account-import-ui-staging-20260923/isolated-worker-replay/`; private JSON/JSONL files have mode `0600`. The previously retained capture hook appended two structural observations to its existing private probe receipt file; the scoped copy contains only this task's two observations. The temporary override remains for inspection and is not staged.

Only this task's `worker-chat`, backend, Redis, and PostgreSQL services were stopped after readback. The new vector volume, retained proof PostgreSQL, older failed-worker preservation, and diagnostics remain. The stopped old chat-embedding container still reflects historical configuration, while all started proof consumers used the isolated volume. Docker container IDs/start timestamps for the running default backend, default document-embedding worker, and private-preview database were unchanged across closeout. No `down -v`, volume prune, shared-store cleanup, private-preview reconfiguration, or production repair occurred.

**Primary classification:** `PASS`; no failed runtime boundary remains for this controlled replay. **ADR impact:** aligned with ADR-067's PostgreSQL authority and derived Chroma boundary and ADR-081's Project ownership authority; no ADR amendment. **Documentation follow-through:** this receipt only. **Current-state and release claims:** unchanged.
