---
tags:
* architecture
* adr
* memory-graph
* graph-backend
* runtime-flag
* docker-compose
  aliases:
* ADR-026
* Graph Write Runtime Flag Boundary on Supported Compose Path
---

# ADR-026: Graph Write Runtime Flag Boundary on Supported Compose Path

## Status

Accepted

## Date

2026-05-08

## Classification

This ADR is architecture-impacting.

## Governing ADRs

- ADR-019: Graph Backend Adapter Contract
- ADR-025: Neo4j Graph Backend Adapter Flagged Off by Default (referenced intent; ADR not yet present in this checkout)

## Context

The live proof recorded in `docs/proofs/2026-05-07-neo4j-graph-backend-live-proof.md` demonstrated that the documented default-off graph-write contract was not actually enforced on the supported Docker Compose path.

Specifically:

1. The proof requested `CODEXIFY_ENABLE_GRAPH_WRITES=false` and `CODEXIFY_GRAPH_BACKEND=noop` via shell exports.
2. The backend container env did not expose those flags — they were not wired into `docker-compose.yml`.
3. A fresh default-off sentinel still appeared in Neo4j (`sentinel_hits=1`), contradicting the intended default-off non-write behavior.
4. `docker compose config` contained no `CODEXIFY_ENABLE_GRAPH_WRITES` or `CODEXIFY_GRAPH_BACKEND` wiring.

The documented architecture contract states that graph writes are default-off on the supported path, but the runtime/config boundary did not enforce this. The factory always returned `NoopGraphBackendAdapter` from `noop_graph_backend.py`, but there was no explicit env-driven factory selection, and the worker imported directly from the noop module rather than through a flag-aware factory.

This ADR repairs the runtime/config boundary so the supported-path truth matches the documented architecture contract.

## Decision

Codexify now enforces the default-off graph-write contract on the supported Docker Compose path through:

1. **Explicit env wiring in `docker-compose.yml`**: The `backend`, `worker-chat`, `worker-coding`, `worker-warmup`, and `graph-backfill` services receive:
   - `CODEXIFY_ENABLE_GRAPH_WRITES` (defaults to `false`)
   - `CODEXIFY_GRAPH_BACKEND` (defaults to `noop`)

2. **Config fields in `guardian/core/config.py`**: Both flags are now typed Pydantic settings with explicit defaults and descriptions.

3. **Fail-closed factory in `guardian/memory_graph/graph_backend_factory.py`**: A new factory module selects the graph backend adapter based on explicit env configuration:
   - Returns `NoopGraphBackendAdapter` unless `CODEXIFY_ENABLE_GRAPH_WRITES=true` AND `CODEXIFY_GRAPH_BACKEND=neo4j`.
   - Invalid backend values fall back to noop.
   - Missing Neo4j adapter module falls back to noop.
   - Neo4j container presence alone does not enable graph writes.

4. **Worker import path updated**: `graph_write_worker.py` imports `get_graph_backend_adapter` from the factory rather than directly from `noop_graph_backend.py`.

### Invariants preserved

- Postgres remains canonical truth.
- Default behavior on the supported path is no-op for graph writes.
- Neo4j container presence alone never implies graph-write enablement.
- No retrieval path consumes graph backend outputs.
- No export/restore path consumes graph backend outputs.
- No chat completion success semantics depend on graph backend success.
- Graph-write tasks remain derived artifacts.

## Non-Negotiable Invariants

- Postgres remains canonical truth
- Redis remains transport and coordination
- graph-write tasks remain derived artifacts
- inspection snapshots remain derived artifacts
- graph backend adapter results remain derived artifacts
- default behavior on the supported path is no-op for graph writes
- Neo4j container presence alone does not imply graph-write enablement
- no retrieval consumer may depend on adapter results
- no export or restore participation is introduced here
- no main-shell diagnostics UI is introduced here
- no chat completion success semantics depend on adapter success

## What This Task Proves

- The supported-path env/config boundary is explicit and auditable via `docker compose config`.
- Factory selection is fail-closed and default-off.
- Unit tests prove that disabled flags always produce noop regardless of Neo4j env presence.
- Worker-level tests prove that disabled flags mean noop backend usage.

## What This Task Does Not Prove

- Release-readiness of default-on graph writes.
- Retrieval use of graph data.
- Export/restore participation.
- User-facing graph features.
- Neo4j adapter correctness (the adapter module does not yet exist in this checkout).

## Consequences

### Positive

- The documented default-off contract is now enforced at the runtime/config boundary.
- Operators can audit graph-write enablement via `docker compose config` and env inspection.
- Factory selection is explicit, grep-friendly, and fail-closed.
- Future Neo4j adapter can attach to the factory seam without changing the default-off contract.

### Negative

- One additional factory module to maintain.
- Env wiring must be kept synchronized across Compose services that participate in the graph lane.

## Deferred Items

The following remain explicitly out of scope:

- Neo4j graph backend adapter implementation (not present in this checkout)
- Retrieval consumption of graph data
- Export/restore participation
- UI surfaces for graph data
- Default-on graph writes for any release posture

## Route and Worker Note

The worker imports `get_graph_backend_adapter` from `guardian.memory_graph.graph_backend_factory`. The factory returns `NoopGraphBackendAdapter` by default on the supported Compose path. Present runtime behavior remains inspection-only unless both flags are explicitly enabled.

## Links

- [[ADR Index]]
- [[019-Graph-Backend-Adapter-Contract|ADR-019 Graph Backend Adapter Contract]]
- [[011-Graph-Write-Task-Seam-and-Worker-Scaffold|ADR-011 Graph Write Task Seam and Worker Scaffold]]
- [[017-Graph-Write-Idempotency-and-Receipt-Semantics|ADR-017 Graph Write Idempotency and Receipt Semantics]]
- [[018-Graph-Write-Inspection-Surface|ADR-018 Graph Write Inspection Surface]]
- [[candidate-ingest-pipeline|Candidate Trace Ingestion Pipeline]]
- [[memory-graph-indexing-plan|Memory Graph Indexing Plan]]
- [[data-and-storage|Data and Storage]]
- [[config-and-ops|Config and Ops]]
- [[00-current-state]]
