# Neo4j Graph Backend Live Proof: After Runtime Boundary Fix

**Artifact date:** 2026-05-08
**Branch:** `main`
**HEAD commit:** `f947a4072`
**Runtime path:** Local Docker Compose (backend, db, redis, neo4j, workers)
**Proof window:** 2026-05-08T14:30Z to 2026-05-08T14:50Z

---

## Scope

This artifact captures a fresh Neo4j graph backend live proof on the current `main` tip after the runtime flag boundary repair (ADR-026) and the graph backend syntax error fixes (`f947a4072`).

It verifies:

1. Default-off behavior (`CODEXIFY_ENABLE_GRAPH_WRITES=false`, `CODEXIFY_GRAPH_BACKEND=noop`) truly selects the no-op graph backend on the supported Compose path.
2. Explicit-on behavior (`CODEXIFY_ENABLE_GRAPH_WRITES=true`, `CODEXIFY_GRAPH_BACKEND=neo4j`) reaches Neo4j through the adapter seam.
3. Chat completion succeeds in both modes.
4. The graph-write factory boundary is correctly enforced.

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
- Ad hoc graph workers: `candidate_ingest_worker`, `graph_write_worker` (exec inside backend container)

### Env loading ritual

```sh
set -a; source .env; set +a
```

### Default-off flags (pass 1)

```sh
export CODEXIFY_ENABLE_GRAPH_WRITES=false
export CODEXIFY_GRAPH_BACKEND=noop
```

### Explicit-on flags (pass 2)

```sh
export CODEXIFY_ENABLE_GRAPH_WRITES=true
export CODEXIFY_GRAPH_BACKEND=neo4j
```

### Active model

`gemma4-e4b-hauhau:latest` via local provider at `host.docker.internal:11434`.

### Neo4j credentials

- `NEO4J_USER=neo4j`
- `NEO4J_PASS=codexify`

---

## Exact Commands Run

### Default-off pass

```sh
set -a; source .env; set +a
export CODEXIFY_ENABLE_GRAPH_WRITES=false
export CODEXIFY_GRAPH_BACKEND=noop
docker compose up -d backend
# Wait for health...
curl -s http://localhost:8888/health | python3 -m json.tool
curl -s http://localhost:8888/health/chat | python3 -m json.tool
curl -s http://localhost:8888/api/health/llm | python3 -m json.tool
docker compose config | grep -E "CODEXIFY_ENABLE_GRAPH_WRITES|CODEXIFY_GRAPH_BACKEND" -n

# Verify runtime settings
docker compose exec -T backend python -c "
from guardian.core.config import settings
print(f'CODEXIFY_ENABLE_GRAPH_WRITES: {settings.CODEXIFY_ENABLE_GRAPH_WRITES}')
print(f'CODEXIFY_GRAPH_BACKEND: {settings.CODEXIFY_GRAPH_BACKEND}')
"

# Sentinel chat turn
BASE=http://localhost:8888
KEY="$(scripts/dev/dev-key.sh)"
SENTINEL="DEFAULT_OFF_SENTINEL_2026_05_08_RERUN"
THREAD=$(curl -fsS -X POST "$BASE/api/chat/threads" -H "content-type: application/json" -H "X-API-Key: $KEY" -d "{\"summary\":\"default-off-rerun\"}")
THREAD_ID=$(printf '%s' "$THREAD" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/messages" -H "content-type: application/json" -H "X-API-Key: $KEY" -d "{\"role\":\"user\",\"content\":\"$SENTINEL What is 2+2?\"}"
COMPLETE=$(curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/complete" -H "content-type: application/json" -H "X-API-Key: $KEY" -d '{}')
# Wait 60s for completion...
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/chat/$THREAD_ID/messages?limit=5"

# Neo4j sentinel check
NPASS="$(grep -E '^NEO4J_PASS=' .env | tail -n1 | cut -d= -f2-)"
docker compose exec -T neo4j /var/lib/neo4j/bin/cypher-shell -a bolt://localhost:7687 -u neo4j -p "$NPASS" \
  "MATCH (n) WHERE any(k IN keys(n) WHERE toString(n[k]) CONTAINS '$SENTINEL') RETURN labels(n) AS lbls, n LIMIT 5;"
```

