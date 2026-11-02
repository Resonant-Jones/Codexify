# Supported-Compose runtime qualification — `41ff6152`

> **Release posture: HOLD.** This receipt is evidence for a later release
> adjudication. It does not authorize promotion, and it did not change any
> release-support classification.

## Result

One integrated qualification of the **supported local Docker Compose runtime**
was executed against a frozen source revision, in an isolated Compose project,
with the live Private Preview left untouched.

| Gate | Subject | Disposition |
| --- | --- | --- |
| A | Supported configuration / provider contract | **PASS** |
| B | Startup, health, and **migrations** | **FAIL** (stock path) — see [Gate B](#gate-b--startup-and-migrations-fail-on-the-stock-supported-path) |
| C | Explicit-model rejection | **PASS** |
| D | Ordinary chat and durable state | **PASS** |
| E | Retrieval and provenance | **PASS** (with a recorded worker-durability caveat) |
| F | Browser and event coherence | **PASS** |
| G | Restart recovery | **PASS** |
| H | Other supported baseline gates | **PASS** for every selector that could execute; **3 selectors INCOMPLETE** (missing optional dependency) |

**One gate fails.** Gate B fails on the stock supported path: the migrator
applies the **baked image's** Alembic head (`3a91d7c4e8b2`) instead of the
frozen source head (`a3115f64dda8`), so the schema in a stock-launched stack is
two real migrations behind the application source it serves. A diagnostic
comparison run shows the frozen revisions apply cleanly once the migrator can
see the source tree, which isolates the cause to the migrator's bind mount
rather than to the migrations themselves.

---

## 1. Evaluated SHA and worktree identity

| Item | Value |
| --- | --- |
| Evaluated (frozen) SHA | `41ff615293ecf6b7bd1b7f21515cd197f19f0848` |
| Worktree | `/Volumes/Dev_SSD/Codexify-main/.worktrees/qual-compose-41ff6152` |
| HEAD state | detached at the frozen SHA |
| Working-tree status | clean — `git status --porcelain` returned 0 lines before the run and after the run |
| `origin/main` at execution time | `4f70d1a826a4c2375192b8926aee2e163c9dff4a` (PR #977, merged *after* the freeze) |
| Freeze honoured | yes — the frozen SHA was never substituted during execution |
| Execution date | **2026-11-02** (the receipt *filename* carries `2026-10-30` because the authorized path is fixed; the body records the real execution date) |
| Executor | MiniMax |

The frozen revision was re-verified as a commit that exists in the repository,
and the worktree used for every container bind mount was created from that
revision only.

## 2. Supported profile and resolved configuration summary

Supported profile: **`v1-local-core-web-mcp`**
(`config/supported_profiles/v1-local-core-web-mcp.yaml`), surface
`local-docker-compose-webui`.

The resolved configuration was inspected before any container was started. All
eight required contract values were in force on the startable qualification
services:

| Contract key | Required | Observed |
| --- | --- | --- |
| `LLM_PROVIDER` | `local` | `local` |
| `LOCAL_PROVIDER_VENDOR` | `whooshd` | `whooshd` |
| `LOCAL_RUNTIME_PRESET` | `whooshd-mlx` | `whooshd-mlx` |
| `LOCAL_CHAT_MODEL` | `local-chat` | `local-chat` |
| `ALLOW_CLOUD_PROVIDERS` | `false` | `false` |
| `CODEXIFY_LOCAL_ONLY_MODE` | `true` | `true` |
| `CODEXIFY_SUPPORTED_PROFILE` | `v1-local-core-web-mcp` | `v1-local-core-web-mcp` |
| `CODEXIFY_EGRESS_ALLOWLIST` | `""` (empty) | `""` (empty) |

Container-to-provider route: **`http://host.docker.internal:8000/v1`**
(`LOCAL_BASE_URL`), confirmed in the resolved Compose output and again in the
model-resolution evidence recorded with every completion.

**No cloud-provider fallback was available.** The host operator `.env` on this
machine is configured for the `v1-friends-family-web` profile with
`ALLOW_CLOUD_PROVIDERS=true` and a real DeepSeek credential present. The
qualification therefore used a scratch Compose override (outside tracked source)
that pins the `v1-local-core-web-mcp` contract on the frontend, migrator,
model-prep, and graph-init, and blanks every cloud key on every startable
service. An automated assertion confirmed that **no qualification-owned service
carries a cloud credential**, so a cloud fallback was not merely disabled — it
was not present.

`worker-account-import` and `worker-voice` were deliberately **not started**:
both carry the operator `.env`'s cloud keys and neither is in the supported
profile's service set.

## 3. Isolation verification

Isolation was established by project label, resolved-configuration inspection,
and a preflight resource inventory — never by a global Docker operation.

| Isolation property | Result |
| --- | --- |
| Compose project | `codexify_qual` (distinct from `codexify_private_preview`) |
| Project-scoped volumes | 9, all `codexify_qual_*`; no shared writable volume |
| Network | `codexify_qual_default` (project-scoped) |
| Bind-mount sources | 15 bind sources, all rooted in the frozen qualification worktree (plus the shared local model directory) |
| Published host ports | exactly `5173, 5433, 7474, 7687, 8889` |
| Preview ingress | `127.0.0.1:8081` untouched; the unrelated `codexify-devproxy` on `8888` untouched |
| Cloud credentials in qualification containers | none |
| External resources permitting writes into Preview state | none |
| Cleanup commands matching other projects | none — no `docker ps -aq --filter "name=codexify"`, no prune, no volume cleanup, no shared-volume removal |
| Host Whoosh'd provider | left running and unmodified for the entire run |

The repository's own `scripts/whooshd_docker_smoke_up.sh` was read as a
reference for its configuration assertions and **was never executed**, because
its global container-removal step can select the live Private Preview. The
qualification used the Compose definitions directly.

## 4. Pre-existing Preview resources observed

Preflight snapshot of the live Private Preview (18 containers, project label
`com.docker.compose.project=codexify_private_preview`):

- Database revision: **`3a91d7c4e8b2`**; 138 public tables.
- Database image: `postgres:15` `sha256:c961aa287d8698297cb26cdfadfbe9fd2cbaf77e53cfffe9636e8d8a1e4d842c`.
- Long-running services up at snapshot time: `backend`, `worker-chat`,
  `worker-warmup`, `worker-chat-embed`, `worker-document-embed`, `worker-voice`,
  `worker-account-import`, `worker-coding`, `db`, `redis`, `neo4j`,
  `private-preview-origin`, `frontend`.
- One-shot services already exited cleanly at snapshot time: `migrator` (exit 0),
  `model-prep` (exit 0), `graph-init` (exit 0), `e2e` (exit 0),
  `private-preview-auth-posture` (exit 0).

No qualification-owned container, volume, network, or process ever referenced a
Preview resource. The Preview database revision and container count were
re-read at the end of the run and compared against this snapshot
(see [§19](#19-cleanup-results)).

## 5. Qualification resource identities

Compose project `codexify_qual`; services started from
`docker-compose.yml` + `docker-compose.whooshd-smoke.yml` + the scratch
override.

| Service | Image | Image digest | Container ID |
| --- | --- | --- | --- |
| `backend` | `codexify-backend-runtime:latest` | `sha256:22d9f5f13e7d…` | `22335b150d8e` |
| `worker-chat` | `codexify-backend-runtime:latest` | `sha256:22d9f5f13e7d…` | `bc389a471b22` |
| `worker-document-embed` | `codexify-backend-runtime:latest` | `sha256:22d9f5f13e7d…` | `aecb8e075e6f` |
| `migrator` (one-shot) | `codexify-backend-runtime:latest` | `sha256:22d9f5f13e7d…` | `f6306972e324` |
| `model-prep` (one-shot) | `codexify-backend-runtime:latest` | `sha256:22d9f5f13e7d…` | `f95601ad0174` |
| `db` | `postgres:15` | `sha256:c961aa287d86…` | `63946430b625` |
| `redis` | `redis:7-alpine` | `sha256:858f009f9709…` | `f535b3eb16ac` |
| `neo4j` | `neo4j:5` | `sha256:d9cfe82983d2…` | `73a5116f9aa9` |
| `graph-init` (one-shot) | `neo4j:5` | `sha256:d9cfe82983d2…` | `07a607af6267` |
| `frontend` | `node:20-alpine` | `sha256:fb4cd12c85ee…` | `4060d9dde7b1` |

**Actual source revision used by each container.** `backend`, `worker-chat`,
and `worker-document-embed` bind-mount `./guardian:/app/guardian` and
`./backend:/app/backend` from the frozen worktree, so their application code
**is** the frozen SHA. This was verified from inside the containers: the
imported `guardian/core/db.py` and `backend/alembic.ini` matched the frozen
worktree byte-for-byte.

**The migrator is the exception, and that is the Gate B finding.** The migrator
bind-mounts **only** `./backend:/app/backend`. See [Gate B](#gate-b--startup-and-migrations-fail-on-the-stock-supported-path).

Host port map for the qualification stack:

| Service | Host port |
| --- | --- |
| frontend (Vite dev server) | `127.0.0.1:5173` |
| backend (Guardian API) | `127.0.0.1:8889` |
| db (PostgreSQL) | `127.0.0.1:5433` |
| neo4j (http / bolt) | `127.0.0.1:7474` / `127.0.0.1:7687` |
| host Whoosh'd provider (not qualification-owned) | `127.0.0.1:8000` |

## 6. Whoosh'd model inventory and execution evidence

Inventory advertised by the live provider at `http://127.0.0.1:8000/v1/models`
at qualification time:

| Model id | Display name | Engine | Context | Lifecycle policy |
| --- | --- | --- | --- | --- |
| `local-chat` | Gemma 4 12B IT QAT 4-bit | `mlx_vlm` | 32768 | `keep_warm` |

Exactly one model is advertised. The provider exposes its own request ledger at
`GET /runtime/requests`, which reports per-request `request_id`,
`upstream_request_id`, `model`, `status`, `error_code`, and timings. That ledger
is the provider-side evidence source for Gates C and D, correlated by the
application's own `request_id`.

Observed provider executions attributable to this qualification:

| Provider `upstream_request_id` | Model | Status | Error | Correlated to |
| --- | --- | --- | --- | --- |
| `req_b095b0acce0b4eac9e6cda144a1b8e82` | `local-chat` | `completed` | none | Gate D ordinary chat (thread 1) |
| `req_bdf8ccfd2dcb44c4b49f950646aea7b9` | `local-chat` | `completed` | none | Gate E retrieval chat (thread 4) |
| `req_cd9d124602724bf1b329837ac87571f8` | `local-chat` | `completed` | none | Gate G post-restart chat (thread 6) |
| `req_465f5956a0b542ddac8c1fe4d99a5a70` | — | **absent from the ledger** | — | Gate C rejected request (thread 2) |

## 7. Explicit-model rejection result — **PASS**

**Gate C passed on every required element.** The claim under test is the full
invariant, not a generic HTTP error.

1. **An ordinary request first proved the advertised route is selectable.**
   `POST /api/chat/1/complete` with `model: "local-chat"` was accepted
   (`acceptance_status: accepted`) and executed (§9).

2. **An explicit selection of an absent model was then issued.**
   `POST /api/chat/2/complete` with `model: "qual-nonexistent-model-41ff6152"`.
   The request was **accepted onto the queue** and then failed in the worker —
   the rejection is not a synchronous HTTP refusal, it is a durable terminal
   failure of the attempt.

3. **The rejection identifies the unavailable model selection.** The durable
   `completion.error` event for task `5a5429bd-bdb6-4f0e-ac0a-a263e3e1de79`
   carries:

   ```json
   {
     "error": "local_model_resolution_error",
     "failure_kind": "local_model_unavailable",
     "message": "Requested model 'qual-nonexistent-model-41ff6152' is not advertised by the local runtime",
     "requested_model": "qual-nonexistent-model-41ff6152",
     "configured_source": "requested_model",
     "advertised_models": ["local-chat"],
     "inventory_source": "whooshd:/v1/models",
     "provider_failure_message": "Requested model 'qual-nonexistent-model-41ff6152' is not advertised by the local runtime",
     "provider_request_started": false,
     "first_output_observed": false,
     "visible_output_emitted": false,
     "failed_after_state": "QUEUED",
     "duration_ms": 1175
   }
   ```

4. **No model was silently substituted and no fallback model executed.** The
   same event carries the canonical truth block:

   ```json
   "completion_truth": {
     "accepted": true, "attempted": false, "fallback_attempted": false,
     "executed": false, "completed": false
   }
   ```

   `attempted: false` and `executed: false` mean the attempt never reached an
   inference call, and `fallback_attempted: false` means no fallback route was
   taken.

5. **Provider-side non-execution was established from the provider's own
   ledger.** The rejected turn's `request_id`
   (`req_465f5956a0b542ddac8c1fe4d99a5a70`) has **no entry** in
   `GET /runtime/requests`, and there is **no entry anywhere in the ledger with
   `model: "qual-nonexistent-model-41ff6152"`**. The application-side
   `provider_request_started: false` and the provider-side absence agree. The
   only provider contact for the rejected turn was the **model inventory read**
   (`GET /v1/models`), which is how the system learns what is advertised — not
   an inference request.

6. **No successful assistant completion was persisted for the rejected
   request.** Readback of `GET /api/chat/2/messages` returns exactly one
   message, the user message. The database confirms it:
   `chat_messages` holds one row for thread 2 (role `user`), and
   `chat_completion_attempts` for that thread has `terminal_event_type =
   task.failed` with `completed_message_id = NULL`.

**No substituted model executed, so the FAIL-and-STOP condition did not
trigger.** The gate is a genuine PASS, not an INCOMPLETE.

## 8. Startup and migration result

### Gate B — Startup and migrations: **FAIL on the stock supported path**

Service startup itself was healthy:

| Check | Result |
| --- | --- |
| Required services start | yes |
| `model-prep` | exit 0 |
| `migrator` | exit 0 |
| `db` | healthy (`postgres:15`) |
| `redis` | healthy |
| `neo4j` | healthy |
| `graph-init` | exit 0 |
| `backend` | healthy |
| `worker-chat` | running — `[chat-worker] started queue=codexify:queue:chat concurrency=2` |
| `worker-document-embed` | running |
| `frontend` | reachable on `127.0.0.1:5173` |
| `/health` | 200 |
| `/health/llm` | 200, `provider=local`, `model=local-chat` |
| `/api/health/llm` | 200 |
| `/api/health/retrieval` | 200, `status: ready`, `proof_capable: true` |
| `/health/chat` | healthy — `worker.status=fresh`, `worker_heartbeat_detected=true`, queue progressing |

**The migration readback fails against the frozen source.**

| Item | Value |
| --- | --- |
| Frozen source head (canonical) | `a3115f64dda8` (mergepoint with parents `b7e2c4a1d903` and `c8e42a91d307`) |
| Alembic revision actually applied by the stock migrator | **`3a91d7c4e8b2`** |
| Rows in `alembic_version` after the stock migrator run | 1 |

**Root cause, established from the Compose definitions and confirmed inside the
image.**

1. `backend/migrations` is a **symlink** to `../guardian/db/migrations`.
2. The migrator service mounts **only** `./backend:/app/backend`. A Docker bind
   mount does not carry a symlink's target across the mount boundary, so inside
   the migrator container the symlink resolves into the **baked image's**
   `/app/guardian/db/migrations`.
3. The baked image `codexify-backend-runtime:latest`
   (`sha256:22d9f5f13e7d…`) contains **128** revision files and **none** of
   `a3115f64dda8`, `c8e42a91d307`, or `b7e2c4a1d903`:

   ```text
   $ docker run --rm --entrypoint sh \
       -v "$WT/backend:/app/backend" -w /app codexify-backend-runtime:latest \
       -c 'readlink /app/backend/migrations; ls /app/guardian/db/migrations/versions | wc -l;
            ls /app/guardian/db/migrations/versions/ | grep -E "a3115f64dda8|c8e42a91d307|b7e2c4a1d903"'
   ../guardian/db/migrations
   128
   (no match)
   ```

4. The migrator's own log confirms the path it used:
   `alembic.ini script_location=%(here)s/../guardian/db/migrations`.
5. The stock **runtime** Compose definition has the same property and no
   mitigation at all: `docker-compose.runtime.yml`'s `migrator` service
   declares **no volumes at all** and runs `codexify-runtime:local-beta` from
   the registry, so that path can only ever migrate to whatever head is baked
   into the published image.

**Consequence.** In a stock-launched supported stack, the schema is two real
migrations behind the application source being served: the campaign-provenance
lineage (`c8e42a91d307` / `b7e2c4a1d903`) and the coding-claim mergepoint
(`a3115f64dda8`) are absent from the database. The live Private Preview shows
the same shape — its database is at `3a91d7c4e8b2` — which corroborates that
this is the behaviour of the supported path, not of this invocation.

**Diagnostic comparison run (scratch override, not a fix).** Adding
`./guardian:/app/guardian` to the migrator in the scratch override — so the
symlink resolves to the frozen source tree — yields:

| Item | Stock path | Source-mounted comparison |
| --- | --- | --- |
| Migrator exit code | 0 | 0 |
| `alembic_version` | `3a91d7c4e8b2` | **`a3115f64dda8`** |
| Public tables | — | 138 |

The frozen revisions therefore apply cleanly. The defect is the migrator's
mount, not the migrations. **The stock supported path is nonetheless FAIL**, and
the source-mounted configuration is recorded here only as the isolating
experiment; it is not a supported configuration and is not proposed as a fix in
this receipt.

**Qualification consequence, stated plainly.** Gates C–H below were executed
against the **source-mounted comparison** stack, so that the application source
and the schema were both at the frozen revision. The findings therefore describe
the frozen application against the frozen schema, and they do **not** silently
absorb the Gate B defect.

### Harness artifact (not a product defect)

The first `model-prep` attempt failed with `[Errno 17] File exists:
'/models/bge-large-en-v1.5'`. This was a qualification-harness artifact: the
model directory was initially exposed through a symlink, which Docker left
dangling inside the container, so `Path.exists()` returned false for a path that
did exist. The harness was corrected to use a hard-linked real directory with a
relative symlink, and `model-prep` then exited 0. This is recorded so that it is
not mistaken for a runtime defect.

## 9. Chat acceptance and terminal outcome — **PASS**

Ordinary supported chat, `POST /api/chat/1/complete` with `model: "local-chat"`:

| Element | Evidence |
| --- | --- |
| Valid request acceptance | HTTP 200, `acceptance_status: accepted`, `acceptance_warnings: []`, `task_id: bad6989b-e85d-4648-891c-5974ff7aa1e5`, `turn_id: 13fbd03a-84df-4360-b4b1-0034952ca311`, `request_id: req_b095b0acce0b4eac9e6cda144a1b8e82` |
| Model selection | `policy_reason: requested_model`, `resolved_model: local-chat`, `attempted_model: local-chat`, `final_model: local-chat`, `fallback_triggered: false`, `fallback_reason: null`, inventory source `whooshd:/v1/models` |
| Worker execution | provider ledger entry `req_b095b0acce0b4eac9e6cda144a1b8e82`, `model: local-chat`, `status: completed`, `error_code: null`; worker log `[chat.inference.request.built` |
| Terminal outcome | `GET /api/chat/threads/1/tasks` → `state: terminal`, `event_type: task.completed`, `reason: durable_completion_recorded`, `completed_message_id: 3` |
| Deadline snapshot | `accepted_at` 20:05:04Z, `work_deadline_at` 20:17:04Z, `terminal_deadline_at` 20:18:04Z — recorded on the attempt row |
| No silent model substitution | `final_model == attempted_model == resolved_model == local-chat`; `fallback_triggered: false` |

The assistant reply produced was a real model completion (the local model
declined the exact-token instruction rather than fabricating it — the point of
the gate is that a *real* completion was produced by the *advertised* model).

## 10. Persistence and readback evidence — **PASS**

Durable state after the Gate D turn:

| Table | Observation |
| --- | --- |
| `chat_threads` | thread 1 present, `project_id 1`, `user_id local` |
| `chat_messages` | 2 rows for thread 1: user message id 1, **assistant** message id 3 |
| `chat_completion_attempts` | 1 row: `request_id req_b095b0acce0b4eac9e6cda144a1b8e82`, `backend_task_id bad6989b-…`, `thread_id 1`, `turn_id 13fbd03a-…`, `accepted_at 20:05:04Z`, `completed_message_id 3`, `terminal_event_type` NULL (the attempt row records the *completed* outcome via `completed_message_id`; `terminal_event_type` is constrained to `task.failed`/`task.cancelled` only) |
| `events_outbox` | `task.running`, `task.completed` and the completion payloads for the turn |

Request / attempt / task relationships are internally consistent: the attempt's
`request_id` equals the acceptance response's `request_id`, its
`backend_task_id` equals the `task_id`, its `turn_id` equals the acceptance
`turn_id`, and `completed_message_id` points at the persisted assistant row.

Readback through the supported API (`GET /api/chat/1/messages`) returns the
assistant message with its execution metadata intact — including
`model_selection.policy_reason = requested_model`, `fallback_triggered: false`,
and the provider inventory evidence.

## 11. Retrieval and provenance evidence — **PASS** (with a durability caveat)

Ingestion, retrieval, and generated-answer evidence were kept separate.

**Ingestion (supported path).** `POST /api/media/upload/document`
(`media` route, tier 0 in the supported profile) with disposable synthetic
content → HTTP 200, `document_id`, `media_asset_id`, `project_id: 1`,
`source_tag: uploaded`, `parsed_text` preserved verbatim. Durable persistence
verified by `GET /api/media/documents/{document_id}` (HTTP 200, content intact)
and by a `project_document_links` row (`project_id 1`, `is_enabled: true`).
Embedding ran in the `worker-document-embed` service against the local
`BAAI/bge-large-en-v1.5` model and the chunk was written to the Chroma
collection `codexify_vault_supported` with `namespace: project:1`,
`source: document`, and the correct `doc_id`.

**Retrieval + provenance (successful attempt).** A chat turn asked what the
ledger records and to name the source document. The generated answer quoted the
correct figure from the ingested file and named the source:

> The retry ledger of QUALMARK-RETRY-2B7D51 records exactly 73 photons.
> Source document: qual-compose-01-retry-QUALMARK-RETRY-2B7D51.txt

The durable assistant-message metadata carries the source identifiers and scope:

```json
"retrieval_executed": true,
"retrieval_absence_reason": null,
"retrieval_provenance": {
  "requested_source_mode": "project",
  "normalized_source_mode": "project",
  "source_hit_counts": { "project_documents": 1, "semantic_total": 0, "..." : 0 },
  "contributing_items": [
    { "role": "document",
      "filename": "qual-compose-01-retry-QUALMARK-RETRY-2B7D51.txt",
      "project_id": 1, "chunk_index": 0,
      "document_id": "d44cab71-b4bb-4741-aeb9-190b0e62ea31",
      "source_type": "uploaded",
      "retrieval_lane": "project_docs" }
  ]
},
"retrieval_suppression": { "items": [], "summary": { "total_suppressed": 0 } },
"completion_truth": { "accepted": true, "executed": true, "attempted": true,
                       "completed": true, "fallback_attempted": false }
```

**No unobserved provenance was claimed.** The answer cited exactly the one
document that was actually ingested, with the correct project scope
(`same_user_same_project`, `source_mode: project`), and `total_suppressed: 0`
confirms nothing was silently withheld.

### Recorded caveat 1 — document-embed worker kill leaves a document permanently stuck

On the **first** ingestion attempt the `worker-document-embed` container was
killed mid-job:

```text
20:11:42  [embedder] embedding model=/models/bge-large-en-v1.5
20:11:56  document_embed_writer_reaped pid=1190 exitcode=-9
20:11:56  [document-embed] embedded doc_id=<19-char id> chunks=<19-char id>
20:12:xx  guardian.core.chat_postgres_deadline.PostgresOperationTimeout:
          PostgreSQL maintenance deadline exceeded
20:12:52  [document-embed] worker started queue=codexify:queue:document-embed …
```

`exitcode=-9` is a SIGKILL — the writer subprocess was killed under host memory
pressure (the host was simultaneously running the 12B MLX model and other
workloads). The Chroma chunk was written, but the worker died before it could
commit `embedding_status = 'ready'` to `uploaded_documents`. After the
container restarted, the queue depth was 0 and the document was **not**
re-queued:

| Field | Value |
| --- | --- |
| `embedding_status` | `processing` (stuck, ~5 minutes later and indefinitely) |
| `embedding_completed_at` | NULL |

The retrieval layer then correctly refused to serve it —
`guardian/context/broker.py` requires `embedding_status == 'ready'` — so the
chat turn retrieved nothing (`rag-trace.documents: []`,
`retrieval-posture.status: empty`) and the model correctly answered that it had
no document access rather than inventing one.

This is a **real durability gap**: a worker kill during embedding leaves the
document permanently in `processing` with no recovery path observed in this
run. The product behaved correctly in refusing to serve a non-ready document;
the defect is the absence of recovery or terminal-failure marking.

### Recorded caveat 2 — operator retrieval surfaces do not reflect what was retrieved

In **both** the failing and the successful retrieval runs, the operator-facing
surfaces reported emptiness while the answer demonstrably used the document:

| Surface | Failing run | Successful run |
| --- | --- | --- |
| `GET /api/chat/debug/rag-trace/{thread}/latest` → `documents[]` | `[]` | `[]` |
| `GET /api/chat/debug/rag-trace/{thread}/latest` → `trace_available` | `false` (`trace_unavailable_reason: trace_source_unavailable`) | `false` |
| `GET /api/chat/debug/retrieval-posture/{thread}/latest` → `status` | `empty` | `empty` |
| assistant-message `retrieval_provenance.contributing_items` | — | 1 document |

The authoritative per-message provenance is correct, but the rag-trace and
retrieval-posture projections stayed empty even on the successful path. These
diagnostic surfaces cannot currently be used to verify retrieval.

### Reproduction check

A second, controlled ingestion was performed with a healthy worker to separate
"the supported path is broken" from "the worker was killed once". The second
document reached `embedding_status = 'ready'` within the same run, was
retrieved, and produced the attributed answer quoted above. **The supported
document-retrieval path works; the failure mode is a worker-kill durability
gap, not a systemic retrieval defect.**

## 12. Browser and event evidence — **PASS**

| Item | Value |
| --- | --- |
| Browser identity | Google Chrome **156.0.0.0** on macOS (`Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) … Chrome/156.0.0.0 Safari/537.36`) |
| Automation method | Chrome DevTools Protocol via the `chrome-devtools` MCP server (`list_pages`, `navigate_page`, `take_snapshot`, `click`, `fill`, `list_network_requests`, `evaluate_script`) |
| Target | `http://127.0.0.1:5173/` (the qualification stack's own frontend, Vite dev server, `VITE_PROXY_TARGET=http://backend:8888`) |
| Page identity | document title `Codexify`; routes `/chat`, `/chat/5`, `/chat/2` |

| Requirement | Evidence |
| --- | --- |
| Thread creation and projection | A message typed in the browser composer created **thread 5**; the URL became `/chat/5` and the thread appeared in the sidebar and thread list. Durable confirmation: `chat_threads` row id 5 with the same title. |
| Message display | The UI rendered the user message (`QUAL-COMPOSE-01 browser gate: reply with exactly the token ACK-BROWSER-41FF6152.`, 03:31 PM) and the assistant reply (`ACK-BROWSER-41FF6152`, 03:32 PM), matching `chat_messages` exactly. |
| Event delivery | The live event stream was open in the browser: `GET /api/events?last_id=20` → 200. Task reconciliation used `GET /api/chat/threads/5/tasks?limit=100&offset=0` → 200, plus `GET /api/chat/5/messages?limit=100&offset=0` → 200, `GET /api/health/llm` → 200, `GET /api/llm/catalog` → 200. |
| Terminal-state reconciliation | The in-UI status region read `Ready` / `Completed` / "The model is loaded and ready for requests." after the reply landed, and the `Send` control returned to its disabled state. |
| Refresh / readback consistency | After a full page reload of `/chat/5`, both messages were re-rendered from the backend with the same text and timestamps — the UI state is not merely client-held. |
| No phantom completion after a failed request | Navigating to `/chat/2` (the Gate C rejected turn) rendered **only** the user message plus the notice **"1 earlier response task failed."** — no assistant bubble, no fabricated reply. This agrees with the durable state (`completed_message_id = NULL`, `terminal_event_type = task.failed`). |
| UI agrees with durable backend state | For every thread opened in the browser, the rendered message set matched the `chat_messages` rows for that thread exactly. |

The browser qualification was **not** substituted with API-only testing: the
thread was created, the turn was submitted, the reply was displayed, the
failure was displayed, and the refresh readback was performed through the real
frontend.

## 13. Restart recovery evidence — **PASS**

**Restarted (qualification-owned only):** `backend`, `worker-chat`,
`worker-document-embed` — via `docker compose … restart`.
**Deliberately not restarted**, so qualification state was preserved and the
restart was attributable to the restarted services alone: `db`, `redis`,
`neo4j`, `frontend`. The live Private Preview was not touched.

| Check | Result |
| --- | --- |
| Service recovery | `/health/chat` → `ok: true`, `worker.status: fresh`, `heartbeat_age_seconds: 0.959`, `worker_heartbeat_detected: true`, `queue.status: progressing`, `threads: 5`, `messages: 9` |
| Durable state preserved | see the before/after table below |
| Original thread and message readback | threads 1–5 re-read through the supported API with the same message sets |
| Ordinary chat still works | a new thread 6 was created and completed after the restart; provider ledger entry `req_cd9d124602724bf1b329837ac87571f8`, `model: local-chat`, `status: completed`; task `0894ef35-…` → `state: terminal`, `event_type: task.completed`, `completed_message_id: 11` |
| Worker / event state coherent | the new attempt recorded a fresh deadline snapshot and a terminal event; the previously failed attempt remained failed |
| No lost or duplicated terminal outcomes | see the before/after table below |

Durable-state comparison across the restart (count and content fingerprints
taken from the database before and after):

| Measure | Before | After | Verdict |
| --- | --- | --- | --- |
| `chat_threads` | 5 | 5 | match |
| `chat_messages` | 9 | 9 | match |
| assistant messages | 4 | 4 | match |
| `chat_completion_attempts` | 5 | 5 | match |
| attempts with a terminal event | 1 | 1 | match |
| attempts with a completed message | 4 | 4 | match |
| `uploaded_documents` | 2 | 2 | match |
| documents `ready` | 1 | 1 | match |
| message content fingerprint (`id:role:md5(content)` for every row) | — | — | **match** |
| attempt fingerprint (`request_id:terminal_event_type:completed_message_id`) | — | — | **match** |

Per-thread readback after the restart:

| Thread | Messages | Roles |
| --- | --- | --- |
| 1 | 2 | user, assistant |
| 2 | 1 | user *(failed turn — still no assistant message; the failure did not "heal" into a completion)* |
| 3 | 2 | user, assistant |
| 4 | 2 | user, assistant |
| 5 | 2 | user, assistant |

## 14. Queue / worker / cancellation / deadline evidence

Live runtime evidence from the qualification stack:

| Property | Evidence |
| --- | --- |
| Queue/worker lifecycle | `[chat-worker] started queue=codexify:queue:chat concurrency=2`; `/health/chat` reports `worker.status: fresh`, `queue.depth: 0`, `queue.status: progressing`, `completion_service.worker_heartbeat_detected: true`, `enqueue_test_ok: true` |
| Cancellation and terminal state | the rejected turn produced a **terminal** `task.failed` with `completed_message_id = NULL`, and the attempt row's check constraint `ck_chat_attempt_orphan_outcome` was not violated; the browser rendered the failure rather than a phantom completion |
| Deadline handling | every attempt carried a `deadline_snapshot` (`accepted_at`, `work_deadline_at` = accepted + 12 min, `terminal_deadline_at` = accepted + 13 min), and `task_id`/`turn_id`/`request_id` were carried through to the durable attempt row |
| Migration health and readback | see [Gate B](#gate-b--startup-and-migrations-fail-on-the-stock-supported-path) — `alembic_version` read back directly from the qualification database |
| Account / scope isolation | the retrieved document's `project_id` (1) matched the thread's `project_id` (1) and the retrieval boundary (`same_user_same_project`); `retrieval_suppression.summary.total_suppressed: 0` |
| Supported document retrieval | see [§11](#11-retrieval-and-provenance-evidence--pass-with-a-durability-caveat) |
| Health and operator diagnostics | `/health`, `/health/chat`, `/health/llm`, `/api/health/llm`, `/api/health/retrieval` all 200; the browser's `System status: Healthy` indicator and `GET /api/events` stream confirmed delivery |

## 15. Tests and commands actually executed

### Live-stack commands (abbreviated; full text in the scratch harness)

```bash
# isolated invocation (never the repo's smoke launcher)
cd $WT
COMPOSE_PROJECT_NAME=codexify_qual \
CODEXIFY_BACKEND_PORT=8889 CODEXIFY_LOCAL_RUNTIME_PORT=8002 CODEXIFY_FRONTEND_PORT=5173 \
CODEXIFY_POSTGRES_PORT=5433 CODEXIFY_NEO4J_HTTP_PORT=7474 CODEXIFY_NEO4J_BOLT_PORT=7687 \
docker compose -f docker-compose.yml -f docker-compose.whooshd-smoke.yml -f "$OVERRIDE" \
  up -d --force-recreate db redis neo4j graph-init model-prep migrator \
  backend worker-chat worker-document-embed frontend

# health
curl -s http://127.0.0.1:8889/health
curl -s http://127.0.0.1:8889/health/chat
curl -s http://127.0.0.1:8889/health/llm
curl -s http://127.0.0.1:8889/api/health/llm
curl -s http://127.0.0.1:8889/api/health/retrieval

# migration readback
docker exec codexify_qual-db-1 psql -U codexify -d Codexify -tAc \
  "select version_num from alembic_version"

# provider-side evidence (the provider's own request ledger)
curl -s http://127.0.0.1:8000/runtime/requests
curl -s http://127.0.0.1:8000/v1/models
```

### Repository test selectors (Gate H)

Two runs of the same 31-selector set were executed against the frozen
worktree, plus a third run of the 21 selectors that were skipped for want of
native database/redis.

**Run 1 — as the qualification harness presented itself** (the worktree
contains a copy of the operator `.env`):

```
345 passed, 6 failed, 21 skipped  (exit 1)
```

**Run 2 — same selectors, with the supported-profile selection aligned to the
hermetic core contract** (`CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp`,
`LLM_PROVIDER=local`, `ALLOW_CLOUD_PROVIDERS=false`,
`CODEXIFY_LOCAL_ONLY_MODE=true`, `CODEXIFY_EGRESS_ALLOWLIST=`):

```
348 passed, 3 failed, 21 skipped  (exit 1)
```

**Run 3 — the 21 previously-skipped selectors, given dedicated disposable
storage** (a dedicated `postgres:15` container and a dedicated
`redis:7-alpine` container, both `--rm`, neither the qualification stack's nor
the Preview's; `TEST_DATABASE_URL` and `TEST_TERMINAL_LOCK_REDIS_URL` pointing
at database `/15` as the selector requires):

```
32 passed, 0 skipped  (exit 0)
```

Selector set (31 paths):

```
tests/queue/
tests/workers/test_chat_worker_lifecycle_events.py
tests/workers/test_chat_worker_explicit_model_authority.py
tests/workers/test_chat_worker_queued_cancellation.py
tests/workers/test_chat_worker_queue_deadline.py
tests/workers/test_chat_worker_rescue_deadline.py
tests/workers/test_chat_worker_terminal_authority.py
tests/workers/test_chat_worker_terminal_cleanup.py
tests/workers/test_chat_worker_heartbeat_activity.py
tests/workers/test_chat_worker_first_token_timing.py
tests/workers/test_chat_worker_latest_turn_integrity.py
tests/workers/test_document_embed_worker.py
tests/core/test_chat_completion_enqueue_service.py
tests/core/test_completion_terminal_integrity.py
tests/core/test_chat_nonstream_accepted_deadline.py
tests/core/test_chat_stream_accepted_deadline.py
tests/core/test_context_deadline_propagation.py
tests/core/test_retrieval_document_chunk_provenance.py
tests/core/test_retrieval_user_isolation_and_widening.py
tests/migration/test_alembic_revision_uniqueness.py
tests/migration/test_campaign_provenance_coding_claim_head_merge.py
tests/migration/test_guardian_coding_claim_schema_merge.py
tests/migration/test_read_state_main_head_merge.py
tests/routes/test_chat_account_scope.py
tests/routes/test_documents_account_scope.py
tests/routes/test_health_endpoints.py
tests/routes/test_health_routes.py
tests/core/test_executor_health.py
tests/test_document_rag_retrieval_gate.py
tests/test_retrieval_context_prompt.py
```

Plus the skipped set, executed separately in Run 3:

```
tests/queue/test_terminal_turn_lock_cleanup.py
tests/migration/test_guardian_coding_claim_schema_merge.py
tests/migration/test_read_state_main_head_merge.py
```

**Baseline harness.** `scripts/validate_core_loops.sh` was executed with the
worktree virtualenv on `PATH`: see [§15.1](#151-baseline-harness-result).

### Document validation

```
python scripts/validate_docs.py            → exit 0
git diff --check                          → clean
python scripts/knowledge_graph/validate_and_generate_dlg.py validate
                                          → exit 0, 0 errors, 6 pre-existing warnings
```

## 15.1 Baseline harness result

`scripts/validate_core_loops.sh` is the repository's own deterministic core-loop
harness. Its six selectors (`rag`, `migration`, `doc-upload`, `image-gallery`,
`image-gen`, `doc-gen`) were executed as part of Gate H.

All six selectors passed:

```
[2026-11-02T20:50:31Z] Starting MVP core loop harness
[2026-11-02T20:51:04Z] PASS rag: tests/integration/test_rag_integration_loop.py::test_rag_integration_memory_loop
[2026-11-02T20:51:25Z] PASS migration: tests/routes/test_migration_routes.py::test_migration_route_executes_real_ingest_and_catches_up_embeddings
[2026-11-02T20:51:35Z] PASS doc-upload: tests/routes/test_media_routes.py::TestUploadDedupeAndResolve::test_upload_document_enqueues_embedding_with_asset_metadata
[2026-11-02T20:51:42Z] PASS image-gallery: tests/routes/test_media_routes.py::TestUploadDedupeAndResolve::test_list_images_generated_tag_returns_generated
[2026-11-02T20:52:01Z] PASS image-gen: tests/routes/test_media_routes.py::TestImageGeneration::test_generate_image_success
[2026-11-02T20:52:15Z] PASS doc-gen: guardian/tests/test_document_gen_persist_and_link.py::test_document_generate_persists_and_links
[2026-11-02T20:52:15Z] PASS: core loop harness completed with 6 passing selector(s)
```

Exit code `0`.

## 16. PASS / FAIL / INCOMPLETE for each gate

| Gate | Disposition | Basis |
| --- | --- | --- |
| **A** Supported configuration | **PASS** | all eight contract keys verified in the resolved configuration; no cloud credential in any qualification container; provider route `http://host.docker.internal:8000/v1` confirmed |
| **B** Startup and migrations | **FAIL** | services healthy, migrator exit 0 — but the applied Alembic head is `3a91d7c4e8b2`, not the frozen source head `a3115f64dda8`; cause isolated to the migrator's bind mount (§8) |
| **C** Explicit-model rejection | **PASS** | durable `local_model_unavailable` rejection naming the absent model; `attempted/executed/fallback_attempted` all false; provider ledger contains no request for the rejected turn; no assistant message persisted (§7) |
| **D** Ordinary chat and durable state | **PASS** | accepted → model selected → worker executed → `task.completed` → assistant message persisted and read back; no substitution (§9, §10) |
| **E** Retrieval and provenance | **PASS** | ingest → embed → retrieve → attributed answer with `project_documents: 1` and the contributing document's identifiers; no unobserved provenance; two caveats recorded (§11) |
| **F** Browser and event coherence | **PASS** | real Chrome against the qualification frontend: thread created, messages displayed, event stream open, terminal state reconciled, refresh readback consistent, failed turn shows a failure and no phantom completion (§12) |
| **G** Restart recovery | **PASS** | services recovered; all durable counts and content fingerprints identical across the restart; new chat completed afterwards; the failed attempt stayed failed (§13) |
| **H** Other supported baseline gates | **PASS** with **3 selectors INCOMPLETE** | 348 selectors passed in the aligned run; all 21 originally-skipped selectors were then executed and passed (32 passed) with dedicated disposable storage; the only unresolved items are 3 `[trio]`-parametrised tests that cannot execute because `trio` is not installed in this environment (§15, §17) |

## 17. Failed and unexecuted requirements

**Failed**

1. **Gate B — the stock supported migrator applies the baked image's Alembic
   head, not the frozen source head.** `alembic_version = 3a91d7c4e8b2` where
   the frozen source head is `a3115f64dda8`. The campaign-provenance lineage
   and the coding-claim mergepoint are absent from the qualified schema. Root
   cause: `backend/migrations` is a symlink to `../guardian/db/migrations`, and
   the migrator mounts only `./backend:/app/backend`, so the symlink resolves
   into the baked image. `docker-compose.runtime.yml`'s migrator has no
   volumes at all and is worse.

**Not a failure, but recorded as an environment artifact**

2. Three health-route selector failures in the as-run environment were caused
   by the operator `.env` present in the qualification worktree: it pins
   `CODEXIFY_SUPPORTED_PROFILE=v1-friends-family-web` (whose blessed contract
   expects the deepseek/cloud configuration) while the hermetic test settings
   resolve `LLM_PROVIDER=local`, producing
   `supported profile requires blessed local gateway contract: LLM_PROVIDER expected 'deepseek' but found 'local' …`.
   With the profile aligned to the hermetic contract, all 19 tests in those two
   files pass. This is a qualification-harness artifact; it is recorded rather
   than hidden, and it means the same failure would appear for any test run in
   a checkout that carries that `.env`.

**Unexecuted / INCOMPLETE**

3. **Three `[trio]`-parametrised selectors could not execute.**
   `tests/test_document_rag_retrieval_gate.py::TestThreadDocumentsEmbeddingStatus::test_thread_documents_includes_embedding_status[trio]`,
   `…::test_thread_documents_surfaces_pending_status[trio]`, and
   `…::test_thread_documents_surfaces_failed_with_error[trio]` fail with
   `ModuleNotFoundError: No module named 'trio'` (`KeyError: 'trio'` in the
   anyio backend). The optional `trio` dependency is not installed in this
   environment (`pip show trio` → not found). The other ten tests in the same
   file pass, including the asyncio-parametrised forms of these three
   behaviours. **These three are recorded as INCOMPLETE and are not counted as
   passes.**

**Explicitly outside this qualification** (unchanged boundaries, per the task's
exclusions and ADR-069): delegated Pi/Codex worker-to-adapter `reasoning_effort`;
Coding Loop release readiness; Private Preview; public ingress; cross-node
messaging; hosted rooms; unrestricted tools/agents; unsupported connectors;
complete account export/restore; every historical import format; browsers
other than the one tested; Saved Widget lifecycle completion.

**Additional coverage not exercised in this run** (stated so the receipt is not
read as broader than it is): cross-browser coverage; a full-stack restart that
also cycles `db`/`redis`/`neo4j` (they were deliberately left running to
preserve qualification state); the `worker-coding`, `worker-voice`,
`worker-account-import`, `worker-chat-embed`, and `e2e` services (out of the
supported profile's service set, and two of them carry the operator `.env`'s
cloud keys).

## 18. Remaining blockers

| # | Blocker | Nature |
| --- | --- | --- |
| B1 | The supported Compose migrator cannot reach the source tree's migrations, so a stock-launched stack runs a schema two revisions behind its own application source | product defect in the supported path; **not remediated here** |
| B2 | A killed `worker-document-embed` leaves the affected document permanently in `embedding_status = 'processing'` with no observed recovery, and the document is then correctly but uselessly withheld from retrieval | durability gap in the document-embed failure path |
| B3 | The rag-trace and retrieval-posture operator surfaces report empty even when retrieval demonstrably succeeded; only per-message `retrieval_provenance` carries the truth | diagnostics-surface gap |
| B4 | Three `[trio]` selectors cannot run in this environment | environment capability gap |
| B5 | The host was memory-constrained during the run (the document-embed writer was SIGKILLed); the root of B2 is host contention plus the absence of worker recovery | environment |

## 19. Cleanup results

All evidence was captured before removal. Ownership was verified by project
label and against the preflight resource inventory.

**Resources removed (qualification-owned only, all labelled
`com.docker.compose.project=codexify_qual`):**

| Kind | Resources |
| --- | --- |
| Containers (10) | `codexify_qual-backend-1`, `-db-1`, `-frontend-1`, `-graph-init-1`, `-migrator-1`, `-model-prep-1`, `-neo4j-1`, `-redis-1`, `-worker-chat-1`, `-worker-document-embed-1` |
| Volumes (6) | `codexify_qual_pg_data`, `_neo4j_data`, `_hf_cache`, `_corepack_cache`, `_frontend_pnpm_store`, `_codexify_cli_home` |
| Network (1) | `codexify_qual_default` |

Command used (project-scoped, with `--remove-orphans`; no global Docker
operation of any kind):

```bash
COMPOSE_PROJECT_NAME=codexify_qual docker compose \
  -f docker-compose.yml -f docker-compose.whooshd-smoke.yml -f "$OVERRIDE" \
  down -v --remove-orphans
```

**Post-cleanup verification**

| Check | Result |
| --- | --- |
| Qualification containers remaining | 0 |
| Qualification volumes remaining | 0 |
| Qualification networks remaining | 0 |
| Host Whoosh'd provider | still running — `GET http://127.0.0.1:8000/health` → HTTP 200 (never stopped) |
| Global Docker prune / system cleanup / shared-volume cleanup | never executed |

**Private Preview inventory comparison (preflight vs. post-cleanup)**

| Measure | Preflight | Post-cleanup | Verdict |
| --- | --- | --- | --- |
| Container count | 18 | 18 | identical |
| Container name set | 18 names | 18 names | **same set** — none added, none removed |
| Container images | as listed in §4 | unchanged for all 18 | identical |
| `alembic_version` | `3a91d7c4e8b2` | `3a91d7c4e8b2` | identical |
| Public table count | 138 | 138 | identical |
| Ingress `127.0.0.1:8081` | — | HTTP 200 | serving |
| Long-running services (`backend`, `db`, `redis`, `neo4j`, `frontend`, `private-preview-origin`, and all seven `worker-*`) | up | up, same uptimes | unchanged |

**One difference observed and reported rather than suppressed.** The Preview's
five *one-shot* services (`migrator`, `model-prep`, `graph-init`, `e2e`,
`private-preview-auth-posture`) showed **new exit timestamps** at the end of
the run compared with the preflight snapshot — i.e. they were re-executed
during the qualification window by another actor. The observable facts:

- Their exit status stayed `Exited (0)`; no Preview container was added or
  removed; the long-running services kept their uptimes.
- The Preview database revision and table count are byte-identical to the
  preflight snapshot.
- Every Compose invocation issued during this qualification ran with
  `COMPOSE_PROJECT_NAME=codexify_qual` and the frozen worktree's Compose
  files, and none of them referenced the `codexify_private_preview` project.
  The qualification's own `down -v` removed only `codexify_qual_*` resources,
  as verified by label and by the removal log above.

The qualification therefore **did not modify the Private Preview**; the
one-shot re-runs are attributable to another actor operating the Preview
project concurrently.

**Host-level observation, reported rather than acted on.** Six unlabelled
`postgres:15` containers named `codexify_account_observability_norm_*` were
found running on the host, created at 20:45:53–20:46:40Z. They were **not**
produced by this qualification: the container-naming helper lives only in
`tests/migration/test_account_observability_compatibility_normalization.py`,
which was never collected by any selector run recorded in §15 (the aligned run's
collected-file list contains no reference to it). They are the known leak
pattern of that fixture, which starts a disposable Postgres without `--rm` and
removes it only on a clean teardown. Because their ownership could not be
established as this qualification's, they were **left running** rather than
removed — deleting another executor's in-flight test resources is not
qualification cleanup. The qualification's own disposable test containers
(`codexify_qual_gateh_pg`, `codexify_qual_gateh_redis`) were removed by their
own teardown trap.

## 20. Release HOLD conclusion

**Release posture remains HOLD.**

This qualification establishes that at the frozen revision
`41ff615293ecf6b7bd1b7f21515cd197f19f0848` the supported local Compose runtime
**does** work for ordinary chat with durable state, for explicit-model rejection
with provider-confirmed non-execution, for document retrieval with source
attribution, for browser-driven event coherence, and for restart recovery. It
**also** establishes that the supported Compose migrator does not apply the
frozen source's schema, so a stock-launched stack serves the frozen application
against a schema that is two migrations behind it.

A green result was not the objective and was not manufactured. Gate B is
recorded as FAIL, two durability/diagnostics caveats are recorded against a
passing gate, three selectors are recorded as INCOMPLETE, and the harness
artifacts (the `model-prep` symlink failure and the `.env` profile mismatch)
are labelled as such rather than being presented as product behaviour.

**No remediation was attempted.** Every finding above is left exactly as
observed, for a separate, atomic Task Spec. This receipt changes no
application source, no supported profile, no architecture document, no CI
definition, and no release-support classification. It does not authorize
promotion, deployment, or a merge.

### Next proof needed

1. A stock-path Compose run in which the qualification database's
   `alembic_version` equals the frozen source head — i.e. Gate B re-run after
   the migrator's migration source is settled.
2. A re-run of the document-embed failure path under a kill injected at a
   controlled point, to characterise whether `processing` documents are ever
   recovered or terminally failed.
3. A re-run of Gate E with the rag-trace and retrieval-posture surfaces
   populated, so that the operator-facing diagnostics can be qualified rather
   than only the per-message provenance.

---

### Reproduction notes

- **Scratch artifacts** (untracked, outside the repository's source tree):
  `/Volumes/Dev_SSD/Codexify-main/.scratch/qual-compose-41ff6152/` and
  `/Volumes/Dev_SSD/Codexify-main/.scratch/qual-preflight/`. These hold the
  override file, the probe scripts, and the raw evidence logs referenced above.
- **No secrets** are recorded in this receipt. The Guardian API key was read
  from the worktree `.env` at run time and never printed; provider payloads and
  container logs were taken in their already-redacted form.
- **The live Private Preview was never modified.** No global Docker cleanup,
  prune, volume removal, or cross-project container removal was executed at any
  point.
