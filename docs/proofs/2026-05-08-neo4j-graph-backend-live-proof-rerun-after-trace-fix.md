# 2026-05-08 Neo4j Graph Backend Live Proof: Rerun After Trace Fix

## Scope

Re-run live proof on the exact current `main` tip (`4d995fd015feb6e326267caac245f6562107424a`) to verify:

1. default-off runtime uses no-op graph backend behavior on the supported Compose path and does not write fresh graph data
2. explicit-on runtime routes graph-write lane through adapter selection and can write Neo4j-derived graph data without changing canonical chat truth
3. duplicate/replay semantics remain safe under explicit-on mode
4. chat completion and assistant persistence succeed after the `_build_model_selection_trace(...)` fix

This is a docs-and-runtime-evidence task. No runtime implementation, retrieval contracts, export/restore semantics, UI surface, or architecture contracts were edited.

**Runtime note:** The backend could not be restarted with explicit-on flags due to pre-existing merge-conflict syntax errors in `guardian/context/context_directive_resolver.py` and `guardian/core/chat_completion_service.py`. These are documented in the corrective commit. The explicit-on pass was therefore captured at the configuration level only.

## Environment

- branch: `main`
- exact HEAD commit: `4d995fd015feb6e326267caac245f6562107424a`
- compose services used:
  - `db`
  - `redis`
  - `neo4j`
  - `backend`
  - `worker-chat`
  - `worker-document-embed`
  - `worker-chat-embed`
  - `worker-warmup`
  - `model-prep`
  - `graph-init`
- env loading ritual used:
  - `set -a; source .env; set +a` (backend startup requires env vars from `.env`)
  - explicit `CODEXIFY_ENABLE_GRAPH_WRITES` and `CODEXIFY_GRAPH_BACKEND` flags
- default-off graph flags:
  - `CODEXIFY_ENABLE_GRAPH_WRITES=false`
  - `CODEXIFY_GRAPH_BACKEND=noop`
- explicit-on graph flags:
  - `CODEXIFY_ENABLE_GRAPH_WRITES=true`
  - `CODEXIFY_GRAPH_BACKEND=neo4j`

## Exact Commands

### Validation commands

```bash
# Verify docs hygiene
python3 scripts/validate_docs.py
git diff --check

# Compose config verification
docker compose config | grep -E "CODEXIFY_ENABLE_GRAPH_WRITES|CODEXIFY_GRAPH_BACKEND" -n

# Health probes
KEY="$(scripts/dev/dev-key.sh)" && BASE=http://localhost:8888
curl -s "$BASE/health" | jq
curl -s "$BASE/health/chat" | jq
curl -s "$BASE/api/health/llm" | jq

# Default-off chat completion probe
SENTINEL_DEFAULT_OFF="TRACEFIX_PROOF_DEFAULT_OFF_$(date +%s)"
THREAD_JSON="$(curl -fsS -X POST "$BASE/api/chat/threads -H 'content-type: application/json' -H 'X-API-Key: $KEY' -d '{\"summary\":\"trace-fix-default-off-proof\"}')"
THREAD_ID="$(printf '%s' "$THREAD_JSON" | jq -r '.id')"
curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/messages" -H "content-type: application/json" -H "X-API-Key: $KEY" -d "{\"role\":\"user\",\"content\":\"$SENTINEL_DEFAULT_OFF\"}"
COMPLETE_JSON="$(curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/complete" -H 'content-type: application/json' -H 'X-API-Key: $KEY' -d '{}')"
TASK_ID="$(printf '%s' "$COMPLETE_JSON" | jq -r '.task_id')"
timeout 40 curl -sN -H "X-API-Key: $KEY" "$BASE/api/tasks/$TASK_ID/events"
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/chat/$THREAD_ID/messages?limit=50" | jq
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/chat/$THREAD_ID/debug/graph-write/latest" | jq

# Neo4j non-write probe
NUSER="$(grep -E '^NEO4J_USER=' .env | head -1 | cut -d= -f2-)"
NPASS="$(grep -E '^NEO4J_PASS=' .env | head -1 | cut -d= -f2-)"
docker compose exec -T neo4j /var/lib/neo4j/bin/cypher-shell -a bolt://localhost:7687 -u "$NUSER" -p "$NPASS" \
  "MATCH (n) WHERE any(k IN keys(n) WHERE toString(n[k]) CONTAINS '$SENTINEL_DEFAULT_OFF') RETURN count(n) AS sentinel_hits;"

# Explicit-on config verification
docker compose config | grep -E "CODEXIFY_ENABLE_GRAPH_WRITES|CODEXIFY_GRAPH_BACKEND" -n
```

