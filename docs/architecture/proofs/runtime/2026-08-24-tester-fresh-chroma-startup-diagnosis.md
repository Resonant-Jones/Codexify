# Tester fresh Chroma startup diagnosis

## Result

**BLOCKED — `INSUFFICIENT_DIAGNOSTIC_EVIDENCE`; causality is `UNRESOLVED`.**

The exited canonical backend did not expose a usable causal exception: its
available log surface reduced the two post-embedder errors to redacted event
summaries. The one permitted isolated normal-entrypoint reproduction, run
against a disposable copy of the preserved partial state, reached Uvicorn and
exited cleanly when stopped. It therefore did not reproduce the canonical exit
code `3` or establish that Chroma, SQLite, permissions, the partial state, or
Codexify initialization caused it.

No repair is made or implied by this record. A diagnostic result is not a
backend-health or release-readiness result.

## Scope and governing state

- **Recovery prerequisite:** `3fe63b4232f12fb305a50ac789311341d6587a9a`
  (`Recover tester Chroma runtime`), confirmed in `HEAD` ancestry.
- **Startup prerequisite:** `9f263fa2fdb9fa2efa884d23be22022377e6d6ee`
  (`Restore tester backend startup`), confirmed in `HEAD` ancestry.
- **Branch:** `codex/diagnose-tester-fresh-chroma-failure`.
- **Governing ADRs:** ADR-067 and ADR-074. Postgres remains the canonical
  application authority; Chroma remains derived retrieval state.
- **ADR impact:** none. This is diagnosis only; it establishes no new runtime
  contract.

The required Tester posture was inspected read-only and remained:

```text
LLM_PROVIDER=local
LOCAL_CHAT_MODEL=gemma-4-12b-it-qat-4bit
ALLOW_CLOUD_PROVIDERS=true
CODEXIFY_LOCAL_ONLY_MODE=false
```

`.env.tester` remained ignored and was not edited. No source, dependency,
Compose, configuration, migration, or test file was changed.

## Canonical partial-state identity and preservation

The failed backend container was owned by Compose project `codexify_tester`,
service `backend`. Its mount and current application configuration resolved
the forensic state to:

| Property | Value |
| --- | --- |
| Canonical host path | `/Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main/.chroma` |
| Container path | `/app/.chroma` |
| Mount mode | read-write at the original failed start; never remounted for this diagnosis |
| Creation timestamp | `2026-08-24T14:23:41Z` |
| Modification timestamp | `2026-08-24T14:23:50Z` |
| Ownership / mode | UID `501`, GID `20`; directory `drwxrwxrwx` |
| Files | one: `chroma.sqlite3` |
| Aggregate bytes | `16,384` |
| `chroma.sqlite3` SHA-256 | `163ed995f24a76a53571f16c9f1e835271264a11136a25f5df854316ce14c58f` |
| Deterministic source manifest SHA-256 | `e3c08c0fc8c57fff5dabefbde312d6d21ffcf526a4f3d54a664b09eb1f14fe71` |

Before any reproduction, a byte-preserving copy was made at:

`/Volumes/Dev_SSD/Codexify-preservation/chroma/20260824T185433Z-3fe63b42/fresh-partial-after-failed-init`

Its relative path, file type, byte size, and SHA-256 manifest matched the
canonical source exactly (`e3c08c0fc8c57fff5dabefbde312d6d21ffcf526a4f3d54a664b09eb1f14fe71`).
The preservation was then made read-only (`dr-xr-xr-x`). It was rechecked after
the reproduction and remained byte-identical to the canonical partial state.

The earlier, incompatible historical preservation remained present, read-only,
and untouched at:

`/Volumes/Dev_SSD/Codexify-preservation/chroma/20260824T182108Z-9f263fa2fdb9/canonical-chroma`

Neither preservation nor the canonical partial state was opened through Chroma,
renamed, repaired, reset, deleted, or restored.

## Read-only partial-state inspection

Only the preservation copy was opened with SQLite in query-only mode. Its
structural evidence was:

| Check | Observation |
| --- | --- |
| `chroma.sqlite3` | present; `16,384` bytes |
| `PRAGMA quick_check` / `integrity_check` | `ok` / `ok` |
| `PRAGMA journal_mode` | `delete` |
| Tables | `acquire_write`, `migrations` only |
| Migration rows | `0` |
| `collections`, `segments`, `embeddings` tables | absent |
| WAL, journal, vector/HNSW directories | absent |

No documents, embeddings, user identifiers, or arbitrary metadata were read
or recorded.

## Exact runtime identity

All runtime evidence came from the image used by the failed backend and the
isolated reproduction:

| Property | Value |
| --- | --- |
| Image | `codexify-backend-runtime:latest` |
| Image digest | `sha256:af108ff65ba1d1fde1417ac776be41eacd106aaf77d2800b7c6e40d2359b6288` |
| Platform | `linux/arm64` |
| Python | `3.11.14` |
| `chromadb` / bundled native runtime | `1.0.15` |
| SQLite library | `3.46.1` |
| Pydantic | `2.12.3` |
| FastAPI | `0.119.1` |
| Uvicorn | `0.38.0` |

