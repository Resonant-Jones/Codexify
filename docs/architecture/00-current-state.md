## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-06-27

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify remains in local-first beta hardening on `main`. The supported path is still the local Docker Compose stack with local-only provider posture. Recent merged work is concentrated on operator-surface documentation, profile-supported runtime clarification, and quarantined continuity proof, not on widening the supported beta surface.

## What changed recently
- `main` refreshed collaborator onboarding docs and linked them into the architecture KB front door.
- `main` added a collab chat identity contract as docs-only guidance, not shipped runtime support.
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
- Live model availability is still proven only by inventory from `/v1/models` or `/api/tags`.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` remain the fastest runtime checks.
- Graph writes remain default-off on the supported Compose path.
- The Continuity operator surface is test-only, API-key-gated, and profile-quarantined under `test-continuity`.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume the collab chat identity contract or personal-facts guardrails are release-proven runtime behavior from docs alone.
- Do not assume Scout/iOS contract docs mean shipped Scout runtime support.
- Do not assume command bus, delegation, federation, or graph-write surfaces are part of the present release promise.
- Do not assume the Guardian delegation loop contract means the end-to-end delegation loop is shipped.
- Do not assume the Continuity operator surface is supported beta, user-facing, Project Pulse, export/restore, graph, chat runtime, worker, or command bus behavior.
- Do not assume any local runtime is available without live endpoint/model inventory proof.
- Do not infer a wider beta claim from docs-only onboarding or README links.
- Do not infer desktop packaging readiness from architecture docs alone.
- Do not infer a wider release promise from docs-only exports, scaffolds, or audit artifacts.
- Do not assume the legacy `AI_BACKEND` path is a new supported contract.

## Active blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains high-blast-radius and trust-policy sensitive.
- Graph-write enablement stays outside the default release promise.
- OpenAI import coverage and embedding deferral still need ongoing regression proof.

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
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
