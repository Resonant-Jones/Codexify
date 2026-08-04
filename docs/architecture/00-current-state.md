## Purpose

This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-08-04

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first beta hardening at `c7d4510c1`. The supported path is the local Docker Compose stack with local-only provider posture. Merged private-preview and browser work adds bounded opt-in or documentation surfaces; neither widens the default release promise.

## What changed recently

- Added static/test-proven configuration and provider-specific proof tooling for the opt-in `v1-whooshd-deepseek-web` preview lane.
- Repaired private-preview startup health, single-origin proxying, and backend re-resolution after container replacement.
- Added thread-refresh backoff and retry guards, idempotent migration changes, and private-preview configuration updates.
- Clarified trusted-remote/private-preview email sign-in behavior.
- Recorded the latest dual-provider preview proof as `next-proof-needed`: missing DeepSeek credential and authenticated session prevented runtime turns.
- Added a Codexify Browser campaign and extension inventory as documentation; this is not shipped browser support.
- Guardian Evidence Packet authoring template and guide are static authoring aids only; they do not implement runtime reducer behavior or widen release support.
- Restored the bounded canonical live-proof receipt handoff in the audit tooling: one qualifying `PASS` receipt can support a deterministic `CURRENT_LIVE_PROOF` manifest, with mandatory fresh runtime comparison and fail-closed receipt lineage.

## Current supported reality

- Local Docker Compose is the supported install path.
- The supported posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, and `LLM_PROVIDER=local`.
- `whooshd-mlx` is the supported Apple Silicon local runtime preset; other local presets require explicit configuration.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval are the supported beta paths.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` are the primary operator checks; use them with the supported profile and model catalog.
- OpenAI export import, Task Prompt Archive, and owner-scoped retry of failed zero-write import jobs are present on `main`.

## Not yet true / do not assume

- Do not assume cloud-provider beta support, packaged-desktop replacement of Compose, or a current local runtime without live endpoint and model-inventory proof.
- Do not assume the private-preview lane is operational from static proof; it still needs authenticated, persisted Whoosh'd and DeepSeek V4 Flash turns.
- Do not assume a green health check, route acceptance, unit test, proof receipt, or docs contract is end-to-end runtime or release proof by itself.
- Do not treat a validator-passing `CURRENT_LIVE_PROOF` manifest as storage, promotion, trusted `latest`, release approval, or proof of the current live Compose runtime without the separately required live execution evidence.
- Do not assume Hosted Room automatic responses, Luna invocation, ambient presence, cross-node rooms, or release qualification.
- Do not treat the Browser campaign, email, federation, graph writes, Continuity/Project Pulse, thread lenses, or P2P video documents as shipped beta behavior.
- Do not assume failed account-import jobs retry automatically, repair partial writes, deduplicate payloads, or reconstruct missing historical staging.
- Do not count local branches, unmerged work, draft plans, obsolete worktrees, or local commits not present on `main` as shipped reality.

## Active blockers

- Fresh live Compose proof is still needed at the current `main` tip, including terminal completion and persisted output.
- Queue-coupled chat still requires healthy Redis, worker, turn-lock, and terminal-event behavior on the supported path.
- Canonical and legacy configuration paths coexist, creating startup and operator-state drift risk.
- The private-preview lane is blocked on its missing DeepSeek credential and authenticated session-token prerequisite; provider-specific runtime proof remains open.
- Hosted Room end-to-end Guardian execution and broader federation/delegation remain outside release qualification.

## This week's priorities

1. Run fresh supported-profile, provider-catalog, health, and local-runtime checks on `main`.
2. Capture live proof for chat, upload/readback, workspace retrieval, queue completion, and import recovery.
3. Complete the private-preview prerequisites and provider-specific proof, or keep that lane explicitly quarantined.
4. Reduce or clearly fence canonical-versus-legacy configuration drift.
5. Keep browser, Hosted Room, and other planning surfaces out of release claims.

## Release definition right now

- [x] The supported profile and local-only flags define the beta posture.
- [x] Whoosh'd local runtime and core chat/upload/retrieval paths are represented on `main`.
- [x] Health surfaces include provider and queue/worker checks for the supported path.
- [ ] Fresh live Compose evidence confirms the current `main` tip, terminal completion, and persisted output.
- [ ] Queue, configuration, migration, and recovery behavior are green for the supported install path.
- [ ] Any claimed private-preview lane has authenticated, provider-specific persisted-turn proof.
- [ ] Every release claim is merged to `main` and backed by evidence at the claimed proof level.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence and invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
