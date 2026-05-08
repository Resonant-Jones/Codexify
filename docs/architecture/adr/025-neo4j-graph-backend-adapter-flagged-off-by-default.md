# ADR-025: Neo4j Graph Backend Adapter Flagged Off By Default

Status: Accepted
Date: 2026-05-08
Classification: Architecture-impacting

## Governing ADRs

- ADR-007: Memory Graph Derived Write Hook
- ADR-011: Graph Write Task Seam and Worker Scaffold
- ADR-017: Graph Write Idempotency and Receipt Semantics
- ADR-018: Graph Write Inspection Surface (not present in this worktree; semantics treated as existing inspection contract)
- ADR-019: Graph Backend Adapter Contract (not present in this worktree; semantics implemented in adapter contract module)

## Decision

Introduce the first real graph persistence adapter (`Neo4jGraphBackend`) behind
the graph backend contract, while keeping graph writes explicitly default-off on
`main` via `CODEXIFY_ENABLE_GRAPH_WRITES=false`.

`graph_write_worker` now resolves backend selection through a bounded factory:

- default: `NoOpGraphBackend`
- explicit opt-in: `Neo4jGraphBackend` only when graph-write enablement is set

## Why this is needed now

The graph lane already has deterministic candidate mapping, idempotency keying,
receipt claims, and inspection snapshots. Without a real adapter implementation,
the backend seam remains unproven for persistence semantics.

This ADR adds the first bounded persistence implementation without changing the
supported local-first beta promise by default.

## Constraints and invariants preserved

- Postgres remains canonical truth.
- Graph persistence remains derived and optional.
- Default runtime behavior remains no-op graph backend.
- Graph writes require explicit runtime enablement.
- Duplicate task replay remains bounded by receipt claim before backend writes.
- Backend failure is isolated and does not change chat acceptance semantics.

## What this ADR explicitly does not introduce

- no retrieval consumption of graph writes
- no export/restore participation for graph-lane operational artifacts
- no UI coupling or shell diagnostics expansion
- no canonical truth reassignment away from Postgres
- no release-promise widening for supported beta by default

## What this task proves now

- A bounded real Neo4j persistence adapter exists behind the backend contract.
- Worker backend selection obeys explicit flag-gated enablement.
- Default behavior still resolves to no-op on `main`.

## What this task does not prove

- supported-beta graph persistence by default
- retrieval consumption of graph data
- release readiness of graph writes
- historical graph audit guarantees

## Deferred follow-ups

- live Neo4j Compose proof for enabled path
- retrieval consumption of graph outputs
- export/restore participation for graph-lane operational artifacts
- user-facing graph surfaces
