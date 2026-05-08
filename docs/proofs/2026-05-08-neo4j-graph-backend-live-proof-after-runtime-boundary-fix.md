# 2026-05-08 Neo4j Graph Backend Live Proof After Runtime Boundary Fix

## Scope

Re-run live proof on the exact current `main` tip to verify:

1. default-off runtime uses no-op graph backend behavior on the supported Compose path and does not write fresh graph data
2. explicit-on runtime routes graph-write lane through adapter selection and can write Neo4j-derived graph data without changing canonical chat truth
3. duplicate/replay semantics remain safe under explicit-on mode

This is a docs-and-runtime-evidence task only. No runtime implementation, retrieval contracts, export/restore semantics, UI surface, or architecture contracts were edited.

## Environment

- branch: `main`
- exact HEAD commit: `8654bcc22d18ce77279e9a759a4c1cb641e06b22`
- compose services used:
  - `db`
  - `redis`
  - `neo4j`
  - `backend`
  - `worker-chat`
  - `worker-document-embed`
  - `worker-chat-embed`
  - `worker-warmup`
  - `graph-backfill` (included because it is present in Compose and mutates graph state)
- env loading ritual used:
  - attempted: `set -a; source .env; set +a`
  - observed failure: `.env:79: command not found: gemma4-e4b-hauhau:latest` (space after `=` in `.env` model vars)
  - operational fallback used for proof execution: Compose `env_file` loading + explicit shell `export CODEXIFY_*` flags + `KEY="$(scripts/dev/dev-key.sh)"`
- default-off graph flags:
  - `CODEXIFY_ENABLE_GRAPH_WRITES=false`
  - `CODEXIFY_GRAPH_BACKEND=noop`
- explicit-on graph flags:
  - `CODEXIFY_ENABLE_GRAPH_WRITES=true`
  - `CODEXIFY_GRAPH_BACKEND=neo4j`

## Exact Commands

