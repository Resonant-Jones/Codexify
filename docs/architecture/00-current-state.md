## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-06-21

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. Recent merged work now includes OpenAI export import into chat history and a native task prompt archive, but it does not widen the release promise.

## What changed recently
- `main` imported OpenAI export conversations into chat history.
- `main` added a native Task Prompt Archive representation.
- `main` added OpenAI export artifact catalog and reconciliation passes.
- `main` added OpenAI export workspace protections and import diagnostics.
- `main` preserved the local-only beta posture and current-state override pattern.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- `AI_BACKEND=local` is accepted only as legacy compatibility.
- `LOCAL_RUNTIME_PRESET` selects `whooshd-mlx`, `ollama`, `lmstudio`, or `custom-openai-compatible` under the same local provider boundary.
- Whoosh'd remains the supported Apple Silicon local runtime preset.
- Whoosh'd local runtime config is standardized across setup and compose surfaces.
- OpenAI export import into chat history is on `main`.
- Task Prompt Archive exists as a native Codexify representation on `main`.
- Live model availability is still proven only by inventory from `/v1/models` or `/api/tags`.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` remain the fastest runtime checks.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval remain the supported beta paths.
- Graph writes remain default-off on the supported Compose path.
- Guardian work-order briefing exists on `main`, but it is operator support material, not a widened runtime promise.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume delegation, federation, or graph write surfaces are part of the present release promise.
- Do not assume docs-only exports, scaffolds, prompt artifacts, or brief-generation output prove runtime support.
- Do not assume OpenAI export import means general third-party sync is supported.
- Do not assume Task Prompt Archive means full workflow authoring or execution support.
- Do not assume Whoosh'd setup equals live provider reachability without endpoint/model inventory proof.
- Do not infer a wider beta claim from the new local preset wiring alone.
- Do not assume the Gemma E2B smoke default is itself live-model proof.
- Do not assume legacy `AI_BACKEND` config is the preferred runtime contract.
- Do not assume Guardian work briefs imply shipped executor capabilities.

## Active blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains high-blast-radius and trust-policy sensitive.
- Graph-write enablement stays outside the default release promise.
- OpenAI import coverage is new and still needs ongoing regression proof.

## This week’s priorities
1. Keep supported-profile, health, and catalog surfaces aligned on `main`.
2. Preserve proof for chat, upload, retrieval, and OpenAI import paths.
3. Keep legacy config compatibility narrow and clearly labeled.
4. Keep delegation, federation, and graph-write work explicitly out of the release promise until proven.
5. Keep the release-truth docs synced with the live `main` posture.

## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
- [x] The current `main` tip includes a supported local runtime preset for Whoosh'd.
- [x] Fresh live evidence exists on the current `main` tip for the supported path.
- [x] Chat completion, upload -> embed -> readback, and workspace-local retrieval are in the supported claim set.
- [x] OpenAI export import and Task Prompt Archive are documented as present on `main`.
- [ ] Queue, config, delegation, and federation risks must stay explicitly documented and rechecked when the supported path drifts.
- [ ] Legacy `AI_BACKEND` compatibility must not be mistaken for a new supported contract.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
