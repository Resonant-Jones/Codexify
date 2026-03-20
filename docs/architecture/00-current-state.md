## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-03-20

## Interpretation rule

This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

Codexify is in runtime-stabilization for a local Docker Compose beta path on `main`. Recent merges made the Redis-backed chat loop more truthful about health, queue pressure, stale locks, event visibility, and acceptance boundaries, but release posture is still `hold` until supported-profile runtime behavior and end-to-end proof are re-validated on the live stack.

## What changed recently

- Runtime hardening merged for transient failures in API event streaming and Redis dequeue paths.
- Startup warmup behavior was made best-effort to reduce noisy boot failures.
- Provider governance classification and baseline governance docs were added to `main`.
- Supported-profile proof artifact was added and recorded a profile/runtime mismatch on live Compose.
- Runtime stability audit template and a 2026-03-17 audit artifact were added under `docs/release/run`.
- Compose env-file selection normalization was merged, but release evidence still flags profile drift at runtime.
- Packaged runtime/bootstrap handling and macOS bundle launchability were updated on `main`.
- Chat UX/runtime behavior was adjusted for cancel unlock and persisted inference mode.
- Completion matching was hardened in chat flow paths.
- `/health/chat` now distinguishes Redis reachability, queue round-trip truth, worker-heartbeat freshness, and sampled queue-progress heuristics more honestly.
- Stale-turn-lock recovery now depends on task-stream and heartbeat evidence and fails closed when the evidence is ambiguous.
- Task-event visibility degradation is now surfaced more explicitly in worker logs.
- Chat acceptance truth is stronger: success now means lock plus enqueue succeeded, while degraded lifecycle visibility is treated as degraded visibility rather than invisible success.

## Current supported reality

- Supported install path is local Docker Compose with backend, frontend, Postgres, Redis, and required workers.
- Core product loop on `main` is thread chat with queue-backed completion, persisted messages, and task/event telemetry.
- The main interaction loop is materially less ambiguous than before:
  - `/health/chat` is more honest about worker freshness and backlog signals
  - stale-lock recovery is evidence-based instead of lease-age-only
  - task-event publish failure is surfaced as visibility degradation
  - route success is a stronger statement about queue acceptance than before
- Release evidence exists on `main` for runtime audits (`docs/release/run/2026-03-17-runtime-stability-audit.md`) and supported-profile proof attempts (`docs/release/run/2026-03-17-beta-smoke-supported-profile-proof.md`).
- Architecture-level readiness baseline was captured on `main` (`docs/audits/history/2026-03-19-platform-readiness-baseline.md`).
- Health, catalog, and supported-profile surfaces are part of current operator workflow; none is sufficient alone for release signoff.

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

## Active blockers

- Supported-profile contract drift: documented profile expectations and live runtime behavior still diverge.
- Fresh live supported-path proof is incomplete for thread -> assistant completion and upload -> embed -> retrieve in one passing run.
- Provider governance, catalog, and runtime health can still present mixed signals without a single release-grade gate.
- Tool execution surface remains split between legacy `/tools` behavior and command bus behavior.
- Redis-backed chat remains a coordination concentration point even after the reliability pass; the branch improves operator truth and failure handling, but does not yet remove Redis as a central dependency for the core loop.

## This week's priorities

1. Re-prove supported-profile runtime flags on the actual Compose stack used for release smoke.
2. Capture one fresh end-to-end supported-path evidence run: thread, completion, upload, embed-ready, retrieval.
3. Close provider release gating drift by aligning supported profile, catalog output, and runtime health interpretation.
4. Reduce `/tools` vs command bus ambiguity in release-facing behavior and docs.
5. Keep chat completion reliability hardening test-backed on `main`.

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
