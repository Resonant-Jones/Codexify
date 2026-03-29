## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-03-29

## Interpretation rule

This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

Codexify is in release-hardening on `main` for the local Docker Compose beta path. Recent merges improved chat event/run consistency, retrieval routing policy scaffolding, and Redis failure behavior; readiness remains gated on fresh end-to-end supported-path proof and explicit release-gate evidence.

## What changed recently

- Chat UI run-state flow was reworked to use a shared per-thread `useAgentRuns` store and task-event-driven updates.
- Live event handling introduced canonical `LiveEvent` normalization across chat runtime paths.
- Backend now enforces Redis fail-fast behavior and explicit `503` degradation contracts on chat/session/health surfaces.
- Redis queue blocking paths were hardened to enforce queue-client usage, with targeted queue tests added.
- Canonical retrieval router policy scaffold landed (`guardian/context/retrieval_router_policy.py`) with tests.
- Daily/weekly audit artifacts continued to refresh under `docs/audits/`.

## Current supported reality

- Supported install path remains local Docker Compose with backend, frontend, Postgres, Redis, and workers.
- Thread chat is the core supported flow, with queue-backed completion and persisted task/message state.
- Chat runtime state on `main` now uses normalized live events and consolidated per-thread agent-runs state.
- Architecture docs now include a chat runtime state contract for frontend/shared-runtime interpretation of provider warmup, request lifecycle ambiguity, and replay semantics; this is documentation alignment, not fresh live-runtime proof.
- Retrieval routing now has an explicit policy scaffold and tests, but this is policy infrastructure rather than a full release gate.
- Runtime now degrades explicitly when Redis coordination is unavailable instead of silently drifting.
- Validation evidence on `main` is still mostly unit/targeted integration tests plus audit snapshots.

## Not yet true / do not assume

- Do not assume one fresh full supported-path smoke (thread -> completion -> upload -> embed -> retrieve) has been published for current `main`.
- Do not assume supported-profile runtime flags were freshly re-verified on the live release Compose stack.
- Do not assume route quarantine posture is continuously enforced without explicit runtime evidence.
- Do not assume `/tools` and command-bus surfaces are fully unified into one release contract.
- Do not assume provider/catalog visibility alone implies release support.
- Do not assume Redis is optional for current chat/queue coordination.
- Do not assume federation durability or broad connector sync is part of the present beta promise.

## Active blockers

- Missing fresh end-to-end supported-path proof on current `main` for chat + ingestion + retrieval.
- Missing current-cycle live verification for supported-profile flags and quarantined-route behavior.
- Release gate evidence across `/health`, `/health/llm`, `/health/chat`, and `/api/llm/catalog` is not yet packaged as one operator-facing signoff.
- `/tools` vs command-bus release-surface boundaries remain ambiguous in current release docs.

## This week's priorities

1. Execute and publish one full supported-path run on `main` (thread, completion, upload, embed, retrieval).
2. Re-verify and record supported-profile flags and route quarantine posture on the live Compose stack.
3. Publish one release-gate check artifact that reconciles `/health`, `/health/llm`, `/health/chat`, and `/api/llm/catalog`.
4. Tighten and document `/tools` versus command-bus release boundaries in operator-facing terms.

## Release definition right now

- [ ] Supported-profile flags are active in live runtime (`CODEXIFY_BETA_CORE_ONLY=true`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`).
- [ ] Quarantined non-core routes match the supported-profile contract in the running stack.
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
