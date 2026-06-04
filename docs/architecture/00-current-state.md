## Purpose
This file is Codexify's canonical short-form source of truth for the current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-06-03

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. Recent `main` changes improved operator visibility, added a site-ready documentation export bundle, and moved the local inference target to a Whoosh'd/OpenAI-compatible endpoint, but they do not widen the release promise.

## What changed recently
- `main` added a site-ready developer guide export bundle under `docs/site-export/developer-guide/`.
- `main` moved the supported local provider endpoint defaults from Ollama to Whoosh'd/OpenAI-compatible `LOCAL_BASE_URL=http://host.docker.internal:8000/v1`.
- Health checks still surface LLM model availability on the supported path.
- Supported-profile, health, and catalog surfaces remain aligned on the local-only stack.
- Personal-facts settings routing remains repaired on `main`.
- GuardianChat still surfaces runtime visual state in the shell.
- Internal/manual local-model draft adapter work remains present, but not a release promise.
- Build Proposal artifacts now have a doctrine/scaffold surface for reviewable
  Guardian Build Loop task candidates; proposal generation remains draft-only
  and does not imply approval, execution, release support, runtime proof, or
  autonomous self-modification.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- The current local inference target is Whoosh'd/OpenAI-compatible, with live model availability proven only when `/v1/models` or `/api/tags` advertises the selected local model.
- Health checks report LLM model availability.
- Chat completion works on the supported path and persists back into the source thread.
- Upload -> embed -> readback works on the supported path.
- Workspace-local Obsidian retrieval is supported on the current tip.
- Coding results return through Guardian into the source thread on the supported path.
- Graph writes remain default-off on the supported Compose path.
- Provider timeout and slow-path failures are classified and presented more accurately in the UI.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume command bus, delegation, federation, or graph write surfaces are part of the present release promise.
- Do not assume the Guardian delegation loop contract means the end-to-end delegation loop is shipped.
- Do not assume the Guardian Retrieval Navigation Model, adaptive route hints, reviewable graph evolution proposals, or self-improving memory are shipped runtime features.
- Do not assume the local-model draft adapter is connected to Heartbeat, publishing, scheduling, command dispatch, or release approval.
- Do not assume UI dispatch, lease allocation, live agent execution, or merge automation are release-proven.
- Do not assume Guardian Build Loop doctrine means autonomous self-modification, auto-merge, push, or release-ready coding-worker behavior.
- Do not assume Build Proposal generation means approval, execution, release
  support, runtime proof, or autonomous self-modification.
- Do not assume Whoosh'd runtime availability without live endpoint/model inventory proof.
- Do not infer desktop packaging readiness from architecture docs alone.
- Do not infer a wider release promise from docs-only exports, scaffolds, or audit artifacts.

## Active blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- Legacy `/tools` behavior still overlaps with the command bus.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains a high-blast-radius area with trust-policy and egress sensitivity.
- Docs-heavy merged work does not remove the need to recheck runtime proof on the supported path.

## This week’s priorities
1. Keep the supported profile, health, and catalog surfaces aligned on `main`.
2. Preserve fresh proof for chat, upload, retrieval, and coding-result return paths.
3. Keep delegation, federation, and graph-write work explicitly out of the release promise until proven.
4. Keep the release-truth docs in sync with the live `main` posture.
5. Avoid widening supported beta claims until a new merged capability is proven end to end.

## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
- [x] Fresh live evidence exists on the current `main` tip for the supported path.
- [x] Chat completion, upload -> embed -> readback, and workspace-local retrieval are proven on the supported stack.
- [x] Coding results return through Guardian into the source thread.
- [x] No internal-only or quarantined surface is part of the release claim.
- [ ] Queue, config, delegation, and federation risks must stay explicitly documented and rechecked when the supported path drifts.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
