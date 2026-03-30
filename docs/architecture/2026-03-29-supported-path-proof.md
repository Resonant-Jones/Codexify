# Supported-Path Proof: 2026-03-29

**Date:** 2026-03-29
**Branch:** main
**Runtime:** Docker Compose (backend, frontend, db, redis, workers, neo4j)
**Profile:** Supported local path with `CODEXIFY_BETA_CORE_ONLY=true`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`

---

## Scope

This artifact documents the end-to-end runtime proof for the supported local Docker Compose path on current main after recent runtime hardening. It verifies supported-profile flags, quarantined routes, health surfaces, chat path, document/embed path, and retrieval runtime parity.

---

## Environment

- **Docker Compose:** v5.1.0
- **Backend:** Python/FastAPI on port 8888
- **Database:** Postgres 15 on port 5433
- **Redis:** 7-alpine (internal)
- **Workers:** chat, chat-embed, document-embed, voice, warmup
- **Neo4j:** 5 on ports 7474/7687
- **LLM Provider:** local (Ollama at 100.109.4.57:11434)
- **Embedding Model:** /models/bge-large-en-v1.5
- **Chat Model:** qwen3.5:0.8b
- **Vector Store:** Chroma at /app/.chroma, collection codexify_vault

---

## Startup Commands

```bash
docker compose down --remove-orphans
docker compose up -d
```

---

## Effective Profile Flags

Verified via backend container introspection:

```
CODEXIFY_BETA_CORE_ONLY: true
CODEXIFY_LOCAL_ONLY_MODE: true
ALLOW_CLOUD_PROVIDERS: false
```

**Status: PASS** — All three flags correctly active in runtime.

---

## Quarantined Route Checks

Cloud provider routes correctly return 404 (not found) on the supported profile:

| Route | Expected | Observed |
|-------|----------|----------|
| /api/providers/groq | 404 | 404 |
| /api/providers/anthropic | 404 | 404 |

**Status: PASS** — Quarantined routes are properly blocked.

---

## Provider and Health Surface Checks

### /health
```
{"status":"ok"}
```
**Status: PASS**

### /health/chat
```
{
  "ok": false,
  "status": "unhealthy",
  "redis": "ok",
  "worker": {"status": "dead", "heartbeat_age_seconds": null},
  "notes": ["worker heartbeat missing; chat completion cannot progress"],
  "threads": 0,
  "messages": 0,
  "provider": "local",
  "model": "qwen3.5:0.8b",
  ...
}
```

**Status: FAIL** — Reports worker heartbeat missing as "dead", but the worker-chat container is running and shows activity in logs. Redis contains the heartbeat key (`codexify:worker:chat:heartbeat` = `{"worker": "chat", "status": "idle", "queue": "codexify:queue:chat", "ts": 1774825742}`). The health check logic appears to have a stale-check bug despite the worker actually running.

### /health/llm
```
{"ok":true,"status":"online","provider":"local","model":"qwen3.5:0.8b",...}
```
**Status: PASS**

### /api/llm/catalog
Cloud providers show `enabled: false` with reason "Cloud providers disabled by config". Local provider shows available models.
**Status: PASS**

### /api/health/retrieval
```
{
  "status": "ready",
  "ok": true,
  "reason": "backend search runtime matches canonical worker write runtime",
  "worker_write_runtime": {"backend": "chroma", "chroma_path": "/app/.chroma", "collection": "codexify_vault"},
  "backend_search_runtime": {"backend": "chroma", "chroma_path": "/app/.chroma", "collection": "codexify_vault"},
  "backend_store_source": "shared",
  "same_runtime_as_worker": true,
  "proof_capable": true
}
```
**Status: PASS**

### /health/vector
```
{"ok":true,"status":"ok","backend":"chroma","source":"probe","added":1,"matches":1}
```
**Status: PASS**

### /api/health/embedder
```
{"status":"ok","embedder":{"backend":"local","model":"/models/bge-large-en-v1.5","ready":true,"present":true,"reason":"local embedder preflight passed"}}
```
**Status: PASS**

---

## Happy-Path Thread and Completion Proof

### Create Thread
```bash
curl -X POST http://localhost:8888/chat/threads \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"title": "proof-test-thread"}'
```
Response:
```json
{"ok":true,"id":1,"thread":{"id":1,"user_id":"default","title":"proof-test-thread",...}}
```
**Status: PASS**

### Create User Message
```bash
curl -X POST http://localhost:8888/chat/1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"role": "user", "content": "Hello, this is a proof test..."}'
```
Response:
```json
{"ok":true,"message":{"id":1,"thread_id":1,"role":"user","content":"Hello, this is a proof test..."}}
```
**Status: PASS**

### Request Completion
```bash
curl -X POST http://localhost:8888/chat/1/complete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"model": "qwen3.5:0.8b"}'
```
Response:
```json
{
  "ok":true,
  "acceptance_status":"accepted",
  "task_id":"611afb59-1671-4b95-89c4-a4cb5cd068e1",
  "turn_id":"576441d3-da3b-4682-9117-ad674cd5c708",
  "thread_id":1,
  ...
}
```
**Status: PARTIAL** — Task was accepted and queued. Worker picked up the task (visible in worker-chat logs) but no assistant message was produced after 60+ seconds. The completion task stalled.

### Confirm Assistant Message Persisted
```bash
curl http://localhost:8888/chat/1/messages -H "X-API-Key: <key>"
```
Response shows only the user message (id=1). No assistant message present.

**Status: FAIL** — Chat completion was accepted but assistant message never persisted. Worker processed the task but output was not written back.

---

## Upload/Embed/Retrieve Proof

### Upload Sentinel Document
```bash
echo "This is a proof test document with unique sentinel content 2026-03-29-PROOF-SENTINEL." > /tmp/proof-test-doc.txt
curl -X POST http://localhost:8888/api/media/upload/document \
  -H "X-API-Key: <key>" \
  -F "file=@/tmp/proof-test-doc.txt"
