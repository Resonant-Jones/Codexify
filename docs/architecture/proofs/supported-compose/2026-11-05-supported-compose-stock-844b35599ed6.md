# Stock Compose runtime qualification — 844b35599ed6 — 2026-11-05

- Evaluated commit: `844b35599ed67123ed7e6434bb4a302728ef52b2`
- Base: `origin/main` at `a0ec5e335` (merged, not rebased)
- Rubric: `docs/qualification/rubrics/supported-compose-stock.md` version 1
- Verdict: **PASS**
- Date: 2026-11-05 (America/New_York)
- Runtime profile: `v1-local-core-web-mcp`
- Startup: stock Docker Compose, without the source-matched launcher
- Provider / model inventory: local / `local-chat` (Whoosh'd), `LOCAL_RUNTIME_PRESET=whooshd-mlx`

This is the second stock-path execution. It supersedes the 2026-11-05 run at
`456da46b8`, whose verdict was **FAIL** on a collection-dimension defect that
this run confirms is fixed. The failure and the fix are both recorded rather
than edited away.

## 1. Environment and disposition

| Property | Value |
| --- | --- |
| Docker engine | client/server 29.9.2, context `desktop-linux` |
| Docker VM memory ceiling | 7.749 GiB — the binding host constraint in this run |
| Host volume free at start | 47 GiB on `/Volumes/Dev_SSD` |
| Disposable project | `cxfstockqual2`; its own network, volumes and container names; all resources removed at teardown |
| Loopback ports | `15933` (postgres), `18999` (backend), `17474`/`17687` (neo4j), `15173` (frontend) — each verified free before start |
| Private Preview, before | 13 containers, healthy, PostgreSQL revision `3a91d7c4e8b2`, backend image `sha256:22d9f5f13e7d…` |
| Private Preview, after | 13 containers, healthy, PostgreSQL revision `3a91d7c4e8b2`, backend image `sha256:22d9f5f13e7d…` — **unchanged** |

**No source-matched launcher was invoked.** `scripts/whooshd_docker_smoke_up.sh`
was not executed. No `codexify-backend-runtime:src-<sha12>` image was resolved
by any service. No shared production tag was replaced or re-pointed.

One isolation overlay was used, exactly as the rubric's isolation provision
allows. It caps the Neo4j JVM heap only:

```yaml
services:
  neo4j:
    environment:
      NEO4J_server_memory_heap_initial__size: 256m
      NEO4J_server_memory_heap_max__size: 512m
      NEO4J_server_memory_pagecache_size: 128m
```

Uncapped, Neo4j was SIGKILLed (exit 137) by the Docker VM under this host's
7.749 GiB ceiling, which made the required topology unstartable. The cap
changes a JVM resource allocation only; it does not touch the migrator's
command, mounts, source guard, or dependency/startup semantics, and it does not
alter any service in the profile's required set.

## 2. Image provenance — verified by content, not by tag

`backend/Dockerfile` cannot be built on this host: it stages two runtime
scripts with a heredoc (`RUN … python - <<'PY'`), a BuildKit-only feature, and
BuildKit cannot run because `buildx` records builder activity by renaming a
temporary file and this session's sandbox denies `rename(2)`. The merged Gate B
proof at `docs/architecture/proofs/runtime/2026-11-05-stock-compose-migration-source-proof.md`
records the same constraint and the same remedy.

The matching image was therefore **assembled** from a base built by the same
repository `backend/Dockerfile` under BuildKit, plus this revision's application
trees overlaid verbatim.

| Component | Identity |
| --- | --- |
| Base | `codexify-qualification/stock-gate-b:e50f5756e-amngz1pe` = `sha256:6ddfa13b31f7…` |
| Overlay | `COPY guardian /app/guardian` and `COPY backend /app/backend` from the evaluated checkout |
| Resulting image | `codexify-backend-runtime:stock-qual-844b35599ed6` = `sha256:54721b1c05e49fc8768c6632b362d286e82e3cffce33d419e64ba3b477b86b0b` |

`backend/Dockerfile` and `backend/requirements.txt` are byte-identical between
`97778bedf` and the evaluated revision, so the base's dependency, apt and
generated-script layers are the layers this revision's Dockerfile produces; the
only image-relevant trees that differ are `guardian/` and `backend/`, both
overlaid verbatim.

Verification performed **inside the assembled image**, before any startup was judged:

| Check | Result |
| --- | --- |
| SHA-256 manifest of the image's `/app/guardian/db/migrations/versions/*.py` versus the checkout's | **identical** — 135 files, `diff` empty |
| SHA-256 of the image's `env.py` versus the checkout's | **identical** |
| SHA-256 of the image's `/app/backend/scripts/docker/run_migrator.py` versus the checkout's | **identical** — `da6e78f52d09601c8c0e2ff889fe0c8bb8c2c302eaa5c72923d8a485e21f55cb` |
| Revision count in the image | **135** — matches the checkout's 135 |
| Generated runtime scripts | `/app/entrypoint.py` and `/app/wait_for_db.py` present and executable |

**Known limit of this provenance.** The base's apt layer was installed on
2026-11-04; a from-scratch build on another date could resolve different
package versions. Neither bears on the invariant under test, which is decided
purely by the SHA-256 content comparison between the baked migration source and
the checkout's. This proof does **not** claim the image is byte-identical to a
from-scratch build of the repository Dockerfile on this date.

## 3. Check matrix

| # | Check | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Supported topology, startup, provider contract | **PASS** | §4 |
| 1 | Migrations applied at the source head | **PASS** | §4 |
| 2 | Health and inventory | **PASS** | §5 |
| 3 | Ordinary chat and durable readback | **PASS** | §6 |
| 4 | Document ingestion and retrieval | **PASS** | §7 |
| 5 | Explicit model authority | **PASS** | §8 |
| 6 | Browser projection | **PASS** | §9 |
| 7 | Restart recovery | **PASS** | §10 |

Overall verdict: **PASS**. Every required check was exercised and passed, no
blocking criterion occurred, and the browser, restart-recovery and provenance
boundaries were all exercised rather than left unproven.

## 4. Check 1 — topology, startup, and the source-head migration contract

`docker compose config --quiet` succeeded for the rendered file set.

Every required service for `v1-local-core-web-mcp` was present and healthy or
running: `frontend`, `backend`, `db`, `redis`, `worker-chat`,
`worker-document-embed`, `migrator`. `graph-init` and `model-prep` exited 0.

Every application service resolved the **same** image:

```
cxfstockqual2-migrator-1              sha256:54721b1c05e49fc8768c6632b362d286e82e3cffce33d419e64ba3b477b86b0b
cxfstockqual2-backend-1               sha256:54721b1c05e49fc8768c6632b362d286e82e3cffce33d419e64ba3b477b86b0b
cxfstockqual2-worker-chat-1           sha256:54721b1c05e49fc8768c6632b362d286e82e3cffce33d419e64ba3b477b86b0b
cxfstockqual2-worker-document-embed-1 sha256:54721b1c05e49fc8768c6632b362d286e82e3cffce33d419e64ba3b477b86b0b
```

`CODEXIFY_BACKEND_IMAGE` was set to the verified immutable assembled image —
the rubric's isolation provision permits exactly this. No launcher-produced
`src-<sha12>` image was resolved.

The provider contract matched the supported profile exactly: local-only
(`CODEXIFY_LOCAL_ONLY_MODE=1`), `ALLOW_CLOUD_PROVIDERS=0`, an **empty**
`CODEXIFY_EGRESS_ALLOWLIST`, and no cloud credential carried by any container.
`OPENAI_API_KEY`, `ANTHROPIC_API_KEY` and `GEMINI_API_KEY` were present in the
backend's environment as **empty strings** — the compose defaults — and no
other service carried any.

The migrator's own coherence proof **passed rather than failing closed**:

```
[Migrator] Alembic heads: ['a7d4c9e2f1b3']
[Migrator] Comparing the migration source against /source-migrations
[Migrator] Migration source is coherent (135 revisions)
```

The live revision was read **directly out of PostgreSQL**, not from a container
exit code:

```
$ docker exec cxfstockqual2-db-1 psql -U codexify -d Codexify \
    -tAc "select version_num from alembic_version"
a7d4c9e2f1b3
$ … -tAc "select count(*) from alembic_version"
1
```

The migrator exited 0, and the dependent services started.

## 5. Check 2 — health and inventory

```
GET /ping       -> {"status":"Guardian awake!"}
GET /health     -> {"status":"ok","service":"core", … "release_hold": false,
                    "supported_profile": {… "valid": true, "mismatches": [] …}}
GET /health/llm -> {"status":"ok","provider":"local","model":"local-chat",
                    "local_base_url":"http://host.docker.internal:8000/v1",
                    "provider_runtime":{"authorized":true,"available":true,
                    "enabled":true,"default_model":"local-chat",
                    "models":[{"id":"local-chat", …}]}}
```

The physical model display metadata the WebUI showed ("Whoosh'd / Gemma 4 12B
IT QAT 4-bit") is observation only, per the repository's provider-identity
rule; the logical route is `local-chat`.

## 6. Check 3 — ordinary chat and durable readback

A thread was created (`POST /api/chat/threads` → HTTP 200, `origin_system:
codexify`), a user message was persisted (`POST /api/chat/1/messages` → HTTP
200), and a completion was accepted (`POST /api/chat/1/complete` → HTTP 200,
`acceptance_status: accepted`, a `task_id` issued).

**Two completions failed closed before the local model finished loading.** The
worker recorded `task.failed` for each, and no assistant message was persisted
for either. The model service then reported `runner_overloaded` (HTTP 429,
`retry_after_seconds: 2`) while loading, and a direct
`POST http://127.0.0.1:8000/v1/chat/completions` returned HTTP 200 resolving to
`mlx-community/Llama-3.2-3B-Instruct-4bit`. After that warm-up the retry
succeeded. The WebUI surfaced both failures honestly as *"2 earlier response
tasks failed."*

The successful completion's durable state:

```
$ GET /api/chat/1/messages
total: 2
  id=1 role=user      content="What is the Quokka habitat identifier? …"  origin=yes
  id=2 role=assistant content="WOMBATS-77"                                  origin=yes
```

Every message carried a native `message_origin` assertion. The durable attempt
linked the assistant message:

```
$ select request_id, completed_message_id, terminal_event_type from chat_completion_attempts
  req_5eb5fddcff034013a17cf145926a5007 | 2 |            <- successful attempt
  req_db4dbc0e026a4965b46a015724e4fd2e |   | task.failed <- cold start
  req_7cf236d2a39e4786a27d190f7fd26ab2 |   | task.failed <- explicit model
```

and the event sequence was recorded durably in `events_outbox`:
`task.running` → `message.created` → `task.completed`. A terminal outcome was
observed for every accepted completion.

## 7. Check 4 — document ingestion and retrieval: **PASS**

This is the check that failed at `456da46b8`, where every embedding was refused
with *"Collection expecting embedding with dimension of 384, got 1024"*.

A document was uploaded through the stock media route (`POST
/api/media/upload/document` → HTTP 200, `parsed_text` populated,
`embedding_status: pending`). The document-embed worker embedded it and the
document reached **`ready`** with no error.

The shared collection was created at the configured model's own dimension:

```
codexify_vault_supported  count=2  dims=[1024, 1024]
```

**Retrieval works end to end.** The question put to the chat
(*"What is the Quokka habitat identifier?"*) was answered **`WOMBATS-77`** —
the identifier carried only in the ingested document — and the answer was
persisted as an assistant message. The document reached the model through the
collection the fix repaired.

The defect and its repair are recorded rather than edited away: the previous
run at `456da46b8` remains in the repository as a FAIL receipt, and its proof
documents the dimension mismatch and the mechanism (a Chroma collection's
dimension is fixed by its first write; the mock embedding backend was hardcoded
to 384 under a comment claiming it matched `bge-large-en-v1.5`, which is
1024-dimensional). The repair derives the dimension from the configured model
instead, and stops the health probe from writing into the shared collection.

## 8. Check 5 — explicit model authority

A completion explicitly requesting an unavailable model
(`{"model":"definitely-not-a-real-model-xyz"}`) was accepted by the route and
then **failed before provider execution** by the worker:

```
  req_7cf236d2a39e4786a27d190f7fd26ab2 |  (no completed_message_id) | task.failed
```

- No substitute model executed.
- **No assistant message was persisted** — the thread still held exactly the two
  messages from the successful completion.
- The durable attempt recorded the terminal failure kind (`task.failed`).

## 9. Check 6 — browser projection

A **real browser** (Chromium via the in-app Browser) was driven against the
stock stack's frontend at `http://127.0.0.1:15173/chat/1`.

- **A real browser renders the thread.** The thread `stock-qual-rerun` appeared
  in the sidebar, and both messages rendered in the conversation lane, the
  assistant reply as a `Guardian` message paragraph reading `WOMBATS-77`.
- **The terminal state converges in the UI.** The rendered conversation showed
  the user message at `11:53 PM` and the assistant reply at `11:58 PM`, with the
  thread title and the sidebar entry matching the durable state.
- **Reload preserves the projected state.** After a full page reload the thread
  re-rendered from the backend with the same two messages and the same
  timestamps.

The onboarding introduction modal, which opens over the chat on a fresh
database, was dismissed once ("Skip for now"); the chat projection beneath it
was already rendered.

**A known limitation was observed and is not silently repaired.** The WebUI
polls the backend's health directly at `http://localhost:18999/health`, and
every such request failed in the browser with `net::ERR_FAILED`. The backend
binds IPv4-only (`127.0.0.1:18999`), while Chromium resolves `localhost` to
`::1` first, so the direct fetch fails before falling back. The UI therefore
shows a persistent *"Backend connection delayed / failed to fetch"* banner even
though the backend is healthy: `GET http://127.0.0.1:18999/health` returns
HTTP 200 from the host, the Vite-proxied `GET http://127.0.0.1:15173/api/chat/threads`
returns HTTP 200, and the chat projection itself is unaffected. Three
profile-quarantined routes (`/api/voice/capabilities`, `/api/codex/entries`,
`/api/ui/session`) returned 404, which is the supported profile's expected
quarantine, not a failure.

This limitation is outside the required criteria of this check and does not
invalidate it, but it is recorded here rather than dropped.

## 10. Check 7 — restart recovery

`cxfstockqual2-backend-1` was restarted and returned to healthy. Durable state
survived:

```
total after restart: 2
  id=1 role=user      content="What is the Quokka habitat identifier? …"
  id=2 role=assistant content="WOMBATS-77"
```

The embedded document's `embedding_status` remained `ready`. No durable state
was lost across the restart.

## 11. What this run does and does not establish

**Establishes.**

- The stock Compose path applies the **source head's** migrations: the
  migrator's coherence proof passed at 135 revisions, the migrator exited 0,
  and the live `alembic_version`, read directly out of PostgreSQL, was the
  evaluated checkout's single head `a7d4c9e2f1b3` with exactly one row.
- Ordinary chat completes and is durably read back, with a native origin
  assertion on every message and a terminal outcome recorded for every
  accepted completion, including the failures.
- **Document ingestion and retrieval work on the stock path.** The shared
  collection is created at the configured model's own dimension, the document
  embedded to `ready`, and the ingested content reached the model's answer.
- An explicitly requested unavailable model fails closed before provider
  execution, persists no assistant message, and records the terminal failure.
- Durable state survives a backend restart.
- A real browser renders the thread, the terminal state converges in the UI,
  and a reload preserves the projected state.
- The Private Preview lane was not modified.

**Does not establish.**

- Anything about `supported-compose` (the source-matched path) or
  `onboarding-and-people`. A receipt for this surface never qualifies another.
- Any release status change. **Release remains HOLD**, and this receipt is
  evidence for one surface, not a release decision.
- That the WebUI's direct backend health fetch works; it does not, for the
  IPv6-resolution reason recorded in §9.

## 12. Host hygiene

The Docker VM's 7.749 GiB memory ceiling, not disk, was the binding host
constraint in this run. Neo4j was SIGKILLed under the combined load until its
JVM heap was capped through the isolation overlay.

All `cxfstockqual2` containers, volumes and network were removed at teardown.
No container, image, volume or network outside this run's disposable project
was removed, stopped or re-pointed.
