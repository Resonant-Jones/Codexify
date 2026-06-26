## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-06-26

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. `main` also added collaborator onboarding docs and README entry points, but that does not widen the release promise.

## What changed recently
- `main` linked collaborator onboarding docs into the architecture README.
- `main` added collaborator-facing protocol and worktree guidance docs.
- `main` preserved the local-only beta posture and current-state override pattern.
- No merged runtime changes on `main` currently widen release support.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- `AI_BACKEND=local` is accepted only as legacy compatibility.
- `LOCAL_RUNTIME_PRESET` selects `whooshd-mlx`, `ollama`, `lmstudio`, or `custom-openai-compatible` under the same local provider boundary.
- Whoosh'd remains the supported Apple Silicon local runtime preset.
- Live model availability is still proven only by inventory from `/v1/models` or `/api/tags`.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` remain the fastest runtime checks.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval remain the supported beta paths.
- Graph writes remain default-off on the supported Compose path.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume command bus, delegation, federation, or graph write surfaces are part of the present release promise.
- Do not assume the Guardian delegation loop contract means the end-to-end delegation loop is shipped.
- Do not assume the Guardian Retrieval Navigation Model, adaptive route hints, reviewable graph evolution proposals, or self-improving memory are shipped runtime features.
- Do not assume the local-model draft adapter is connected to Heartbeat, publishing, scheduling, command dispatch, or release approval.
- Do not assume UI dispatch, lease allocation, live agent execution, or merge automation are release-proven.
- Do not assume Guardian Build Loop doctrine means autonomous self-modification, auto-merge, push, or release-ready coding-worker behavior.
- Do not assume any local runtime is available without live endpoint/model inventory proof.
- Do not infer a wider beta claim from docs-only onboarding or README links.
- Do not infer desktop packaging readiness from architecture docs alone.
- Do not infer a wider release promise from docs-only exports, scaffolds, or audit artifacts.

## Active blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains high-blast-radius and trust-policy sensitive.
- Graph-write enablement stays outside the default release promise.

## This week's priorities
1. Keep supported-profile, health, and catalog surfaces aligned on `main`.
2. Preserve proof for chat, upload, retrieval, and import paths.
3. Keep legacy config compatibility narrow and clearly labeled.
4. Keep delegation, federation, and graph-write work explicitly out of the release promise until proven.
5. Keep the release-truth docs synced with the live `main` posture.

## Release definition right now
- Supported-profile flags match the local-only beta contract.
- The current `main` tip includes a supported local runtime preset for Whoosh'd.
- Fresh live evidence exists on the current `main` tip for the supported path.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval are in the supported claim set.
- Queue, config, delegation, and federation risks stay explicitly documented and rechecked when the supported path drifts.
- Legacy `AI_BACKEND` compatibility is not mistaken for a new supported contract.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
