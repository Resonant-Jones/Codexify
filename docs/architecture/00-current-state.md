## Purpose

This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-07-30

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` is in local-first beta hardening at `7dceb0140`. The supported path remains the local Docker Compose stack with local-only provider posture. Recent merged work refines mobile chat presentation and health surfaces while adding Hosted Room and account-import seams; it does not establish a broader release surface.

## What changed recently

- Added Hosted Room persistence, owner lifecycle, invitation and guest-session exchange, human transcript read/write, participant provenance, and explicit asynchronous Guardian invocation on `main`.
- Added zero-write OpenAI account-import retry handling and repaired tester staging continuity; partial-write jobs remain non-retryable.
- Finalized the mobile composer as one visible surface with shared draft/send state and mobile model actions; the earlier projection implementation is not the current shipped UI behavior.
- Removed queue timing and detail diagnostics from user-facing chat cards while retaining lifecycle status labels; queue semantics were not changed.
- Health checks now probe the configured provider endpoint; friends/family tester configuration is pinned to DeepSeek V4 Flash.
- Added migration-safety, account-import, Hosted Room invocation, accent-preservation, and frontend test/proof coverage.
- Added P2P video, email, Project Pulse, and related implementation-target documents; these remain planning or proof-only surfaces.

## Current supported reality

- Local Docker Compose is the supported install path.
- The supported posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, and `LLM_PROVIDER=local`.
- `whooshd-mlx` is the supported Apple Silicon local runtime preset; other local presets remain explicit configuration choices.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval are the supported beta paths.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` are the primary operator checks; read them with the supported profile and catalog.
- OpenAI export import, Task Prompt Archive, and owner-scoped retry of failed zero-write import jobs are present on `main`.
- Hosted Room owner/guest routes and explicit Guardian enqueue are implemented, but are not release-qualified and do not create automatic agent responses.

## Not yet true / do not assume

- Do not assume cloud-provider beta support, packaged-desktop replacement of Compose, or a current local runtime without live endpoint and model-inventory proof.
- Do not assume Hosted Room automatic responses, Luna invocation, ambient presence, cross-node rooms, join links, participant removal, or release qualification.
- Do not assume a green health check, route acceptance, unit test, proof receipt, or docs contract is end-to-end runtime or release proof by itself.
- Do not treat the mobile projection-plane architecture note as current runtime behavior; `main` currently uses the single-surface mobile composer.
- Do not assume Guardian delegation/Codex Runner bridge documents establish a supported end-to-end delegation path.
- Do not assume email, federation, graph writes, Continuity/Project Pulse, thread lenses, or P2P video are shipped beta behavior.
- Do not assume failed account-import jobs retry automatically, repair partial writes, deduplicate payloads, or reconstruct missing historical staging.
- Do not count local branches, unmerged work, draft plans, or obsolete worktree payloads as `main` reality.

## Active blockers

- Queue-coupled chat still requires healthy Redis, worker, turn-lock, and terminal-event behavior.
- Canonical and legacy configuration paths coexist, creating startup and operator-state drift risk.
- The supported path still needs fresh live Compose proof after material `main` changes; tests and health code are not that proof.
- Hosted Room end-to-end Guardian execution is not release-supported; federation remains high-blast-radius and trust-policy sensitive.
- Email, graph-write enablement, and broader delegation remain outside the default release promise.

## This week's priorities

1. Recheck supported-profile, provider-catalog, health, and local-runtime alignment on `main`.
2. Preserve fresh live proof for chat, upload/readback, workspace retrieval, and import recovery.
3. Keep Hosted Room route/provenance evidence separate from release qualification.
4. Reduce or clearly fence canonical-versus-legacy configuration drift.
5. Keep docs-only and branch-local work out of release reporting.

## Release definition right now

- [x] The supported profile and local-only flags define the beta posture.
- [x] Whoosh'd local runtime and core chat/upload/retrieval paths are represented on `main`.
- [x] Health surfaces perform real provider and queue/worker checks in the supported path.
- [ ] Fresh live Compose evidence confirms the current `main` tip, including terminal completion and persisted output.
- [ ] Queue, configuration, migration, and recovery behavior are green for the supported install path.
- [ ] Every new release claim is merged to `main` and backed by evidence at the claimed proof level.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence and invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
