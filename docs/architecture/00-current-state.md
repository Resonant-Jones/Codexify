## Purpose

This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-08-03

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` is in local-first beta hardening at `50721d0f5`. The supported path remains the local Docker Compose stack with local-only provider posture. Mainline has narrowed the accepted release surface by pruning unmerged forge and UI-personalization artifacts; private-preview and browser work remain bounded opt-in or documentation surfaces.

## What changed recently

- Pruned the unaccepted Soft Serve/VaultNode local-forge workflow and ADR-054/ADR-055 artifacts from `main`.
- Added a dedicated architecture-contract CI workflow; it strengthens repository validation but is not live runtime proof.
- Preserved private-preview startup/proxy hardening and browser campaign documentation without widening the default beta promise.
- Local `main` is two commits behind `origin/main`; origin-only changes are excluded from this audit's shipped reality.

## Current supported reality

- Local Docker Compose is the supported install path.
- The supported posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, and `LLM_PROVIDER=local`.
- `whooshd-mlx` is the supported Apple Silicon local runtime preset; other local presets require explicit configuration.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval are the supported beta paths.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` are the primary operator checks.
- OpenAI export import, Task Prompt Archive, and owner-scoped retry of failed zero-write import jobs are present on `main`.
- Architecture-contract validation is defined on `main`; it does not prove live service behavior or release readiness.

## Not yet true / do not assume

- Do not assume cloud-provider beta support, packaged-desktop replacement of Compose, or a current local runtime without live endpoint and model-inventory proof.
- Do not assume the private-preview lane is operational; authenticated Whoosh'd and DeepSeek V4 Flash persisted-turn proof remains open.
- Do not treat a green health check, route acceptance, unit test, proof receipt, or docs contract as end-to-end runtime proof by itself.
- Do not assume Hosted Room automatic responses, Luna invocation, ambient presence, cross-node rooms, or release qualification.
- Do not treat browser, email, federation, graph writes, Continuity/Project Pulse, thread lenses, or P2P video documents as shipped beta behavior.
- Do not assume failed account-import jobs retry automatically, repair partial writes, deduplicate payloads, or reconstruct missing historical staging.
- Do not count local branches, unmerged work, draft plans, obsolete worktrees, origin-only commits, or local commits not present on `main` as shipped reality.

## Active blockers

- Local `main` trails `origin/main` by two commits; reconcile the audited tip before using remote state as release evidence.
- Fresh live Compose proof is still needed at the audited `main` tip, including terminal completion and persisted output.
- Queue-coupled chat still requires healthy Redis, worker, turn-lock, and terminal-event behavior on the supported path.
- Canonical and legacy configuration paths coexist, creating startup and operator-state drift risk.
- The private-preview lane lacks its required DeepSeek credential and authenticated session-token prerequisite.
- Hosted Room end-to-end Guardian execution and broader federation/delegation remain outside release qualification.

## This week's priorities

1. Reconcile the intended audited `main` tip, then rerun release checks from that commit.
2. Capture live proof for health, model inventory, chat, upload/readback, workspace retrieval, queue completion, and import recovery.
3. Reduce or clearly fence canonical-versus-legacy configuration drift.
4. Complete private-preview prerequisites and provider-specific proof, or keep that lane quarantined.
5. Keep browser, Hosted Room, federation, and other planning surfaces out of release claims.

## Release definition right now

- [x] The supported profile and local-only flags define the beta posture.
- [x] Whoosh'd local runtime and core chat/upload/retrieval paths are represented on `main`.
- [x] Architecture-contract validation is defined on `main`.
- [ ] The audited `main` tip is reconciled with the intended release commit.
- [ ] Fresh live Compose evidence confirms terminal completion and persisted output.
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
