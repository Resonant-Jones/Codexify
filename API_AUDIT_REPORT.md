# Codexify / Guardian API — Full Endpoint Audit

**Generated:** 2026-02-13
**Scope:** Main `guardian_api` FastAPI application (`guardian/guardian_api.py`)
**Method:** Static analysis of all `include_router` registrations + direct `@app.*` decorators

---

## A) NORMALIZE + CLEAN — Cleanup Log

### Input Summary

| Metric | Count |
|--------|-------|
| Total input lines (routes discovered across all source files) | 234 |
| Routes in main `guardian_api` app (actually registered) | 152 |
| Routes in standalone service apps | 32 |
| Routes defined but **never registered** (dead code) | ~50 |

### Exact Duplicates Removed

**0 exact duplicates among active routes.**

All routes that appear to share the same method+path are in fact registered through different mechanisms (direct `@app` decorator vs router) and resolve to distinct handler functions, OR one copy is dead code (not registered). No two identical method+path combinations are served by the main app from separate registrations.

> **Note:** Several route files define endpoints that overlap with other files (e.g., `graph.py` defines `GET /graph` but `guardian_api.py` also defines `GET /graph` directly). In these cases, only the `guardian_api.py` version is active because `graph.py`'s router is never imported. These are flagged as dead code, not duplicates.

### Alias Groups Detected (16 groups)

Aliases are defined as: path is identical after removing a single leading `/api` prefix.

| # | Canonical Path | Alias Path | Method |
|---|---------------|------------|--------|
| 1 | `/health/llm` | `/api/health/llm` | GET |
| 2 | `/chat` | `/api/chat` | POST |
| 3 | `/chat/threads` | `/api/chat/threads` | POST |
| 4 | `/chat/threads` | `/api/chat/threads` | GET |
| 5 | `/chat/{thread_id}/messages` | `/api/chat/{thread_id}/messages` | POST |
| 6 | `/chat/{thread_id}/messages` | `/api/chat/{thread_id}/messages` | GET |
| 7 | `/chat/{thread_id}/complete` | `/api/chat/{thread_id}/complete` | POST |
| 8 | `/chat/{thread_id}/messages/{message_id}` | `/api/chat/{thread_id}/messages/{message_id}` | DELETE |
| 9 | `/chat/{thread_id}/branch` | `/api/chat/{thread_id}/branch` | POST |
| 10 | `/chat/{thread_id}` | `/api/chat/{thread_id}` | PATCH |
| 11 | `/chat/threads/{thread_id}` | `/api/chat/threads/{thread_id}` | PATCH |
| 12 | `/chat/debug/rag-trace/{thread_id}/latest` | `/api/chat/debug/rag-trace/{thread_id}/latest` | GET |
| 13 | `/upload-chatgpt-export` | `/api/upload-chatgpt-export` | POST |
| 14 | `/codex/entries` | `/api/codex/entries` | GET |
| 15 | `/codex/entries/{entry_id}` | `/api/codex/entries/{entry_id}` | GET |
| 16 | `/codex/entries/{entry_id}/export` | `/api/codex/entries/{entry_id}/export` | GET |

### Path Inconsistency (NOT aliases — flagged)

| Non-API Path | API Path | Method | Issue |
|-------------|----------|--------|-------|
| `DELETE /chat/{thread_id}` | `DELETE /api/chat/threads/{thread_id}` | DELETE | Different path structure after removing `/api`. The non-API version uses `/chat/{thread_id}`, the API version uses `/chat/threads/{thread_id}`. These are distinct endpoints, not aliases. |

### Double-Prefix Bugs (2 detected)

| Resolved Path | Router Route | Mount Prefix | Source |
|--------------|-------------|--------------|--------|
| `GET /agent/agent/ping` | `/agent/ping` | `/agent` | `agent.py:6`, mounted at `guardian_api.py:455` |
| `POST /research/research` | `/research` | `/research` | `research.py:16`, mounted at `guardian_api.py:456` |

### Dead Code — Unregistered Route Modules

These files define routers that are **never imported or included** in `guardian_api.py`:

| Module | Routes Defined | Status |
|--------|---------------|--------|
| `routes/graph.py` | 2 (GET /graph, GET /health/neo4j) | Dead — `/graph` is served directly from `guardian_api.py` |
| `routes/federation_context.py` | 3 (search, peers, trust) | Dead — not a sub-router of `federation.router` |
| `routes/channels.py` | 10 (configs, allowlist, pairings, messages) | Dead — entire module unregistered |
| `routes/browser.py` | 7 (approvals, sessions) | Dead — entire module unregistered |
| `routes/workspace.py` | 1 (GET /api/workspace/{thread_id}) | Dead — never imported |
| `routes/meta.py` | 1 (GET /meta/selfcheck) | Dead — never imported |
| `routes/rag_upload.py` | 2 (upload-chat, upload-chatgpt-export) | Dead — superseded by `migration.py` |
| `connectors/google.py` | 2 (OAuth start, callback) | Dead — never imported |

### Dead Code — Unregistered Routers Within Imported Modules

| Module | Dead Router | Routes Lost | Reason |
|--------|------------|-------------|--------|
| `threads.py` | `api_router` (prefix `/api`) | GET/POST `/api/threads` | Only `router` imported |
| `projects.py` | `api_router` (prefix `/api/projects`) | GET/PATCH/DELETE `/api/projects/...` | Only `router` imported |
| `chat.py` | `threads_router` (prefix `/threads`) | GET/POST `/threads` | Not imported (separate `threads.py` serves these) |
| `chat.py` | `thread_router` (prefix `/thread`) | GET `/thread/{id}`, `/thread/{id}/children`, `/thread/{id}/summary`, POST `/thread` | Not imported |
| `memory.py` | `github_router` | GET `/api/github/search` | Not included |
| `memory.py` | `search_router` | GET `/search`, GET `/history`, POST `/log`, POST `/summarize` | Not included |
| `memory.py` | `log_router` | (depends on routes defined) | Not included |

### Standalone Service Apps (Outside Main Guardian API)

| App | File | Routes | Purpose |
|-----|------|--------|---------|
| Legacy Guardian | `guardian/main.py` | 2 | Minimal POST /chat + GET /health |
| Server App | `guardian/server/app.py` | 2 | GET /healthz, GET / |
| Tools API | `guardian/server/tools_api.py` | 2 | GET /manifest, POST /call |
| Codexify API | `guardian/server/codexify_api.py` | 9 | GDrive export/import, iCloud, OAuth |
| Pulse Orchestrator | `guardian/core/orchestrator/pulse_orchestrator.py` | 2 | POST /orchestrate, GET /health |
| TTS Service | `backend/tts_service/app.py` | 3 | POST /tts, GET /, GET /health |
| Legacy Codexify | `guardian/codexify/api_server.py` | 4 | GDrive/iCloud import/export |
| Deprecated API | `guardian/api/deprecated-guardian_api.py` | 5 | Legacy chat, embeddings, healthz |
| Test Plugin | `scripts/test_plugin_server.py` | 2 | POST /rpc, GET /health |

---

## B) CATEGORIZE + ORDER

**136 unique endpoint families** across **11 categories**, totaling **152 active routes** (including 16 `/api` aliases).

### Category 1: Health & Observability

