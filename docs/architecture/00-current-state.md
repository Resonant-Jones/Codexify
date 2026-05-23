## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-05-23

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. Recent `main` work stayed focused on release-truth maintenance, architecture consolidation, and export workflow plumbing rather than widening the supported runtime surface.

## What changed recently
- `main` picked up a core export sync workflow refactor in the frontend lockfile.
- The core export sync script now includes `backend/` in the export set.
- Guardian Build Loop doctrine was consolidated into the architecture KB as architecture consolidation only; it does not add autonomous runtime behavior, weaken human review, or widen release scope.
- The current-state override and README doc map were refreshed on `main`.
- A Unity Audit scaffold and coherence doctrine landed in the architecture layer as governance framing only; it does not claim new runtime implementation.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- Supported-profile, health, and catalog surfaces are aligned on `main`.
- Chat completion works on the supported path and persists back into the source thread.
- Upload -> embed -> readback works on the supported path.
- Workspace-local Obsidian retrieval is supported on the current tip.
- Image-turn containment remains proven on the supported profile.
- Coding results return through Guardian into the source thread on the supported path.
- Graph writes remain default-off on the supported Compose path.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume command bus, delegation, federation, or graph write surfaces are part of the present release promise.
- Do not assume the Guardian Retrieval Navigation Model, adaptive route hints, reviewable graph evolution proposals, or self-improving memory are shipped runtime features. The new retrieval navigation note is planning doctrine only, does not expand the supported release surface, and does not change the current graph-writes-default-off boundary.
- Do not assume UI dispatch, lease allocation, live agent execution, or merge automation are release-proven.
- Do not treat architecture-only doctrine additions, including Guardian Build Loop consolidation docs, as proof of autonomous self-build, auto-merge, push, release readiness, or broader coding-worker support than current supported-path evidence proves.
- Do not assume the core export sync workflow changes, `Publishing_Portal/Core/` source mirrors, or generated source bundles broaden runtime support or provide release readiness evidence.
- Do not assume draft or local-only artifacts, including the local-model draft adapter, are shipped behavior or connected to Heartbeat, publishing, scheduling, command dispatch, or release approval.
- Do not infer desktop packaging readiness from architecture docs alone.

## Active blockers
- No current supported-path blocker is proven on `main`.
- Chat completion still depends on Redis and worker health, so runtime stalls remain a release risk.
- Legacy config paths still coexist, so startup and operator state can drift if the supported profile is not kept aligned.

## This week’s priorities
1. Keep the supported profile, health, and catalog surfaces aligned on `main`.
2. Preserve fresh proof for the supported path when runtime behavior changes.
3. Keep internal-only surfaces labeled as such and out of the release promise.
4. Maintain release-truth docs as the weekly override layer.
5. Keep Unity Audit and Guardian Build Loop consolidation explicitly docs/governance-only, without changing runtime behavior or release-scope truth.

## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
- [x] Fresh live evidence exists on the current `main` tip for the supported path.
- [x] Chat completion, upload -> embed -> readback, and workspace-local retrieval are proven on the supported stack.
- [x] Coding results return through Guardian into the source thread.
- [x] No internal-only or quarantined surface is part of the release claim.
- [ ] Runtime proof must be refreshed whenever the supported path drifts.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