```
Response:
```json
{
  "id":"eb685661-1254-4093-b5d4-bc5506cebf23",
  "embedding_status":"pending",
  ...
}
```
**Status: PASS** — Document uploaded successfully.

### Confirm Parse/Embedding Lifecycle Reaches Ready
Document status observed over 2+ minutes:
- 23:11:20 — `embedding_status: "pending"`
- 23:11:20.793 — `embedding_status: "processing"` (worker picked up task)
- 23:11:27 — Worker restarted after processing began
- 2+ minutes later — Still `embedding_status: "processing"`

Worker-chat-document-embed logs show the worker started, picked up the task, but did not complete embedding before restarting.

**Status: FAIL** — Document embedding stuck in "processing" indefinitely. Worker appears to crash/restart during embedding task.

### Attempt Retrieval for Fresh Sentinel
Retrieval health shows `proof_capable: true` and runtime parity is confirmed, but actual search endpoint is not exposed. Cannot verify retrieval of sentinel content because embedding never completed.

**Status: BLOCKED** — Cannot test retrieval path because embedding path is blocked.

---

## Retrieval-Runtime Parity Proof

### Vector Backend Configuration
| Component | Backend | Path | Collection |
|-----------|---------|------|------------|
| Backend Search | chroma | /app/.chroma | codexify_vault |
| Worker Write | chroma | /app/.chroma | codexify_vault |

**Status: PASS** — Both backend and worker are pointed at the same Chroma runtime.

### Backend-Side Search Capability
`/api/health/retrieval` shows `proof_capable: true` and `same_runtime_as_worker: true`.

**Status: PASS** — Runtime parity confirmed.

### Actual Retrieval of Sentinel Content
Cannot verify — document embedding never completed.

**Status: BLOCKED**

---

## Release-Gate Reconciliation

| Surface | Expected | Observed | Status |
|---------|----------|----------|--------|
| /health | ok | ok | AGREE |
| /health/chat | healthy (worker running) | unhealthy (heartbeat bug) | PARTIAL - worker running but health reports dead |
| /health/llm | online | online | AGREE |
| /api/llm/catalog | cloud disabled | cloud disabled | AGREE |
| /api/health/retrieval | ready, same runtime | ready, same runtime | AGREE |

**Summary:** 4/5 surfaces agree with supported-profile contract. /health/chat has a heartbeat-check bug that misreports worker status despite worker actually running.

---

## Drift or Caveats

1. **/health/chat heartbeat bug:** Reports worker as "dead" when worker-chat is actively running and has a valid heartbeat in Redis. Likely a stale-check or key-format mismatch in health logic.

2. **Chat completion stalled:** Task is accepted and picked up by worker, but no assistant message is persisted. The worker's context broker initializes but appears to stall before producing output.

3. **Document embedding stalled:** Document upload succeeds, worker picks up embedding task, but embedding never completes. Worker restarts during processing.

4. **Retrieval verification blocked:** Cannot verify actual retrieval because document embedding never completes.

---

## Pass/Fail Summary

| Check | Status |
|-------|--------|
| Profile flags active | PASS |
| Quarantined routes blocked | PASS |
| /health | PASS |
| /health/chat accurate | FAIL (heartbeat bug) |
| /health/llm | PASS |
| /api/llm/catalog cloud disabled | PASS |
| /api/health/retrieval | PASS |
| Thread creation | PASS |
| Message creation | PASS |
| Completion task acceptance | PASS |
| Assistant message persisted | FAIL (stalled) |
| Document upload | PASS |
| Document embedding reaches ready | FAIL (stuck processing) |
| Retrieval runtime parity | PASS |
| Actual retrieval verification | BLOCKED |

---

## Final Verdict

**Release gate: STILL OPEN**

### Exact Blockers:

1. **Chat completion output not persisting** — Worker processes tasks but assistant messages never reach the database. This breaks the core chat path end-to-end.

2. **Document embedding never completing** — Uploaded documents remain in "processing" state indefinitely. Worker restarts during task execution.

3. **/health/chat reports incorrect status** — Misleading operator signal even though the underlying worker appears functional.

### Named Caveats:

- Runtime parity work (vector-store unification) has landed correctly — backend and worker Chroma paths match.
- Profile flags are correctly enforced.
- Quarantined routes work as expected.
- The infrastructure scaffolding is in place, but the worker execution paths for both chat completion and document embedding are failing silently after task acceptance.

### This Was an Evidence Artifact Task

No runtime behavior was modified. All findings are from live observation only. The failures above represent real runtime failures that require investigation in worker execution logic, not documentation or configuration issues.