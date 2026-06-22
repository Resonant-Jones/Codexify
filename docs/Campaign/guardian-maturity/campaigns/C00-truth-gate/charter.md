# C00: Truth Gate and Worktree Classification

## Metadata

- **Campaign ID**: C00
- **Title**: Truth Gate and Worktree Classification
- **Wave**: 0
- **Status**: `planned`
- **Owner**: resonant_jones
- **Risk**: LOW
- **Architecture Impact**: no (read-only audit)
- **Governing ADRs/Contracts**:
  - [00-current-state.md](../../../architecture/00-current-state.md)
  - [Config and Ops](../../../architecture/config-and-ops.md)
  - [Chat Runtime Contract](../../../architecture/chat-runtime-contract.md)

## Purpose

Establish the starting line before touching runtime or UI. Classify branch/worktree state, identify dirty state, inventory runtime proof gaps, and confirm the release boundary.

## Current Truth Anchors

What is true now:
- Codexify is in local-first beta hardening on `main`.
- The supported path is local Docker Compose.
- Whoosh'd is the supported local runtime preset.
- Live model availability is proven only by inventory endpoints.
- Health surfaces (`/health`, `/health/chat`, `/health/llm`) exist per config-and-ops.md.
- `/api/llm/catalog` is the discovered inventory surface.

## Non-Goals

- This campaign does **not** modify any files.
- This campaign does **not** implement backend routes or frontend components.
- This campaign does **not** fix discovered issues.
- This campaign does **not** change the release boundary.

## Invariants

- Do not mutate files, routes, UI, or configuration during proof collection.
- Do not treat catalog presence as runtime proof.
- Do not treat smoke defaults as live model proof.
- Do not widen the release promise based on proof gaps discovered.

## Dependencies

- None. This is the first campaign in the program.

Campaigns that this campaign enables:
- C11 (API Route Audit) — needs worktree/runtime truth baseline
- C01 (Command Center) — needs verified health surfaces
- C02 (Chat Runtime State) — needs runtime truth baseline
- C08 (Whoosh'd Runtime Setup) — needs model inventory proof

## Proof Gates

| Category | Required Evidence |
|----------|-------------------|
| Docs proof | `00-current-state.md` is consistent with observed runtime truth |
| Backend seam proof | Health endpoints (`/health`, `/health/chat`, `/health/llm`) return structured responses |
| Backend seam proof | `/api/llm/catalog` and `/api/llm/catalog?include=all` return provider/model inventory |
| Live supported-path proof | Whoosh'd `/v1/models` or equivalent returns model inventory |
| Live supported-path proof | `git status --short --branch --untracked-files=all` shows clean or classified worktree |

## Proof Surfaces

The following read-only surfaces must be inspected:

1. `git status --short --branch --untracked-files=all`
2. `/health`
3. `/health/chat`
4. `/health/llm`
5. `/api/llm/catalog`
6. `/api/llm/catalog?include=all`
7. Whoosh'd `/v1/models` or configured equivalent model inventory endpoint

## Gate Decision

**Current**: `next-proof-needed` — proof has not yet been collected.

Expected gate decision after proof collection: `go` if all surfaces return valid structured responses and worktree is classified; `hold` if any surface is unreachable, returns errors, or worktree has unclassified dirty state.

## Done-When

The campaign is done when:
1. All seven proof surfaces have been inspected.
2. Worktree state is classified (clean, dirty-tracked, dirty-untracked, or drift).
3. Runtime proof gaps are documented in `proof-pack.md`.
4. Gate decision is recorded in `decision-log.md`.
5. Release boundary is confirmed against observed truth.

## Risks

- **Stale health data**: Health endpoints may return cached or stale data. Cross-reference with catalog and inventory.
- **Whoosh'd not running**: If Whoosh'd is not running locally, model inventory proof will fail. This is a legitimate gap, not a false failure.

## Task Queue

Tasks are tracked in [`backlog.md`](./backlog.md).