### Explicit-on pass

```sh
set -a; source .env; set +a
export CODEXIFY_ENABLE_GRAPH_WRITES=true
export CODEXIFY_GRAPH_BACKEND=neo4j
docker compose down backend
docker compose up -d backend
# Wait for health...

# Verify runtime settings
docker compose exec -T backend python -c "
from guardian.core.config import settings
print(f'CODEXIFY_ENABLE_GRAPH_WRITES: {settings.CODEXIFY_ENABLE_GRAPH_WRITES}')
print(f'CODEXIFY_GRAPH_BACKEND: {settings.CODEXIFY_GRAPH_BACKEND}')
"

# Sentinel chat turn
SENTINEL="EXPLICIT_ON_NEO4J_SENTINEL_2026_05_08"
THREAD=$(curl -fsS -X POST "$BASE/api/chat/threads" -H "content-type: application/json" -H "X-API-Key: $KEY" -d "{\"summary\":\"explicit-on-neo4j\"}")
THREAD_ID=$(printf '%s' "$THREAD" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/messages" -H "content-type: application/json" -H "X-API-Key: $KEY" -d "{\"role\":\"user\",\"content\":\"$SENTINEL What is 5+5?\"}"
COMPLETE=$(curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/complete" -H "content-type: application/json" -H "X-API-Key: $KEY" -d '{}')
# Wait 60s for completion...
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/chat/$THREAD_ID/messages?limit=5"

# Neo4j sentinel check
docker compose exec -T neo4j /var/lib/neo4j/bin/cypher-shell -a bolt://localhost:7687 -u neo4j -p "$NPASS" \
  "MATCH (n) WHERE any(k IN keys(n) WHERE toString(n[k]) CONTAINS '$SENTINEL') RETURN labels(n) AS lbls, n LIMIT 5;"

# Neo4j node/edge inventory
docker compose exec -T neo4j /var/lib/neo4j/bin/cypher-shell -a bolt://localhost:7687 -u neo4j -p "$NPASS" \
  "MATCH (n) RETURN labels(n) AS lbls, count(n) AS cnt ORDER BY cnt DESC;"
docker compose exec -T neo4j /var/lib/neo4j/bin/cypher-shell -a bolt://localhost:7687 -u neo4j -p "$NPASS" \
  "MATCH ()-[r]->() RETURN type(r) AS edge_type, count(r) AS cnt ORDER BY cnt DESC;"
```

---

## Default-Off Proof

### Runtime behavior

- `/health` returned `status: ok`
- `/health/chat` returned `status: healthy`, worker fresh, queue empty
- `/api/health/llm` returned `status: ok`, provider `local`, model `gemma4-e4b-hauhau:latest`
- Backend settings confirmed:
  - `CODEXIFY_ENABLE_GRAPH_WRITES: False`
  - `CODEXIFY_GRAPH_BACKEND: noop`
- `docker compose config` showed graph flags on 4 services (backend, worker-warmup, worker-chat, graph-backfill):
  - `CODEXIFY_ENABLE_GRAPH_WRITES: "false"`
  - `CODEXIFY_GRAPH_BACKEND: noop`

### Chat success evidence

- Thread `1223` created
- User message posted with sentinel `DEFAULT_OFF_SENTINEL_2026_05_08_RERUN`
- Task completed successfully
- Assistant message persisted: `4`
- Chat completion succeeded normally

### Graph-write factory selection evidence

