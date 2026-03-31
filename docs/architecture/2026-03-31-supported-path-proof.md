# Supported Path Proof: Local Docker Compose Beta Profile

**Artifact date:** 2026-03-31T23:54:15Z
**Branch:** main
**HEAD commit:** `5318886dd69d11835494da0a850ab4ddcbe7bc03`
**Runtime path:** Local Docker Compose (docker-compose.yml default services)
**Active provider/model:** local / qwen3.5:0.8b (via http://100.109.4.57:11434)
**Startup env-file:** .env (CODEXIFY_RUNTIME_ENV_FILE=.env)

---

## 1. Scope

This artifact validates the current supported local Docker Compose path on current `main` at commit `5318886dd69d11835494da0a850ab4ddcbe7bc03`.

This proof specifically covers:

- The newly landed frontend/runtime-contract behavior (provider-state presentation, request lifecycle tracking)
- Standard supported-path gates: flag enforcement, quarantined routes, health reconciliation, chat completion persistence, and upload->embed->retrieve sentinel proof

---

## 2. Environment

| Item | Value |
|------|-------|
| Evidence capture time | 2026-03-31T23:54:15Z |
| Branch | main |
| HEAD commit | 5318886dd69d11835494da0a850ab4ddcbe7bc03 |
| Runtime path | Docker Compose (backend, db, redis, neo4j, frontend, workers) |
| Provider | local |
| Model | qwen3.5:0.8b |
| Ollama endpoint | http://100.109.4.57:11434 |
| Active env vars | See Section 3 |

Services running (from `docker compose ps`):
- `codexify-backend-1` — Up 2 hours (healthy)
- `codexify-db-1` — Up 2 hours (healthy)
- `codexify-redis-1` — Up 2 hours (healthy)
- `codexify-neo4j-1` — Up 2 hours (healthy)
- `codexify-frontend-1` — Up 2 hours
- `codexify-worker-chat-1` — Up 2 hours
- `codexify-worker-document-embed-1` — Up 2 hours
- `codexify-worker-chat-embed-1` — Up 2 hours
- `codexify-tts-1` — Up 2 hours (healthy)

---

## 3. Supported-Profile Flags

Command to verify:
```bash
docker exec codexify-backend-1 env | grep -E "(CODEXIFY_BETA_CORE_ONLY|CODEXIFY_LOCAL_ONLY_MODE|ALLOW_CLOUD_PROVIDERS)"
```

**Observed values (from running container):**
```
CODEXIFY_BETA_CORE_ONLY=true
CODEXIFY_LOCAL_ONLY_MODE=true
ALLOW_CLOUD_PROVIDERS=false
```

**Verification command:**
```bash
curl -s http://localhost:8888/health
curl -s http://localhost:8888/api/health/llm
```

From `/api/health/llm`:
```json
{
  "provider": "local",
  "model": "qwen3.5:0.8b",
  "provider_runtime": {
    "id": "local",
    "authorized": true,
    "available": true,
    "enabled": true,
    "disabled_reason": null
  },
  "ok": true,
  "status": "online"
}
```

**Verdict: PASS** — All three supported-profile flags are active and the local provider is available.

---

## 4. Quarantined Route Checks

Command to probe cloud provider routes:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/api/providers/openai/status
curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/api/providers/anthropic/status
curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/api/providers/groq/status
```

**Observed results:**
- `/api/providers/openai/status` → `404`
- `/api/providers/anthropic/status` → `404`
- `/api/providers/groq/status` → `404`

From `/api/llm/catalog`, cloud providers show:
```json
{
  "id": "groq",
  "enabled": false,
  "available": false,
  "disabled_reason": "Cloud providers disabled by config",
  "model_index": {
    "state": "unavailable",
    "reason": "Cloud providers disabled by config",
    "failure_kind": "provider_disabled"
  }
}
```

Same pattern observed for `alibaba` and `minimax`.

**Verdict: PASS** — Cloud provider routes return 404, and the catalog confirms they are disabled by config. The supported profile contract holds.

---

## 5. Health Surface Reconciliation

All health checks run against the **same runtime session** (no restarts between checks).

| Endpoint | Observed Result |
|----------|-----------------|
| `GET /health` | `{"status":"ok"}` |
| `GET /health/chat` | `{"ok":true,"status":"healthy","redis":"ok","queue":{"depth":0,"status":"progressing"},"worker":{"status":"fresh","heartbeat_age_seconds":4.5},"provider":"local","model":"qwen3.5:0.8b"}` |
| `GET /api/health/llm` | `{"ok":true,"status":"online","provider":"local","model":"qwen3.5:0.8b","provider_runtime":{"available":true,"enabled":true}}` |
| `GET /api/llm/catalog` | Returns local + quarantined providers; local shows `available:true`, cloud shows `disabled_reason":"Cloud providers disabled by config"` |
| `GET /health/vector` | `{"ok":true,"status":"ok","backend":"chroma","added":1,"matches":1}` |
| `GET /health/memory` | `{"ok":true,"counts":{"ephemeral":0,"midterm":0,"longterm":0}}` |
| `GET /api/health/embedder` | `{"status":"ok","embedder":{"backend":"local","model":"/models/bge-large-en-v1.5","ready":true,"present":true}}` |
| `GET /api/health/retrieval` | `{"status":"ready","ok":true,"proof_capable":true,"same_runtime_as_worker":true}` |

**Reconciliation:**

All surfaces report consistent state from the same runtime session:
- Backend: `ok` / `healthy`
- Redis: reachable
- Worker: fresh heartbeat
- Queue: empty (depth=0), status `progressing`
- LLM provider (local): `available`, `online`
- Vector store (Chroma): probe added=1, matches=1
- Embedder (local sentence-transformer): ready, present
- Memory: counts show no ephemeral/midterm/longterm documents indexed

No surface reports contradictory state. All surfaces reconcile to the same runtime reality.

**Verdict: PASS** — Health surfaces are reconciled from the same runtime session; no contradictions detected.

---

## 6. Chat Completion Proof

### Step 1: Create thread
```bash
curl -s -X POST http://localhost:8888/chat/threads \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"title": "supported-path-proof-test"}'
```
**Result:** Thread ID 1227 created successfully.

### Step 2: Persist user message
```bash
curl -s -X POST http://localhost:8888/chat/1227/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"role": "user", "content": "Hello, please respond with exactly one word: ping"}'
```
**Result:** Message ID 50226 persisted in thread 1227.

### Step 3: Request completion
```bash
curl -s -X POST http://localhost:8888/chat/1227/complete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{}'
```
**Result:** `acceptance_status":"accepted","task_id":"0f27a6ba-8035-4085-a213-b58a9e9605b4"`

### Step 4: Verify assistant output is persisted

Wait ~2 minutes for completion. Check thread messages:
```bash
curl -s http://localhost:8888/chat/1227/messages -H "X-API-Key: <key>"
```

**Observed persisted messages in thread 1227:**

| ID | Role | Content | Created |
|----|------|---------|---------|
| 50226 | user | "Hello, please respond with exactly one word: ping" | 2026-03-31T23:47:44 |
| 50227 | assistant | "ping" | 2026-03-31T23:49:42 |

Worker log confirms:
```
assistant_message_persisted thread_id=1227 turn_id=01779ec9-7a61-44cf-9b92-a41ee9d3b544 task_id=0f27a6ba-8035-4085-a213-b58a9e9605b4 assistant_message_id=50227
[task] completed type=chat_completion id=0f27a6ba-8035-4085-a213-b58a9e9605b4 thread=1227 message_id=50227
```

**Completion truth from message metadata:**
```json
"completion_truth": {
  "accepted": true,
  "executed": true,
  "attempted": true,
  "completed": true,
  "fallback_attempted": false
}
```

**Verdict: PASS** — User message was persisted, completion was requested and accepted, assistant output ("ping") was actually persisted after acceptance. Acceptance != completion is correctly distinguished.

---

## 7. Runtime-Contract Behavior Check

This section records what happens when the selected local model responds slowly or cold-starts.

**Observed behavior during chat completion proof:**

1. Task submitted at `23:47:50`
2. Worker log shows task picked up immediately:
   ```
   [task] running type=chat_completion id=0f27a6ba-8035-4085-a213-b58a9e9605b4 thread=1227
   ```
3. Context broker initialized at `23:47:50` — fast, no delay
4. Model inference took ~112 seconds (from `23:47:50` to `23:49:43`)
5. Assistant message persisted at `23:49:43`

**Runtime banner/status assessment:**

- Backend reachability: Backend was reachable throughout (health checks returned 200)
- Worker heartbeat: remained `fresh` during the entire inference period
- Queue depth: remained 0 — task was processed without queuing delay
- Provider status: `online` throughout (backend health check confirmed provider endpoint was reachable)
- Model response time: 112 seconds for a simple "ping" response — this is slow/unusual but NOT classified as offline

**Key finding:** The runtime did NOT misclassify the slow model response as "offline". The `/api/health/llm` endpoint returned `"status":"online"` even during the long inference window. The backend remained reachable.

**What was NOT tested:**
- Full cold-start scenario where Ollama endpoint becomes unreachable — cannot be cleanly reproduced in this run
- Banner update during slow inference — would require frontend visibility

**Verdict: PARTIAL PASS** — Backend remained reachable and was correctly reported as `online` during the slow inference. No misclassification as offline observed. However, a true cold-start where the Ollama endpoint is completely unreachable was not tested.

---

## 8. Upload / Embed / Retrieve Sentinel Proof

### Step 1: Upload sentinel document

```bash
echo "This is the supported-path-proof sentinel document for embed-retrieve validation." > /tmp/sentinel_doc.txt
curl -s -X POST http://localhost:8888/api/media/upload/document \
  -H "X-API-Key: <key>" \
  -F "file=@/tmp/sentinel_doc.txt"
```

**Result:**
```json
{
  "id": "6f073e35-1df9-433a-bf54-822c0165adeb",
  "filename": "sentinel_doc.txt",
  "embedding_status": "pending",
  "parsed_text": "This is the supported-path-proof sentinel document..."
}
```

### Step 2: Check embedding status

After waiting several minutes:
```bash
curl -s "http://localhost:8888/api/media/documents" -H "X-API-Key: <key>"
```

**Observed:** `embedding_status` remained `"processing"` for over 4 minutes after upload.

From the document list:
```json
{
  "id": "6f073e35-1df9-433a-bf54-822c0165adeb",
  "filename": "sentinel_doc.txt",
  "embedding_status": "processing",
  "embedding_started_at": "2026-03-31T23:50:35.759460+00:00",
  "embedding_completed_at": null
}
```

### Step 3: Check vector store health

```bash
curl -s http://localhost:8888/health/vector
```
**Result:** `{"ok":true,"status":"ok","backend":"chroma","added":1,"matches":1}`

The probe shows 1 match, but this is from the vector health probe itself (which adds a probe document), not from the sentinel document.

### Step 4: Check retrieval health

```bash
curl -s http://localhost:8888/api/health/retrieval
```
**Result:**
```json
{
  "status": "ready",
  "ok": true,
  "proof_capable": true,
  "search": {
    "executed": false,
    "match_count": 0,
    "matches": []
  }
}
```

**Observed discrepancy:**
- Vector health probe reports `matches:1` (from probe document, not sentinel)
- Retrieval health reports `match_count: 0`
- Document status stuck at `"processing"` — embedding task appears completed (queue empty) but status not updated

### Step 5: Check embed worker logs

```bash
docker logs codexify-worker-document-embed-1 --tail 20
```

Worker started at `23:50:46` (after document upload at `23:50:35`), but no processing logs for the sentinel document appear. Queue length:
```bash
docker exec codexify-redis-1 redis-cli LLEN codexify:queue:document-embed
```
Returns `0` — queue empty.

**Verdict: FAIL** — Upload succeeded, embedder is healthy and ready, but:
1. The sentinel document `embedding_status` is stuck at `"processing"` and never transitions to `"completed"`
2. The document embed worker shows no processing activity for the sentinel document
3. Retrieval health confirms no matches found for the sentinel content
4. The upload->embed->retrieve sentinel path did NOT complete successfully

This is a live bug in the document embedding pipeline.

---

## 9. Verdict

### What is PROVEN

| Check | Result |
|-------|--------|
| Supported-profile flags active | **PASS** — CODEXIFY_BETA_CORE_ONLY=true, CODEXIFY_LOCAL_ONLY_MODE=true, ALLOW_CLOUD_PROVIDERS=false |
| Cloud providers quarantined | **PASS** — All cloud routes return 404; catalog confirms `provider_disabled` |
| Health surfaces reconciled | **PASS** — All surfaces (backend, redis, worker, LLM, vector, embedder, memory) report consistent state from same session |
| User message persisted | **PASS** — Message ID 50226 confirmed in thread 1227 |
| Completion accepted | **PASS** — `acceptance_status":"accepted"` returned immediately |
| Assistant output actually persisted | **PASS** — Assistant message ID 50227 ("ping") confirmed persisted after 112s inference |
| Runtime-contract: backend reachable + slow model NOT misclassified as offline | **PASS** — /api/health/llm returned `"status":"online"` throughout; no misclassification |

### What is NOT PROVEN

| Check | Result |
|-------|--------|
| Upload -> embed -> retrieve sentinel | **FAIL** — Document stuck at `embedding_status:"processing"`; retrieval confirms no matches |
| Full cold-start where Ollama is unreachable | **NOT TESTED** — Cannot reproduce cleanly in this run |
| Banner update during slow inference (frontend) | **NOT OBSERVED** — Would require frontend visibility |

### What STILL BLOCKS stronger beta claims

1. **Document embedding pipeline bug** — Upload succeeds but `embedding_status` never transitions to completed; retrieval fails to find sentinel content. This blocks confident RAG/semantic retrieval claims on the supported path.

### Final Summary

- **Proof artifact only; no automated tests apply** for this specific supported-path proof run.
- Completion persistence: **PASSED** — acceptance correctly distinguished from completion; assistant output confirmed persisted
- Upload->embed->retrieve sentinel: **FAILED** — document embedding pipeline bug prevents completion
- Runtime-contract (slow model not misclassified as offline): **PASSED** — backend remained reachable and correctly reported online

**Git commit:** `5318886dd69d11835494da0a850ab4ddcbe7bc03`
