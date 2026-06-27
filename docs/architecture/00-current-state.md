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
Codexify is in local-first beta hardening on `main`. The supported path is still the local Docker Compose stack with local-only provider posture, and the week's merged work is mostly contract and operator-surface expansion rather than new runtime scope.

## What changed recently
- `main` added collab chat identity contract docs.
- `main` added Scout Vault operator-surface baseline docs.
- `main` added personal-facts guardrails contract docs and review UI support.
- `main` added Scout endpoint configuration and iOS Scout Vault remote contract docs.
- `main` added a Zac Mac Studio local bring-up path.
- `main` imported OpenAI export conversations into chat history and added Task Prompt Archive.
- `main` preserved the local-only beta posture and current-state override pattern.
- `main` added a six-route Continuity operator surface (write, readback, diagnostics, state readback, commit readback, link readback) as a test-only, profile-quarantined, API-key-gated operator surface under the `continuity_operator` route key. It is live-proven and regression-pinned under the `test-continuity` profile only. It **remains quarantined** from the supported beta profile `v1-local-core-web-mcp`. It does not widen the supported beta release promise.
- `main` added a thin, gated Remote Recall Search-as-RAG runtime seam under ADR-021 / Web Agent Spec v1. It implements the first provider adapter (Groq built-in web search) behind a provider-neutral boundary, a Web Evidence Intake Gate, canonical tokens, and a narrow completion-context integration that runs only on an explicit `global_search` posture. This is an implementation seam with unit-test proof only. It **remains default-off** (`REMOTE_RECALL_ENABLED=false`, `GROQ_WEB_SEARCH_ENABLED=false`) and does not widen the supported beta release promise; live Remote Recall release support still requires configured egress, credentials, and supported-path live proof.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- `AI_BACKEND=local` is accepted only as legacy compatibility.
- `LOCAL_RUNTIME_PRESET` selects `whooshd-mlx`, `ollama`, `lmstudio`, or `custom-openai-compatible` under the same local provider boundary.
- Whoosh'd remains the supported Apple Silicon local runtime preset.
- Whoosh'd local runtime config is standardized across setup and compose surfaces.
- The Zac Mac Studio bring-up path is documented on `main`.
- OpenAI export import into chat history is on `main`.
- Task Prompt Archive exists as a native Codexify representation on `main`.
- Live model availability is still proven only by inventory from `/v1/models` or `/api/tags`.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` remain the fastest runtime checks.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval remain the supported beta paths.
- Graph writes remain default-off on the supported Compose path.
- The Continuity operator surface (`continuity_operator`) lives under `test-continuity` profile with `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true` and `require_api_key`. It is test-only and quarantined from `v1-local-core-web-mcp`. It is not user-facing, not Project Pulse, not export/restore, not graph support, and not supported beta behavior.
- Guardian work-order briefing exists on `main`, but it is operator support material, not a widened runtime promise.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume the Scout/iOS contract docs mean shipped Scout runtime support.
- Do not assume personal-facts guardrails or collab chat identity contracts are release-proven runtime behavior from docs alone.
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
- Do not assume the Zac Mac Studio bring-up path is a wider deployment promise than the documented local path.
- Do not assume the Continuity operator surface is supported beta, user-facing, Project Pulse, export/restore, graph, chat runtime, worker, command bus, or list/search behavior. It is test-only and profile-quarantined.
- Do not assume Remote Recall (web search / Search-as-RAG) is part of the supported beta release promise from the runtime seam or its unit tests. The seam exists and is default-off; live release support still requires configured egress, credentials, feature flags, and supported-path live proof.

## Active blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains high-blast-radius and trust-policy sensitive.
- Graph-write enablement stays outside the default release promise.
- OpenAI import coverage and embedding deferral still need ongoing regression proof.

## This week's priorities
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
