# 2026-05-08 Neo4j Graph Backend Explicit-On Proof After Parse Repair

## Scope

Run a live proof on the exact current `main` tip to answer one narrow question:

When graph writes are explicitly enabled with `CODEXIFY_ENABLE_GRAPH_WRITES=true` and `CODEXIFY_GRAPH_BACKEND=neo4j`, does the graph-write lane select the Neo4j adapter and materialize fresh graph data through the graph-write worker path?

This is a docs-and-runtime-evidence task only. No runtime implementation, retrieval contracts, export semantics, UI behavior, or ADR contracts were changed.

## Environment

- branch: `main`
- exact HEAD commit: `4d995fd015feb6e326267caac245f6562107424a`
- worktree state:
  - `git status --short` was not reliable because Git LFS filters were failing in this checkout
  - a cleanliness read using `git -c filter.lfs.required=false status --short` showed existing modified audit files only:
    - `docs/audits/daily/evening/2026-05-08-audit.json`
    - `docs/audits/daily/evening/latest.json`
    - `docs/audits/latest.json`
- Compose services used:
  - `db`
  - `redis`
  - `neo4j`
  - `graph-init`
  - `backend`
  - `worker-chat`
  - `worker-document-embed`
  - `worker-chat-embed`
  - `worker-warmup`
  - isolated backend-image graph worker via `docker compose run --rm --no-deps --entrypoint sh backend -lc 'timeout ... python -m guardian.workers.graph_write_worker'`
- env loading ritual used:
  - attempted `set -a; source .env; set +a`
  - that failed because `.env` is malformed in this checkout
  - fallback used manual sanitized exports:
    - `GUARDIAN_API_KEY="$(scripts/dev/dev-key.sh)"`
    - `CODEXIFY_ENABLE_GRAPH_WRITES=true|false`
    - `CODEXIFY_GRAPH_BACKEND=neo4j|noop`
    - `NEO4J_USER="${NEO4J_USER:-neo4j}"`
    - `NEO4J_PASS="$(grep -E '^NEO4J_PASS=' .env | head -n1 | sed 's/^NEO4J_PASS=//')"`
- explicit-on graph flags:
  - `CODEXIFY_ENABLE_GRAPH_WRITES=true`
  - `CODEXIFY_GRAPH_BACKEND=neo4j`
- default-off sanity-check flags:
  - `CODEXIFY_ENABLE_GRAPH_WRITES=false`
  - `CODEXIFY_GRAPH_BACKEND=noop`

## Exact Commands

