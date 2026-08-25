# Tester Chroma compatibility recovery proof

## Result

**BLOCKED — the proven incompatible active derived index was preserved and
retired under ADR-067, but the one permitted canonical backend recovery start
exited before application readiness.** The historical Chroma Rust panic is
absent from that recovery attempt. The available application log safety layer
redacts the new exception detail, so this receipt does not infer a cause or
authorize a second start, source change, dependency change, or restoration.

## Scope and authority

- **Branch / source:** `codex/define-github-watchdog-control-plane` at
  `9f263fa2fdb9fa2efa884d23be22022377e6d6ee` (`Restore tester backend
  startup`). Both `9f263fa2...` and the model-authority prerequisite
  `45736720aeb7cfa210aeb69b966795a83897fbe5` were present and ancestors of
  `HEAD`.
- **Governing ADR:** ADR-067 is Accepted. It authorizes
  preserve → retire active derived index → fresh supported-runtime
  initialization. ADR-074 remains unchanged.
- **Authority boundary:** Postgres remains canonical application state;
  Chroma is derived retrieval/index state.
- **Provider posture observed read-only:** `LLM_PROVIDER=local`,
  `LOCAL_CHAT_MODEL=gemma-4-12b-it-qat-4bit`,
  `ALLOW_CLOUD_PROVIDERS=true`, and `CODEXIFY_LOCAL_ONLY_MODE=false`.
  `.env.tester` remained ignored and was not edited or staged.

No source, Compose, Dockerfile, Chroma implementation, dependency,
migration, provider, Whoosh'd, DeepSeek, Watchdog, Redis configuration, or
Postgres schema change was made.

## Active-path and runtime identity

The current canonical Tester Compose assembly (project `codexify_tester`,
service `backend`) and the pre-recovery backend container converged on one
active path:

| Property | Observed value |
| --- | --- |
| Host source | `/Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main/.chroma` |
| Container destination | `/app/.chroma` |
| Mount semantics | Compose bind mount, read-write |
| Application resolution | `CODEXIFY_CHROMA_PATH=./.chroma` resolves to `/app/.chroma` under `/app` |
| Backend image | `codexify-backend-runtime:latest` (`sha256:af108ff65ba1d1fde1417ac776be41eacd106aaf77d2800b7c6e40d2359b6288`, arm64) |
| Runtime | Python 3.11.14; `chromadb` 1.0.15; SQLite 3.46.1 |
| Source dependency | `backend/requirements.txt` pins `chromadb==1.0.15` |

The active path is distinct from the historical preservation root
`/Volumes/Dev_SSD/Codexify-preservation/chroma/...`; it neither equals nor
contains a preservation artifact.

Before quiescence, the canonical current backend mounted the active path.
Older Tester embedding-worker containers were also found, but they mounted a
different historical checkout under `/Volumes/Dev_SSD/Codexify-main`, not the
active path above. The documented `make tester-down` lifecycle stopped the
whole Tester stack (without `-v`) rather than stopping individual containers.
Afterward, no container mounted the active path. `lsof` showed only Docker
Desktop holding the directory as read-only (`r`); therefore
`ACTIVE_CHROMA_WRITERS=0`.

## Current active-store diagnosis before retirement

The active store was inspected only with filesystem metadata and read-only
SQLite; no `PersistentClient` opened it.

| Check | Result |
| --- | --- |
| Files / aggregate bytes | 5 / 1,083,556 |
| Deterministic relative manifest digest | `2205e32c5fe82b2ee256028a72745a8817c70956b278103ee1381f95105b2176` |
| Symlinks | 0 |
| `PRAGMA quick_check` / `integrity_check` | `ok` / `ok` |
| SQLite schema shape | 21 tables, 20 indexes, including `embedding_metadata_array` |
| Migration generations | `sysdb: 1..10`; `metadb: 1..6`; `embeddings_queue: 1..2` |
| Safe bounded counts | collections 1; segments 2; embeddings 2; `embedding_metadata_array` 0; databases 1; tenants 1 |

The existing backend failed against this active path at Chroma construction
with the bounded signature `range start index 10 out of range for slice of
length 9`.

## Current-runtime empty-store control

An isolated temporary directory was initialized with `PersistentClient` and
`get_or_create_collection` in the exact current backend image. It did not
mount or copy the active or historical store and was removed with its
ephemeral container.

