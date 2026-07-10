## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-07-10

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. `main` is absorbing Guardian Codex Runner bridge proof and contract work, not expanding the supported beta runtime surface.

## What changed recently
- `main` added Guardian bridge proof and contract work for selected validation receipt, validation receipt availability, orchestration receipt prerequisite, and module live-validate coverage.
- `main` added a mounted live-validate proof packet plus an opt-in container visibility contract.
- `main` added an executable-availability seam for the bridge when `codexrun` is not on container PATH.
- `main` added backend bridge contracts and a JSON adapter for the Guardian Codex Runner seam.
- `main` did not add a new supported install path or widen the beta release promise.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported posture remains local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- `AI_BACKEND=local` remains legacy compatibility only.
- `LOCAL_RUNTIME_PRESET` still selects `whooshd-mlx`, `ollama`, `lmstudio`, or `custom-openai-compatible` under the local provider boundary.
- Whoosh'd remains the supported Apple Silicon local runtime preset.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval remain the supported beta paths.
- OpenAI export import and Task Prompt Archive are present on `main`.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` remain the fastest runtime checks.
- Graph writes remain default-off on the supported Compose path.
- The Continuity operator surface remains test-only, API-key-gated, and profile-quarantined under `test-continuity`.
- Guardian bridge work on `main` is proof/contract only and does not widen the supported runtime promise.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume docs-only contracts mean shipped runtime support.
- Do not assume shared presence, hosted rooms, chat transport recovery, thread lenses, or Guardian orientation docs are shipped runtime behavior.
- Do not assume the Guardian delegation loop or Guardian Codex Runner bridge docs imply an end-to-end supported delegation/runtime path.
- Do not assume the Continuity operator surface is supported beta, user-facing, Project Pulse, export/restore, graph, chat runtime, worker, or command bus behavior.
- Do not assume the new Guardian bridge proof chain means live orchestration support.
- Do not infer a wider release promise from docs-only onboarding, scaffolds, or audit artifacts.
- Do not assume any local runtime is available without live endpoint/model inventory proof.
- Do not assume hosted rooms, participant node attachment, Shared Room KB, or cross-node document handoff are implemented from planning docs alone.

## Active blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains high-blast-radius and trust-policy sensitive.
- Graph-write enablement stays outside the default release promise.
- New docs-only contracts and bridge proofs are guidance only until runtime proof lands on `main`.

## This week’s priorities
1. Keep supported-profile, health, and catalog surfaces aligned on `main`.
2. Preserve proof for chat, upload, retrieval, and OpenAI import paths.
3. Keep Guardian bridge proof separated from shipped runtime claims.
4. Keep legacy config compatibility narrow and clearly labeled.
5. Recheck blocker status only when `main` moves.

## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
- [x] The current `main` tip includes a supported local runtime preset for Whoosh'd.
- [x] Chat completion, upload -> embed -> readback, and workspace-local retrieval are in the supported claim set.
- [x] OpenAI export import and Task Prompt Archive are documented as present on `main`.
- [ ] Queue, config, delegation, and federation risks stay explicitly documented and rechecked when the supported path drifts.
- [ ] Legacy `AI_BACKEND` compatibility must not be mistaken for a new supported contract.
- [ ] New docs-only contracts and bridge proofs must stay out of the supported runtime claim set until proven on `main`.
- [ ] Any new release claim needs fresh proof on `main`, not branch-local evidence.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence and invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