```bash
# repo state / env ritual
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
git -c filter.lfs.required=false status --short
set -a; source .env; set +a

# compose service inventory
docker compose config --services | grep -E "graph|worker"

# default-off compose render
export CODEXIFY_ENABLE_GRAPH_WRITES=false
export CODEXIFY_GRAPH_BACKEND=noop
export GUARDIAN_API_KEY="$(scripts/dev/dev-key.sh)"
export NEO4J_USER="${NEO4J_USER:-neo4j}"
export NEO4J_PASS="$(grep -E '^NEO4J_PASS=' .env | head -n1 | sed 's/^NEO4J_PASS=//')"
docker compose config | grep -E "CODEXIFY_ENABLE_GRAPH_WRITES|CODEXIFY_GRAPH_BACKEND|NEO4J_URI|NEO4J_USER|NEO4J_DATABASE" -n

# runtime bring-up
docker compose down
docker compose up -d db redis neo4j graph-init
docker compose run --rm migrator
docker compose up -d backend worker-chat worker-document-embed worker-chat-embed worker-warmup
docker compose ps
docker compose logs backend --no-color --tail=200

# explicit-on compose render
export CODEXIFY_ENABLE_GRAPH_WRITES=true
export CODEXIFY_GRAPH_BACKEND=neo4j
docker compose config | grep -E "CODEXIFY_ENABLE_GRAPH_WRITES|CODEXIFY_GRAPH_BACKEND|NEO4J_URI|NEO4J_USER|NEO4J_DATABASE" -n

# health probe fallback used because host shell lacks curl/jq
python3 - <<'PY'
import json
import urllib.request
import urllib.error

base = "http://localhost:8888"
for path in ["/health", "/health/chat", "/api/health/llm"]:
    print(f"== {path}")
    try:
        with urllib.request.urlopen(base + path, timeout=5) as r:
            print(json.dumps(json.load(r), indent=2, sort_keys=True))
    except Exception as e:
        print(f"UNREACHABLE: {type(e).__name__}: {e}")
PY

# explicit-on isolated graph worker seam
export CODEXIFY_ENABLE_GRAPH_WRITES=true
export CODEXIFY_GRAPH_BACKEND=neo4j
docker compose run --rm --no-deps --entrypoint sh backend -lc 'timeout 30 python -m guardian.workers.graph_write_worker'
PAYLOAD='{"request_id":"proof-20260508-k7p2","thread_id":424242,"candidate_trace_id":"trace-20260508-k7p2","created_at":"2026-05-08T21:38:20Z","graph_write_id":"gwr-20260508-k7p2","idempotency_key":"idemp-20260508-k7p2","nodes":[{"node_key":"node-20260508-k7p2","node_type":"Message","source_type":"proof","source_id":"proof-20260508-k7p2","content":"neo4j-explicit-on-after-parse-repair-20260508-k7p2","metadata":{"sentinel":"neo4j-explicit-on-after-parse-repair-20260508-k7p2"}}],"edges":[],"warnings":[]}'
docker compose exec -T redis redis-cli RPUSH codexify:queue:graph-write "$PAYLOAD"
docker compose exec -T redis redis-cli RPUSH codexify:queue:graph-write "$PAYLOAD"
docker compose exec -T redis redis-cli GET codexify:graph-write:inspection:424242
docker compose exec -T neo4j /var/lib/neo4j/bin/cypher-shell -a bolt://localhost:7687 -u "${NEO4J_USER:-neo4j}" -p "$NEO4J_PASS" "MATCH (n) WHERE any(k IN keys(n) WHERE toString(n[k]) CONTAINS 'neo4j-explicit-on-after-parse-repair-20260508-k7p2') RETURN count(n) AS sentinel_hits;"
docker compose exec -T neo4j /var/lib/neo4j/bin/cypher-shell -a bolt://localhost:7687 -u "${NEO4J_USER:-neo4j}" -p "$NEO4J_PASS" "MATCH (n {node_key:'node-20260508-k7p2'}) RETURN count(n) AS node_count;"

# default-off sanity check
export CODEXIFY_ENABLE_GRAPH_WRITES=false
export CODEXIFY_GRAPH_BACKEND=noop
docker compose run --rm --no-deps --entrypoint sh backend -lc 'timeout 20 python -m guardian.workers.graph_write_worker'
PAYLOAD='{"request_id":"proof-defaultoff-20260508-k7p2","thread_id":424243,"candidate_trace_id":"trace-defaultoff-20260508-k7p2","created_at":"2026-05-08T21:39:20Z","graph_write_id":"gwr-defaultoff-20260508-k7p2","idempotency_key":"idemp-defaultoff-20260508-k7p2","nodes":[{"node_key":"node-defaultoff-20260508-k7p2","node_type":"Message","source_type":"proof","source_id":"proof-defaultoff-20260508-k7p2","content":"neo4j-default-off-sanity-20260508-k7p2","metadata":{"sentinel":"neo4j-default-off-sanity-20260508-k7p2"}}],"edges":[],"warnings":[]}'
docker compose exec -T redis redis-cli RPUSH codexify:queue:graph-write "$PAYLOAD"
docker compose exec -T neo4j /var/lib/neo4j/bin/cypher-shell -a bolt://localhost:7687 -u "${NEO4J_USER:-neo4j}" -p "$NEO4J_PASS" "MATCH (n) WHERE any(k IN keys(n) WHERE toString(n[k]) CONTAINS 'neo4j-default-off-sanity-20260508-k7p2') RETURN count(n) AS default_off_sentinel_hits;"

# validation
make docs PYTHON=python3
git -c filter.lfs.required=false diff --check
```

## Explicit-On Neo4j Proof

### Runtime startup evidence

- Compose rendered the explicit-on graph flags correctly:
  - `CODEXIFY_ENABLE_GRAPH_WRITES: "true"`
  - `CODEXIFY_GRAPH_BACKEND: neo4j`
- The data services came up healthy:
  - `db`
  - `redis`
  - `neo4j`
- The backend container did not reach a serving state.
- Backend startup failed during import with:
  - `SyntaxError: from __future__ imports must occur at the beginning of the file`
  - file: `guardian/context/context_directive_resolver.py`
- The health probes could not reach the API and returned:
  - `ConnectionResetError: [Errno 54] Connection reset by peer`

### Assistant persistence evidence