| Check | Result |
| --- | --- |
| Persistent client / collection initialization | success |
| SQLite integrity | `ok` |
| Table count | 20 |
| Embeddings | 0 |
| Migration generations | `sysdb: 1..9`; `metadb: 1..5`; `embeddings_queue: 1..2` |

**Compatibility classification before destructive action:**
`PERSISTED_STORE_COMPATIBILITY_BOUNDARY`.

The current supported runtime succeeds against an empty store; the active
store was structurally one sysdb and one metadb generation ahead and produced
the historical Rust/SQLite panic. This met the ADR-067 retirement gate.

## Postgres baseline and preservation

Current source Alembic has one head, `6e9f0a1b2c3`, and the live Tester
database reported the same revision before retirement. Bounded pre-retirement
counts were: users 28; projects 4; chat threads 5,136; chat messages 113,326;
uploaded documents 0; generated documents 0; hosted rooms 1; repository
bindings 0. The post-startup-attempt counts and revision were identical.

A new external preservation was created before retirement:

- path:
  `/Volumes/Dev_SSD/Codexify-preservation/chroma/20260824T182108Z-9f263fa2fdb9/canonical-chroma`
- relative manifest digest:
  `2205e32c5fe82b2ee256028a72745a8817c70956b278103ee1381f95105b2176`
- preservation comparison: relative paths, types, sizes, and SHA-256 content
  entries matched the diagnosed active store exactly
- preservation SQLite `quick_check` / `integrity_check`: `ok` / `ok`
- protection: recursive write permission removed; preservation root mode is
  `dr-xr-xr-x`

No individual data-file hash, document, embedding, metadata, user identifier,
or message identifier is recorded here.

Immediately before retirement, ADR status, classification, active manifest,
preservation equality/integrity, zero writers, Postgres availability and
baseline, exact non-symlink path identity, and a clean tracked source tree all
passed.

## Retirement and single recovery start

Exactly one guarded removal targeted only:

`/Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main/.chroma`

The path was absent immediately afterward. No parent path, preservation path,
Docker volume, Postgres data, or other Chroma path was deleted.

`ACTIVE_CHROMA_INDEX_RETIRED=PASS`

The documented Tester lifecycle started only the required dependencies, then
the canonical Compose backend service exactly once. `worker-warmup` was kept
stopped so the startup warmup task could not invoke a model. `worker-chat` was
not started because the backend did not become healthy.

The recovery backend advanced through database verification, default seeding,
route assembly, and embedding-model initialization. It did **not** emit the
historical panic string. It then exited once with code 3 before either
`[startup] Guardian API ready` or normal application-startup completion.
The available error records were safety-redacted; no reliable exception name
or message remains in the bounded logs.

The normal backend runtime, not a manual Chroma command, created a fresh
partial active path. Read-only inspection found one 16,384-byte
`chroma.sqlite3` with `acquire_write` and `migrations` tables but no migration
rows and none of the current-runtime control's full 20-table schema. Its
`quick_check` and `integrity_check` both return `ok`. It is not
byte-identical to the retired preservation.

`RETIRED_HISTORICAL_RECORDS_COPIED=0`: no operation copied a record, HNSW
file, vector file, or other data from the preservation. The partial fresh
database did not reach a queryable embeddings table, so no record count could
be read from it.

## Final status and boundaries

- **Final classification:** `BLOCKED_AFTER_ADR067_RETIREMENT`.
- **New first blocker:** an unclassified, safety-redacted backend startup
  failure after the historical Chroma panic point, leaving a compatible-looking
  but incomplete fresh SQLite initialization. One recovery startup was used;
  no retry is authorized by this task.
- **Backend health:** not reachable; backend is exited (3), not restarting.
- **Worker-chat / Redis / heartbeat / `/health/chat`:** `worker-chat` was not
  started; Redis remains healthy; no worker heartbeat or chat-health claim is
  made.
- **Historical panic:** absent from the one post-retirement backend log.
- **Preservation:** present and read-only at the path above.
- **No inference:** no ordinary chat completion was submitted, and the
  warmup worker remained stopped; no model/provider inference was performed.
- **No Watchdog activity:** no Watchdog attempt, snapshot, task, model call,
  or publication was created.
- **Release posture:** unchanged. This is not a release-support or current-tip
  runtime qualification claim.

The next task must diagnose the new first backend startup failure from a
separately authorized bounded diagnostic surface. It must not automatically
restore the historical Chroma preservation or recreate the fresh path.