```bash
# attempted env ritual (fails in this checkout)
set -a; source .env; set +a

BASE=http://localhost:8888
KEY="$(scripts/dev/dev-key.sh)"

# -------------------------
# default-off pass
# -------------------------
export CODEXIFY_ENABLE_GRAPH_WRITES=false
export CODEXIFY_GRAPH_BACKEND=noop

docker compose down
docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d backend worker-chat worker-document-embed worker-chat-embed worker-warmup graph-backfill

docker compose ps
docker compose config | grep -E "CODEXIFY_ENABLE_GRAPH_WRITES|CODEXIFY_GRAPH_BACKEND|NEO4J_URI|NEO4J_USER|NEO4J_DATABASE" -n

curl -s "$BASE/health" | jq
curl -s "$BASE/health/chat" | jq
curl -s "$BASE/api/health/llm" | jq

THREAD_JSON="$(curl -fsS -X POST "$BASE/api/chat/threads" -H "content-type: application/json" -H "X-API-Key: $KEY" -d '{"summary":"default-off-runtime-boundary-proof"}')"
THREAD_ID="$(printf '%s' "$THREAD_JSON" | jq -r '.id')"
SENTINEL_DEFAULT_OFF="DEFAULT_OFF_SENTINEL_1778254885"

curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/messages" -H "content-type: application/json" -H "X-API-Key: $KEY" -d "{\"role\":\"user\",\"content\":\"$SENTINEL_DEFAULT_OFF\"}"
COMPLETE_JSON="$(curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/complete" -H "content-type: application/json" -H "X-API-Key: $KEY" -d '{}')"
TASK_ID="$(printf '%s' "$COMPLETE_JSON" | jq -r '.task_id')"

timeout 40 curl -sN -H "X-API-Key: $KEY" "$BASE/api/tasks/$TASK_ID/events"
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/chat/$THREAD_ID/messages?limit=50" | jq
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/chat/$THREAD_ID/debug/graph-write/latest" | jq

NUSER="$(grep -E '^NEO4J_USER=' .env | tail -n1 | cut -d= -f2- | xargs)"; [ -n "$NUSER" ] || NUSER=neo4j
NPASS="$(grep -E '^NEO4J_PASS=' .env | tail -n1 | cut -d= -f2-)"
docker compose exec -T neo4j /var/lib/neo4j/bin/cypher-shell -a bolt://localhost:7687 -u "$NUSER" -p "$NPASS" \
  "MATCH (n) WHERE any(k IN keys(n) WHERE toString(n[k]) CONTAINS '$SENTINEL_DEFAULT_OFF') RETURN count(n) AS sentinel_hits;"

docker compose logs backend worker-chat graph-backfill --since=10m

# -------------------------
# explicit-on pass
# -------------------------
export CODEXIFY_ENABLE_GRAPH_WRITES=true
export CODEXIFY_GRAPH_BACKEND=neo4j

docker compose down
docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d backend worker-chat worker-document-embed worker-chat-embed worker-warmup graph-backfill

docker compose ps
docker compose config | grep -E "CODEXIFY_ENABLE_GRAPH_WRITES|CODEXIFY_GRAPH_BACKEND|NEO4J_URI|NEO4J_USER|NEO4J_DATABASE" -n

curl -s "$BASE/health" | jq
curl -s "$BASE/health/chat" | jq
curl -s "$BASE/api/health/llm" | jq

THREAD_JSON="$(curl -fsS -X POST "$BASE/api/chat/threads" -H "content-type: application/json" -H "X-API-Key: $KEY" -d '{"summary":"explicit-on-runtime-boundary-proof"}')"
THREAD_ID="$(printf '%s' "$THREAD_JSON" | jq -r '.id')"
SENTINEL_EXPLICIT_ON="EXPLICIT_ON_SENTINEL_1778255077"

curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/messages" -H "content-type: application/json" -H "X-API-Key: $KEY" -d "{\"role\":\"user\",\"content\":\"$SENTINEL_EXPLICIT_ON\"}"
COMPLETE_JSON="$(curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/complete" -H "content-type: application/json" -H "X-API-Key: $KEY" -d '{}')"
TASK_ID="$(printf '%s' "$COMPLETE_JSON" | jq -r '.task_id')"

timeout 40 curl -sN -H "X-API-Key: $KEY" "$BASE/api/tasks/$TASK_ID/events"
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/chat/$THREAD_ID/messages?limit=50" | jq
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/chat/$THREAD_ID/debug/graph-write/latest" | jq

docker compose exec -T neo4j /var/lib/neo4j/bin/cypher-shell -a bolt://localhost:7687 -u "$NUSER" -p "$NPASS" \
  "MATCH (n) WHERE any(k IN keys(n) WHERE toString(n[k]) CONTAINS '$SENTINEL_EXPLICIT_ON') RETURN labels(n) AS labels, properties(n) AS props LIMIT 5;"

docker compose logs backend worker-chat graph-backfill --since=10m

# duplicate/replay probe under explicit-on mode
# (bounded direct graph_write_worker seam to capture receipt behavior)
docker compose exec -d backend sh -lc 'timeout 20 python -m guardian.workers.graph_write_worker > /tmp/graph_write_worker_proof.log 2>&1'
PAYLOAD='{"thread_id":1227,"project_id":1,"nodes":[{"id":"n-proof-dup-2","label":"ProofNode","properties":{"sentinel":"REPLAY_PROOF_SENTINEL_2"}}],"edges":[],"warnings":[],"idempotency_key":"proof-dup-neo4j-20260508-b","graph_write_id":"gwr-proof-dup-20260508-b","source":"proof-manual"}'
docker compose exec -T redis redis-cli RPUSH codexify:queue:graph-write "$PAYLOAD"
docker compose exec -T redis redis-cli RPUSH codexify:queue:graph-write "$PAYLOAD"
sleep 8
docker compose exec -T backend sh -lc 'cat /tmp/graph_write_worker_proof.log'
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/chat/1227/debug/graph-write/latest" | jq

docker compose exec -T neo4j /var/lib/neo4j/bin/cypher-shell -a bolt://localhost:7687 -u "$NUSER" -p "$NPASS" \
  "MATCH (n {id:'n-proof-dup-2'}) RETURN count(n) AS dup2_nodes;"

make docs
git diff --check
```

## Default-Off Proof

### Runtime behavior

- Compose env wiring rendered with default-off flags:
  - `CODEXIFY_ENABLE_GRAPH_WRITES: "false"`
  - `CODEXIFY_GRAPH_BACKEND: noop`
- Health surfaces were up:
  - `/health.status=ok`
  - `/health/chat.status=healthy`
  - `/api/health/llm.status=ok`

### Backend selection evidence

- Config evidence confirms default-off values in rendered Compose config.
- Thread inspection surface stayed empty:
  - `GET /api/chat/1226/debug/graph-write/latest` returned:
    - `status: "empty"`
    - `graph_write_inspection: null`
- No direct `[graph-backend] ... NoopGraphBackendAdapter selected` line was emitted in backend/worker-chat logs for this chat turn.

### Chat success evidence

- Chat completion enqueue succeeded (`task_id=239eda54-4c96-44c1-b169-a7f819f4f476`), but task failed at runtime:
  - `task.failed`
  - error: `_build_model_selection_trace() missing 3 required keyword-only arguments: 'resolved_provider', 'resolved_model', and 'model_resolution'`
- Message list for thread `1226` contains only the user message (no assistant persistence).

