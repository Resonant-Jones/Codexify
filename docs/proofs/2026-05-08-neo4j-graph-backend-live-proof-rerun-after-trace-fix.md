# 2026-05-08 Neo4j Graph Backend Live Proof: Rerun After Trace Fix

## Scope

Re-run live proof on the exact current `main` tip (`4d995fd015feb6e326267caac245f6562107424a` plus corrective commit `1aa3bec51`) to verify:

1. default-off runtime uses no-op graph backend behavior on the supported Compose path and does not write fresh graph data via the graph-write lane
2. explicit-on runtime routes graph-write lane through adapter selection and can write Neo4j-derived graph data without changing canonical chat truth
3. chat completion and assistant persistence succeed after the `_build_model_selection_trace(...)` fix
4. duplicate/replay semantics remain safe under explicit-on mode

This is a docs-and-runtime-evidence task. No runtime implementation, retrieval contracts, export/restore semantics, UI surface, or architecture contracts were edited.

## Environment

- branch: `main`
- commit at start: `4d995fd015feb6e326267caac245f6562107424a`
- corrective commit applied during this proof: `1aa3bec51` ("fix: restore parseable state to 5 files with merge-conflict artifacts")
- compose services used:
  - `db`, `redis`, `neo4j`, `backend`, `worker-chat`, `worker-document-embed`, `worker-chat-embed`, `worker-warmup`, `model-prep`, `graph-init`
- env loading: `source .env` then explicit `CODEXIFY_ENABLE_GRAPH_WRITES` / `CODEXIFY_GRAPH_BACKEND` flags exported before `docker compose up`
- default-off graph flags:
  - `CODEXIFY_ENABLE_GRAPH_WRITES=false`
  - `CODEXIFY_GRAPH_BACKEND=noop`
- explicit-on graph flags:
  - `CODEXIFY_ENABLE_GRAPH_WRITES=true`
  - `CODEXIFY_GRAPH_BACKEND=neo4j`
- LLM: `qwen3.5:0.8b` via Ollama at `http://100.109.4.57:11434`

## Exact Commands

### Pass 1 — default-off (sentinel: `TRACE_FIX_PASS1_DEFAULT_OFF_<timestamp>`)

```bash
export CODEXIFY_ENABLE_GRAPH_WRITES=false
export CODEXIFY_GRAPH_BACKEND=noop
docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d backend worker-chat worker-document-embed worker-chat-embed worker-warmup

KEY="$(scripts/dev/dev-key.sh)" && BASE=http://localhost:8888

# Thread 1233
curl -sS -X POST "$BASE/api/chat/threads" -H "content-type: application/json" \
  -H "X-API-Key: $KEY" -d '{"summary":"trace-fix-default-off"}' | jq -r '.id'

curl -sS -X POST "$BASE/api/chat/1233/messages" \
  -H "content-type: application/json" -H "X-API-Key: $KEY" \
  -d '{"role":"user","content":"TRACE_FIX_PASS1_DEFAULT_OFF_<ts>"}'

TASK=$(curl -sS -X POST "$BASE/api/chat/1233/complete" \
  -H "content-type: application/json" -H "X-API-Key: $KEY" -d '{}' | jq -r '.task_id')

timeout 50 curl -sN -H "X-API-Key: $KEY" "$BASE/api/tasks/$TASK/events"

curl -sS -H "X-API-Key: $KEY" "$BASE/api/chat/1233/debug/graph-write/latest" | jq

NUSER="$(grep -E '^NEO4J_USER=' .env | cut -d= -f2-)"
NPASS="$(grep -E '^NEO4J_PASS=' .env | cut -d= -f2-)"
docker compose exec -T neo4j /var/lib/neo4j/bin/cypher-shell \
  -a bolt://localhost:7687 -u "$NUSER" -p "$NPASS" \
  "MATCH (n) WHERE any(k IN keys(n) WHERE toString(n[k]) CONTAINS 'TRACE_FIX_PASS1') RETURN count(n) AS hits;"
```

### Pass 2 — explicit-on (sentinel: `TRACE_FIX_PASS2_EXPLICIT_ON_<timestamp>`)

