## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-05-16

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify remains in local-first beta hardening on `main`. The supported path is still the local Docker Compose stack with the local-only provider posture, and the current release focus is preserving the shipped proof surface rather than widening the promise. On `main`, the supported profile, health, catalog, coding-result return path, and workspace-local Obsidian retrieval claims remain the validated runtime facts; the recent repo activity is mostly architecture-doc expansion around Flow Builder contracts, not a new release surface.

## What changed recently
- `main` added a read-only Heartbeat status route (`GET /api/heartbeat/status`) and a Heartbeat lens in Agent Command Center.  Execution, scheduling, and publishing remain manual and deferred.
- `main` added `flow-builder-testrun-activation-contract.md`.
- `main` added `flow-builder-runreceipt-persistence-model.md`.
- `main` also resolved a current-state merge and kept the override doc in sync with the KB map.
- No new shipped runtime surface landed with those docs-only changes.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported beta posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- The supported profile is loaded in the live Compose backend, and `/health`, `/health/chat`, `/api/health/llm`, and `/api/llm/catalog` agree on the active local-only beta posture.
- Chat completion works on the supported path and persists back into the source thread.
- Upload -> embed -> readback works on the supported path after the document detail route repair.
- Workspace-local Obsidian retrieval now works on the supported path and the worker-visible completion payload is the canonical proof surface.
- Supported-profile, health, and catalog surfaces are aligned on the current `main` tip; `/api/llm/catalog` stays local-only by default while `?include=all` remains diagnostic-only for unauthorized or unavailable cloud providers.
- Image-turn containment on the supported profile remains proven by the latest live proof.
- Graph writes remain default-off on the supported Compose path.
- Command Center now has a live-proofed non-dispatch worker-control panel for coding work-order visibility, create/cancel, and recommendation-only next-task inspection (`docs/proofs/2026-05-10-command-center-worker-control-plane-live-proof-rerun-after-null-safety-repair.md`).
- `main` now also shows a runner supervision summary inside Agent Command, but that is a UI/control-plane refinement, not a broader release expansion.
- Campaign Runner MVP control-plane spine exists on backend surfaces for goal/campaign representation and durable execution-attempt ledger evidence, while remaining recommendation-only for next-work selection.
- Agent Command Center can now display read-only Heartbeat pipeline status via the `GET /api/heartbeat/status` route and the Heartbeat lens in Command Center.  This surfaces the latest local heartbeat date, review status, outbox status, and publication-disabled posture without adding execution, scheduling, or publishing.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume command bus, delegation, federation, or graph write surfaces are part of the present release promise.
- Do not assume successful Codex adapter completion: the live proof terminal run ended `failed` because the adapter timed out, even though Guardian delivery and terminal-state behavior passed.
- Do not assume UI dispatch, lease allocation, live MiniMax/Codex execution, or merge automation are release-proven; the worker-control Command Center seam is recommendation-only and non-dispatch.
- Do not assume Flow Builder planning docs imply a shipped runtime Flow Builder release surface.
- Do not infer desktop packaging readiness from architecture docs alone.

## Active blockers
- No active supported-profile/catalog/health blocker remains on the current `main` tip.
- Future runtime changes still require fresh proof if the supported profile, catalog, or health surfaces drift again.

## This week's priorities
1. Keep the supported-profile health and catalog surfaces aligned on the current `main` tip.
2. Keep the fresh workspace-local Obsidian proof evidence attached to the current release claim and refresh it if the runtime drifts.

## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
- [x] Fresh live evidence exists on the current `main` tip for the supported path.
- [x] Chat completion and upload -> embed -> readback are proven on the supported stack.
- [x] Coding results return through Guardian into the source thread without duplicate delivery.
- [x] Workspace-local Obsidian retrieval has fresh current-tip proof that survives supersession review.
- [x] No internal-only or quarantined surface is part of the release claim.

Release checklist is complete on current evidence.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
