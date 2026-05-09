# 2026-05-07 Neo4j Graph Backend Live Proof

## Scope

Run a live runtime proof on local Docker Compose to verify:

1. default-off graph behavior (`CODEXIFY_ENABLE_GRAPH_WRITES=false`, `CODEXIFY_GRAPH_BACKEND=noop`)
2. explicit-on graph behavior (`CODEXIFY_ENABLE_GRAPH_WRITES=true`, `CODEXIFY_GRAPH_BACKEND=neo4j`)
3. duplicate/replay handling in the graph-write lane

This is a runtime-evidence artifact only. No runtime code, retrieval contracts, export semantics, UI behavior, or ADR contracts were changed in this task.

## Environment

- Branch: `main`
- Exact HEAD: `ae1ee8f9f5b8827ef9df9a151af1946789207cd3`
- Compose services used:
  - `db`
  - `redis`
  - `neo4j`
  - `backend`
  - `worker-chat`
  - `worker-document-embed`
  - `worker-chat-embed`
  - `worker-warmup`
  - plus ad hoc worker processes for graph lane:
    - `python -m guardian.workers.candidate_ingest_worker`
    - `python -m guardian.workers.graph_write_worker`
- Env loading ritual used:
  - `set -a; source .env; set +a`
- Default-off flags requested:
  - `CODEXIFY_ENABLE_GRAPH_WRITES=false`
  - `CODEXIFY_GRAPH_BACKEND=noop`
- Explicit-on flags requested:
  - `CODEXIFY_ENABLE_GRAPH_WRITES=true`
  - `CODEXIFY_GRAPH_BACKEND=neo4j`

### Required pre-read path mismatches in this checkout

- `docs/architecture/adr/025-neo4j-graph-backend-adapter-flagged-off-by-default.md` is not present.
- `docs/dev-setup.md` is not present; nearest setup doc is `docs/infra/dev-setup.md`.

## Exact Commands