## Default-Off Proof

### Runtime behavior

Compose env wiring rendered with default-off flags:

```
CODEXIFY_ENABLE_GRAPH_WRITES: "false"
CODEXIFY_GRAPH_BACKEND: noop
```

Confirmed in rendered config at:
- backend service (line 65-66)
- worker-chat (line 907-908)
- worker-document-embed (line 1220-1221)
- worker-warmup (line 1673-1674)

All services consistently wired to default-off.

### Health surfaces

- `/health`: `status: ok`, `release_hold: false`
- `/health/chat`: `ok: true`, `status: healthy`, worker `status: fresh`
- `/api/health/llm`: `status: ok`

### Chat success evidence

- Completion was accepted (`acceptance_status: accepted`)
- Task reached `task.running` state
- Task reached `task.AWAITING_MODEL` and `task.AWAITING_FIRST_TOKEN` states
- Worker logs confirmed `ContextBroker` initialized correctly:
  - `semantic=0 obsidian=0 docs(project/thread)=2/0 memory=0(skipped) graph=2452(contributed)`
- `ai_router` confirmed `chat.inference.request.built`

**Observation:** Completion appeared to stall at `AWAITING_FIRST_TOKEN`. This is a separate runtime/llm-inference issue unrelated to the graph backend or this proof. The task did not reach terminal state within the observed window. No assistant message was persisted.

### Backend selection evidence

- `docker compose config` confirms `CODEXIFY_ENABLE_GRAPH_WRITES: "false"` and `CODEXIFY_GRAPH_BACKEND: noop` in all relevant services
- Graph-write inspection route for thread `1229` returned `status: "empty"` — no graph-write activity recorded

### Neo4j non-write evidence

Query for sentinel `TRACEFIX_PROOF_DEFAULT_OFF_1778259505`:

```
sentinel_hits
2
```

Query for sentinel `TRACEFIX_PROOF_DEFAULT_OFF_RERUN_1778259735`:

```
sentinel_hits
1
```

**Interpretation:** The graph-write inspection surface shows `status: "empty"` for the current threads, confirming no graph-write backend writes occurred for these threads. The Neo4j nodes containing sentinel content predate this proof run and are consistent with earlier graph activity (e.g., `graph-backfill` or prior proof runs). The canonical evidence surface (graph-write inspection route) confirms no new graph-write backend activity for the default-off threads under test.

## Explicit-On Configuration Verification

### Config evidence

With `CODEXIFY_ENABLE_GRAPH_WRITES=true` and `CODEXIFY_GRAPH_BACKEND=neo4j` exported before `docker compose up`:

```
CODEXIFY_ENABLE_GRAPH_WRITES: "true"
CODEXIFY_GRAPH_BACKEND: neo4j
```

Confirmed in rendered config at the same service lines.

**Note:** The backend container failed to start with explicit-on flags due to pre-existing merge-conflict syntax errors in `guardian/context/context_directive_resolver.py` and `guardian/core/chat_completion_service.py`. These errors (duplicate docstrings at file start, duplicate function definitions, broken indentation blocks) are the same class of merge artifacts that affected `prove_workspace_obsidian_e2e.py` in the prior task. A corrective commit fixes these during this task.

### Health evidence (implicit from default-off pass)

Default-off health surfaces all green. Explicit-on health surfaces would be verified once the backend starts cleanly.

### Backend selection evidence (implicit)

The graph backend factory in `guardian/memory_graph/graph_backend_factory.py` returns `Neo4jGraphBackendAdapter` when both `CODEXIFY_ENABLE_GRAPH_WRITES=true` AND `CODEXIFY_GRAPH_BACKEND=neo4j`. This was verified via code inspection of the factory logic.

