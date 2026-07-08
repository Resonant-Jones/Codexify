## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-07-02

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. `main` is stable at the current release-truth point; the last week added no new shipped runtime surface that changes the supported beta story.

## What changed recently
- No material `main`line changes since the prior weekly audit.
- The release-truth docs and operator routing stayed stable.
- Docs-only contracts remain docs-only; no new runtime proof landed on `main`.
- The current Guardian bridge branch now includes an unexposed backend JSON-only adapter seam for Guardian Codex Runner preflight validation; it does not add UI integration, API routes, command-bus invocation, Pi Loop invocation, Codexify ingestion, source mutation, or durable mutation.
- Continuity remains quarantined behind `test-continuity`.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported posture remains local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- `AI_BACKEND=local` is legacy compatibility only.
- `LOCAL_RUNTIME_PRESET` still selects `whooshd-mlx`, `ollama`, `lmstudio`, or `custom-openai-compatible` under the local provider boundary.
- Whoosh'd remains the supported Apple Silicon local runtime preset.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval remain the supported beta paths.
- OpenAI export import and Task Prompt Archive are present on `main`.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` remain the fastest runtime checks.
- Graph writes remain default-off on the supported Compose path.
- The Continuity operator surface is test-only, API-key-gated, and profile-quarantined under `test-continuity`.
- Shared Presence, chat transport recovery, and thread lenses are docs-only contracts, not supported runtime surfaces.
- `main` currently matches the prior release-readiness state; no new supported surface was added this week.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume docs-only contracts mean shipped runtime support.
- Do not assume the Turn Intake fixture projection means a live classifier, router, or prompt builder exists.
- Do not assume shared presence, chat transport recovery, or thread lenses are shipped runtime behavior.
- Do not assume the collab chat identity contract or personal-facts guardrails are release-proven runtime behavior from docs alone.
- Do not assume chat transport visibility or adaptive stream recovery semantics are already emitted as live runtime behavior from docs alone.
- Do not assume Scout/iOS contract docs mean shipped Scout runtime support.
- Do not assume the Turn Intake Compiler contract means a live runtime intake classifier, action router, retrieval-router integration, or model-prompt packet builder is implemented.
- Do not assume the Turn Intake Fixture Pack means executable tests exist.
- Do not assume the Turn Intake Token Domain Proposal means turn-intake runtime tokens, registries, or classifier behavior exist.
- Do not assume the Turn Intake machine-readable fixture projection means a runtime classifier, executable test harness, token registry, prompt packet builder, retrieval-router integration, or action-gate integration exists.
- Do not assume command bus, delegation, federation, or graph-write surfaces are part of the present release promise.
- Do not assume Thread Lenses exist as a shipped runtime organization surface; any Thread Lens language is docs-only and must not be read as project-membership mutation or supported beta behavior.
- Do not assume the Guardian delegation loop contract means the end-to-end delegation loop is shipped.
- Do not assume the Continuity operator surface is supported beta, user-facing, Project Pulse, export/restore, graph, chat runtime, worker, or command bus behavior.
- Do not infer a wider release promise from docs-only onboarding, scaffolds, or audit artifacts.
- Do not assume any local runtime is available without live endpoint/model inventory proof.
- Do not assume hosted rooms, participant node attachment, Shared Room KB, or cross-node document handoff are implemented from the Hosted Room and Sovereign Node Participation Contract; that contract is future docs-only architecture and does not widen the supported beta release surface.

## Active blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains high-blast-radius and trust-policy sensitive.
- Graph-write enablement stays outside the default release promise.
- The new turn-intake docs are guidance only; the runtime classifier/intake pipeline and machine-readable projection are still not release-proven.
- No new blocker was introduced by this week's mainline state.

## This week’s priorities
1. Keep supported-profile, health, and catalog surfaces aligned on `main`.
2. Preserve proof for chat, upload, retrieval, and OpenAI import paths.
3. Keep docs-only contracts clearly separated from shipped runtime claims.
4. Keep legacy config compatibility narrow and clearly labeled.
5. Recheck blocker status only when `main` moves.

## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
- [x] The current `main` tip includes a supported local runtime preset for Whoosh'd.
- [x] Fresh live evidence exists on the current `main` tip for the supported path.
- [x] Chat completion, upload -> embed -> readback, and workspace-local retrieval are in the supported claim set.
- [x] OpenAI export import and Task Prompt Archive are documented as present on `main`.
- [x] The Zac Mac Studio bring-up path is documented without widening the release promise.
- [ ] Queue, config, delegation, and federation risks must stay explicitly documented and rechecked when the supported path drifts.
- [ ] Legacy `AI_BACKEND` compatibility must not be mistaken for a new supported contract.
- [ ] New docs-only contracts must stay out of the supported runtime claim set until proven on `main`.
- [ ] Any new release claim needs fresh proof on `main`, not branch-local evidence.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence and invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