`backend/requirements.txt` pins `chromadb==1.0.15`; the inspected image
matches that declared backend runtime dependency. The broader project
constraint is not treated as runtime identity.

The relevant implementation path is
`backend/rag/embedder.py:LocalSemanticEmbedder`, which constructs
`chromadb.PersistentClient` from the resolved `CODEXIFY_CHROMA_PATH` and then
calls `get_or_create_collection`. `guardian/core/dependencies.py` constructs
the vector store during the Guardian application lifespan. No implementation
was executed against the canonical partial path during this task.

## First evidence source: exited backend

The original container `codexify_tester-backend-1` was inspected before the
isolated reproduction. It was exited with code `3`; its command was the normal
backend startup wrapper. The host log path could not be read directly, so
bounded `docker logs --timestamps` output was captured to a mode-`0600`
temporary file and removed after extraction.

The log reached local embedder initialization for the configured BGE model and
then emitted two redacted application logging events. They contained no
exception class, message, Python frame, Rust frame, or failure phase. There was
no unredacted Chroma panic and no evidence sufficient to attribute the exit to
the partial store or to any listed alternative cause.

**Original causal exception:** unavailable from the existing failed-container
evidence.

## Authorized isolated reproduction

Because the original logs were insufficient, exactly one isolated diagnostic
backend reproduction was run. It used:

- the exact image and Tester environment above;
- the normal backend entrypoint, without tracked Compose changes;
- `PYTHONFAULTHANDLER=1` and `RUST_BACKTRACE=1` for that run only; and
- a writable temporary copy derived from the new fresh-partial preservation at
  `/private/tmp/codexify-fresh-chroma-diag.I8o449/chroma`.

The canonical `.chroma` path was never passed to the reproduction. The
temporary container was `codexify-tester-fresh-chroma-diagnostic`. It reached
`Uvicorn running`, remained healthy long enough to return HTTP health `200`,
and exited `0` after it was explicitly stopped. The container, temporary
Chroma copy, and mode-`0600` raw reproduction log were removed after evidence
capture.

The disposable copy completed Chroma initialization: SQLite integrity remained
`ok`, it contained the current Chroma migration tables/generations, and bounded
structural counts were `collections=1`, `segments=2`, and `embeddings=1`. That
one local embedding is a normal deterministic startup/retrieval artifact in
the disposable store, not historical or user-record restoration. It is not
evidence of a chat completion or provider inference.

### Non-causal observation

After Uvicorn had started, a background ChatGPT-import startup sweep emitted a
logging-format `TypeError` at
`guardian/guardian_api.py:_run_chatgpt_import_startup_sweep` (line `351`): the
message's `%d` placeholder received a safety-redacted string for its candidate
count. The configured retry limit itself remained integer `128`.

This was a logging-surface error, not the original causal exception: the
isolated backend continued serving health `200` and later stopped cleanly. It
does not explain the prior canonical exit `3`, so it is not repaired or used
as the blocker classification.

## Classification

| Required decision | Result |
| --- | --- |
| Reproduction required | yes |
| Reproduction count | `1` |
| Sanitized causal exception type/message/frames | unavailable |
| Original failure phase | unresolved after local embedder initialization; no causal frame exposed |
| Blocker classification | `INSUFFICIENT_DIAGNOSTIC_EVIDENCE` |
| Canonical-vs-partial causality | `UNRESOLVED` |

The successful diagnostic copy means only that the exact normal startup did
not reproduce the original failure in that one run. It does not establish that
the canonical partial state was harmless, that empty-store initialization is
reliable, or that a filesystem, dependency, or application defect is absent.

## State safety and bounded side effects

- The canonical backend was not retried; the last observed canonical backend
  state remained exited code `3`.
- `worker-chat` was not started. No Watchdog worker or Watchdog operation ran.
- No chat, cloud, DeepSeek, or Watchdog inference occurred. The one disposable
  local retrieval embedding described above is the only model-adjacent startup
  artifact observed.
- No direct SQL, migration, reset, deletion, Redis clear, or historical-state
  restoration was performed. The checked canonical Postgres revision and
  bounded row counts were unchanged: Alembic `6e9f0a1b2c3`; users `28`;
  projects `4`; chat threads `5,136`; chat messages `113,326`; uploaded files
  `0`; generated files `0`; hosted files `1`; repository bindings `0`.
- The ordinary application startup reported idempotent provider reconciliation
  as `created=0 updated=6`. This record therefore does not overclaim that
  Postgres row timestamps were byte-for-byte unchanged; it establishes no
  schema/data-count loss and no destructive or manual database operation.
- The normal startup enqueued one warmup item (observed Redis queue depth `1`).
  No warmup or chat worker was run and Redis was not cleared.

## Deferred next seam

Authorize one bounded observability repair: **record a secret-safe structured
backend-startup failure receipt at the process/lifespan boundary**, preserving
the exception class, bounded sanitized message, and selected frames before the
current logging redaction removes causal detail. Only after that repair should
a separately authorized canonical backend retry occur.

## Validation

The repository validation and diff checks for this proof are recorded at
commit closeout. This artifact deliberately makes no runtime-health claim.