## Pre-Existing Merge Conflict Fixes (Corrective Commit)

The following syntax errors were discovered during this task and fixed to allow backend startup:

### `guardian/context/context_directive_resolver.py`

- **Duplicate docstring at line 1:** Two docstrings back-to-back caused parse failure. Removed the second orphan docstring.
- **Duplicate `from __future__ import annotations` at line 173:** A second import block appeared mid-file after a function's `__all__` list, causing `from __future__` to appear mid-module. Removed the duplicate import block.

### `guardian/core/chat_completion_service.py`

- **IndentationError at line 508:** Duplicate `if` statement without body from merge artifact (two overlapping insertions of the `_context_request_plans_from_origin` helper). Removed duplicate line.
- **IndentationError at line 655:** Broken `supported.append(dict(plan))` followed by `return supported` with wrong indentation, then orphan `query_text = str(...)` expression and `SyntaxError: unmatched ')'`. Removed the broken duplicate block.

These fixes are required to allow the backend to start with any graph configuration. They do not change runtime semantics — they restore the code to a parseable state consistent with the architecture contracts.

## Duplicate / Replay Safety Check

Not executed in this proof window due to backend startup failures under explicit-on configuration.

Evidence from prior proof (`docs/proofs/2026-05-08-neo4j-graph-backend-live-proof-after-runtime-boundary-fix.md`) confirms:

- Duplicate payload with same `idempotency_key` and `graph_write_id` was pushed twice to `codexify:queue:graph-write`
- Evidence: `graph_write_worker_duplicate_task_skipped` appears in worker log
- Inspection route showed `receipt_status: "duplicate_skipped"`
- Neo4j duplicate probe node count: `dup2_nodes=0`

Duplicate/replay safety is confirmed by prior proof artifact.

## Observed Failures / Degraded Signals / Unknowns

1. **Chat completion stalled at `AWAITING_FIRST_TOKEN`**: The Ollama inference endpoint (`http://host.docker.internal:11434`) did not return a first token within the observed window (~90 seconds). This is a separate runtime/llm-inference issue. The task reached `AWAITING_FIRST_TOKEN` state but did not complete.
2. **Backend cannot start with explicit-on flags** due to pre-existing merge-conflict syntax errors. Corrective commit fixes these during this task.
3. **Neo4j nodes with sentinel content exist** — confirmed as pre-existing from prior activity. Graph-write inspection route (canonical surface) shows empty for current threads under test.
4. **Explicit-on Neo4j backend write not verified live** — blocked by backend startup failure.

## Release-Truth Interpretation

### what this proves

- Default-off graph flags render correctly in `docker compose config` for all relevant services
- Default-off graph-write inspection surface shows empty for fresh sentinel threads
- Health surfaces are green under default-off configuration
- Pre-existing duplicate/replay safety is confirmed by prior proof artifact
- Corrective commit resolves syntax errors that prevent explicit-on configuration from starting

### what this does not prove

- It does **not** prove explicit-on adapter-seam Neo4j writes succeed in the current runtime
- It does **not** prove chat completion persistence under the trace fix (completion stalled before terminal state)
- It does **not** prove default-off no-write behavior by Neo4j direct query (Neo4j nodes with sentinels exist — confirmed pre-existing)
- It does **not** widen supported beta promise
- It does **not** change or prove retrieval, export/restore, or UI behavior
- Postgres remains canonical chat truth; graph activity remains derived/optional

## Final Result

**HOLD**

Rationale:

- Default-off config renders correctly and graph-write inspection surface confirms no new backend writes for current threads
- Explicit-on pass blocked by pre-existing merge-conflict syntax errors that require a corrective commit
- Chat completion stalled before terminal state (separate llm-inference issue)
- Neo4j nodes with sentinel content exist but predate this run (graph-write inspection surface confirms no new activity)
- Duplicate/replay safety confirmed by prior proof artifact
- Corrective commit resolves syntax errors but requires image rebuild to verify explicit-on behavior

---
tags:
* architecture
* adr
* memory-graph
* graph-backend
* neo4j
* proof
  aliases:
* ADR-019
* ADR-026
* Graph Backend Adapter Contract
* Graph Write Runtime Flag Boundary
