## Purpose

This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-08-08

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` is in local-first beta hardening at `fc2bb353e`. The current release interpretation remains the local Docker Compose path and local-only provider posture. Recent DLG, ontology, Campaign Engine, Browser Host, and Coding Loop work is merged evidence or contract/test surface; it does not widen the release promise without matching runtime proof.

## What changed recently

- Accepted and inventoried the Document Lifecycle Graph and Product Architecture Ontology as Git-backed docs/control-plane architecture.
- Added DLG/PAO schemas, examples, deterministic tests, and publication-proof receipts; no runtime corpus migration or graph projection was added.
- Added the Campaign Engine v0 contract and core schemas/tests; no scheduler, agent dispatcher, overnight executor, or auto-merge path was added.
- Made the tester dual-provider startup profile permanent, with provider-specific configuration still bounded to the opt-in tester lane.
- Exposed the bounded Guardian Composer Coding Loop routes in the local profile and restored worker mutation guards; successful terminal coding execution remains unproven.
- Merged Browser Host Electron selection and qualification artifacts; packaged desktop replacement of Compose remains future work.
- Added repository-hygiene and daily-audit receipts; these are reporting and maintenance changes, not runtime readiness proof.

## Current supported reality

- Local Docker Compose is the supported install path.
- The supported beta posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, and `LLM_PROVIDER=local`.
- `whooshd-mlx` is the supported Apple Silicon local runtime preset; other local presets require explicit configuration.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval are the supported beta paths.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` are the primary operator checks.
- OpenAI export import, Task Prompt Archive, and owner-scoped retry of failed zero-write import jobs are present on `main`.
- Coding Loop route registration, focused tests, and guard logic are present; they do not prove a successful adapter turn or durable terminal result.
- Architecture-contract, schema, and proof-validation tooling is present on `main`; it is not live-service proof.

## Not yet true / do not assume

- Do not assume cloud-provider beta support, a packaged desktop runtime, or a current local model without live endpoint and inventory proof.
- Do not assume the tester dual-provider lane is release-supported; it still needs authenticated, provider-specific persisted turns.
- Do not assume a green health check, route acceptance, unit test, proof receipt, or docs contract proves end-to-end runtime readiness.
- Do not assume DLG/PAO documents provide corpus migration, automatic retrieval, database projection, assertion resolution, or agent authority.
- Do not assume Campaign Engine schemas provide scheduling, delegation, overnight execution, auto-merge, or auto-push.
- Do not assume Browser Host, Chrome extension, Hosted Room, email, federation, graph writes, Continuity/Project Pulse, or P2P video are shipped beta behavior.
- Do not count local branches, unmerged work, draft plans, origin-only commits, or proof from another checkout as shipped reality.

## Active blockers

- Fresh live Compose proof is still needed at `fc2bb353e`, including terminal completion and persisted output.
- Queue-coupled chat still needs current-tip evidence for Redis, worker, turn-lock, and terminal-event behavior.
- Canonical and legacy configuration paths coexist, creating startup and operator-state drift risk.
- The bounded Coding Loop lane lacks fresh proof of provider adapter execution, terminal result persistence, and durable source-thread readback on current `main`.
- The private-preview lane lacks its required DeepSeek credential and authenticated session-token prerequisite.

## This week's priorities

1. Capture fresh supported-Compose proof at the current `main` tip: health, model inventory, chat, persistence, and retrieval.
2. Verify queue completion, turn locking, migration behavior, and import recovery under the supported profile.
3. Reconcile or clearly fence canonical-versus-legacy configuration paths.
4. Re-prove the enabled Coding Loop lane end to end, or quarantine it until terminal persistence is proven.
5. Keep DLG/PAO, Campaign Engine, Browser Host, Hosted Room, and provider-preview work outside release claims until their required proof exists.

## Release definition right now

- [x] The supported profile and local-only flags define the beta posture.
- [x] Whoosh'd local runtime and core chat/upload/retrieval paths are represented on `main`.
- [x] Relevant architecture and schema validation is defined on `main`.
- [ ] Fresh live Compose evidence confirms terminal completion and persisted output at the audited tip.
- [ ] Queue, configuration, migration, and recovery behavior are green for the supported install path.
- [ ] Enabled Coding Loop routes have authenticated adapter, terminal, and durable readback proof, or are quarantined.
- [ ] Any claimed preview or alternate surface has provider- or surface-specific runtime proof.
- [ ] Every release claim is merged to `main` and backed by evidence at the claimed proof level.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence and invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