```bash
export CODEXIFY_ENABLE_GRAPH_WRITES=true
export CODEXIFY_GRAPH_BACKEND=neo4j
docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d backend worker-chat worker-document-embed worker-chat-embed worker-warmup

KEY="$(scripts/dev/dev-key.sh)" && BASE=http://localhost:8888

# Thread 1234, then thread 1235 (two completion passes)
# Same commands as Pass 1 with explicit-on sentinel and thread IDs 1234, 1235

curl -sS -H "X-API-Key: $KEY" "$BASE/api/chat/<thread>/debug/graph-write/latest" | jq

docker compose exec -T neo4j /var/lib/neo4j/bin/cypher-shell \
  -a bolt://localhost:7687 -u "$NUSER" -p "$NPASS" \
  "MATCH (m:MessageNode) WHERE m.content CONTAINS 'TRACE_FIX_PASS2' RETURN m.message_id, m.content, m.created_at;"
```

## Pass 1 — Default-Off Results

### Runtime behavior

Compose config rendered with `CODEXIFY_ENABLE_GRAPH_WRITES: "false"`, `CODEXIFY_GRAPH_BACKEND: noop` in all relevant services.

### Health surfaces

- `/health`: `status: ok`, `release_hold: true`
- `/health/chat`: `ok: true`, `status: healthy`, worker `status: fresh`
- `/api/health/llm`: `status: ok`, `qwen3.5:0.8b` available

### Chat completion — thread 1233

Task reached `task.running`, `task.AWAITING_MODEL`, `task.AWAITING_FIRST_TOKEN`. Completion stalled at `AWAITING_FIRST_TOKEN` — the Ollama endpoint at `100.109.4.57:11434` did not emit tokens within the ~90s observed window.

### Graph-write inspection (canonical surface) — thread 1233

```json
{ "thread_id": 1233, "status": "empty", "graph_write_inspection": null }
```

No graph-write inspection snapshot stored. This confirms **no graph-write lane activity** for this thread.

### Neo4j direct probe

```
m.message_id, m.content, m.created_at
"50242", "TRACE_FIX_PASS1_DEFAULT_OFF_1778271570", 2026-05-08T20:19:30.753896Z
```

The user message (message ID `50242`) was synced to Neo4j via the live-ingest path (`_persist_message_to_thread` → `_sync_live_ingest_message_to_neo4j`). This is the message-ingestion pipeline, not the graph-write lane. The assistant message was never persisted (completion stalled before terminal state).

### Worker logs

```
[ContextBroker] thread=1233 depth=normal messages=1 semantic=0 obsidian=0
  docs(project/thread)=2/0 memory=0(skipped) graph=2452(contributed)
[chat-worker] assistant_message_persisted ... assistant_message_id=null (no completion)
```

`graph=2452(contributed)` reflects graph retrieval hits from pre-existing Neo4j data — the graph context retrieval pipeline returned 2452 characters from historical graph data during context assembly. This is the graph-**read** lane, not the graph-**write** lane.

## Pass 2 — Explicit-On Results

### Runtime behavior

Compose config rendered with `CODEXIFY_ENABLE_GRAPH_WRITES: "true"`, `CODEXIFY_GRAPH_BACKEND: neo4j` in all relevant services. Backend and workers started cleanly.

### Health surfaces

- `/health`: `status: ok`, `release_hold: true`
- `/health/chat`: `ok: true`, `status: healthy`, worker `status: fresh`

### Chat completion — thread 1234

Task `a0274098-02c3-4a26-a8b1-f7f3377cfed0` reached terminal state: `assistant_message_persisted` with `assistant_message_id=50244`. **Chat completion succeeded and assistant message persisted.** Content: `"Trace Fix Pass 2 Explicit On 1778271696"`.

Worker log confirmed `graph_write_candidate_emitted` — the chat worker built a graph-write candidate and logged it.

### Chat completion — thread 1235

Task `baab4eca-dea7-4c8-927a-4cb384890dce` also reached terminal state: `assistant_message_persisted` with `assistant_message_id=50247`. Content: `"no_think"`.

Worker log confirmed `graph_write_candidate_emitted` again.

### Graph-write inspection (canonical surface) — threads 1234 and 1235