- Not obtainable on this run.
- The backend never reached `/api/chat/threads`, `/api/chat/{thread_id}/messages`, or `/api/chat/{thread_id}/complete` because the API process crashed during startup.

### Graph-write worker evidence

The isolated backend-image graph worker started and processed the manual payload queue, but it did not select a Neo4j adapter:

```text
[graph-backend] CODEXIFY_GRAPH_BACKEND=neo4j requested but Neo4jGraphBackendAdapter is not available; falling back to noop.
[graph-write] graph_write_worker_inspected_task
[graph-write] graph_write_worker_duplicate_task_skipped
```

The graph-write inspection snapshot stored in Redis for the explicit-on payload was:

```json
{
  "adapter_failure_message": null,
  "candidate_trace_id": "trace-20260508-k7p2",
  "created_at": "2026-05-08T21:38:20Z",
  "edge_count": 0,
  "edge_types": [],
  "graph_write_id": "gwr-20260508-k7p2",
  "idempotency_key": "idemp-20260508-k7p2",
  "node_count": 1,
  "node_types": ["Message"],
  "receipt_status": "duplicate_skipped",
  "request_id": "proof-20260508-k7p2",
  "thread_id": 424242,
  "warning_count": 0
}
```

### Backend selection evidence

- Explicit-on selection was attempted.
- The factory still fell back to noop because `Neo4jGraphBackendAdapter` is not available in this checkout.
- That means the explicit-on graph-write lane did not actually resolve to a Neo4j adapter on this tip.

### Neo4j query evidence

Direct Neo4j queries for the fresh explicit-on sentinel and manual node key both returned zero:

```text
sentinel_hits
0
```

```text
node_count
0
```

This means the isolated graph-write worker did not materialize fresh Neo4j data for the explicit-on payload.

## Duplicate / Replay Safety Check

- The same explicit-on graph-write payload was pushed twice to `codexify:queue:graph-write`.
- Evidence surfaces:
  - worker log: `graph_write_worker_duplicate_task_skipped`
  - Redis inspection snapshot: `receipt_status: "duplicate_skipped"`
- The duplicate path exited before any second backend write.
- Neo4j did not gain a second materialization for the replayed identity because no fresh Neo4j materialization was observed at all on this run.

## Default-Off Boundary Sanity Check

The default-off sanity pass rendered the expected Compose values:

- `CODEXIFY_ENABLE_GRAPH_WRITES: "false"`
- `CODEXIFY_GRAPH_BACKEND: noop`

The isolated worker seam also behaved fail-closed under default-off flags:

```text
[graph-backend] NoopGraphBackendAdapter selected (graph writes disabled or backend=noop)
[graph-write] graph_write_worker_inspected_task
```

The fresh default-off sentinel stayed absent from Neo4j:

```text
default_off_sentinel_hits
0
```

This preserves the supported beta boundary: the default-off path did not widen into active graph persistence.

## Observed Failures / Degraded Signals / Unknowns

1. `.env` is malformed for shell sourcing in this checkout.
   - `set -a; source .env; set +a` emitted shell parse errors and could not be used as-is.
   - Sanitized manual exports were required for the proof.
2. Host shell lacks `curl` and `jq`.
   - Health probes were run with a Python fallback instead.
3. The backend API never booted.
   - Startup crashed with a syntax error in `guardian/context/context_directive_resolver.py`.
4. Explicit-on graph-write selection did not reach Neo4j.
   - The graph backend factory logged a fallback to noop because `Neo4jGraphBackendAdapter` is not available.
5. No assistant persistence evidence was obtainable.
   - The chat API never reached a runnable state on this run.

## Release-Truth Interpretation

### What this proves

- The Compose file renders the explicit-on and default-off graph-write flags correctly.
- The isolated graph-write worker seam is fail-closed under both explicit-on and default-off flags.
- Duplicate receipt handling remains active and produces `duplicate_skipped`.
- The default-off boundary still stays off and does not widen the beta promise.

### What this does not prove

- It does not prove assistant persistence on the current tip, because the backend crashed before the chat API booted.
- It does not prove that explicit-on graph writes select a Neo4j adapter on this tip.
- It does not prove fresh graph materialization through the graph-write worker path.
- It does not change retrieval, export/restore, UI behavior, or architecture contracts.

## Final Result

`HOLD`

Reason:

- runtime startup was blocked by a backend import syntax error before the chat API could serve requests
- explicit-on graph-write selection still fell back to noop rather than selecting a Neo4j adapter
- assistant persistence could not be proven on this run
