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

Codexify is in runtime-stabilization for a local Docker Compose beta path on `main`. Recent merges improved packaging, startup resilience, completion matching, and diagnostics, but release posture is still `hold` until supported-profile runtime behavior and end-to-end proof are re-validated on the live stack.

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

## Current supported reality

- Supported install path is local Docker Compose with backend, frontend, Postgres, Redis, and required workers.
- Core product loop on `main` is thread chat with queue-backed completion, persisted messages, and task/event telemetry.
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

## Active blockers

- Supported-profile contract drift: documented profile expectations and live runtime behavior still diverge.
- Fresh live supported-path proof is incomplete for thread -> assistant completion and upload -> embed -> retrieve in one passing run.
- Provider governance, catalog, and runtime health can still present mixed signals without a single release-grade gate.
- Tool execution surface remains split between legacy `/tools` behavior and command bus behavior.

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

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
