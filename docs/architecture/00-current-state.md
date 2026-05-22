## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-05-22

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. Recent `main` work focused on release-adjacent truth surfaces: heartbeat review fixes, KB organization for cognition specs, Guardian retrieval navigation docs, and execution-ledger gate metadata storage.

## What changed recently
- Heartbeat review findings were fixed on `main`.
- Organizational cognition specs were classified into the KB matrix.
- Guardian retrieval navigation docs landed on `main`.
- Execution-ledger gate metadata storage landed on `main`.
- Daily audit artifacts were refreshed around the current `main` tip.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- Supported-profile, health, catalog, and heartbeat review surfaces are aligned on `main`.
- Chat completion works on the supported path and persists back into the source thread.
- Upload -> embed -> readback works on the supported path.
- Workspace-local Obsidian retrieval is supported on the current tip.
- Image-turn containment remains proven on the supported profile.
- Coding results return through Guardian into the source thread on the supported path.
- Command Center exposes non-dispatch worker-control visibility and recommendation-only next-task inspection.
- Heartbeat status is readable in Agent Command Center; polling is gated by `CODEXIFY_ENABLE_HEARTBEAT_ROUTES`.
- Execution, scheduling, and publishing remain off this path.
- Graph writes remain default-off on the supported Compose path.
- The local-model draft adapter is an internal/manual artifact lane only.
- KB organization now includes an explicit Cognition/spec classification lane.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume command bus, delegation, federation, or graph write surfaces are part of the present release promise.
- Do not assume Codex Entry draft/save work is a general release promise beyond the surfaced endpoints and filters on `main`.
- Do not assume portal publishing, heartbeat gating, or KB cleanup means the broader release story is complete.
- Do not assume UI dispatch, lease allocation, live agent execution, or merge automation are release-proven.
- Do not infer desktop packaging readiness from architecture docs alone.
- Do not assume organizational cognition specs imply a new runtime capability.

## Active blockers
- No current supported-path blocker is proven on `main`.
- Chat completion still depends on Redis and worker health, so runtime stalls remain a release risk.
- Legacy config paths still coexist, so startup and operator state can drift if the supported profile is not kept aligned.
- Heartbeat route coverage is now a release dependency for operator visibility, so regressions there are a readiness risk.

## This week’s priorities
1. Keep the supported profile, health, catalog, and heartbeat surfaces aligned on `main`.
2. Preserve fresh proof for the supported path when runtime behavior changes.
3. Keep internal-only surfaces labeled as such and out of the release promise.

## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
- [x] Fresh live evidence exists on the current `main` tip for the supported path.
- [x] Chat completion, upload -> embed -> readback, and workspace-local retrieval are proven on the supported stack.
- [x] Coding results return through Guardian into the source thread.
- [x] No internal-only or quarantined surface is part of the release claim.
- [x] Heartbeat review surfaces are gated and mapped without widening the release promise.
- [ ] Runtime proof must be refreshed whenever the supported path drifts.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