### Neo4j non-write evidence

Expected: fresh default-off sentinel should produce `sentinel_hits=0`.

Observed query result for `DEFAULT_OFF_SENTINEL_1778254885`:

```text
sentinel_hits
1
```

Interpretation: default-off non-write requirement was not met on this run.

## Explicit-On Neo4j Proof

### Runtime behavior

- Compose env wiring rendered with explicit-on values:
  - `CODEXIFY_ENABLE_GRAPH_WRITES: "true"`
  - `CODEXIFY_GRAPH_BACKEND: neo4j`
- `/health.status=ok`, `/api/health/llm.status=ok`, but `/health/chat.status=unhealthy` during first probe window (`worker heartbeat missing`), then worker resumed and executed task.

### Backend selection evidence

Bounded graph-write worker probe log under explicit-on mode:

```text
[graph-backend] CODEXIFY_GRAPH_BACKEND=neo4j requested but Neo4jGraphBackendAdapter is not available; falling back to noop.
```

Interpretation: adapter seam selected explicit-on intent but failed closed to noop in the `graph_write_worker` lane.

### Chat success evidence

- Completion was accepted and queued (`task_id=2e212d79-3acb-4b9d-87c9-434567476418`) but failed with the same runtime exception as default-off.
- Message list for thread `1227` contains only the user message (no assistant persistence).

### Graph-write worker evidence

Bounded probe log (`python -m guardian.workers.graph_write_worker` inside backend container):

```text
[graph-write] graph_write_worker_inspected_task
[graph-write] graph_write_worker_duplicate_task_skipped
```

This demonstrates receipt/duplicate handling in the graph-write queue seam.

### Neo4j query evidence

Sentinel query for `EXPLICIT_ON_SENTINEL_1778255077` returned:

```text
labels, props
["MessageNode"], { ..., content: "EXPLICIT_ON_SENTINEL_1778255077" }
```

At the same time, bounded replay payload node probe returned:

```text
dup2_nodes
0
```

Interpretation: Neo4j received sentinel-linked writes during the explicit-on window, but those writes were not proven to come from `graph_write_worker` adapter invocation (which fell back to noop). They are consistent with parallel `graph-backfill` graph mutation activity.

## Duplicate / Replay Safety Check

- Duplicate payload (same `idempotency_key` and `graph_write_id`) was pushed twice to `codexify:queue:graph-write`.
- Evidence:
  - `graph_write_worker_duplicate_task_skipped` appears in the bounded worker log.
  - inspection route response shows:
    - `receipt_status: "duplicate_skipped"`
    - `graph_write_id: "gwr-proof-dup-20260508-b"`
- Neo4j duplicate node count for probe node id `n-proof-dup-2`:
  - `dup2_nodes=0`

Conclusion: duplicate was skipped before backend write in this seam, and duplicate graph data was avoided for the replay probe.

## Observed Failures / Degraded Signals / Unknowns

1. `.env` shell-loading ritual fails due malformed model-value lines (`LOCAL_CHAT_MODEL= gemma...`).
2. Both default-off and explicit-on chat completion probes failed with the same worker exception in `_build_model_selection_trace(...)`.
3. Default-off sentinel still appeared in Neo4j (`sentinel_hits=1`), violating non-write expectation.
4. Explicit-on graph-write worker adapter path did not reach Neo4j backend; it fell back to noop (`Neo4jGraphBackendAdapter is not available`).
5. Neo4j writes observed in explicit-on window are likely driven by `graph-backfill` and/or other graph lane paths, not proven adapter-seam writes for the chat task under test.

## Release-Truth Interpretation

### what this proves

- Compose runtime wiring now renders both default-off and explicit-on graph flags as configured.
- Graph-write receipt duplicate handling remains active in the explicit-on queue seam (`duplicate_skipped`).
- Neo4j mutation still occurs in this runtime topology (at least via backfill-linked activity).

### what this does not prove

- It does **not** prove default-off no-op behavior prevents fresh Neo4j writes on the supported path.
- It does **not** prove explicit-on adapter-seam Neo4j writes succeed from `graph_write_worker`; current evidence shows fallback to noop in that seam.
- It does **not** widen supported beta promise.
- It does **not** change or prove retrieval, export/restore, or UI behavior.
- Postgres remains canonical chat truth; graph activity remains derived/optional from a release-claim perspective.

## Final Result

`FAIL`

Rationale:

- Required default-off non-write proof failed (`sentinel_hits=1` for fresh sentinel).
- Required explicit-on adapter-seam Neo4j write proof failed (bounded worker lane fell back to noop due unavailable `Neo4jGraphBackendAdapter`).
- Chat completion persistence requirement was degraded in both passes due a runtime exception unrelated to this docs task.