| # | Method | Path | Source |
|---|--------|------|--------|
| 1 | GET | `/health` | `health.py:70` |
| 2 | GET | `/health/llm` | `health.py:76` |
| — | GET | `/api/health/llm` *(alias of #2)* | `health.py:77` |
| 3 | GET | `/health/chat` | `health.py:135` |
| 4 | GET | `/health/memory` | `health.py:156` |
| 5 | GET | `/health/vector` | `health.py:185` |
| 6 | GET | `/health/deps` | `health.py:265` |
| 7 | GET | `/metrics` | `health.py:253` |
| 8 | GET | `/ping` | `admin.py:135` |
| 9 | GET | `/healthz` | `admin.py:142` |
| 10 | GET | `/backfill/status` | `backfill.py:19` |

### Category 2: Auth & Session

| # | Method | Path | Source |
|---|--------|------|--------|
| 11 | POST | `/auth/session` | `admin.py:168` |
| 12 | POST | `/auth/session/cookie` | `admin.py:198` |
| 13 | GET | `/authz/debug` | `admin.py:245` |

### Category 3: Chat, Threads & Projects

| # | Method | Path | Source |
|---|--------|------|--------|
| 14 | GET | `/threads` | `threads.py:27` |
| 15 | POST | `/threads` | `threads.py:55` |
| 16 | GET | `/projects` | `projects.py:57` |
| 17 | PATCH | `/projects/{project_id}` | `projects.py:71` |
| 18 | DELETE | `/projects/{project_id}` | `projects.py:99` |
| 19 | POST | `/chat` | `chat.py:1026` |
| — | POST | `/api/chat` *(alias of #19)* | `chat.py:1172` |
| 20 | GET | `/chat/stream` | `chat.py:1136` |
| 21 | POST | `/chat/threads` | `chat.py:367` |
| — | POST | `/api/chat/threads` *(alias)* | `chat.py:1180` |
| 22 | GET | `/chat/threads` | `chat.py:421` |
| — | GET | `/api/chat/threads` *(alias)* | `chat.py:1188` |
| 23 | POST | `/chat/{thread_id}/messages` | `chat.py:437` |
| — | POST | `/api/chat/{thread_id}/messages` *(alias)* | `chat.py:1194` |
| 24 | GET | `/chat/{thread_id}/messages` | `chat.py:610` |
| — | GET | `/api/chat/{thread_id}/messages` *(alias)* | `chat.py:1204` |
| 25 | POST | `/chat/{thread_id}/complete` | `chat.py:630` |
| — | POST | `/api/chat/{thread_id}/complete` *(alias)* | `chat.py:1215` |
| 26 | DELETE | `/chat/{thread_id}/messages/{message_id}` | `chat.py:763` |
| — | DELETE | `/api/chat/{thread_id}/messages/{message_id}` *(alias)* | `chat.py:1233` |
| 27 | POST | `/chat/{thread_id}/branch` | `chat.py:782` |
| — | POST | `/api/chat/{thread_id}/branch` *(alias)* | `chat.py:1243` |
| 28 | PATCH | `/chat/{thread_id}` | `chat.py:844` |
| — | PATCH | `/api/chat/{thread_id}` *(alias)* | `chat.py:1253` |
| 29 | PATCH | `/chat/threads/{thread_id}` | `chat.py:855` |
| — | PATCH | `/api/chat/threads/{thread_id}` *(alias)* | `chat.py:1263` |
| 30 | DELETE | `/chat/{thread_id}` | `chat.py:882` |
| 31 | DELETE | `/api/chat/threads/{thread_id}` | `chat.py:1273` |
| 32 | GET | `/chat/debug/rag-trace/{thread_id}/latest` | `chat.py:1110` |
| — | GET | `/api/chat/debug/rag-trace/{thread_id}/latest` *(alias)* | `chat.py:1225` |

> **Ordering note:** Thread/project listing comes first (read), then chat creation, then message CRUD, then mutations, then delete. The two distinct delete endpoints (#30, #31) have inconsistent path structures — flagged as risk.

### Category 4: Memory & Knowledge

| # | Method | Path | Source |
|---|--------|------|--------|
| 33 | GET | `/api/memory/health/memory` | `memory.py:369` |
| 34 | GET | `/api/memory/{silo}` | `memory.py:157` |
| 35 | POST | `/api/memory/{silo}` | `memory.py:195` |
| 36 | PATCH | `/api/memory/{silo}/{entry_id}` | `memory.py:256` |
| 37 | DELETE | `/api/memory/{silo}/{entry_id}` | `memory.py:316` |
| 38 | POST | `/api/embeddings` | `embeddings.py:36` |
| 39 | GET | `/personal-facts` | `personal_facts.py:75` |
| 40 | POST | `/personal-facts` | `personal_facts.py:92` |
| 41 | GET | `/personal-facts/{fact_id}` | `personal_facts.py:112` |
| 42 | PATCH | `/personal-facts/{fact_id}` | `personal_facts.py:125` |
| 43 | POST | `/personal-facts/{fact_id}/confirm` | `personal_facts.py:147` |
| 44 | POST | `/personal-facts/{fact_id}/dispute` | `personal_facts.py:165` |
| 45 | GET | `/personal-facts/{fact_id}/evidence` | `personal_facts.py:184` |
| 46 | POST | `/personal-facts/{fact_id}/evidence` | `personal_facts.py:197` |
| 47 | GET | `/personal-facts/{fact_id}/revisions` | `personal_facts.py:219` |
| 48 | POST | `/codexify` | `codexify_router.py:48` |
| 49 | POST | `/embed` | `codexify_router.py:63` |
| 50 | POST | `/search` | `codexify_router.py:85` |

### Category 5: Identity & System Configuration

| # | Method | Path | Source |
|---|--------|------|--------|
| 51 | GET | `/api/imprint/status` | `imprint.py:80` |
| 52 | POST | `/api/imprint/proposal` | `imprint.py:164` |
| 53 | POST | `/api/imprint/accept` | `imprint.py:218` |
| 54 | POST | `/api/imprint/reject` | `imprint.py:288` |
| 55 | POST | `/api/imprint/persona` | `imprint.py:340` |
| 56 | GET | `/api/system_prompt/summary` | `imprint.py:300` |
| 57 | GET | `/api/system_docs` | `imprint.py:385` |
| 58 | POST | `/api/system_docs/toggle` | `imprint.py:409` |
| 59 | GET | `/api/iddb/settings` | `iddb.py:44` |
| 60 | POST | `/api/iddb/settings` | `iddb.py:49` |

### Category 6: Media & Generation

| # | Method | Path | Source |
|---|--------|------|--------|
| 61 | GET | `/api/media/images` | `media.py:1507` |
| 62 | GET | `/api/media/documents` | `media.py:1601` |
| 63 | POST | `/api/media/upload/image` | `media.py:309` |
| 64 | GET | `/api/media/images/{image_id}` | `media.py:619` |
| 65 | DELETE | `/api/media/images/{image_id}` | `media.py:647` |
| 66 | POST | `/api/media/upload/document` | `media.py:671` |
| 67 | POST | `/api/media/generate/image` | `media.py:1127` |
| 68 | POST | `/api/media/tts/synthesize` | `media.py:1363` |
| 69 | GET | `/api/media/tts/{tts_id}` | `media.py:1431` |
| 70 | GET | `/api/media/resolve` | `media.py:1463` |

### Category 7: Connectors & Integration

| # | Method | Path | Source |
|---|--------|------|--------|
| 71 | GET | `/api/connectors/health` | `connectors.py:701` |
| 72 | GET | `/api/connectors/worker/stats` | `connectors.py:714` |
| 73 | GET | `/api/connectors` | `connectors.py:584` |
| 74 | POST | `/api/connectors` | `connectors.py:591` |
| 75 | GET | `/api/connectors/{connector_name}` | `connectors.py:611` |
| 76 | PATCH | `/api/connectors/{connector_name}` | `connectors.py:618` |
| 77 | POST | `/api/connectors/{connector_name}/config` | `connectors.py:630` |
| 78 | POST | `/api/connectors/{connector_name}/test` | `connectors.py:643` |
| 79 | POST | `/api/connectors/{connector_name}/sync` | `connectors.py:650` |
| 80 | POST | `/api/connectors/{connector_name}/authorize` | `connectors.py:658` |
| 81 | GET | `/api/connectors/{connector_name}/status` | `connectors.py:669` |
| 82 | POST | `/api/connectors/{name}/ingest` | `connectors.py:682` |

### Category 8: Federation & Graph

| # | Method | Path | Source |
|---|--------|------|--------|
| 83 | GET | `/api/federation/manifest` | `federation.py:129` |
| 84 | GET | `/api/federation/graph/stats` | `federation.py:781` |
| 85 | POST | `/api/federation/session/request` | `federation.py:156` |
| 86 | POST | `/api/federation/session/accept` | `federation.py:262` |
| 87 | POST | `/api/federation/diff/push` | `federation.py:482` |
| 88 | GET | `/api/federation/diff/pull` | `federation.py:589` |
| 89 | POST | `/api/federation/graph/update` | `federation.py:668` |
| 90 | GET | `/api/federation/graph/snapshot` | `federation.py:746` |
| 91 | WEBSOCKET | `/api/federation/relay/{relay_id}` | `federation.py:333` |
| 92 | GET | `/graph` | `guardian_api.py:652` |
| 93 | POST | `/api/neo/graph-message` | `neo.py:23` |

### Category 9: Flows & Scheduling

| # | Method | Path | Source |
|---|--------|------|--------|
| 94 | GET | `/api/flows` | `flows.py:65` |
| 95 | POST | `/api/flows` | `flows.py:53` |
| 96 | GET | `/api/flows/{flow_id}` | `flows.py:71` |
| 97 | PATCH | `/api/flows/{flow_id}` | `flows.py:77` |
| 98 | POST | `/api/flows/{flow_id}/validate` | `flows.py:94` |
| 99 | POST | `/api/flows/{flow_id}/run` | `flows.py:108` |
| 100 | GET | `/api/flows/{flow_id}/runs` | `flows.py:120` |
| 101 | GET | `/api/flows/runs/{run_id}` | `flows.py:127` |
| 102 | GET | `/api/cron/jobs` | `cron.py:186` |
| 103 | POST | `/api/cron/jobs` | `cron.py:157` |
| 104 | GET | `/api/cron/jobs/{job_id}` | `cron.py:199` |
| 105 | PATCH | `/api/cron/jobs/{job_id}` | `cron.py:214` |
| 106 | DELETE | `/api/cron/jobs/{job_id}` | `cron.py:247` |
| 107 | POST | `/api/cron/jobs/{job_id}/trigger` | `cron.py:264` |
| 108 | GET | `/api/cron/jobs/{job_id}/runs` | `cron.py:287` |

### Category 10: Documents, Codex & Exports

| # | Method | Path | Source |
|---|--------|------|--------|
| 109 | GET | `/codex/entries` | `guardian_api.py:482` |
| — | GET | `/api/codex/entries` *(alias)* | `codex.py:40` |
| 110 | GET | `/codex/entries/{entry_id}` | `guardian_api.py:488` |
| — | GET | `/api/codex/entries/{entry_id}` *(alias)* | `codex.py:46` |
| 111 | GET | `/codex/entries/{entry_id}/export` | `guardian_api.py:494` |
| — | GET | `/api/codex/entries/{entry_id}/export` *(alias)* | `codex.py:60` |
| 112 | POST | `/api/documents/autosave` | `documents.py:105` |
| 113 | POST | `/api/documents/generate` | `documents.py:253` |
| 114 | GET | `/api/threads/{thread_id}/documents` | `documents.py:396` |
| 115 | POST | `/api/share` | `share.py:68` |
| 116 | GET | `/api/share/{token}` | `share.py:195` |
| 117 | GET | `/exports/threads.ndjson` | `api_exports.py:33` |
| 118 | POST | `/upload-chatgpt-export` | `migration.py:28` |
| — | POST | `/api/upload-chatgpt-export` *(alias)* | `migration.py:29` |

### Category 11: Dev, Debug & Realtime

| # | Method | Path | Source |
|---|--------|------|--------|
| 119 | GET | `/debug/config` | `admin.py:262` |
| 120 | GET | `/dev/state/{thread_id}` | `devtools.py:49` |
| 121 | GET | `/dev/plugins` | `devtools.py:73` |
| 122 | POST | `/dev/delegate` | `devtools.py:88` |
| 123 | POST | `/dev/guardian_loop/{thread_id}` | `devtools.py:111` |
| 124 | POST | `/dev/inject_result/{task_id}` | `devtools.py:119` |
| 125 | GET | `/dev/timeline/{thread_id}` | `devtools.py:125` |
| 126 | GET | `/dev/task/{task_id}/status` | `devtools.py:158` |
| 127 | GET | `/dev/results/{task_id}` | `devtools.py:173` |
| 128 | POST | `/tools/execute` | `tools.py:48` |
| 129 | GET | `/api/events` *(SSE)* | `guardian_api.py:500` |
| 130 | GET | `/api/tasks/{task_id}/events` *(SSE)* | `guardian_api.py:583` |
| 131 | WEBSOCKET | `/api/ws/rpc` | `websocket.py:151` |
| 132 | GET | `/api/collab/{document_id}/audit` | `collaboration.py:282` |
| 133 | WEBSOCKET | `/api/collab/ws/{document_id}` | `collaboration.py:327` |
| 134 | GET | `/` | `guardian_api.py:725` |
| 135 | GET | `/agent/agent/ping` | `agent.py:6` |
| 136 | POST | `/research/research` | `research.py:16` |

---

## C) PER-ENDPOINT INTERPRETATION CARDS

---

### Category 1: Health & Observability

---

### 1. General health check
- Endpoint(s): `GET /health`
- What it is: Returns overall application health status.
- Why it matters: Entry point for load balancers, uptime monitors, and liveness probes.
- Inputs needed:
  - No path params
  - No query params
  - No body
  - Auth: unknown (likely unauthenticated for probe access)
- Output artifact:
  - JSON object with health status fields
  - No side effects
- Risk / ambiguity notes:
  - Confirm whether this requires API key or is public

---

### 2. LLM provider health check
- Endpoint(s): `GET /health/llm`, `GET /api/health/llm`
- What it is: Checks connectivity and responsiveness of the backing LLM provider.
- Why it matters: Early warning for LLM outages that would degrade chat functionality.
- Inputs needed:
  - No params or body
  - Auth: unknown
- Output artifact:
  - JSON with LLM provider status, latency, model availability
  - No side effects
- Risk / ambiguity notes:
  - Dual-path alias (with and without `/api` prefix)
  - Response schema unknown

---

### 3. Chat subsystem health check
- Endpoint(s): `GET /health/chat`
- What it is: Verifies that the chat subsystem (DB, message pipeline) is operational.
- Why it matters: Isolates chat-specific failures from general health.
- Inputs needed:
  - No params or body
  - Auth: unknown
- Output artifact:
  - JSON with chat subsystem status
- Risk / ambiguity notes:
  - Response schema unknown

---

### 4. Memory subsystem health check
- Endpoint(s): `GET /health/memory`
- What it is: Checks memory/knowledge-base storage layer health.
- Why it matters: Memory is a dependency for RAG and personal fact retrieval.
- Inputs needed:
  - No params or body
  - Auth: unknown
- Output artifact:
  - JSON with memory subsystem status
- Risk / ambiguity notes:
  - There is also `/api/memory/health/memory` in the memory router — possible overlap

---

### 5. Vector store health check
- Endpoint(s): `GET /health/vector`
- What it is: Checks vector database connectivity (embeddings store).
- Why it matters: Embedding search depends on vector store uptime.
- Inputs needed:
  - No params or body
  - Auth: unknown
- Output artifact:
  - JSON with vector store status
- Risk / ambiguity notes:
  - `retrieve/api.py` also defines `GET /health/vector` but that router is NOT registered (dead code)

---

### 6. Dependency tree health check
- Endpoint(s): `GET /health/deps`
- What it is: Aggregated health check across all subsystem dependencies.
- Why it matters: Single endpoint to determine if all upstream services are healthy.
- Inputs needed:
  - No params or body
  - Auth: unknown
- Output artifact:
  - JSON with per-dependency status map
- Risk / ambiguity notes:
  - Response schema unknown; unclear which deps are checked

---

### 7. Prometheus metrics endpoint
- Endpoint(s): `GET /metrics`
- What it is: Exposes application metrics in a scrapeable format.
- Why it matters: Required for observability dashboards and alerting.
- Inputs needed:
  - No params or body
  - Auth: unknown (should be restricted in production)
- Output artifact:
  - Metrics payload (format unknown — likely Prometheus text or JSON)
- Risk / ambiguity notes:
  - Exposing metrics without auth is a security concern

---

### 8. Lightweight ping
- Endpoint(s): `GET /ping`
- What it is: Minimal liveness check returning a static response.
- Why it matters: Fastest possible check for load balancer health probes.
- Inputs needed:
  - None
  - Auth: unknown
- Output artifact:
  - Static JSON response (e.g., `{"status": "ok"}`)
- Risk / ambiguity notes:
  - Overlaps conceptually with `/health` and `/healthz`

---

### 9. Kubernetes-style health check
- Endpoint(s): `GET /healthz`
- What it is: Kubernetes-convention liveness/readiness probe endpoint.
- Why it matters: Standard path expected by K8s orchestrators.
- Inputs needed:
  - None
  - Auth: unknown
- Output artifact:
  - JSON or plain text health status
- Risk / ambiguity notes:
  - Overlaps with `/health` and `/ping` — three separate health endpoints for the same purpose

---

### 10. Backfill process status
- Endpoint(s): `GET /backfill/status`
- What it is: Reports the current status of any running backfill operations.
- Why it matters: Operators need visibility into long-running data migration/backfill jobs.
- Inputs needed:
  - No params or body
  - Auth: unknown
- Output artifact:
  - JSON with backfill job status, progress
- Risk / ambiguity notes:
  - Response schema unknown; unclear what triggers a backfill

---

### Category 2: Auth & Session

---

### 11. Create API session (token-based)
- Endpoint(s): `POST /auth/session`
- What it is: Creates a new authenticated session and returns a session token.
- Why it matters: Primary authentication entry point; all authed endpoints depend on this.
- Inputs needed:
  - Body: credentials (format unknown)
  - Auth: none (this IS the auth endpoint)
- Output artifact:
  - JSON with session token / API key
  - Session record created in DB
- Risk / ambiguity notes:
  - Request/response schema unknown
  - Rate limiting status unknown
  - No visible CSRF protection mentioned

---

### 12. Create session via cookie
- Endpoint(s): `POST /auth/session/cookie`
- What it is: Creates a session and sets an HTTP cookie for browser-based auth.
- Why it matters: Enables browser/UI clients to authenticate without manual token management.
- Inputs needed:
  - Body: credentials (format unknown)
  - Auth: none
- Output artifact:
  - Set-Cookie header with session cookie
  - Session record created in DB
- Risk / ambiguity notes:
  - Cookie security flags (HttpOnly, Secure, SameSite) unknown
  - Request schema unknown

---

### 13. Authorization debug info
- Endpoint(s): `GET /authz/debug`
- What it is: Returns authorization/permission debugging information for the current session.
- Why it matters: Enables developers to troubleshoot permission issues.
- Inputs needed:
  - Auth: likely requires API key
- Output artifact:
  - JSON with current auth context, permissions, roles
- Risk / ambiguity notes:
  - Should be restricted to dev/admin environments only
  - Exposing auth internals in production is a security risk

---

### Category 3: Chat, Threads & Projects

---

### 14. List legacy threads
- Endpoint(s): `GET /threads`
- What it is: Returns a list of legacy thread records from the chatlog DB.
- Why it matters: Provides thread listing for the legacy thread lineage system.
- Inputs needed:
  - Auth: requires API key (`require_api_key` dependency)
- Output artifact:
  - `{"threads": [...]}` array of thread objects
- Risk / ambiguity notes:
  - `chat.py` also defines a `threads_router` with `GET /threads` but it is NOT registered — only this `threads.py` version is active
  - Thread object shape delegated to chatlog_db implementation; schema unknown

---

### 15. Create legacy thread
- Endpoint(s): `POST /threads`
- What it is: Creates a new legacy thread row in the chatlog DB.
- Why it matters: Entry point for creating conversation lineage in the legacy system.
- Inputs needed:
  - Body: `{"title": str?, "project_id": str?}`
  - Auth: requires API key
- Output artifact:
  - `{"thread_id": int}` — the created thread's integer ID
  - Thread row inserted in DB
- Risk / ambiguity notes:
  - Returns integer thread_id while chat system uses string UUIDs — possible type mismatch

---

### 16. List projects
- Endpoint(s): `GET /projects`
- What it is: Returns all projects for organizing threads.
- Why it matters: Projects provide organizational structure for thread grouping.
- Inputs needed:
  - Auth: likely requires API key
- Output artifact:
  - JSON array of project objects
- Risk / ambiguity notes:
  - `api_router` (prefix `/api/projects`) exists in `projects.py` but is NOT imported — no `/api/projects` alias
  - Response schema unknown

---

### 17. Update project
- Endpoint(s): `PATCH /projects/{project_id}`
- What it is: Updates a project's metadata (name, settings).
- Why it matters: Allows renaming or reconfiguring project organization.
- Inputs needed:
  - Path: `project_id` (string)
  - Body: partial project update fields (unknown schema)
  - Auth: likely requires API key
- Output artifact:
  - Updated project object
- Risk / ambiguity notes:
  - No `/api/projects/{project_id}` alias active

---

### 18. Delete project
- Endpoint(s): `DELETE /projects/{project_id}`
- What it is: Removes a project and presumably unlinks its threads.
- Why it matters: Cleanup for project-based organization.
- Inputs needed:
  - Path: `project_id` (string)
  - Auth: likely requires API key
- Output artifact:
  - Confirmation response
  - Project record deleted; thread re-assignment behavior unknown
- Risk / ambiguity notes:
  - Cascade behavior unknown — do threads become orphaned or deleted?

---

### 19. Send chat message (simple)
- Endpoint(s): `POST /chat`, `POST /api/chat`
- What it is: Sends a single chat message and returns the AI response.
- Why it matters: Primary conversational interface — the core product interaction.
- Inputs needed:
  - Body: message payload (format unknown — likely `{"message": str}` or similar)
  - Auth: likely requires API key
- Output artifact:
  - AI response JSON
  - Message stored in conversation history
- Risk / ambiguity notes:
  - Two separate handler functions (simple_chat_router vs api_chat_router) — may have different behavior
  - Request/response schema unknown

---

### 20. Stream chat response
- Endpoint(s): `GET /chat/stream`
- What it is: Server-Sent Events stream for receiving chat responses in real-time.
- Why it matters: Enables streaming UI for progressive response display.
- Inputs needed:
  - Query params: unknown (likely thread_id, message context)
  - Auth: unknown
- Output artifact:
  - SSE stream of response chunks
- Risk / ambiguity notes:
  - No `/api/chat/stream` alias exists
  - GET with side effects (sends a message?) — unusual; may be read-only stream

---

### 21. Create chat thread
- Endpoint(s): `POST /chat/threads`, `POST /api/chat/threads`
- What it is: Creates a new chat thread (conversation container).
- Why it matters: Required before sending messages — threads organize conversations.
- Inputs needed:
  - Body: thread creation payload (unknown schema)
  - Auth: likely requires API key
- Output artifact:
  - New thread object with ID
  - Thread record created in DB
- Risk / ambiguity notes:
  - Separate from `POST /threads` (legacy) — two thread creation paths exist

---

### 22. List chat threads
- Endpoint(s): `GET /chat/threads`, `GET /api/chat/threads`
- What it is: Returns a list of chat threads.
- Why it matters: Thread listing for the chat UI sidebar.
- Inputs needed:
  - Query params: pagination, filters (unknown)
  - Auth: likely requires API key
- Output artifact:
  - JSON array of thread summaries
- Risk / ambiguity notes:
  - Separate from `GET /threads` (legacy) — two thread listing paths exist

---

### 23. Post message to thread
- Endpoint(s): `POST /chat/{thread_id}/messages`, `POST /api/chat/{thread_id}/messages`
- What it is: Sends a new user message to a specific thread, triggering AI completion.
- Why it matters: Core messaging endpoint — every conversation turn goes through this.
- Inputs needed:
  - Path: `thread_id` (string)
  - Body: message content (unknown schema)
  - Auth: likely requires API key
- Output artifact:
  - AI response message
  - User + assistant messages stored in thread
  - Possible event emission
- Risk / ambiguity notes:
  - Request/response schema unknown
  - Streaming behavior unclear (does this return complete response or use SSE?)

---

### 24. Get thread messages
- Endpoint(s): `GET /chat/{thread_id}/messages`, `GET /api/chat/{thread_id}/messages`
- What it is: Retrieves the message history for a thread.
- Why it matters: Required for loading conversation history in the UI.
- Inputs needed:
  - Path: `thread_id` (string)
  - Query: pagination params (unknown)
  - Auth: likely requires API key
- Output artifact:
  - JSON array of messages with roles, content, timestamps
- Risk / ambiguity notes:
  - Message schema unknown

---

### 25. Complete thread (AI response)
- Endpoint(s): `POST /chat/{thread_id}/complete`, `POST /api/chat/{thread_id}/complete`
- What it is: Triggers AI completion for the most recent message in a thread.
- Why it matters: Allows decoupled message posting and AI response generation.
- Inputs needed:
  - Path: `thread_id` (string)
  - Body: completion params (unknown)
  - Auth: likely requires API key
- Output artifact:
  - AI-generated response message
  - Message appended to thread
- Risk / ambiguity notes:
  - Relationship to `POST /chat/{thread_id}/messages` unclear — possible overlap

---

### 26. Delete specific message
- Endpoint(s): `DELETE /chat/{thread_id}/messages/{message_id}`, `DELETE /api/chat/{thread_id}/messages/{message_id}`
- What it is: Removes a specific message from a thread.
- Why it matters: Allows users to retract or clean up messages.
- Inputs needed:
  - Path: `thread_id`, `message_id`
  - Auth: likely requires API key
- Output artifact:
  - Confirmation response
  - Message record deleted
- Risk / ambiguity notes:
  - Impact on downstream messages (AI responses that reference deleted message) unknown

---

### 27. Branch thread
- Endpoint(s): `POST /chat/{thread_id}/branch`, `POST /api/chat/{thread_id}/branch`
- What it is: Creates a new thread branching from an existing conversation point.
- Why it matters: Enables conversation forking for exploring alternative response paths.
- Inputs needed:
  - Path: `thread_id`
  - Body: branch point specification (unknown)
  - Auth: likely requires API key
- Output artifact:
  - New thread object (the branch)
  - Parent-child relationship stored
- Risk / ambiguity notes:
  - Branch point specification unknown — by message_id? by index?

---

### 28. Update thread metadata
- Endpoint(s): `PATCH /chat/{thread_id}`, `PATCH /api/chat/{thread_id}`
- What it is: Updates thread properties like title, metadata, or settings.
- Why it matters: Allows renaming threads, updating status, changing thread config.
- Inputs needed:
  - Path: `thread_id`
  - Body: partial update fields (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Updated thread object
- Risk / ambiguity notes:
  - There is also `PATCH /chat/threads/{thread_id}` (#29) — two PATCH endpoints for threads with different path structures

---

### 29. Update thread metadata (alternate path)
- Endpoint(s): `PATCH /chat/threads/{thread_id}`, `PATCH /api/chat/threads/{thread_id}`
- What it is: Updates thread properties — appears to be an alternate path for the same operation as #28.
- Why it matters: Provides a more RESTful path structure for thread updates.
- Inputs needed:
  - Path: `thread_id`
  - Body: partial update fields (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Updated thread object
- Risk / ambiguity notes:
  - **Possible duplicate** of #28 (`PATCH /chat/{thread_id}`) — two paths, potentially same handler
  - Naming inconsistency: `/chat/{id}` vs `/chat/threads/{id}`

---

### 30. Delete thread (short path)
- Endpoint(s): `DELETE /chat/{thread_id}`
- What it is: Deletes an entire chat thread and its messages.
- Why it matters: Conversation cleanup and data removal.
- Inputs needed:
  - Path: `thread_id`
  - Auth: likely requires API key
- Output artifact:
  - Confirmation response
  - Thread and messages deleted
- Risk / ambiguity notes:
  - **Path inconsistency** with #31 — this uses `/chat/{id}`, the API version uses `/chat/threads/{id}`
  - No `/api/chat/{thread_id}` DELETE alias exists

---

### 31. Delete thread (API path)
- Endpoint(s): `DELETE /api/chat/threads/{thread_id}`
- What it is: Deletes a chat thread — API-prefixed version with different path structure.
- Why it matters: Same purpose as #30 but under the `/api` prefix with `/threads/` in path.
- Inputs needed:
  - Path: `thread_id`
  - Auth: likely requires API key
- Output artifact:
  - Confirmation response
  - Thread and messages deleted
- Risk / ambiguity notes:
  - **NOT an alias of #30** — path structure differs (`/chat/threads/{id}` vs `/chat/{id}`)
  - Likely routes to a different handler; may have different behavior
  - Clients must choose which delete path to use

---

### 32. RAG trace debug for thread
- Endpoint(s): `GET /chat/debug/rag-trace/{thread_id}/latest`, `GET /api/chat/debug/rag-trace/{thread_id}/latest`
- What it is: Returns the most recent RAG (retrieval-augmented generation) trace for a thread.
- Why it matters: Critical for debugging retrieval quality and understanding what context the AI used.
- Inputs needed:
  - Path: `thread_id`
  - Auth: likely requires API key
- Output artifact:
  - RAG trace object with retrieved chunks, scores, selected context
- Risk / ambiguity notes:
  - Debug endpoint — should be restricted in production
  - Response schema unknown

---

### Category 4: Memory & Knowledge

---

### 33. Memory subsystem health (via memory router)
- Endpoint(s): `GET /api/memory/health/memory`
- What it is: Health check for the memory subsystem, exposed under the memory API prefix.
- Why it matters: Allows memory-specific health monitoring separate from the global health endpoints.
- Inputs needed:
  - Auth: likely requires API key
- Output artifact:
  - JSON with memory store health status
- Risk / ambiguity notes:
  - Overlaps with `GET /health/memory` from the health router — two endpoints checking the same thing

---

### 34. List memory entries by silo
- Endpoint(s): `GET /api/memory/{silo}`
- What it is: Retrieves all memory entries within a named silo (partition).
- Why it matters: Silos organize knowledge by category; listing is required for browsing and management.
- Inputs needed:
  - Path: `silo` (string — silo name/identifier)
  - Query: pagination, filters (unknown)
  - Auth: likely requires API key
- Output artifact:
  - JSON array of memory entries
- Risk / ambiguity notes:
  - Valid silo names unknown — no enumeration endpoint visible
  - Potential path collision with `/api/memory/health/memory` if silo is named "health"

---

### 35. Create memory entry
- Endpoint(s): `POST /api/memory/{silo}`
- What it is: Stores a new memory entry in the specified silo.
- Why it matters: Core write path for the knowledge base — all learned information goes through this.
- Inputs needed:
  - Path: `silo`
  - Body: memory entry payload (unknown schema)
  - Auth: likely requires API key
- Output artifact:
  - Created entry object with ID
  - Entry stored in memory DB
  - Possible embedding generated
- Risk / ambiguity notes:
  - Request schema unknown
  - Unclear if embeddings are auto-generated on write

---

### 36. Update memory entry
- Endpoint(s): `PATCH /api/memory/{silo}/{entry_id}`
- What it is: Partially updates an existing memory entry.
- Why it matters: Allows correcting or enriching stored knowledge.
- Inputs needed:
  - Path: `silo`, `entry_id`
  - Body: partial update fields
  - Auth: likely requires API key
- Output artifact:
  - Updated entry object
- Risk / ambiguity notes:
  - Whether embedding is re-generated on update unknown

---

### 37. Delete memory entry
- Endpoint(s): `DELETE /api/memory/{silo}/{entry_id}`
- What it is: Removes a memory entry from the specified silo.
- Why it matters: Knowledge cleanup and correction.
- Inputs needed:
  - Path: `silo`, `entry_id`
  - Auth: likely requires API key
- Output artifact:
  - Confirmation response
  - Entry + associated embedding deleted
- Risk / ambiguity notes:
  - Cascade to embeddings/vector store unknown

---

### 38. Generate embeddings
- Endpoint(s): `POST /api/embeddings`
- What it is: Generates vector embeddings for provided text.
- Why it matters: Embeddings power semantic search and RAG across the entire system.
- Inputs needed:
  - Body: text content to embed (unknown schema)
  - Auth: likely requires API key
- Output artifact:
  - JSON with embedding vector(s)
- Risk / ambiguity notes:
  - Embedding model and dimensions unknown
  - Rate limiting / cost implications unknown

---

### 39. List personal facts
- Endpoint(s): `GET /personal-facts`
- What it is: Returns all personal facts stored about the user.
- Why it matters: Personal facts power personalized AI responses and user modeling.
- Inputs needed:
  - Query: filters (unknown)
  - Auth: likely requires API key
- Output artifact:
  - JSON array of personal fact objects
- Risk / ambiguity notes:
  - No `/api` prefix — inconsistent with other knowledge endpoints

---

### 40. Create personal fact
- Endpoint(s): `POST /personal-facts`
- What it is: Stores a new personal fact about the user.
- Why it matters: Enables explicit user preference and information capture.
- Inputs needed:
  - Body: fact payload (unknown schema)
  - Auth: likely requires API key
- Output artifact:
  - Created fact object with ID
- Risk / ambiguity notes:
  - PII storage — privacy/GDPR implications

---

### 41. Get specific personal fact
- Endpoint(s): `GET /personal-facts/{fact_id}`
- What it is: Retrieves a single personal fact by ID.
- Why it matters: Needed for fact detail views and edit workflows.
- Inputs needed:
  - Path: `fact_id`
  - Auth: likely requires API key
- Output artifact:
  - Personal fact object
- Risk / ambiguity notes:
  - None

---

### 42. Update personal fact
- Endpoint(s): `PATCH /personal-facts/{fact_id}`
- What it is: Updates an existing personal fact.
- Why it matters: Allows correcting inaccurate personal information.
- Inputs needed:
  - Path: `fact_id`
  - Body: partial update fields
  - Auth: likely requires API key
- Output artifact:
  - Updated fact object
  - Revision record created (see #47)
- Risk / ambiguity notes:
  - None

---

### 43. Confirm personal fact
- Endpoint(s): `POST /personal-facts/{fact_id}/confirm`
- What it is: Marks a personal fact as confirmed/verified by the user.
- Why it matters: Confirmation increases the fact's weight in AI reasoning.
- Inputs needed:
  - Path: `fact_id`
  - Auth: likely requires API key
- Output artifact:
  - Updated fact with confirmed status
- Risk / ambiguity notes:
  - None

---

### 44. Dispute personal fact
- Endpoint(s): `POST /personal-facts/{fact_id}/dispute`
- What it is: Marks a personal fact as disputed/incorrect.
- Why it matters: Allows users to flag incorrect inferences before deletion.
- Inputs needed:
  - Path: `fact_id`
  - Body: dispute reason (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Updated fact with disputed status
- Risk / ambiguity notes:
  - Effect of dispute on AI behavior unknown

---

### 45. List evidence for personal fact
- Endpoint(s): `GET /personal-facts/{fact_id}/evidence`
- What it is: Returns supporting evidence (conversation excerpts, sources) for a fact.
- Why it matters: Transparency — shows users why the system believes a fact.
- Inputs needed:
  - Path: `fact_id`
  - Auth: likely requires API key
- Output artifact:
  - JSON array of evidence objects
- Risk / ambiguity notes:
  - Evidence object schema unknown

---

### 46. Add evidence for personal fact
- Endpoint(s): `POST /personal-facts/{fact_id}/evidence`
- What it is: Attaches new evidence supporting a personal fact.
- Why it matters: Strengthens fact reliability through additional sourcing.
- Inputs needed:
  - Path: `fact_id`
  - Body: evidence payload (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Created evidence object
- Risk / ambiguity notes:
  - None

---

### 47. List revisions for personal fact
- Endpoint(s): `GET /personal-facts/{fact_id}/revisions`
- What it is: Returns the revision history of a personal fact.
- Why it matters: Audit trail for how personal knowledge has evolved.
- Inputs needed:
  - Path: `fact_id`
  - Auth: likely requires API key
- Output artifact:
  - JSON array of revision objects with timestamps
- Risk / ambiguity notes:
  - None

---

### 48. Codexify content
- Endpoint(s): `POST /codexify`
- What it is: Processes and indexes content into the Codexify knowledge system.
- Why it matters: Primary ingestion path for turning raw content into structured knowledge.
- Inputs needed:
  - Body: content payload (unknown schema)
  - Auth: unknown
- Output artifact:
  - Processed/indexed content record
- Risk / ambiguity notes:
  - No `/api` prefix — inconsistent naming
  - Request schema unknown

---

### 49. Embed content
- Endpoint(s): `POST /embed`
- What it is: Generates and stores embeddings for content.
- Why it matters: Parallel embedding path alongside `/api/embeddings` — purpose overlap unclear.
- Inputs needed:
  - Body: content to embed (unknown)
  - Auth: unknown
- Output artifact:
  - Embedding stored
- Risk / ambiguity notes:
  - **Possible duplicate** of `POST /api/embeddings` (#38) — different path, potentially different behavior
  - No `/api` prefix

---

### 50. Search knowledge base
- Endpoint(s): `POST /search`
- What it is: Performs semantic search across the indexed knowledge base.
- Why it matters: Core retrieval endpoint for RAG and user-facing search.
- Inputs needed:
  - Body: search query (unknown schema)
  - Auth: unknown
- Output artifact:
  - JSON array of search results with relevance scores
- Risk / ambiguity notes:
  - No `/api` prefix
  - `memory.py` also defines `GET /search` in an unregistered router — different method

---

### Category 5: Identity & System Configuration

---

### 51. Get imprint status
- Endpoint(s): `GET /api/imprint/status`
- What it is: Returns the current status of the AI's identity imprint (personality configuration).
- Why it matters: Shows whether the imprint is active, pending, or needs configuration.
- Inputs needed:
  - Auth: likely requires API key
- Output artifact:
  - JSON with imprint state, active persona details
- Risk / ambiguity notes:
  - Response schema unknown

---

### 52. Propose imprint change
- Endpoint(s): `POST /api/imprint/proposal`
- What it is: Submits a proposal to modify the AI's identity/personality imprint.
- Why it matters: Enables guided, reviewable changes to the system's personality.
- Inputs needed:
  - Body: imprint proposal (unknown schema)
  - Auth: likely requires API key
- Output artifact:
  - Proposal object with ID, pending status
- Risk / ambiguity notes:
  - Proposal workflow unclear — who reviews?

---

### 53. Accept imprint proposal
- Endpoint(s): `POST /api/imprint/accept`
- What it is: Approves and applies a pending imprint proposal.
- Why it matters: Completes the imprint change workflow, activating new personality traits.
- Inputs needed:
  - Body: proposal reference (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Confirmation; imprint updated
  - System prompt may be regenerated
- Risk / ambiguity notes:
  - Unclear if this takes a proposal_id in body or applies the latest proposal

---

### 54. Reject imprint proposal
- Endpoint(s): `POST /api/imprint/reject`
- What it is: Rejects a pending imprint proposal.
- Why it matters: Allows vetoing unwanted personality changes.
- Inputs needed:
  - Body: proposal reference, rejection reason (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Proposal marked as rejected
- Risk / ambiguity notes:
  - None

---

### 55. Set persona
- Endpoint(s): `POST /api/imprint/persona`
- What it is: Directly sets the active persona for the AI system.
- Why it matters: Bypass for the proposal workflow — direct persona assignment.
- Inputs needed:
  - Body: persona definition (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Active persona updated
- Risk / ambiguity notes:
  - Relationship to proposal workflow unclear — can this override an active proposal?

---

### 56. Get system prompt summary
- Endpoint(s): `GET /api/system_prompt/summary`
- What it is: Returns a summary of the current system prompt configuration.
- Why it matters: Transparency into what instructions the AI is operating under.
- Inputs needed:
  - Auth: likely requires API key
- Output artifact:
  - JSON with system prompt summary/metadata
- Risk / ambiguity notes:
  - May expose sensitive system prompt content

---

### 57. List system documentation
- Endpoint(s): `GET /api/system_docs`
- What it is: Returns system documentation entries that inform AI behavior.
- Why it matters: System docs augment the system prompt with domain knowledge.
- Inputs needed:
  - Auth: likely requires API key
- Output artifact:
  - JSON array of system doc entries
- Risk / ambiguity notes:
  - None

---

### 58. Toggle system documentation
- Endpoint(s): `POST /api/system_docs/toggle`
- What it is: Enables or disables specific system documentation entries.
- Why it matters: Controls which knowledge sources are active in the system prompt.
- Inputs needed:
  - Body: doc identifier + toggle state (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Updated doc state
- Risk / ambiguity notes:
  - Request schema unknown

---

### 59. Get IDDB settings
- Endpoint(s): `GET /api/iddb/settings`
- What it is: Retrieves identity database settings.
- Why it matters: IDDB settings control user identity resolution and matching behavior.
- Inputs needed:
  - Auth: likely requires API key
- Output artifact:
  - JSON settings object
- Risk / ambiguity notes:
  - "IDDB" is an internal term — unclear scope

---

### 60. Update IDDB settings
- Endpoint(s): `POST /api/iddb/settings`
- What it is: Updates identity database settings.
- Why it matters: Configures identity resolution behavior.
- Inputs needed:
  - Body: settings payload (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Updated settings object
- Risk / ambiguity notes:
  - POST for update (not PATCH) — convention inconsistency

---

### Category 6: Media & Generation

---

### 61. List all images
- Endpoint(s): `GET /api/media/images`
- What it is: Returns a paginated list of all uploaded images.
- Why it matters: Gallery/browser view for media management.
- Inputs needed:
  - Query: pagination (unknown)
  - Auth: likely requires API key
- Output artifact:
  - JSON array of image metadata objects
- Risk / ambiguity notes:
  - None

---

### 62. List all documents
- Endpoint(s): `GET /api/media/documents`
- What it is: Returns a paginated list of all uploaded documents.
- Why it matters: Document library view for media management.
- Inputs needed:
  - Query: pagination (unknown)
  - Auth: likely requires API key
- Output artifact:
  - JSON array of document metadata objects
- Risk / ambiguity notes:
  - None

---

### 63. Upload image
- Endpoint(s): `POST /api/media/upload/image`
- What it is: Uploads an image file to the media storage system.
- Why it matters: Enables image attachments in conversations and documents.
- Inputs needed:
  - Body: multipart file upload
  - Auth: likely requires API key
- Output artifact:
  - Image metadata object with ID, URL
  - File stored in media storage
- Risk / ambiguity notes:
  - File size limits unknown
  - Accepted formats unknown
  - Virus scanning unknown

---

### 64. Get image by ID
- Endpoint(s): `GET /api/media/images/{image_id}`
- What it is: Retrieves a specific image's metadata or binary content.
- Why it matters: Image serving for display in UI.
- Inputs needed:
  - Path: `image_id`
  - Auth: unknown
- Output artifact:
  - Image metadata or binary file
- Risk / ambiguity notes:
  - Unclear if this returns metadata JSON or the actual image binary

---

### 65. Delete image
- Endpoint(s): `DELETE /api/media/images/{image_id}`
- What it is: Removes an image from media storage.
- Why it matters: Storage cleanup and content removal.
- Inputs needed:
  - Path: `image_id`
  - Auth: likely requires API key
- Output artifact:
  - Confirmation; file deleted from storage
- Risk / ambiguity notes:
  - Cascade to messages referencing this image unknown

---

### 66. Upload document
- Endpoint(s): `POST /api/media/upload/document`
- What it is: Uploads a document file (PDF, DOCX, etc.) to media storage.
- Why it matters: Enables document attachments and potential RAG ingestion.
- Inputs needed:
  - Body: multipart file upload
  - Auth: likely requires API key
- Output artifact:
  - Document metadata with ID
  - File stored
- Risk / ambiguity notes:
  - Accepted document types unknown
  - Whether auto-indexing for RAG occurs unknown

---

### 67. Generate image via AI
- Endpoint(s): `POST /api/media/generate/image`
- What it is: Generates an AI image based on a text prompt.
- Why it matters: Enables AI art/illustration generation within the platform.
- Inputs needed:
  - Body: generation prompt + parameters (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Generated image metadata with URL
  - Image stored in media storage
- Risk / ambiguity notes:
  - Image generation provider unknown
  - Cost implications unknown

---

### 68. Synthesize text-to-speech
- Endpoint(s): `POST /api/media/tts/synthesize`
- What it is: Converts text to speech audio.
- Why it matters: Enables audio responses and voice interaction.
- Inputs needed:
  - Body: text + voice parameters (unknown)
  - Auth: likely requires API key
- Output artifact:
  - TTS job/audio metadata with ID
  - Audio file generated and stored
- Risk / ambiguity notes:
  - TTS provider unknown
  - Separate TTS microservice exists (`backend/tts_service/app.py`)

---

### 69. Get TTS audio result
- Endpoint(s): `GET /api/media/tts/{tts_id}`
- What it is: Retrieves a previously generated TTS audio file or metadata.
- Why it matters: Fetches the result of an async TTS synthesis job.
- Inputs needed:
  - Path: `tts_id`
  - Auth: unknown
- Output artifact:
  - Audio file or metadata JSON
- Risk / ambiguity notes:
  - Return format unclear (binary audio vs metadata)

---

### 70. Resolve media reference
- Endpoint(s): `GET /api/media/resolve`
- What it is: Resolves a media reference (URL, ID, or path) to its canonical form.
- Why it matters: Normalizes media references across different storage backends.
- Inputs needed:
  - Query: media reference identifier (unknown)
  - Auth: unknown
- Output artifact:
  - Resolved media URL or metadata
- Risk / ambiguity notes:
  - Query parameter format unknown

---

### Category 7: Connectors & Integration

---

### 71. Connectors health check
- Endpoint(s): `GET /api/connectors/health`
- What it is: Health check for the connectors subsystem.
- Why it matters: Monitors the health of external service connections.
- Inputs needed:
  - Auth: likely requires API key
- Output artifact:
  - JSON with connector subsystem health
- Risk / ambiguity notes:
  - Could collide with `GET /api/connectors/{connector_name}` if FastAPI route ordering is wrong

---

### 72. Connector worker statistics
- Endpoint(s): `GET /api/connectors/worker/stats`
- What it is: Returns statistics for the background connector worker process.
- Why it matters: Monitoring connector sync job throughput and queue depth.
- Inputs needed:
  - Auth: likely requires API key
- Output artifact:
  - JSON with worker stats (jobs processed, queue size, errors)
- Risk / ambiguity notes:
  - None

---

### 73. List all connectors
- Endpoint(s): `GET /api/connectors`
- What it is: Returns all configured connector integrations.
- Why it matters: Shows which external services are connected.
- Inputs needed:
  - Auth: likely requires API key
- Output artifact:
  - JSON array of connector objects
- Risk / ambiguity notes:
  - None

---

### 74. Register new connector
- Endpoint(s): `POST /api/connectors`
- What it is: Creates a new connector integration configuration.
- Why it matters: Entry point for connecting external services.
- Inputs needed:
  - Body: connector config (type, name, credentials — unknown schema)
  - Auth: likely requires API key
- Output artifact:
  - Created connector object
- Risk / ambiguity notes:
  - Credential storage mechanism unknown

---

### 75. Get connector details
- Endpoint(s): `GET /api/connectors/{connector_name}`
- What it is: Retrieves details for a specific connector.
- Why it matters: Needed for connector management UI.
- Inputs needed:
  - Path: `connector_name`
  - Auth: likely requires API key
- Output artifact:
  - Connector detail object
- Risk / ambiguity notes:
  - Uses name (not ID) as path param — names must be unique

---

### 76. Update connector
- Endpoint(s): `PATCH /api/connectors/{connector_name}`
- What it is: Updates connector configuration.
- Why it matters: Allows modifying connection settings without recreating.
- Inputs needed:
  - Path: `connector_name`
  - Body: partial update (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Updated connector object
- Risk / ambiguity notes:
  - None

---

### 77. Set connector config
- Endpoint(s): `POST /api/connectors/{connector_name}/config`
- What it is: Sets or replaces the full configuration for a connector.
- Why it matters: Full config replacement for connectors that need complete reconfiguration.
- Inputs needed:
  - Path: `connector_name`
  - Body: complete config object (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Updated config confirmation
- Risk / ambiguity notes:
  - Overlap with PATCH (#76) — PATCH vs POST config unclear

---

### 78. Test connector
- Endpoint(s): `POST /api/connectors/{connector_name}/test`
- What it is: Tests connectivity to the external service.
- Why it matters: Validates credentials and connectivity before relying on the connector.
- Inputs needed:
  - Path: `connector_name`
  - Auth: likely requires API key
- Output artifact:
  - JSON with test result (success/failure, latency, error details)
- Risk / ambiguity notes:
  - None

---

### 79. Sync connector data
- Endpoint(s): `POST /api/connectors/{connector_name}/sync`
- What it is: Triggers a data synchronization from the external service.
- Why it matters: Pulls latest data from connected services into the knowledge base.
- Inputs needed:
  - Path: `connector_name`
  - Body: sync options (full/incremental — unknown)
  - Auth: likely requires API key
- Output artifact:
  - Sync job status/ID
  - Data ingested in background
- Risk / ambiguity notes:
  - Async behavior; completion tracking unknown

---

### 80. Authorize connector (OAuth)
- Endpoint(s): `POST /api/connectors/{connector_name}/authorize`
- What it is: Initiates OAuth authorization flow for a connector.
- Why it matters: Required for connectors that use OAuth (Google, GitHub, etc.).
- Inputs needed:
  - Path: `connector_name`
  - Body: authorization params (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Authorization URL or confirmation
- Risk / ambiguity notes:
  - OAuth callback handling unknown — `google.py` has callback routes but they're not registered

---

### 81. Get connector status
- Endpoint(s): `GET /api/connectors/{connector_name}/status`
- What it is: Returns current operational status of a connector.
- Why it matters: Shows sync state, last sync time, error status.
- Inputs needed:
  - Path: `connector_name`
  - Auth: likely requires API key
- Output artifact:
  - Status object with last_sync, error_count, state
- Risk / ambiguity notes:
  - None

---

### 82. Ingest data via connector
- Endpoint(s): `POST /api/connectors/{name}/ingest`
- What it is: Manually pushes data into the system through a connector's ingestion pipeline.
- Why it matters: Enables manual data loading without a full sync.
- Inputs needed:
  - Path: `name` (note: uses `name` not `connector_name` — inconsistency)
  - Body: data payload (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Ingestion confirmation
- Risk / ambiguity notes:
  - **Path param naming inconsistency**: uses `{name}` while all other connector routes use `{connector_name}`

---

### Category 8: Federation & Graph

---

### 83. Get federation manifest
- Endpoint(s): `GET /api/federation/manifest`
- What it is: Returns this instance's federation identity, capabilities, and protocol version.
- Why it matters: Required for peer discovery and capability negotiation.
- Inputs needed:
  - Auth: unknown (may be public for peer discovery)
- Output artifact:
  - JSON manifest with instance ID, supported features, version
- Risk / ambiguity notes:
  - None

---

### 84. Get federation graph statistics
- Endpoint(s): `GET /api/federation/graph/stats`
- What it is: Returns statistics about the federated knowledge graph.
- Why it matters: Monitoring federated graph health and size.
- Inputs needed:
  - Auth: likely requires API key
- Output artifact:
  - JSON with node/edge counts, sync status
- Risk / ambiguity notes:
  - None

---

### 85. Request federation session
- Endpoint(s): `POST /api/federation/session/request`
- What it is: Initiates a federation session request to establish a peer connection.
- Why it matters: First step in the federation handshake — establishes trust.
- Inputs needed:
  - Body: peer identity, requested scopes (unknown)
  - Auth: unknown
- Output artifact:
  - Session request token/ID
  - Pending session record created
- Risk / ambiguity notes:
  - Trust model and validation unknown

---

### 86. Accept federation session
- Endpoint(s): `POST /api/federation/session/accept`
- What it is: Accepts an incoming federation session request.
- Why it matters: Completes the federation handshake, enabling data exchange.
- Inputs needed:
  - Body: session request ID, acceptance params (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Active session confirmation
  - Bi-directional sync enabled
- Risk / ambiguity notes:
  - Authorization for acceptance unknown — who can accept?

---

### 87. Push federation diff
- Endpoint(s): `POST /api/federation/diff/push`
- What it is: Pushes a set of changes (diff) to federated peers.
- Why it matters: Core data replication mechanism for federation.
- Inputs needed:
  - Body: diff payload (changes since last sync)
  - Auth: federation session token (unknown)
- Output artifact:
  - Push acknowledgment
  - Peer's data updated
- Risk / ambiguity notes:
  - Conflict resolution strategy unknown

---

### 88. Pull federation diff
- Endpoint(s): `GET /api/federation/diff/pull`
- What it is: Retrieves pending changes from a federated peer.
- Why it matters: Complement to push — pulls updates from peers.
- Inputs needed:
  - Query: since timestamp, peer ID (unknown)
  - Auth: federation session token (unknown)
- Output artifact:
  - Diff payload of changes
- Risk / ambiguity notes:
  - None

---

### 89. Update federated graph
- Endpoint(s): `POST /api/federation/graph/update`
- What it is: Applies graph mutations (node/edge changes) from federation.
- Why it matters: Merges federated knowledge graph changes into local graph.
- Inputs needed:
  - Body: graph mutation payload (unknown)
  - Auth: federation session token (unknown)
- Output artifact:
  - Update confirmation
  - Local graph updated
- Risk / ambiguity notes:
  - Merge conflict handling unknown

---

### 90. Get federated graph snapshot
- Endpoint(s): `GET /api/federation/graph/snapshot`
- What it is: Returns a full or partial snapshot of the federated graph.
- Why it matters: Enables full graph synchronization for new peers.
- Inputs needed:
  - Query: scope, filters (unknown)
  - Auth: federation session token (unknown)
- Output artifact:
  - Graph snapshot (nodes + edges)
- Risk / ambiguity notes:
  - Snapshot size could be very large — pagination/streaming unknown

---

### 91. Federation relay WebSocket
- Endpoint(s): `WEBSOCKET /api/federation/relay/{relay_id}`
- What it is: Real-time WebSocket connection for live federation data relay.
- Why it matters: Enables low-latency data exchange between federated instances.
- Inputs needed:
  - Path: `relay_id`
  - Auth: federation session token (unknown)
- Output artifact:
  - Bi-directional WebSocket stream
- Risk / ambiguity notes:
  - WebSocket auth mechanism unknown
  - Connection lifecycle and reconnection unknown

---

### 92. Get knowledge graph visualization
- Endpoint(s): `GET /graph`
- What it is: Returns the local knowledge graph data for visualization.
- Why it matters: Powers the graph visualization UI.
- Inputs needed:
  - Query: filters, depth (unknown)
  - Auth: unknown
- Output artifact:
  - Graph data (nodes + edges) for rendering
- Risk / ambiguity notes:
  - `graph.py` router also defines `GET /graph` but is NOT registered — only the `guardian_api.py` direct route is active

---

### 93. Post Neo4j graph message
- Endpoint(s): `POST /api/neo/graph-message`
- What it is: Sends a message/mutation to the Neo4j graph database.
- Why it matters: Direct graph manipulation for knowledge graph operations.
- Inputs needed:
  - Body: graph message payload (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Graph operation result
- Risk / ambiguity notes:
  - Request schema unknown
  - Direct graph DB access — potential for data corruption

---

### Category 9: Flows & Scheduling

---

### 94. List all flows
- Endpoint(s): `GET /api/flows`
- What it is: Returns all defined automation flows.
- Why it matters: Flow listing for the automation builder UI.
- Inputs needed:
  - Query: pagination, filters (unknown)
  - Auth: likely requires API key
- Output artifact:
  - JSON array of flow objects
- Risk / ambiguity notes:
  - None

---

### 95. Create flow
- Endpoint(s): `POST /api/flows`
- What it is: Creates a new automation flow definition.
- Why it matters: Entry point for building automated workflows.
- Inputs needed:
  - Body: flow definition (steps, triggers — unknown schema)
  - Auth: likely requires API key
- Output artifact:
  - Created flow object with ID
- Risk / ambiguity notes:
  - Flow definition schema unknown

---

### 96. Get flow by ID
- Endpoint(s): `GET /api/flows/{flow_id}`
- What it is: Retrieves a specific flow's full definition.
- Why it matters: Needed for viewing and editing a flow.
- Inputs needed:
  - Path: `flow_id`
  - Auth: likely requires API key
- Output artifact:
  - Complete flow object
- Risk / ambiguity notes:
  - None

---

### 97. Update flow
- Endpoint(s): `PATCH /api/flows/{flow_id}`
- What it is: Updates a flow's definition or metadata.
- Why it matters: Allows iterating on flow design.
- Inputs needed:
  - Path: `flow_id`
  - Body: partial update (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Updated flow object
- Risk / ambiguity notes:
  - None

---

### 98. Validate flow
- Endpoint(s): `POST /api/flows/{flow_id}/validate`
- What it is: Validates a flow definition without executing it.
- Why it matters: Pre-execution check to catch configuration errors.
- Inputs needed:
  - Path: `flow_id`
  - Auth: likely requires API key
- Output artifact:
  - Validation result (valid/invalid + error details)
- Risk / ambiguity notes:
  - None

---

### 99. Execute flow
- Endpoint(s): `POST /api/flows/{flow_id}/run`
- What it is: Triggers execution of a flow.
- Why it matters: Actually runs the automation — the action endpoint.
- Inputs needed:
  - Path: `flow_id`
  - Body: runtime parameters (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Run object with ID and initial status
  - Flow execution begins (async)
- Risk / ambiguity notes:
  - Async execution — completion tracking via run status

---

### 100. List flow runs
- Endpoint(s): `GET /api/flows/{flow_id}/runs`
- What it is: Returns execution history for a specific flow.
- Why it matters: Audit trail and debugging for flow executions.
- Inputs needed:
  - Path: `flow_id`
  - Query: pagination (unknown)
  - Auth: likely requires API key
- Output artifact:
  - JSON array of run objects
- Risk / ambiguity notes:
  - None

---

### 101. Get specific flow run
- Endpoint(s): `GET /api/flows/runs/{run_id}`
- What it is: Retrieves details of a specific flow execution.
- Why it matters: Detailed inspection of a flow run's progress, output, and errors.
- Inputs needed:
  - Path: `run_id`
  - Auth: likely requires API key
- Output artifact:
  - Run detail object with status, output, step results
- Risk / ambiguity notes:
  - None

---

### 102. List cron jobs
- Endpoint(s): `GET /api/cron/jobs`
- What it is: Returns all scheduled cron jobs.
- Why it matters: Schedule management overview.
- Inputs needed:
  - Auth: likely requires API key
- Output artifact:
  - JSON array of cron job objects
- Risk / ambiguity notes:
  - None

---

### 103. Create cron job
- Endpoint(s): `POST /api/cron/jobs`
- What it is: Creates a new scheduled job.
- Why it matters: Enables periodic automation (daily summaries, sync schedules, etc.).
- Inputs needed:
  - Body: cron expression, action config (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Created job object with ID
- Risk / ambiguity notes:
  - Cron expression validation unknown

---

### 104. Get cron job details
- Endpoint(s): `GET /api/cron/jobs/{job_id}`
- What it is: Retrieves a specific cron job's configuration and status.
- Why it matters: Needed for job management and debugging.
- Inputs needed:
  - Path: `job_id`
  - Auth: likely requires API key
- Output artifact:
  - Cron job detail object
- Risk / ambiguity notes:
  - None

---

### 105. Update cron job
- Endpoint(s): `PATCH /api/cron/jobs/{job_id}`
- What it is: Updates a cron job's schedule or action configuration.
- Why it matters: Allows adjusting schedules without recreating jobs.
- Inputs needed:
  - Path: `job_id`
  - Body: partial update (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Updated job object
- Risk / ambiguity notes:
  - None

---

### 106. Delete cron job
- Endpoint(s): `DELETE /api/cron/jobs/{job_id}`
- What it is: Removes a scheduled cron job.
- Why it matters: Cleanup for decommissioned schedules.
- Inputs needed:
  - Path: `job_id`
  - Auth: likely requires API key
- Output artifact:
  - Confirmation; job removed from scheduler
- Risk / ambiguity notes:
  - In-progress run behavior on delete unknown

---

### 107. Trigger cron job manually
- Endpoint(s): `POST /api/cron/jobs/{job_id}/trigger`
- What it is: Manually triggers a cron job execution outside its schedule.
- Why it matters: Testing and on-demand execution of scheduled tasks.
- Inputs needed:
  - Path: `job_id`
  - Auth: likely requires API key
- Output artifact:
  - Triggered run status
- Risk / ambiguity notes:
  - None

---

### 108. List cron job run history
- Endpoint(s): `GET /api/cron/jobs/{job_id}/runs`
- What it is: Returns execution history for a specific cron job.
- Why it matters: Audit trail for scheduled job runs.
- Inputs needed:
  - Path: `job_id`
  - Query: pagination (unknown)
  - Auth: likely requires API key
- Output artifact:
  - JSON array of run records
- Risk / ambiguity notes:
  - None

---

### Category 10: Documents, Codex & Exports

---

### 109. List codex entries
- Endpoint(s): `GET /codex/entries`, `GET /api/codex/entries`
- What it is: Returns all entries in the Codex knowledge repository.
- Why it matters: Codex is the structured knowledge export — listing enables browsing.
- Inputs needed:
  - Auth: unknown
- Output artifact:
  - JSON array of codex entry objects
- Risk / ambiguity notes:
  - Two sources: `guardian_api.py:482` (direct) and `codex.py:40` (router) — both active, creating alias

---

### 110. Get codex entry by ID
- Endpoint(s): `GET /codex/entries/{entry_id}`, `GET /api/codex/entries/{entry_id}`
- What it is: Retrieves a specific codex entry.
- Why it matters: Detail view for individual knowledge entries.
- Inputs needed:
  - Path: `entry_id`
  - Auth: unknown
- Output artifact:
  - Codex entry object
- Risk / ambiguity notes:
  - Dual-source alias (same as #109)

---

### 111. Export codex entry
- Endpoint(s): `GET /codex/entries/{entry_id}/export`, `GET /api/codex/entries/{entry_id}/export`
- What it is: Exports a codex entry in a portable format.
- Why it matters: Enables sharing or archiving individual knowledge entries.
- Inputs needed:
  - Path: `entry_id`
  - Query: export format (unknown)
  - Auth: unknown
- Output artifact:
  - Exported file or formatted data
- Risk / ambiguity notes:
  - Export format(s) unknown

---

### 112. Autosave document
- Endpoint(s): `POST /api/documents/autosave`
- What it is: Auto-saves a document draft during editing.
- Why it matters: Prevents data loss during document composition.
- Inputs needed:
  - Body: document content + metadata (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Save confirmation with timestamp
  - Draft stored
- Risk / ambiguity notes:
  - Autosave frequency/conflict resolution unknown

---

### 113. Generate document via AI
- Endpoint(s): `POST /api/documents/generate`
- What it is: Generates a document based on a prompt or template.
- Why it matters: AI-assisted document creation from conversation context.
- Inputs needed:
  - Body: generation prompt, context, template (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Generated document content
- Risk / ambiguity notes:
  - Request schema unknown

---

### 114. List documents for thread
- Endpoint(s): `GET /api/threads/{thread_id}/documents`
- What it is: Returns all documents associated with a specific thread.
- Why it matters: Links conversation context to generated documents.
- Inputs needed:
  - Path: `thread_id`
  - Auth: likely requires API key
- Output artifact:
  - JSON array of document objects
- Risk / ambiguity notes:
  - None

---

### 115. Create share link
- Endpoint(s): `POST /api/share`
- What it is: Creates a shareable link for content (thread, document, etc.).
- Why it matters: Enables sharing conversations or content externally.
- Inputs needed:
  - Body: content reference, share options (unknown)
  - Auth: likely requires API key
- Output artifact:
  - Share token/URL
  - Share record created
- Risk / ambiguity notes:
  - Expiration policy unknown
  - Access control on shared content unknown

---

### 116. View shared content
- Endpoint(s): `GET /api/share/{token}`
- What it is: Retrieves content via a share token.
- Why it matters: Public-facing endpoint for viewing shared content.
- Inputs needed:
  - Path: `token`
  - Auth: none (token IS the auth)
- Output artifact:
  - Shared content (thread, document, etc.)
- Risk / ambiguity notes:
  - Token entropy and security unknown
  - Rate limiting for public endpoint unknown

---

### 117. Export threads as NDJSON
- Endpoint(s): `GET /exports/threads.ndjson`
- What it is: Exports all threads in newline-delimited JSON format.
- Why it matters: Bulk data export for backup, analysis, or migration.
- Inputs needed:
  - Auth: likely requires API key
- Output artifact:
  - Streaming NDJSON file
- Risk / ambiguity notes:
  - Could be very large — streaming/pagination unknown
  - PII exposure in export

---

### 118. Import ChatGPT export
- Endpoint(s): `POST /upload-chatgpt-export`, `POST /api/upload-chatgpt-export`
- What it is: Imports a ChatGPT conversation export file.
- Why it matters: Migration path for users switching from ChatGPT.
- Inputs needed:
  - Body: ChatGPT export file (multipart upload, format unknown)
  - Auth: likely requires API key
- Output artifact:
  - Import summary (threads created, messages imported)
  - Threads and messages created in DB
- Risk / ambiguity notes:
  - `rag_upload.py` also defines this route but is NOT registered (dead code)
  - Supported ChatGPT export format version unknown

---

### Category 11: Dev, Debug & Realtime

---

### 119. Debug configuration dump
- Endpoint(s): `GET /debug/config`
- What it is: Returns the current application configuration for debugging.
- Why it matters: Helps developers verify configuration values.
- Inputs needed:
  - Auth: unknown (should be restricted)
- Output artifact:
  - JSON with configuration values
- Risk / ambiguity notes:
  - **Security risk**: may expose secrets, API keys, and connection strings
  - Must be disabled in production

---

### 120. Get thread dev state
- Endpoint(s): `GET /dev/state/{thread_id}`
- What it is: Returns internal state for a thread (context, memories, tools active).
- Why it matters: Developer introspection into what the AI "sees" for a given thread.
- Inputs needed:
  - Path: `thread_id`
  - Auth: unknown
- Output artifact:
  - Internal state dump
- Risk / ambiguity notes:
  - Dev-only endpoint

---

### 121. List registered plugins
- Endpoint(s): `GET /dev/plugins`
- What it is: Returns all registered plugins/extensions.
- Why it matters: Plugin system visibility for development.
- Inputs needed:
  - Auth: unknown
- Output artifact:
  - JSON array of plugin descriptors
- Risk / ambiguity notes:
  - None

---

### 122. Delegate task to sub-agent
- Endpoint(s): `POST /dev/delegate`
- What it is: Delegates a task to a sub-agent for execution.
- Why it matters: Enables agent orchestration and task decomposition.
- Inputs needed:
  - Body: task specification (unknown)
  - Auth: unknown
- Output artifact:
  - Task ID and delegation confirmation
- Risk / ambiguity notes:
  - Agent execution model unknown

---

### 123. Run guardian loop for thread
- Endpoint(s): `POST /dev/guardian_loop/{thread_id}`
- What it is: Manually triggers the guardian reasoning loop for a thread.
- Why it matters: Dev tool for testing the core AI reasoning pipeline.
- Inputs needed:
  - Path: `thread_id`
  - Auth: unknown
- Output artifact:
  - Loop execution result
- Risk / ambiguity notes:
  - Could trigger AI actions and side effects

---

### 124. Inject task result
- Endpoint(s): `POST /dev/inject_result/{task_id}`
- What it is: Manually injects a result for a pending task.
- Why it matters: Enables mocking external task results during development.
- Inputs needed:
  - Path: `task_id`
  - Body: result payload (unknown)
  - Auth: unknown
- Output artifact:
  - Task updated with injected result
- Risk / ambiguity notes:
  - Can subvert normal task execution — dev only

---

### 125. Get thread timeline
- Endpoint(s): `GET /dev/timeline/{thread_id}`
- What it is: Returns a timeline of all events/actions in a thread.
- Why it matters: Detailed audit trail for debugging conversation flow.
- Inputs needed:
  - Path: `thread_id`
  - Auth: unknown
- Output artifact:
  - JSON array of timestamped events
- Risk / ambiguity notes:
  - None

---

### 126. Get task status
- Endpoint(s): `GET /dev/task/{task_id}/status`
- What it is: Returns the current status of an async task.
- Why it matters: Task tracking for async operations.
- Inputs needed:
  - Path: `task_id`
  - Auth: unknown
- Output artifact:
  - Task status object (pending/running/completed/failed)
- Risk / ambiguity notes:
  - None

---

### 127. Get task results
- Endpoint(s): `GET /dev/results/{task_id}`
- What it is: Returns the output/results of a completed task.
- Why it matters: Retrieves async task output.
- Inputs needed:
  - Path: `task_id`
  - Auth: unknown
- Output artifact:
  - Task result payload
- Risk / ambiguity notes:
  - None

---

### 128. Execute tool
- Endpoint(s): `POST /tools/execute`
- What it is: Executes a registered tool/function by name with provided arguments.
- Why it matters: Generic tool execution endpoint — enables the AI to invoke tools.
- Inputs needed:
  - Body: tool name + arguments (unknown schema)
  - Auth: likely requires API key
- Output artifact:
  - Tool execution result
- Risk / ambiguity notes:
  - **Security risk**: arbitrary tool execution — must validate tool names and arguments
  - Available tools list unknown

---

### 129. Global SSE event stream
- Endpoint(s): `GET /api/events` *(SSE)*
- What it is: Server-Sent Events stream for all application events.
- Why it matters: Real-time updates for the UI (new messages, status changes, etc.).
- Inputs needed:
  - Auth: unknown
- Output artifact:
  - Continuous SSE stream of typed events
- Risk / ambiguity notes:
  - Event types and schema unknown
  - Connection lifecycle unknown

---

### 130. Task-specific SSE event stream
- Endpoint(s): `GET /api/tasks/{task_id}/events` *(SSE)*
- What it is: SSE stream scoped to events for a specific task.
- Why it matters: Allows UI to subscribe to progress updates for a single task.
- Inputs needed:
  - Path: `task_id`
  - Auth: unknown
- Output artifact:
  - SSE stream of task events (progress, completion, errors)
- Risk / ambiguity notes:
  - None

---

### 131. WebSocket RPC endpoint
- Endpoint(s): `WEBSOCKET /api/ws/rpc`
- What it is: General-purpose WebSocket endpoint for JSON-RPC style communication.
- Why it matters: Low-latency bidirectional communication for real-time features.
- Inputs needed:
  - Auth: unknown (WebSocket auth via query params or first message)
- Output artifact:
  - Bidirectional message stream
- Risk / ambiguity notes:
  - `ws/router.py` also defines this route but checking which is actually registered is ambiguous — both files exist
  - RPC method catalog unknown

---

### 132. Collaboration audit log
- Endpoint(s): `GET /api/collab/{document_id}/audit`
- What it is: Returns the edit audit log for a collaboratively edited document.
- Why it matters: Accountability and history for multi-user document editing.
- Inputs needed:
  - Path: `document_id`
  - Auth: likely requires API key
- Output artifact:
  - JSON array of edit events with user, timestamp, change
- Risk / ambiguity notes:
  - None

---

### 133. Collaboration WebSocket
- Endpoint(s): `WEBSOCKET /api/collab/ws/{document_id}`
- What it is: Real-time collaboration WebSocket for concurrent document editing.
- Why it matters: Enables Google Docs-style multi-user editing.
- Inputs needed:
  - Path: `document_id`
  - Auth: unknown
- Output artifact:
  - Bidirectional WebSocket for OT/CRDT operations
- Risk / ambiguity notes:
  - Conflict resolution strategy (OT vs CRDT) unknown

---

### 134. Application root
- Endpoint(s): `GET /`
- What it is: Root endpoint — likely returns API info or redirects.
- Why it matters: Entry point for API discovery.
- Inputs needed:
  - None
- Output artifact:
  - API info JSON or redirect
- Risk / ambiguity notes:
  - None

---

### 135. Agent ping (double prefix bug)
- Endpoint(s): `GET /agent/agent/ping`
- What it is: Liveness check for the agent subsystem.
- Why it matters: Verifies agent service is responsive.
- Inputs needed:
  - None
- Output artifact:
  - `{"status": "Agent is active."}`
- Risk / ambiguity notes:
  - **Bug**: Double prefix. Route is `/agent/ping` in `agent.py`, mounted with `prefix="/agent"`, yielding `/agent/agent/ping`. Should likely be `GET /agent/ping`.

---

### 136. Research handler (double prefix bug)
- Endpoint(s): `POST /research/research`
- What it is: Performs research queries across configured sources.
- Why it matters: Enables the AI to research topics using external sources.
- Inputs needed:
  - Body: `{"query": str, "sources": [str]}`
  - Auth: unknown
- Output artifact:
  - `{"result": ...}` — research findings
- Risk / ambiguity notes:
  - **Bug**: Double prefix. Route is `/research` in `research.py`, mounted with `prefix="/research"`, yielding `/research/research`. Should likely be `POST /research`.

---

## D) FINAL REPORT

---

### 1. Executive Summary

- **136 unique endpoint families** serve the main Guardian API across **152 total routes** (including 16 `/api`-prefix aliases)
- **~50 routes are dead code** — defined in source files whose routers are never imported into `guardian_api.py`
- **8 entire route modules are unregistered**: channels, browser, workspace, meta, graph, rag_upload, federation_context, and Google OAuth
- **2 double-prefix bugs** produce awkward paths: `/agent/agent/ping` and `/research/research`
- **1 delete-path inconsistency**: `DELETE /chat/{thread_id}` vs `DELETE /api/chat/threads/{thread_id}` — different path structures for the same conceptual operation
- **16 alias groups** duplicate every chat endpoint under both `/chat/` and `/api/chat/` — intentional for backward compat but doubles the attack surface
- **Multiple health endpoints** serve overlapping purposes: `/health`, `/healthz`, `/ping`, plus subsystem-specific checks
- **No OpenAPI spec file** exists in the project — API documentation is not machine-generated
- **Request/response schemas are unknown** for the majority of endpoints — Pydantic models may exist but were not auditable from route paths alone
- **Security concerns**: `/debug/config`, `/authz/debug`, `/metrics`, and `/tools/execute` need production access controls

---

### 2. Category Breakdown Table

| # | Category | Endpoint Families | Total Routes (incl. aliases) |
|---|----------|:-----------------:|:----------------------------:|
| 1 | Health & Observability | 10 | 11 |
| 2 | Auth & Session | 3 | 3 |
| 3 | Chat, Threads & Projects | 19 | 30 |
| 4 | Memory & Knowledge | 18 | 18 |
| 5 | Identity & System Configuration | 10 | 10 |
| 6 | Media & Generation | 10 | 10 |
| 7 | Connectors & Integration | 12 | 12 |
| 8 | Federation & Graph | 11 | 11 |
| 9 | Flows & Scheduling | 15 | 15 |
| 10 | Documents, Codex & Exports | 10 | 14 |
| 11 | Dev, Debug & Realtime | 18 | 18 |
| **Total** | **11 categories** | **136** | **152** |

---

### 3. Top 10 Highest-Leverage Endpoint Families

| Rank | Family | Leverage |
|------|--------|----------|
| 1 | `POST /chat/{thread_id}/messages` (#23) | Core conversational loop — every product interaction depends on this working correctly |
| 2 | `POST /auth/session` (#11) | Auth gate for all protected endpoints — nothing works without session creation |
| 3 | `POST /api/memory/{silo}` (#35) | Write path for knowledge base — RAG quality depends entirely on memory ingestion |
| 4 | `POST /api/flows` (#95) | Flow creation unlocks the entire automation platform — cron, triggers, and orchestration build on flows |
| 5 | `POST /api/connectors` (#74) | Connector registration unlocks external data integration — feeds memory, enables sync |
| 6 | `POST /api/federation/session/request` (#85) | Federation session is the prerequisite for all peer-to-peer data exchange |
| 7 | `POST /api/embeddings` (#38) | Embedding generation underlies semantic search, RAG retrieval, and knowledge matching |
| 8 | `GET /api/events` (#129) | Global SSE stream — the real-time UI layer depends on this for all live updates |
| 9 | `POST /api/imprint/proposal` (#52) | Imprint system controls AI personality — getting this right shapes entire user experience |
| 10 | `POST /api/cron/jobs` (#103) | Cron job creation enables periodic automation — daily summaries, sync schedules, maintenance |

---

### 4. Top 10 Riskiest / Unclear Endpoint Families

| Rank | Family | Risk Reason | Clarifying Questions |
|------|--------|-------------|---------------------|
| 1 | `GET /debug/config` (#119) | Exposes full app configuration — may include secrets, API keys, DB credentials | 1. Is this disabled in production? 2. What config values are included? 3. Is there auth required? |
| 2 | `POST /tools/execute` (#128) | Arbitrary tool execution endpoint — potential for command injection or privilege escalation | 1. What tools are available? 2. How is input validated? 3. Is there a tool allowlist? |
| 3 | `DELETE /chat/{thread_id}` vs `DELETE /api/chat/threads/{thread_id}` (#30, #31) | Two delete paths with different URL structures — may have different handlers, different behavior | 1. Do these call the same handler? 2. Is one deprecated? 3. Which should clients use? |
| 4 | `GET /metrics` (#7) | Prometheus metrics may leak internal architecture, resource usage, and business metrics | 1. Is this behind auth? 2. What metrics are exposed? |
| 5 | Dead code: channels.py (10 routes), browser.py (7 routes) | 17 unregistered routes suggest incomplete features — unclear if intentionally disabled or forgotten | 1. Are channels/browser features planned? 2. Should the code be deleted? 3. Is there a feature flag? |
| 6 | `POST /embed` vs `POST /api/embeddings` (#49, #38) | Two embedding endpoints from different routers — purpose overlap unclear | 1. Are these the same operation? 2. Which is canonical? 3. Can one be removed? |
| 7 | `PATCH /chat/{thread_id}` vs `PATCH /chat/threads/{thread_id}` (#28, #29) | Two update paths for threads — naming inconsistency creates confusion | 1. Do these differ in behavior? 2. Is one deprecated? |
| 8 | `GET /agent/agent/ping` (#135) | Double-prefix bug makes the path nonsensical | 1. Should this be `/agent/ping`? 2. Is anything calling the current broken path? |
| 9 | `POST /api/share` + `GET /api/share/{token}` (#115, #116) | Shared content is accessible via token without auth — security depends on token unpredictability | 1. What is the token entropy? 2. Do tokens expire? 3. Can shares be revoked? |
| 10 | `WEBSOCKET /api/ws/rpc` (#131) | General-purpose RPC over WebSocket — the scope of callable methods is unknown | 1. What RPC methods are available? 2. How is auth handled? 3. Is there input validation per method? |

---

### 5. Recommended 3-Phase Plan

#### Phase 1: Stabilize & Secure (Foundation)
**Rationale:** Fix bugs, remove dead code, lock down security-sensitive endpoints, and establish API documentation. Nothing else should ship until the surface area is clean and secure.

- Fix double-prefix bugs: `/agent/agent/ping` → `/agent/ping`, `/research/research` → `/research`
- Resolve delete-path inconsistency: unify `DELETE /chat/{thread_id}` and `DELETE /api/chat/threads/{thread_id}`
- Resolve PATCH duplication: unify `PATCH /chat/{thread_id}` and `PATCH /chat/threads/{thread_id}`
- Audit and restrict `/debug/config`, `/authz/debug`, `/metrics` (disable in production or require admin auth)
- Audit `/tools/execute` — add tool allowlist and input validation
- Audit `/api/share/{token}` — verify token entropy, add expiration
- Remove or archive dead route modules (channels.py, browser.py, workspace.py, meta.py, rag_upload.py, google.py)
- Remove or archive dead sub-routers (threads.api_router, projects.api_router, chat.threads_router, chat.thread_router, memory.github_router, memory.search_router)
- Decide on `/embed` vs `/api/embeddings` — remove the redundant one
- Generate OpenAPI spec from FastAPI's built-in `/openapi.json` and publish it
- Auth endpoints (#11, #12): document and harden (rate limiting, CSRF, cookie flags)

#### Phase 2: Consolidate & Document (Core Product)
**Rationale:** With the foundation clean, standardize the core product endpoints, document schemas, and ensure consistent API conventions.

- Standardize all endpoint families on the `/api/` prefix convention (decide if bare paths like `/chat/`, `/threads/`, `/projects/` should remain or be deprecated in favor of `/api/chat/`, `/api/threads/`, `/api/projects/`)
- Document request/response schemas for all Chat & Messaging endpoints (#19–#32)
- Document Memory & Knowledge schemas (#34–#50)
- Document Identity & System schemas (#51–#60)
- Document Media schemas (#61–#70)
- Document Flows & Scheduling schemas (#94–#108)
- Consolidate overlapping health endpoints (decide canonical set: `/health` + subsystem checks, deprecate `/ping` or `/healthz`)
- Add pagination conventions across all list endpoints
- Add integration tests for the 10 highest-leverage endpoints
- Document WebSocket protocols (RPC method catalog, collaboration ops)

#### Phase 3: Extend & Federate (Growth)
**Rationale:** With core product stable and documented, activate dormant features and expand the platform.

- Evaluate and activate `channels.py` (10 routes) — multi-channel messaging support
- Evaluate and activate `browser.py` (7 routes) — browser automation and approvals
- Evaluate and activate `federation_context.py` (3 routes) — federated context search
- Activate `workspace.py` (workspace per-thread isolation)
- Activate `google.py` OAuth connector (or integrate into `/api/connectors/{name}/authorize`)
- Activate `memory.github_router` (GitHub search integration)
- Activate `memory.search_router` (unified search, history, logging, summarization)
- Build out Connectors ecosystem with documented connector SDK
- Federation hardening: auth model, conflict resolution, rate limiting
- Build admin dashboard using Dev/Debug endpoints (restrict to admin role)
- Performance test SSE and WebSocket endpoints under load

---

*End of audit report. 136 endpoint families cataloged. 152 active routes. 11 categories. ~50 dead-code routes flagged.*