```bash
# common
set -a; source .env; set +a
BASE=http://localhost:8888
KEY="$(scripts/dev/dev-key.sh)"

# default-off pass
export CODEXIFY_ENABLE_GRAPH_WRITES=false
export CODEXIFY_GRAPH_BACKEND=noop
docker compose down
docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d backend worker-chat worker-document-embed worker-chat-embed worker-warmup
docker compose exec -d backend python -m guardian.workers.candidate_ingest_worker
docker compose exec -d backend python -m guardian.workers.graph_write_worker
docker compose ps
curl -s "$BASE/health" | jq
curl -s "$BASE/health/chat" | jq
curl -s "$BASE/api/health/llm" | jq

# default-off sentinel turn
THREAD=$(curl -fsS -X POST "$BASE/api/chat/threads" -H "content-type: application/json" -H "X-API-Key: $KEY" -d '{"summary":"default-off-final"}')
THREAD_ID=$(printf '%s' "$THREAD" | jq -r '.id')
SENTINEL="DEFAULT_OFF_SENTINEL_FINAL_1778234377"
curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/messages" -H "content-type: application/json" -H "X-API-Key: $KEY" -d "{\"role\":\"user\",\"content\":\"$SENTINEL\"}"
COMPLETE=$(curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/complete" -H "content-type: application/json" -H "X-API-Key: $KEY" -d '{}')
TASK_ID=$(printf '%s' "$COMPLETE" | jq -r '.task_id')
timeout 15 curl -sN -H "X-API-Key: $KEY" "$BASE/api/tasks/$TASK_ID/events" > /tmp/defaultoff-final-events.sse || true
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/chat/$THREAD_ID/messages?limit=50" | jq

NPASS="$(grep -E '^NEO4J_PASS=' .env | tail -n1 | cut -d= -f2-)"
NUSER="$(grep -E '^NEO4J_USER=' .env | tail -n1 | cut -d= -f2-)"
[ -n "$NUSER" ] || NUSER=neo4j
docker compose exec -T neo4j /var/lib/neo4j/bin/cypher-shell -a bolt://localhost:7687 -u "$NUSER" -p "$NPASS" \
  "MATCH (n) WHERE any(k IN keys(n) WHERE toString(n[k]) CONTAINS '$SENTINEL') RETURN count(n) AS sentinel_hits;"

# explicit-on pass
export CODEXIFY_ENABLE_GRAPH_WRITES=true
export CODEXIFY_GRAPH_BACKEND=neo4j
docker compose down
docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d backend worker-chat worker-document-embed worker-chat-embed worker-warmup
docker compose exec -d backend python -m guardian.workers.candidate_ingest_worker
docker compose exec -d backend python -m guardian.workers.graph_write_worker
docker compose ps
curl -s "$BASE/health" | jq
curl -s "$BASE/health/chat" | jq
curl -s "$BASE/api/health/llm" | jq

# explicit-on sentinel turn
THREAD=$(curl -fsS -X POST "$BASE/api/chat/threads" -H "content-type: application/json" -H "X-API-Key: $KEY" -d '{"summary":"explicit-on-neo4j-manual"}')
THREAD_ID=$(printf '%s' "$THREAD" | jq -r '.id')
curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/messages" -H "content-type: application/json" -H "X-API-Key: $KEY" -d '{"role":"user","content":"EXPLICIT_ON_SENTINEL_1"}'
COMPLETE=$(curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/complete" -H "content-type: application/json" -H "X-API-Key: $KEY" -d '{}')
TASK_ID=$(printf '%s' "$COMPLETE" | jq -r '.task_id')
timeout 45 curl -sN -H "X-API-Key: $KEY" "$BASE/api/tasks/$TASK_ID/events" > /tmp/exp-events-45s.sse || true
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/chat/$THREAD_ID/messages?limit=50" | jq

docker compose exec -T neo4j /var/lib/neo4j/bin/cypher-shell -a bolt://localhost:7687 -u "$NUSER" -p "$NPASS" \
  "MATCH (n) WHERE any(k IN keys(n) WHERE toString(n[k]) CONTAINS 'EXPLICIT_ON_SENTINEL_1') RETURN labels(n) AS labels, properties(n) AS props LIMIT 5;"

# duplicate / replay check (graph-write queue)
PAYLOAD='{"thread_id":1218,"project_id":1,"nodes":[{"id":"n-proof-1","label":"ProofNode"}],"edges":[],"warnings":[],"idempotency_key":"proof-dup-neo4j-1","graph_write_id":"gwr-proof-dup-1","source":"proof-manual"}'
docker compose exec -T redis redis-cli RPUSH codexify:queue:graph-write "$PAYLOAD"
docker compose exec -T redis redis-cli RPUSH codexify:queue:graph-write "$PAYLOAD"
docker compose exec -T redis redis-cli LLEN codexify:queue:graph-write
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/chat/1218/debug/graph-write/latest" | jq

# docs hygiene
make docs
git diff --check
```

## Default-Off Proof

### Runtime behavior

- Chat completion succeeded for default-off sentinel thread `1219`.
- Task stream reached terminal state:
  - `event: task.completed` observed in `/tmp/defaultoff-final-events.sse`.
- Assistant persistence succeeded:
  - `assistant_count: 1`
  - `last_role: assistant`

### Backend selection evidence

- Requested shell env flags were set before Compose launch.
- But backend container env did not expose those flags:
  - `CODEXIFY_ENABLE_GRAPH_WRITES=`
  - `CODEXIFY_GRAPH_BACKEND=`
- `docker compose config` contained no `CODEXIFY_ENABLE_GRAPH_WRITES` or `CODEXIFY_GRAPH_BACKEND` wiring.

### Chat success evidence

- Accepted completion response contained:
  - `task_id=1ef142ca-ab0c-4527-8cdf-3ecfe824d727`
  - `messages_url=/api/chat/1219/messages`
- Task stream emitted `task.completed`.
- `GET /api/chat/1219/messages?limit=50` showed assistant output persisted.

### Neo4j non-write evidence (expected) vs observed

Expected for default-off: no Neo4j write for fresh default-off sentinel.

Observed:

```text
sentinel_hits
1
```

for sentinel `DEFAULT_OFF_SENTINEL_FINAL_1778234377`.

Result: default-off non-write expectation was **not** satisfied.

## Explicit-On Neo4j Proof

### Runtime behavior

- Explicit-on pass completed health checks and accepted a fresh completion turn:
  - `thread_id=1218`
  - `task_id=95d7c5b7-601c-4d6a-bcd8-ab18f95a5850`
- Task stream reached:
  - `event: task.completed`
- Assistant message persisted:
  - `assistant_count: 1`

### Backend selection evidence

- Worker log evidence from runtime:
  - `worker-chat` emitted `graph_write_candidate_emitted`
  - ad hoc `graph_write_worker` process emitted:
    - `graph_write_worker_inspected_task`
    - `graph_write_worker_duplicate_task_skipped` (from duplicate test below)

### Graph-write worker evidence

- Duplicate test route output:

```json
{
  "thread_id": 1218,
  "status": "ok",
  "graph_write_inspection": {
    "graph_write_id": "gwr-proof-dup-1",
    "idempotency_key": "proof-dup-neo4j-1",
    "receipt_status": "duplicate_skipped",
    "node_count": 1,
    "edge_count": 0
  }
}
```

### Neo4j query evidence

Explicit-on sentinel query:

```text
labels, props
["MessageNode"], {created_at: 2026-05-08T09:55:49.530699Z, message_id: "50219", uuid: "a01b73124669437ca9356e26d128b8d2", content: "EXPLICIT_ON_SENTINEL_1"}
```

This confirms Neo4j contains sentinel-linked graph data during the explicit-on proof window.

### Canonical chat isolation

- Chat completion persisted normally in Postgres-backed chat routes.
- Graph lane evidence remained derived and inspection-oriented; no proof in this task shows graph data becoming canonical chat truth.

## Duplicate / Replay Safety Check

- Injected identical graph-write payload twice with same `idempotency_key=proof-dup-neo4j-1`.
- Worker evidence:
  - first task inspected
  - duplicate task skipped
- Inspection route showed `receipt_status: "duplicate_skipped"`.
- Queue drained to `LLEN=0` after processing.

Interpretation: duplicate-handling path is active at the receipt seam.

## Observed Failures / Degraded Signals / Unknowns

1. **Flag wiring gap in Compose runtime**
   - Backend container env did not show `CODEXIFY_ENABLE_GRAPH_WRITES` or `CODEXIFY_GRAPH_BACKEND`.
   - This means shell exports used in proof commands were not proven to control backend behavior in this checkout.

2. **Default-off contradiction**
   - Fresh default-off sentinel still appeared in Neo4j (`sentinel_hits=1`).
   - This contradicts the intended default-off non-write behavior.

3. **Path mismatches vs requested pre-read**
   - `ADR-025` path provided in task is absent in this checkout.
   - `docs/dev-setup.md` path provided in task is absent; `docs/infra/dev-setup.md` exists.

4. **SSE endpoint format mismatch**
   - `/api/tasks/{task_id}/events` is Server-Sent Events (`text/event-stream`), not JSON.
   - Parsing must treat it as SSE.

## Release-Truth Interpretation

### What this proves

- The supported local Compose path runs and can complete chat turns.
- Neo4j graph data can be observed for explicit-on sentinel content.
- Duplicate receipt semantics in graph-write worker are active (`duplicate_skipped`).

### What this does not prove

- It does not prove that default-off behavior uses a strict no-op backend with zero Neo4j writes.
- It does not prove that `CODEXIFY_ENABLE_GRAPH_WRITES` and `CODEXIFY_GRAPH_BACKEND` are currently wired into Compose backend env in this checkout.
- It does not widen beta release promise.
- It does not change retrieval, export/restore, UI surfaces, or architecture contracts.

## Final Result

`FAIL`

Reason:

- Requirement (1) failed under live evidence: default-off sentinel still appeared in Neo4j.
- Runtime gating control via the two requested env flags was not demonstrably wired into backend container env on this Compose path.
