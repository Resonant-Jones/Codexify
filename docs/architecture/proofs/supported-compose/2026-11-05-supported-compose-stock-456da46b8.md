# Stock Compose runtime qualification — 456da46b8 — 2026-11-05

- Evaluated commit: `456da46b8a0549ea1d2bd440971f7477efa1669b`
- Base: `origin/main` at `c28bc8f46` (`Merge pull request #1004 from Resonant-Jones/docs/adr-108-plan-authority-pointer`)
- Rubric: `docs/qualification/rubrics/supported-compose-stock.md` version 1
- Verdict: **FAIL**
- Date: 2026-11-05 (America/New_York)
- Runtime profile: `v1-local-core-web-mcp`
- Startup: stock Docker Compose, without the source-matched launcher
- Provider / model inventory: local / `local-chat` (Whoosh'd), `LOCAL_RUNTIME_PRESET=whooshd-mlx`

This receipt records an integrated stock-startup execution of the supported
profile. It proves the **source-head migration contract** on the stock path at
this tip, and it isolates a **document-ingestion dimension defect** that
blocks the ingestion/retrieval check. It does not qualify the surface, and it
does not promote any release status.

## 1. Environment and disposition

| Property | Value |
| --- | --- |
| Docker engine | client/server 29.9.2, context `desktop-linux` |
| Docker VM memory ceiling | 7.749 GiB — the binding host constraint in this run |
| Host volume free at start | 57 GiB on `/Volumes/Dev_SSD` |
| Private Preview, before | 13 containers, healthy, PostgreSQL revision `3a91d7c4e8b2`, backend image `sha256:22d9f5f13e7d…` |
| Private Preview, after | 13 containers, healthy, PostgreSQL revision `3a91d7c4e8b2`, backend image `sha256:22d9f5f13e7d…` — **unchanged** |
| Disposable project | `cxfstockqual`; its own network, volumes and container names; all resources removed at teardown |
| Loopback ports | `15933` (postgres), `18999` (backend), `17474`/`17687` (neo4j), `15173` (frontend) — each verified free before start |

**No source-matched launcher was invoked.** `scripts/whooshd_docker_smoke_up.sh`
was not executed. No `codexify-backend-runtime:src-<sha12>` image was resolved by
any service. No shared production tag was replaced: the Private Preview's
`codexify-backend-runtime:latest` was neither rebuilt nor re-pointed.

## 2. Image provenance — verified by content, not by tag

`backend/Dockerfile` cannot be built on this host: it stages two runtime
scripts with a heredoc (`RUN … python - <<'PY'`), which is BuildKit-only, and
BuildKit itself cannot run here because `buildx` records builder activity by
renaming a temporary file and this session's sandbox denies `rename(2)`. This
was reproduced by the merged Gate B proof at
`docs/architecture/proofs/runtime/2026-11-05-stock-compose-migration-source-proof.md`.

The matching image was therefore **assembled** from a base that was built by
the same repository `backend/Dockerfile` under BuildKit from source revision
`97778bedf`, plus this revision's application trees overlaid verbatim.

| Component | Identity |
| --- | --- |
| Base | `codexify-qualification/stock-gate-b:e50f5756e-amngz1pe` = `sha256:6ddfa13b31f77e4b05bbd0892092ca343e567d3e7978ca85aac665a59288e98b` |
| Overlay | `COPY guardian /app/guardian` and `COPY backend /app/backend` from the evaluated checkout |
| Resulting image | `codexify-backend-runtime:stock-qual-456da46b8a05` = `sha256:f7f583b71a142c180e5cf12769c8e71b5c6e60b06887a6ed0848ce5fb4a2eba0`, created 2026-11-05T22:21:31Z |

The equivalence argument is checkable rather than asserted:

- `backend/Dockerfile` and `backend/requirements.txt` are **byte-identical**
  between `97778bedf` and the evaluated revision (`git diff --stat 97778bedf
  HEAD -- backend/requirements.txt backend/Dockerfile` is empty), so the base's
  dependency, apt and generated-script layers are the layers this revision's
  Dockerfile produces.
- The only image-relevant trees that differ between the two revisions are
  `guardian/` and `backend/`, both overlaid verbatim.

Verification performed **inside the assembled image**, before any startup was judged:

| Check | Result |
| --- | --- |
| SHA-256 manifest of the image's `/app/guardian/db/migrations` (`versions/*.py`) versus the checkout's | **identical** — `diff` empty |
| SHA-256 of the image's `/app/guardian/db/migrations/env.py` versus the checkout's | **identical** |
| SHA-256 of the image's `/app/backend/scripts/docker/run_migrator.py` versus the checkout's | **identical** — `da6e78f52d09601c8c0e2ff889fe0c8bb8c2c302eaa5c72923d8a485e21f55cb` |
| Revision count in the image | **135** — matches the checkout's 135 |
| Generated runtime scripts | `/app/entrypoint.py` and `/app/wait_for_db.py` present and executable |

**Known limit of this provenance.** The base's apt layer was installed on
2026-11-04; a from-scratch build on another date could resolve different
package versions. Neither bears on the invariant under test, which is decided
purely by the SHA-256 content comparison between the baked migration source and
the checkout's. This proof does **not** claim the image is byte-identical to a
from-scratch build of the repository Dockerfile on this date.

## 3. Isolation overlay

The rubric permits a disposable isolation overlay that selects a verified
immutable image, allocates unique resources and host ports, provides synthetic
credentials, and applies the supported profile's provider values, provided it
does not replace the stock migrator's command, mounts, source guard, or
dependency/startup semantics.

The overlay used here (`/tmp/cxf-overlay/isolation.yml`) does exactly one
thing beyond image selection and port allocation:

```yaml
services:
  neo4j:
    environment:
      NEO4J_server_memory_heap_initial__size: 256m
      NEO4J_server_memory_heap_max__size: 512m
      NEO4J_server_memory_pagecache_size: 128m
```

**Why.** Neo4j is not one of the profile's required services, but `backend`
depends on `graph-init`, which depends on Neo4j. Uncapped, the Neo4j container
was SIGKILLed by the Docker VM under this host's 7.749 GiB memory ceiling
(exit 137), which made the required topology unstartable. The cap changes a JVM
resource allocation only. It does not touch the migrator's command, mounts,
source guard, or dependency/startup semantics, and it does not alter any
service in the profile's required set. The provider values came from the
supported profile's own `provider_contract`
(`config/supported_profiles/v1-local-core-web-mcp.yaml:85-95`), applied
verbatim.

## 4. Check matrix

| # | Check | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Supported topology, startup, source-head migration | **PASS** | §5 |
| 2 | Health and inventory | **PASS** | §6 |
| 3 | Ordinary chat and durable readback | **PASS** | §7 |
| 4 | Document ingestion and retrieval | **FAIL** | §8 |
| 5 | Explicit model authority | **PASS** | §9 |
| 6 | Browser projection | **UNPROVEN** | §10 |
| 7 | Restart recovery | **PASS** | §11 |

Overall verdict: **FAIL**. Check 4 hit a blocking criterion. Check 6 was not
exercised in a real browser, which under this rubric is an open boundary and
would independently prevent a PASS.

## 5. Check 1 — topology, startup, and the source-head migration contract

`docker compose config --quiet` succeeded for the rendered file set.

Required services for `v1-local-core-web-mcp` — `frontend`, `backend`, `db`,
`redis`, `worker-chat`, `worker-document-embed`, `migrator` — all reached a
healthy or running state:

| Service | State at observation |
| --- | --- |
| `cxfstockqual-db-1` | Up (healthy) |
| `cxfstockqual-redis-1` | Up (healthy) |
| `cxfstockqual-neo4j-1` | Up (healthy) |
| `cxfstockqual-backend-1` | Up (healthy) |
| `cxfstockqual-worker-chat-1` | Up |
| `cxfstockqual-worker-document-embed-1` | Up |
| `cxfstockqual-frontend-1` | Up |
| `cxfstockqual-migrator-1` | Exited 0 |
| `cxfstockqual-graph-init-1` | Exited 0 |
| `cxfstockqual-model-prep-1` | Exited 0 |

The migrator's own coherence proof **passed rather than failing closed**:

```
[Migrator] Alembic heads: ['a7d4c9e2f1b3']
[Migrator] Comparing the migration source against /source-migrations
[Migrator] Migration source is coherent (135 revisions)
```

The live revision was read **directly out of PostgreSQL**, not from a container
exit code:

```
$ docker exec cxfstockqual-db-1 psql -U codexify -d Codexify \
    -tAc "select version_num, count(*) over () from alembic_version"
a7d4c9e2f1b3|1
```

One row, equal to the evaluated checkout's single Alembic head. The
`alembic_version` table was **not** written by this run's migration — it was
read after the migrator exited 0.

The resolved environment matched the supported profile's provider contract
exactly: local-only, no cloud credentials, empty egress allowlist, with
`LOCAL_RUNTIME_PRESET=whooshd-mlx`, `LOCAL_BASE_URL=http://host.docker.internal:8000/v1`,
`LOCAL_COMPAT_FIRST=true`, `LOCAL_PROVIDER_DISPLAY_NAME=Whoosh'd`,
`LOCAL_PROVIDER_VENDOR=whooshd`. The backend enforces this itself: an initial
startup with an incomplete contract failed closed with a drift receipt naming
each mismatched value, which is the designed behaviour and was corrected by
applying the profile's own values.

## 6. Check 2 — health and inventory

```
GET /ping        -> {"status":"Guardian awake!"}
GET /health      -> {"status":"ok","service":"core", … "supported_profile":{…"valid":true,"mismatches":[]…}}
GET /health/llm  -> {"status":"ok","provider":"local","model":"local-chat",
                     "local_base_url":"http://host.docker.internal:8000/v1",
                     "provider_runtime":{"authorized":true,"available":true,"enabled":true,
                     "default_model":"local-chat","models":[{"id":"local-chat",…}]}}
```

`release_hold: false`; the supported profile resolved `valid: true` with an
empty `mismatches` list. The local provider was authorized, available and
enabled, and advertised `local-chat`.

## 7. Check 3 — ordinary chat and durable readback

A thread was created (`POST /api/chat/threads` → `{"ok":true,"id":1,…,"origin_system":"codexify"}`),
a user message was persisted (`POST /api/chat/1/messages` → HTTP 200), and a
completion was accepted (`POST /api/chat/1/complete` → HTTP 200,
`acceptance_status: accepted`, `task_id` issued).

**The first completion failed closed** because the local model had not yet
loaded: the worker recorded `task.failed` and no assistant message was
persisted. The model service then reported `runner_overloaded` (HTTP 429,
`retry_after_seconds: 2`) while loading, and `active_model` was `null`. This
was a **cold-start transient, not a defect**: after the model finished loading,
a direct `POST http://127.0.0.1:8000/v1/chat/completions` returned HTTP 200
resolving to `mlx-community/Llama-3.2-3B-Instruct-4bit`, and the retry
succeeded.

Durable readback after the successful completion:

```
$ GET /api/chat/1/messages
total: 3
  id=1 role=user      content="Reply with exactly: STOCK-QUAL-PASS"
       origin: {'version': 1, 'asserted_at': '2026-11-06T00:29:41.945757+00:00', 'origin_system': 'codexify'}
  id=2 role=user      content="Reply with exactly: STOCK-QUAL-PASS"
       origin: {'version': 1, 'asserted_at': '2026-11-06T00:29:41.976641+00:00', 'origin_system': 'codexify'}
  id=3 role=assistant content="STOCK-QUAL-PASS"
       origin: {'version': 1, 'asserted_at': '2026-11-06T00:35:36.267276+00:00', 'origin_system': 'codexify'}
```

The assistant message was persisted, and every message carries a native
`message_origin` assertion.

**A terminal outcome was observed**, not merely an acceptance. The durable
attempt table linked the assistant message to its attempt:

```
$ select request_id, completed_message_id, terminal_event_type from chat_completion_attempts …
  req_893e58e93d5447a2bbf394641a4ae0cb | 3 |                      <- successful attempt
  req_1f689db21e2341749358c95247050b8d |   | task.failed          <- cold-start failure
```

and the event sequence was recorded durably in `events_outbox`:

```
  4 | task.running     | pending
  5 | task.failed      | pending     <- cold-start attempt
  6 | completion.error | pending
  7 | task.running     | pending
  8 | message.created  | pending
  9 | task.completed   | pending
```

## 8. Check 4 — document ingestion and retrieval: **FAIL**

A text document was uploaded through the stock media route
(`POST /api/media/upload/document` → HTTP 200, `embedding_status: pending`,
`parsed_text` populated). The document-embed worker took it and **failed it
terminally**:

```
embedding_status = failed
embedding_error  = Collection expecting embedding with dimension of 384, got 1024
```

**Mechanism, as measured.** The shared Chroma collection
`codexify_vault_supported` had been created with dimension **384**, while the
configured local embedder produces **1024**:

| Artifact | Dimension | Source |
| --- | --- | --- |
| `cxfstockqual` collection `codexify_vault_supported` | **384** | created by this run |
| Private Preview collection `codexify_vault_supported` | **1024** | live lane, unchanged |

The collection contained seven vectors, **all 384-dimensional**, with metadata
`source: api/embeddings` (five) and `health_check: True` (two), plus
`namespace: global`. The document-embed worker resolved the real model —
`[embedder] backend=sentence_transformer model=/models/bge-large-en-v1.5`, which
is a 1024-dimensional model — and Chroma refused the add.

**Where the 384 comes from.** The Guardian-side shared vector store and the
document-embed worker do not agree on embedding dimension, and they share one
collection:

- `backend/rag/embedder.py:305` and `guardian/runtime/embed/embedder.py:109`
  create the collection with `get_or_create_collection(name=…)` and **no
  dimension argument**, so Chroma's default applies until the first write fixes
  the dimension for the collection's life.
- `guardian/memoryos/utils.py:189` defines `_DEFAULT_EMBED_DIM = 384`, the
  zero-embedding fallback dimension.
- `backend/rag/embedder.py:327-328` creates a mock embedding backend with
  `MockEmbeddingBackend(dim=384, normalize=True)` under the comment *"Use 384
  dims to match bge-large-en-v1.5 default"* — **bge-large-en-v1.5 is
  1024-dimensional**, so that comment is factually wrong and the dimension it
  pins is the mock's, not the model's.
- The Private Preview lane's collection is 1024, so the mismatch is specific to
  a fresh stock-path volume whose collection is created before the real
  embedder writes to it.

**Observed behaviour of the mismatch.** The failure is fail-closed and
correctly terminal: the document was marked `failed` with the reason recorded,
and nothing was indexed. The retrieval layer then correctly withheld it. That
is correct behaviour over a broken path, not a working path — and it means
**document ingestion and retrieval do not function on the stock Compose path at
this tip**.

**Falsification attempt.** The collection was deleted and the document was
requeued to `pending` in the disposable database. The worker did not recreate
the collection at 1024, because the poisoning writer is not the worker. A
direct probe of `GET /health/vector` after clearing the collection returned
`{"ok":false,"status":"error","backend":"unknown","error":"Vector search
requires user_id"}` and wrote nothing, so the probe path requires a user id
that the health route did not supply in this run.

**Status.** The precise writer that fixed the collection at 384 in this run was
not isolated to a single call site before the run was closed. What is proven is
that the stock path creates the shared collection at 384, that the configured
embedder produces 1024, and that every document embedding then fails closed.
Closing this requires either pinning the collection dimension to the embedder's
actual dimension at creation, or making the Guardian shared vector store and
the document-embed worker resolve the same embedding backend and dimension.

## 9. Check 5 — explicit model authority: **PASS**

A completion explicitly requesting an unavailable model
(`{"model":"definitely-not-a-real-model-xyz"}`) was accepted by the route and
then **failed before provider execution** by the worker:

```
  req_064a5b2328ef4ee6aeeb9115bead5790 |  (no completed_message_id) | task.failed
```

- No substitute model executed.
- **No assistant message was persisted** for the failed attempt — the thread
  still held exactly the three messages from the successful completion.
- The durable attempt recorded the terminal failure kind (`task.failed`).

## 10. Check 6 — browser projection: **UNPROVEN**

The frontend container was running and served the application
(`GET http://127.0.0.1:15173/` → HTTP 200), and the thread projection the UI
reads was correct and complete (`GET /api/chat/1/messages` → three messages
including the completed assistant reply), with event delivery recorded durably
in `events_outbox` (`task.running` → `message.created` → `task.completed`).

**No real-browser observation was performed.** This check is therefore
UNPROVEN, not PASS. Under this rubric an unexercised browser boundary prevents
a PASS independently of check 4.

## 11. Check 7 — restart recovery: **PASS**

`cxfstockqual-backend-1` was restarted and returned to healthy. Durable state
survived:

```
total after restart: 3
  id=1 role=user      content="Reply with exactly: STOCK-QUAL-PASS"
  id=2 role=user      content="Reply with exactly: STOCK-QUAL-PASS"
  id=3 role=assistant content="STOCK-QUAL-PASS"
```

No durable state was lost across the restart.

## 12. What this run does and does not establish

**Establishes.**

- The stock Compose path applies the **source head's** migrations: the
  migrator's own coherence proof passed at 135 revisions, the migrator exited 0,
  and the live `alembic_version`, read directly out of PostgreSQL, was the
  evaluated checkout's single head `a7d4c9e2f1b3` with exactly one row.
- Ordinary chat completes and is durably read back, with a native origin
  assertion on every message and a terminal outcome recorded for every attempt.
- An explicitly requested unavailable model fails closed before provider
  execution, persists no assistant message, and records the terminal failure.
- Durable state survives a backend restart.
- The Private Preview lane was not modified: 13 containers, healthy, revision
  `3a91d7c4e8b2`, backend image digest unchanged.

**Does not establish.**

- Any qualification of the `supported-compose-stock` surface. The verdict is
  FAIL, and the registry projects HOLD for a surface with no passing run.
- A working document-ingestion or retrieval path on the stock Compose path.
  Check 4 is a FAIL, and the release-definition item that requires a stock-path
  run to pass "retrieval" cannot be closed on this evidence.
- Browser projection. Check 6 is UNPROVEN.
- Any release status change. **Release remains HOLD.**

## 13. Host hygiene

The Docker VM's 7.749 GiB memory ceiling, not disk, was the binding host
constraint: the backend and Neo4j were SIGKILLed (exit 137) under the
combined load of this run, the Private Preview lane, and 72 leaked
`codexify_account_observability_norm_*` disposable PostgreSQL fixtures from
completed test runs.

Those 72 fixtures were reclaimed — all were between 35 minutes and 27 hours
old, their count was stable across repeated sampling (no run was active), and
none belonged to the Private Preview or to any compose project. No other
container, image, volume or network was removed. The Private Preview's 13
containers, its nine named volumes, its network, its PostgreSQL revision and
its image digest were verified unchanged before and after.

All `cxfstockqual` containers, volumes and network were removed at teardown.