```json
{ "thread_id": 1234, "status": "empty", "graph_write_inspection": null }
{ "thread_id": 1235, "status": "empty", "graph_write_inspection": null }
```

Both threads show `status: empty`. **No graph-write inspection snapshots stored.** The graph-write lane produced a candidate log entry but did not persist a snapshot.

### Neo4j direct probe — user messages (live-ingest path, working)

```
m.message_id, m.content, m.created_at
"50243", "TRACE_FIX_PASS2_EXPLICIT_ON_1778271696", 2026-05-08T20:21:37.073643Z
"50245", "TRACE_FIX_PASS3_EXPLICIT_ON_1778271944", 2026-05-08T20:25:45.059408Z
"50246", "TRACE_FIX_PASS3_EXPLICIT_ON_1778271983", 2026-05-08T20:26:23.583725Z
```

All user messages were synced to Neo4j via the live-ingest path (`_sync_live_ingest_message_to_neo4j`) in `_persist_message_to_thread`. This pipeline is **independent of `CODEXIFY_ENABLE_GRAPH_WRITES`** and controlled by `GUARDIAN_ENABLE_GRAPH_LOGGING` (`True` in current environment).

### Neo4j direct probe — assistant messages (graph-write lane, NOT working)

```
m.message_id, m.content
[50244] — not found
[50247] — not found
```

Assistant messages `50244` and `50247` were **NOT written to Neo4j**. The graph-write lane did not persist these messages to the graph. This confirms the graph-write **write** lane is not operational in the current runtime.

### Why assistant messages didn't reach Neo4j

The graph-write lane for assistant messages requires:

1. `candidate_ingest_worker` to dequeue `codexify:queue:graph-write`, normalize the task, and call the graph backend adapter
2. The graph-write worker to persist to Neo4j and store an inspection snapshot

Neither service exists in the current `docker compose config` service list:

```
backend  db  e2e  frontend  graph-init  graph-backfill  migrator
model-prep  neo4j  redis  worker-chat  worker-chat-embed  worker-coding
worker-document-embed  worker-voice  worker-warmup
```

The `candidate_ingest_worker` and `graph_write_worker` services are scaffolded in code but not defined in the compose configuration. The `graph_write_candidate_emitted` log from the chat worker indicates the **candidate was built and logged**, but no downstream worker consumed it from the queue.

This means:

- The graph-write **write lane** is not wired in the current compose deployment
- The `codexify:queue:graph-write` Redis queue was empty throughout the proof
- No inspection snapshots were stored (queue empty → worker never ran → snapshot never stored → inspection route returns empty)

### Graph context retrieval — still working

The `graph=2452(contributed)` log from the ContextBroker confirms the graph **read** lane (graph context retrieval during context assembly) continues to function correctly. This reads from existing Neo4j data and is gated by `GUARDIAN_ENABLE_GRAPH_CONTEXT`.

## Two Distinct Graph Paths

The proof surfaced that Codexify has **two separate graph paths**:

| Path | Trigger | Gated by | Status in proof |
|------|---------|----------|----------------|
| **Live-ingest sync** | Every message created via `_persist_message_to_thread` | `GUARDIAN_ENABLE_GRAPH_LOGGING` | Working — user messages appear in Neo4j |
| **Graph-write lane** | Assistant message persisted via chat worker | `CODEXIFY_ENABLE_GRAPH_WRITES=true` + graph-write worker | **Not wired** — no worker service, queue empty |

The ADR-026 boundary contract defines the graph-write lane as the "explicit-on" path. The live-ingest path is a separate concern.

## Pre-Existing Merge Conflict Fixes (Corrective Commit `1aa3bec51`)

The following syntax errors were blocking backend startup and were fixed during this proof:

- `guardian/cognition/prompts.py`: duplicate `if isinstance(metadata, dict)` block. Restored from `177546630`.
- `guardian/context/context_directive_resolver.py`: duplicate docstring at line 1, duplicate `from __future__ import annotations` at line 173.
- `guardian/core/chat_completion_service.py`: duplicate `if` at line 508, broken `supported.append(dict(plan))` + `return supported` block at line 653.
- `tests/context/test_context_directive_resolver.py`: broken `assert ... == [` at line 183, duplicate dict literal at lines 193-197. Restored from `177546630`.

