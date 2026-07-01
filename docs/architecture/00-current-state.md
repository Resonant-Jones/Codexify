## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-06-30

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. Recent merged work is concentrated on docs-first operator routing, turn-intake doctrine, and quarantined continuity proof, not on widening the supported beta surface.

## What changed recently
- `main` added the machine-readable Turn Intake fixture projection and refreshed turn-intake contract docs.
- `main` added `docs/feedback` issue forms and a passive assistant intake guide.
- `main` refined Persona Studio controls and federation routing.
- `main` adopted the Codexify source-available license and refreshed the README banner.
- `main` merged the weekly current-state override refresh from the prior audit.
- `main` kept the six-route Continuity operator proof chain quarantined behind `test-continuity`.
- `main` added a docs-only Turn Intake Compiler Contract, Fixture Pack, Token Domain Proposal, and machine-readable fixture projection.
- `main` added a Guardian operator index to route operator questions to the right docs and checks.
- `main` refreshed collaborator onboarding docs and linked them into the architecture KB front door.
- `main` added a collab chat identity contract as docs-only guidance, not shipped runtime support.
- `main` added docs-only chat transport visibility and adaptive stream recovery semantics alongside the chat runtime contract.
- `main` surfaced personal-facts guardrails and Scout operator-surface docs in the KB.
- `main` merged a Whoosh'd inventory source fix and launcher/model-environment cleanup.
- `main` completed the six-route Continuity operator proof chain, but kept it quarantined behind `test-continuity`.
- `main` tightened continuity docs to state the phase is complete but not beta-supported.

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

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume docs-only contracts mean shipped runtime support.
- Do not assume the Turn Intake fixture projection means a live classifier, router, or prompt builder exists.
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

## Active blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains high-blast-radius and trust-policy sensitive.
- Graph-write enablement stays outside the default release promise.
- The new turn-intake docs are guidance only; the runtime classifier/intake pipeline and machine-readable projection are still not release-proven.

## This week’s priorities
1. Keep supported-profile, health, and catalog surfaces aligned on `main`.
2. Preserve proof for chat, upload, retrieval, and OpenAI import paths.
3. Keep the Zac Mac Studio bring-up path aligned with the supported local posture.
4. Keep legacy config compatibility narrow and clearly labeled.
5. Keep docs-only contract work separate from shipped runtime claims.

## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
- [x] The current `main` tip includes a supported local runtime preset for Whoosh'd.
- [x] Fresh live evidence exists on the current `main` tip for the supported path.
- [x] Chat completion, upload -> embed -> readback, and workspace-local retrieval are in the supported claim set.
- [x] OpenAI export import and Task Prompt Archive are documented as present on `main`.
- [x] The Zac Mac Studio bring-up path is documented without widening the release promise.
- [ ] Queue, config, delegation, and federation risks must stay explicitly documented and rechecked when the supported path drifts.
- [ ] Legacy `AI_BACKEND` compatibility must not be mistaken for a new supported contract.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence and invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
