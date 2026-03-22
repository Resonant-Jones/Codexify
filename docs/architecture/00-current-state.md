## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-03-21

## Interpretation rule

This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

Codexify is in release-criteria tightening for a local Docker Compose beta path on `main`. Runtime truth surfaces for chat reliability are stronger than last week, and new audits clarified where compatibility and recon work still exceeds the release promise, but release posture is still `hold` until supported-profile behavior and one full supported-path proof are re-validated on the live stack.

## What changed recently

- Chat flow reliability hardening landed on `main` for completion matching, stale-lock recovery, queue-progress truth, and task-event visibility signaling.
- Route acceptance signaling was tightened so accepted chat work reflects lock + enqueue success rather than ambiguous partial success.
- `/health/chat` now distinguishes Redis reachability, queue round-trip truth, worker-heartbeat freshness, and sampled queue-progress heuristics more honestly.
- Release/run artifacts were refreshed on `main`, including a 2026-03-18 supported-profile proof entry and daily/evening audit snapshots.
- A legacy tools dependency audit was added on `main` and confirmed live runtime callers still depend on `/tools/execute` compatibility.
- Obsidian sync recon was added on `main` and confirmed the current path is CLI-based local ingest with no shipped Obsidian connector sync workflow.

## Current supported reality

- Supported install path is local Docker Compose with backend, frontend, Postgres, Redis, and required workers.
- Core product loop on `main` is thread chat with queue-backed completion, persisted messages, and task/event telemetry.
- The main interaction loop is materially less ambiguous than before:
  - `/health/chat` is more honest about worker freshness and backlog signals
  - stale-lock recovery is evidence-based instead of lease-age-only
  - task-event publish failure is surfaced as visibility degradation
  - route success is a stronger statement about queue acceptance than before
- Release evidence exists on `main` for runtime audits and supported-profile proof attempts under `docs/release/run/`.
- Architecture-level readiness baseline was captured on `main` (`docs/audits/history/2026-03-19-platform-readiness-baseline.md`).
- Health, catalog, and supported-profile surfaces are part of current operator workflow; none is sufficient alone for release signoff.
- Knowledge ingestion remains local-first: Obsidian support is via manual CLI ingest into the vector store, not an active connector sync pipeline.

## Not yet true / do not assume

- Do not assume the Beta-1 supported-profile flags are reliably active in live Compose runtime.
- Do not assume quarantined non-core routes are consistently unavailable on the supported profile.
- Do not assume provider catalog visibility equals runtime-executable and supported release paths.
- Do not assume command center/action-center UI is the released operator source of truth.
- Do not assume legacy `/tools` and command bus contracts are fully unified.
- Do not assume federation/sync durability is in the current release promise.
- Do not assume queue-progress status proves a worker dequeued a specific chat task.
- Do not assume task-event publication proves downstream UI receipt or rendering.
- Do not assume accepted work will complete successfully just because the route returned success.
- Do not assume Redis coupling risk is removed; it is better surfaced, not eliminated.
- Do not assume Obsidian sync is a shipped connector feature; only local CLI ingest is evidenced on `main`.

## Active blockers

- Supported-profile contract drift: documented profile expectations and live runtime behavior still diverge.
- Fresh live supported-path proof is incomplete for thread -> assistant completion and upload -> embed -> retrieve in one passing run.
- Provider governance, catalog, and runtime health can still present mixed signals without a single release-grade gate.
- Tool execution surface remains split between legacy `/tools` behavior and command bus behavior.
- Redis-backed chat remains a coordination concentration point even after the reliability pass; the branch improves operator truth and failure handling, but does not yet remove Redis as a central dependency for the core loop.
- Obsidian/local knowledge-source exposure remains unproven in runtime evidence beyond manual ingest and vector-store mechanics.

## This week's priorities

1. Re-prove supported-profile runtime flags on the actual Compose stack used for release smoke.
2. Capture one fresh end-to-end supported-path evidence run: thread, completion, upload, embed-ready, retrieval.
3. Close provider release gating drift by aligning supported profile, catalog output, and runtime health interpretation.
4. Reduce `/tools` vs command bus ambiguity in release-facing behavior and client call paths.
5. Decide and document the beta promise for Obsidian: explicit CLI-only support or scoped connector delivery criteria.

## Release definition right now

- [ ] Supported-profile flags are active in live runtime (`CODEXIFY_BETA_CORE_ONLY=true`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`).
- [ ] Quarantined non-core routes match the current supported-profile contract.
- [ ] One fresh supported-path smoke on `main` proves thread create, assistant completion, document upload, embed readiness, and retrieval evidence.
- [ ] `/health/chat`, `/health/llm`, `/health`, and `/api/llm/catalog` agree with supported-profile and provider-governance expectations.
- [ ] No release claim depends on internal-only or dev-only surfaces.
- [ ] Release language stays precise about partial truth surfaces: queue progress is heuristic, task-event visibility is not UI receipt, and route acceptance is not eventual completion.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
