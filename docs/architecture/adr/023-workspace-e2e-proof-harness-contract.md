---
status: accepted
date: 2026-05-05
---

# ADR-023: Workspace E2E Proof Harness Contract

## Context

ADR-016 made `retrievalSource="workspace"` a live backend meaning for local, user-bounded knowledge. That contract needed a canonical live proof surface so operators could validate the real end-to-end seam on the supported local Compose path, not just acceptance of the enqueue request.

The risk is overclaiming. If the harness is not explicit about what it proves, operators could mistake queue acceptance, document ingest, or a dev-only trace snapshot for proof of the actual live completion path.

## Decision

Codexify now has a canonical workspace-local live proof harness:

- `scripts/proofs/prove_workspace_obsidian_e2e.py`

The harness:

- stages a sentinel local note under the repo's ignored `tmp/` tree
- indexes that note through the supported Obsidian control plane
- creates a thread with `retrievalSource="workspace"`
- sends a user message that can only be answered from the sentinel note
- waits for the real queue-backed task to complete
- checks the persisted assistant message
- checks retrieval/trace evidence for workspace-local participation

The harness is intentionally scoped to the supported local Compose path only. It does not widen the release promise to packaged desktop, webUI-only, or other install modes.

## Evidence Sources

The harness reads evidence from:

- `/health`
- `/health/chat`
- `/api/health/llm`
- `/api/health/retrieval`
- `/api/obsidian/config`
- `/api/obsidian/index`
- `GET /api/tasks/{task_id}/events`
- `GET /api/chat/{thread_id}/messages`
- latest retrieval/trace debug surfaces when available on the live path

## Consequences

- Release evidence can now prove the actual `workspace` completion seam end to end.
- Queue acceptance is no longer treated as completion proof.
- Workspace-local retrieval evidence is separated from the assistant message itself.
- Operators get one repeatable command for this seam instead of ad hoc probes.

## Non-Goals

- No sync automation
- No connector UX
- No new retrieval subsystem
- No storage model change
- No support claim for non-Compose install modes
- No claim that debug trace endpoints are the sole source of truth

## Governing Contracts

- [ADR-016: Workspace Retrieval Source for Local Knowledge](./016-workspace-retrieval-source-for-local-knowledge.md)
- [Critical Flows](../flows.md)
- [System Overview](../system-overview.md)
- [Config and Ops](../config-and-ops.md)
- [Current State](../00-current-state.md)

## Related Notes

- [ADR Index](./adr-index.md)
- [Proof Harness README](../../scripts/proofs/README.md)