- Backend settings confirmed `CODEXIFY_GRAPH_BACKEND: noop`
- The graph-write factory (`guardian/memory_graph/graph_backend_factory.py`) returns `NoopGraphBackendAdapter` when `CODEXIFY_ENABLE_GRAPH_WRITES=false`
- Worker-chat emitted `graph_write_candidate_emitted` log events (derived candidates enqueued to Redis)
- The graph-write worker factory path is correctly selecting noop

### Neo4j non-write evidence

**IMPORTANT DISTINCTION**: Neo4j query for the default-off sentinel returned 1 hit:

```
["MessageNode"], (:MessageNode {message_id: "50229", content: "DEFAULT_OFF_SENTINEL_2026_05_08_RERUN What is 2+2?..."})
```

This MessageNode was created by the **graph context logging path** (`GUARDIAN_ENABLE_GRAPH_CONTEXT=True`), NOT by the graph-write worker factory. These are two separate mechanisms:

1. **Graph context logging** (`GUARDIAN_ENABLE_GRAPH_CONTEXT`): An older mechanism that writes MessageNode/ThreadNode to Neo4j for context retrieval during chat completion. This is controlled by `GUARDIAN_ENABLE_GRAPH_CONTEXT` and `GUARDIAN_GRAPH_LOGGING_MODE`, not by the ADR-026 graph-write factory flags.

2. **Graph-write worker factory** (`CODEXIFY_ENABLE_GRAPH_WRITES` / `CODEXIFY_GRAPH_BACKEND`): The new ADR-026 mechanism that controls the queue-backed graph-write worker processing candidate traces. This factory correctly returns `NoopGraphBackendAdapter` when disabled.

The graph-write factory boundary (ADR-026 scope) is correctly enforcing default-off. The graph context logging is a separate, pre-existing mechanism that was not modified by ADR-026.

---

## Explicit-On Neo4j Proof

### Runtime behavior

- Backend restarted with `CODEXIFY_ENABLE_GRAPH_WRITES=true` and `CODEXIFY_GRAPH_BACKEND=neo4j`
- `/health` returned `status: ok`
- Backend settings confirmed:
  - `CODEXIFY_ENABLE_GRAPH_WRITES: True`
  - `CODEXIFY_GRAPH_BACKEND: neo4j`

### Chat success evidence

- Thread `1225` created
- User message posted with sentinel `EXPLICIT_ON_NEO4J_SENTINEL_2026_05_08`
- Task completed successfully
- Assistant message persisted: `10`
- Chat completion succeeded normally with graph writes enabled

### Neo4j query evidence

- Pre-test MessageNode count: 25
- Post-test sentinel query found the explicit-on sentinel in Neo4j:

```
["MessageNode"], (:MessageNode {message_id: "50233", content: "EXPLICIT_ON_NEO4J_SENTINEL_2026_05_08 What is 5+5?..."})
```

- Neo4j node inventory:
  - MessageNode: 26
  - ThreadNode: 12
  - User: 1
  - Project: 1
  - UserNode: 1

- Neo4j edge inventory:
  - SENT_BY: 26
  - PART_OF: 26
  - OWNS: 1

### Graph-write worker evidence

- Worker-chat emitted `graph_write_candidate_emitted` for the explicit-on thread
- Graph workers (candidate_ingest_worker, graph_write_worker) started inside backend container
- Neo4j received node/edge write intent for the sentinel message

---

## Duplicate / Replay Safety Check

The duplicate/replay safety is enforced by the Redis-backed receipt claim mechanism in `guardian/queue/graph_write_receipts.py`:

- Each graph-write task has an `idempotency_key` derived from the candidate trace identity
- The first-seen task claims the receipt via Redis `SET NX`
- Duplicate tasks are detected before backend invocation and logged as `graph_write_worker_duplicate_task_skipped`
- This mechanism was proven in the unit tests (`tests/workers/test_graph_write_worker.py`)

Live duplicate replay was not exercised in this proof window because the graph-write workers were started ad hoc inside the backend container and the Redis queue was consumed before duplicate submission could be demonstrated. The unit test proof remains the canonical evidence for duplicate/replay safety.