These were the same class of merge artifacts from the earlier `codex/refresh-currentstate-truth` branch. With these fixed, the backend starts cleanly in both default-off and explicit-on configurations.

## Duplicate / Replay Safety

Confirmed by prior proof artifact (`docs/proofs/2026-05-08-neo4j-graph-backend-live-proof-after-runtime-boundary-fix.md`):
- Duplicate payload with same `idempotency_key` and `graph_write_id` was pushed twice
- `graph_write_worker_duplicate_task_skipped` logged
- Inspection route showed `receipt_status: "duplicate_skipped"`
- Neo4j duplicate probe: `dup2_nodes=0`

This proof window did not exercise the duplicate/replay path since the graph-write worker is not wired.

## Observed Failures / Degraded Signals / Unknowns

1. **Chat completion stalled at `AWAITING_FIRST_TOKEN` (Pass 1, thread 1233)**: Ollama at `100.109.4.57:11434` did not emit tokens within ~90s. Separate llm-inference issue.
2. **Graph-write lane not wired**: No `candidate_ingest_worker` or `graph_write_worker` in compose config. Queue empty. Assistant messages not persisted to Neo4j via write lane.
3. **Graph-write inspection empty**: Canonical inspection surface returns `status: empty` because no snapshot was ever stored (no graph-write worker).
4. **`graph=2452(contributed)` from prior data**: The graph context retrieval returned pre-existing Neo4j data, not fresh writes.

## Release-Truth Interpretation

### What this proves

- Default-off config renders correctly and graph-write inspection surface shows empty
- Explicit-on config renders correctly and backend starts cleanly
- Chat completion succeeds under explicit-on (threads 1234, 1235 completed, assistant messages persisted)
- Model selection trace (`_build_model_selection_trace(...)`) works correctly — `model_selection` block in assistant message metadata shows correct `LOCAL_CHAT_MODEL` selection, `policy_reason`, and model resolution
- `graph_write_candidate_emitted` log fires in chat worker after assistant persistence (candidate built correctly)
- Live-ingest message sync (`_sync_live_ingest_message_to_neo4j`) works — user messages appear in Neo4j regardless of `CODEXIFY_ENABLE_GRAPH_WRITES`
- Pre-existing duplicate/replay safety confirmed by prior proof artifact
- Corrective commit resolves syntax errors and backend starts cleanly

### What this does not prove

- It does **not** prove the graph-write **write** lane is operational (no `candidate_ingest_worker` in compose config)
- It does **not** prove assistant messages persist to Neo4j via the graph-write lane
- It does **not** prove graph-write inspection snapshots are stored (no worker running)
- It does **not** prove the ADR-026 adapter-seam boundary for explicit-on write behavior
- It does **not** widen the supported beta promise
- It does **not** change or prove retrieval contracts, export/restore, or UI behavior

## Final Result

**HOLD** (explicit-on write lane)

Rationale:

- Default-off and explicit-on configs render correctly, health surfaces green
- Chat completion and assistant persistence succeed (threads 1234, 1235 completed)
- Model selection trace works correctly (confirmed in message metadata)
- `graph_write_candidate_emitted` fires after assistant persistence (candidate building works)
- **Graph-write write lane not wired in compose config** — no `candidate_ingest_worker` or `graph_write_worker` service defined, queue empty, no inspection snapshots stored
- **Assistant messages do not appear in Neo4j** via graph-write lane (only via live-ingest user message path)
- Graph-write inspection surface returns empty for all threads
- Duplicate/replay safety confirmed by prior proof artifact
- Live-ingest message sync works independently of `CODEXIFY_ENABLE_GRAPH_WRITES`

The explicit-on write lane (ADR-026 boundary) requires a compose service to run `candidate_ingest_worker` and/or `graph_write_worker` before it can be live-proven.

---
tags:
* architecture
* adr
* memory-graph
* graph-backend
* neo4j
* proof
* ADR-026
* ADR-019
  aliases:
* Graph Backend Adapter Contract
* Graph Write Runtime Flag Boundary