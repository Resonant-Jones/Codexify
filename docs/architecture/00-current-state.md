## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-07-23

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. Recent `main` changes are mostly release cleanup, health/probing fixes, UI polish, and release-truth documentation, plus email implementation-target inspection work that does not widen runtime support.

## What changed recently
- Integrated live-proof receipts into canonical evidence manifest generation; qualifying `PASS` receipts now support deterministic `CURRENT_LIVE_PROOF` manifests with receipt identity preserved as hashed evidence and explicit lineage. The generated manifest remains unpromoted; durable storage, cross-record freshness, and trusted `latest` remain deferred.
- Added an email implementation-target inspection and campaign index on `main`; this is planning and target mapping only.
- Removed the legacy document generation UI from the frontend.
- Fixed mobile composer viewport settling.
- Updated health checks to probe the cloud-provider endpoint instead of returning a stub degraded status.
- Pinned friends/family chat to DeepSeek V4 Flash.
- Separated live Continuity database proof from broader operator routes.
- Restored thread-first project retrieval.
- Removed Zac's last name from the email campaign materials.
- Added a docs/proof-only Project Pulse exact-ID read proof fixture contract and static fixture after implementation-target inspection. This does not implement Project Pulse, routes, services, adapter methods, schemas, migrations, UI, CLI, workers, command bus, provider calls, retrieval changes, graph use, browser capture, export/restore, tests, runtime fixture loading, database seeds, writes, or supported-beta activation.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported posture remains local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- `AI_BACKEND=local` remains legacy compatibility only.
- `LOCAL_RUNTIME_PRESET` still selects `whooshd-mlx`, `ollama`, `lmstudio`, or `custom-openai-compatible` under the local provider boundary.
- Whoosh'd remains the supported Apple Silicon local runtime preset.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval remain the supported beta paths.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` remain the fastest runtime checks.
- The friends/family chat profile is pinned to DeepSeek V4 Flash on `main`.
- Thread-first project retrieval is restored on `main`.
- Supported Compose live proof receipts exist as a bounded proof and validation seam, not a release expansion.
- OpenAI export import and Task Prompt Archive are present on `main`.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume docs-only contracts or implementation-target inspections mean shipped runtime support.
- Do not assume the email campaign index or inspection implies an email runtime, mailbox, or send path.
- Do not assume the Continuity operator surface is supported beta, user-facing, Project Pulse, export/restore, graph, chat runtime, worker, or command bus behavior.
- Do not assume the Guardian delegation loop or Guardian Codex Runner bridge docs imply an end-to-end supported delegation/runtime path.
- Do not assume shared presence, hosted rooms, chat transport recovery, thread lenses, or Guardian orientation docs are shipped runtime behavior.
- Do not infer a wider release promise from docs-only onboarding, scaffolds, or audit artifacts.
- Do not assume any local runtime is available without live endpoint and model inventory proof.

## Active blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains high-blast-radius and trust-policy sensitive.
- Graph-write enablement stays outside the default release promise.
- Email remains in inspection and planning only; no runtime behavior is shipped yet.

## This week's priorities
1. Keep supported-profile, health, and catalog surfaces aligned on `main`.
2. Preserve proof for chat, upload, retrieval, and OpenAI import paths.
3. Keep Guardian bridge proof separated from shipped runtime claims.
4. Keep legacy config compatibility narrow and clearly labeled.
5. Recheck blocker status only when `main` moves.

## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
- [x] The current `main` tip includes a supported local runtime preset for Whoosh'd.
- [x] Chat completion, upload -> embed -> readback, and workspace-local retrieval are in the supported claim set.
- [x] Health endpoints return real probe-based status on the supported path.
- [ ] Queue, config, delegation, and federation risks stay explicitly documented and rechecked when the supported path drifts.
- [ ] Legacy `AI_BACKEND` compatibility must not be mistaken for a new supported contract.
- [ ] New docs-only contracts, inspections, and bridge proofs must stay out of the supported runtime claim set until proven on `main`.
- [ ] Any new release claim needs fresh proof on `main`, not branch-local evidence.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence and invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