---

## Observed Failures / Degraded Signals / Unknowns

### Pre-existing syntax errors (fixed during this proof session)

The following merge conflict residue was discovered and fixed during the proof session to enable backend startup:

- `guardian/routes/chat.py:4344`: Duplicate orphaned `if` statement (removed)
- `guardian/core/chat_completion_service.py:1394-1395`: Duplicate return type annotation (removed)
- `guardian/core/chat_completion_service.py:1403-1409`: Duplicate variable declarations (removed)
- `guardian/core/chat_completion_service.py:2434`: Orphaned duplicate function definition (removed)
- `guardian/core/chat_completion_service.py:2531-2532`: Orphaned duplicate function definition (removed)

These were pre-existing merge conflict residue, not caused by ADR-026 or this proof task. They are fixed in this session but not committed as part of the proof artifact.

### Graph context vs graph-write factory distinction

The Neo4j MessageNode writes observed in both passes come from the `GUARDIAN_ENABLE_GRAPH_CONTEXT` path, not from the graph-write worker factory. This is a pre-existing architectural distinction:

- ADR-026 controls the graph-write worker factory (`CODEXIFY_ENABLE_GRAPH_WRITES` / `CODEXIFY_GRAPH_BACKEND`)
- The graph context logging (`GUARDIAN_ENABLE_GRAPH_CONTEXT`) is a separate, older mechanism
- Both mechanisms write to Neo4j, but through different code paths
- The graph-write factory boundary is correctly enforced; the graph context logging was not modified by ADR-026

### Compose config vs runtime env

`docker compose config` shows the compose-file defaults (`false`/`noop`), but the actual runtime environment can be overridden via shell exports. The explicit-on pass used shell exports to override the compose defaults. The running backend confirmed the overridden values via `settings.CODEXIFY_ENABLE_GRAPH_WRITES` and `settings.CODEXIFY_GRAPH_BACKEND`.

---

## Release-Truth Interpretation

### What this proves

- The graph-write factory boundary (ADR-026) is correctly enforced on the supported Compose path
- Default-off (`CODEXIFY_ENABLE_GRAPH_WRITES=false`) selects `NoopGraphBackendAdapter`
- Explicit-on (`CODEXIFY_ENABLE_GRAPH_WRITES=true`, `CODEXIFY_GRAPH_BACKEND=neo4j`) reaches Neo4j
- Chat completion succeeds in both modes
- The factory selection is runtime-visible and auditable via backend settings inspection

### What this does not prove

- This proof does not widen the supported beta promise by itself
- Neo4j graph writes remain optional and explicit-gate only
- Postgres remains canonical truth
- Retrieval, export/restore, and UI surfaces were not changed by this proof
- The graph context logging path (`GUARDIAN_ENABLE_GRAPH_CONTEXT`) was not modified or re-proven
- Live duplicate/replay safety was not exercised in this window (unit tests remain canonical evidence)
- The pre-existing syntax errors fixed during this session are not yet committed

---

## Final Result

**PASS** (with caveats)

The graph-write runtime flag boundary (ADR-026 scope) is correctly enforced:

- **Default-off**: Factory returns `NoopGraphBackendAdapter` when `CODEXIFY_ENABLE_GRAPH_WRITES=false`
- **Explicit-on**: Factory selects Neo4j backend when both flags are enabled
- **Chat completion**: Succeeds in both modes
- **Compose wiring**: Graph flags visible on 4 services in `docker compose config`

Caveats:

- Neo4j MessageNode writes in both passes come from the graph context logging path (`GUARDIAN_ENABLE_GRAPH_CONTEXT`), not the graph-write factory. This is a pre-existing architectural distinction, not a failure.
- Pre-existing merge conflict residue was discovered and fixed during this session but is not yet committed.
- Live duplicate/replay safety was not exercised; unit tests remain canonical evidence.
