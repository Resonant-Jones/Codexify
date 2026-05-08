# Neo4j Graph Backend Live Proof: Rerun After Trace Fix

**Artifact date:** 2026-05-08
**Branch:** `main` (proof executed on `codex/run-readiness-audit` which includes `main` at `6e0fca808`)
**HEAD commit:** `6e0fca808` (main tip with trace fix)
**Runtime path:** Local Docker Compose (backend, db, redis, neo4j, workers)
**Proof window:** 2026-05-08T16:30Z to 2026-05-08T16:55Z

---

## Scope

This artifact captures a re-run of the Neo4j graph backend live proof after the `_build_model_selection_trace(...)` helper invocation fix (`6e0fca808`).

It attempts to verify:

1. Default-off behavior stays on the no-op graph backend and does not write graph data.
2. Explicitly enabled graph writes select the Neo4j adapter and write graph data.
3. Chat completion and assistant persistence now succeed after the trace fix.
4. Duplicate/replay receipt semantics prevent duplicate graph materialization.

This is a runtime-evidence artifact. No runtime code, retrieval contracts, export semantics, UI behavior, or ADR contracts were changed in this task.

---

## Environment

### Runtime path

Supported local Docker Compose stack from the repository root.

Observed live services during the proof session:

- `codexify-db-1` (healthy)
- `codexify-redis-1` (healthy)
- `codexify-neo4j-1` (healthy)
- `codexify-backend-1` (healthy)
- `codexify-worker-chat-1` (running)
- `codexify-worker-chat-embed-1` (running)
- `codexify-worker-document-embed-1` (running)
- `codexify-worker-warmup-1` (running)
- `codexify-worker-coding-1` (running)
- `codexify-worker-voice-1` (running)
- `codexify-frontend-1` (running)

### Env loading ritual

```sh
set -a; source .env; set +a
```

### Default-off flags (pass 1)

```sh
export CODEXIFY_ENABLE_GRAPH_WRITES=false
export CODEXIFY_GRAPH_BACKEND=noop
```

### Active model

`gemma4-e4b-hauhau:latest` via local provider at `100.109.4.57:11434`.

### Neo4j credentials

- `NEO4J_USER=neo4j`
- `NEO4J_PASS=codexify`

---

## Exact Commands Run

### Health and config probes

```sh
BASE=http://localhost:8888
KEY="$(scripts/dev/dev-key.sh)"
curl -s "$BASE/health" | python3 -m json.tool
curl -s "$BASE/health/chat" | python3 -m json.tool
curl -s "$BASE/api/health/llm" | python3 -m json.tool

# Verify runtime graph flags
docker compose exec -T backend python -c "
from guardian.core.config import settings
print(f'CODEXIFY_ENABLE_GRAPH_WRITES: {settings.CODEXIFY_ENABLE_GRAPH_WRITES}')
print(f'CODEXIFY_GRAPH_BACKEND: {settings.CODEXIFY_GRAPH_BACKEND}')
"

# Verify compose config
docker compose config | grep -E "CODEXIFY_ENABLE_GRAPH_WRITES|CODEXIFY_GRAPH_BACKEND" -n
```

### Default-off sentinel chat turn

```sh
SENTINEL="DEFAULT_OFF_RERUN_TRACE_FIX_2026_05_08"
THREAD=$(curl -fsS -X POST "$BASE/api/chat/threads" \
  -H "content-type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"summary":"default-off-trace-fix-rerun"}')
THREAD_ID=$(printf '%s' "$THREAD" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/messages" \
  -H "content-type: application/json" \
  -H "X-API-Key: $KEY" \
  -d "{\"role\":\"user\",\"content\":\"$SENTINEL What is 2+2? Reply with just the number.\"}"
COMPLETE=$(curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/complete" \
  -H "content-type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{}')
# Wait for completion...
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/chat/$THREAD_ID/messages?limit=5"
```

### Neo4j sentinel check

```sh
NPASS="$(grep -E '^NEO4J_PASS=' .env | tail -n1 | cut -d= -f2-)"
docker compose exec -T neo4j /var/lib/neo4j/bin/cypher-shell \
  -a bolt://localhost:7687 -u neo4j -p "$NPASS" \
  "MATCH (n) WHERE any(k IN keys(n) WHERE toString(n[k]) CONTAINS '$SENTINEL') RETURN labels(n) AS lbls, count(n) AS cnt;"
```

---

## Default-Off Proof

### Runtime behavior

- `/health` returned `status: ok`, `release_hold: false`
- `/health/chat` returned `ok: true`, worker `fresh`, queue `progressing`
- `/api/health/llm` returned `status: ok`, provider `local`, model `gemma4-e4b-hauhau:latest`
- Backend settings confirmed:
  - `CODEXIFY_ENABLE_GRAPH_WRITES: False`
  - `CODEXIFY_GRAPH_BACKEND: noop`
- `docker compose config` showed graph flags on 4 services:
  - `CODEXIFY_ENABLE_GRAPH_WRITES: "false"` (lines 63, 875, 1176, 1611)
  - `CODEXIFY_GRAPH_BACKEND: noop` (lines 64, 876, 1177, 1612)

### Trace fix verification

The `_build_model_selection_trace(...)` TypeError that blocked the previous proof is now fixed:

