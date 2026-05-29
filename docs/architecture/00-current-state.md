## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-05-29

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. Recent `main` changes improved chat context behavior, widened local provider catalog metadata, and added a site-ready developer-guide export bundle, but they do not widen the release promise.

## What changed recently
- `main` fixed chat context assembly and enabled memory preselection in chat completion.
- `main` added Whooshd local provider catalog metadata.
- `main` added a site-ready developer-guide export bundle under `docs/site-export/developer-guide/`.
- Supported-profile, health, and catalog surfaces remain aligned on the local-only stack.
- Personal-facts settings routing remains repaired on `main`.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- Health checks report LLM model availability.
- Chat completion works on the supported path and persists back into the source thread.
- Upload -> embed -> readback works on the supported path.
- Workspace-local Obsidian retrieval is supported on the current tip.
- Coding results return through Guardian into the source thread on the supported path.
- Graph writes remain default-off on the supported Compose path.
- The release-truth override at `docs/architecture/00-current-state.md` is the live interpretation layer for this week.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume command bus, delegation, federation, or graph write surfaces are part of the present release promise.
- Do not assume the Guardian Retrieval Navigation Model, adaptive route hints, reviewable graph evolution proposals, or self-improving memory are shipped runtime features.
- Do not assume the site-export bundle changes runtime support or release readiness.
- Do not assume the local-model draft adapter is connected to Heartbeat, publishing, scheduling, command dispatch, or release approval.
- Do not assume UI dispatch, lease allocation, live agent execution, or merge automation are release-proven.
- Do not infer desktop packaging readiness from architecture docs alone.

## Active blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- Legacy `/tools` behavior still overlaps with the command bus.
- Sync subscriptions are still process-local rather than durable across restarts.
- Federation remains a high-blast-radius area with trust-policy and egress sensitivity.

## This week's priorities
1. Keep the supported profile, health, and catalog surfaces aligned on `main`.
2. Preserve fresh proof for chat, upload, retrieval, and coding-result return paths.
3. Keep internal-only surfaces labeled as such and out of the release promise.
4. Keep the release-truth docs in sync with the live `main` posture.
5. Avoid widening supported beta claims until a new merged capability is proven end to end.

## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
- [x] Fresh live evidence exists on the current `main` tip for the supported path.
- [x] Chat completion, upload -> embed -> readback, and workspace-local retrieval are proven on the supported stack.
- [x] Coding results return through Guardian into the source thread.
- [x] No internal-only or quarantined surface is part of the release claim.
- [ ] Queue, config, sync, and federation risks must stay explicitly documented and rechecked when the supported path drifts.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