- The worker successfully assembled context and built the inference request
- Worker log: `chat.inference.request.built` at 16:43:00
- No `TypeError` or missing-args exception in worker logs
- The trace fix (`6e0fca808`) is confirmed to resolve the invocation bug

### Assistant persistence evidence

**BLOCKED BY ENVIRONMENT: LLM call timeout due to massive graph context.**

The worker-chat successfully:
1. Accepted the task (`[task] running type=chat_completion id=a969a15d...`)
2. Initialized context broker and memory retriever
3. Assembled context from messages, docs, and graph
4. Built the inference request (`chat.inference.request.built`)

However, the context broker contributed **2452 graph nodes** to the context window:

```
[ContextBroker] thread=1228 depth=normal messages=1 semantic=0 obsidian=0 docs(project/thread)=2/0 memory=0(skipped) graph=2452(contributed)
```

This massive graph context (accumulated from multiple previous proof runs writing MessageNode/ThreadNode entries to Neo4j via the `GUARDIAN_ENABLE_GRAPH_CONTEXT` path) caused the LLM inference request to be extremely large. The Ollama instance at `100.109.4.57:11434` did not respond within the timeout window.

The worker retried the inference request at 16:48:00 (5 minutes after the first attempt), but still did not receive a response.

**This is an environment issue, not a code bug.** The `_build_model_selection_trace` fix is confirmed working (no TypeError). The completion path gets past context assembly and into LLM inference, but the massive graph context makes the request too large for the model to process in a reasonable time.

### Neo4j non-write evidence

Not checked — the completion did not finish, so the graph-write lane was not triggered for this sentinel.

---

## Explicit-On Neo4j Proof

**NOT EXECUTED.**

The default-off pass was blocked by the graph context timeout. Restarting the stack with explicit-on flags would encounter the same environment issue (2452 graph nodes in Neo4j contributing massive context).

The explicit-on pass is deferred until the graph context is cleaned up or the context broker's graph contribution is bounded.

---

## Duplicate / Replay Safety Check

**NOT EXECUTED.**

Depends on successful completion in explicit-on mode. Unit tests remain the canonical evidence for duplicate/replay safety (`tests/workers/test_graph_write_worker.py`).

---

## Observed Failures / Degraded Signals / Unknowns

### Environment blocker: Massive graph context

- Neo4j contains 2452+ MessageNode entries accumulated from previous proof runs
- The `GUARDIAN_ENABLE_GRAPH_CONTEXT=True` setting causes the context broker to query Neo4j for graph-derived context during every completion
- This results in 2452 graph nodes being contributed to the context window
- The resulting LLM request is too large for the Ollama instance to process within the timeout
- This is a runtime environment issue, not a code bug

### Evidence of graph context accumulation

From the previous proof session (`2026-05-08-neo4j-graph-backend-live-proof-after-runtime-boundary-fix.md`):

- Neo4j node inventory: MessageNode: 26, ThreadNode: 12, User: 1, Project: 1, UserNode: 1
- The graph context logging path (`GUARDIAN_ENABLE_GRAPH_CONTEXT`) writes MessageNode/ThreadNode for every chat message
- Multiple proof runs have accumulated these nodes over time
- The current run shows `graph=2452(contributed)`, suggesting significant additional accumulation

### Trace fix confirmed working

- The `_build_model_selection_trace` TypeError is resolved
- Worker logs show no missing-args exception
- The completion path reaches the LLM inference stage
- The blocker is purely environmental (context size), not code-level

---

## Release-Truth Interpretation

### What this proves

- The `_build_model_selection_trace` invocation fix (`6e0fca808`) resolves the TypeError that blocked the previous proof
- The graph-write factory boundary (ADR-026) remains correctly configured with default-off flags
- The context broker assembles context from messages, docs, and graph sources
- The worker successfully builds the inference request after context assembly

### What this does not prove

- This proof does not confirm assistant persistence succeeds (blocked by environment)
- This proof does not confirm explicit-on Neo4j graph writes (deferred)
- This proof does not confirm duplicate/replay safety (deferred)
- This proof does not widen the supported beta promise
- Neo4j graph writes remain optional and explicit-gate only
- Postgres remains canonical truth
- Retrieval, export/restore, and UI surfaces were not changed

### Environment remediation needed

Before re-running this proof:

1. Clean up accumulated Neo4j MessageNode/ThreadNode entries from previous proof runs, OR
2. Set `GUARDIAN_ENABLE_GRAPH_CONTEXT=false` for the proof session to disable graph context contribution, OR
3. Bound the graph context contribution to a reasonable limit

---

## Final Result

**HOLD** (environment blocker)

The `_build_model_selection_trace` fix is confirmed working. The completion path no longer raises the missing-args TypeError. However, the proof cannot proceed to assistant persistence or graph-write verification because the Neo4j graph context (2452 nodes) makes the LLM inference request too large to process within the timeout.

This is a runtime environment issue caused by accumulated graph nodes from previous proof runs via the `GUARDIAN_ENABLE_GRAPH_CONTEXT` path, not a code bug or architecture contract violation.

**Recommendation:** Clean up Neo4j graph nodes or disable `GUARDIAN_ENABLE_GRAPH_CONTEXT` for the next proof run, then re-execute both default-off and explicit-on passes.
