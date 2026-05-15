## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-05-15

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. The supported path is the local Docker Compose stack, the live runtime still uses the local provider posture, and release work is centered on keeping the shipped stack honest under fresh proof rather than widening the promise surface. The supported live coding-result proof, the workspace-local Obsidian retrieval proof, and the supported-profile/catalog/health proof now pass on the current `main` tip: Guardian returns a bounded source-thread `coding_result`, replay stays idempotent, the durable run record converges to a terminal state even when the adapter itself times out, workspace-local Obsidian evidence is selected and injected into the executed completion path, and the supported profile is loaded into the live Compose backend with aligned health/catalog truth.

## What changed recently
- `main` added a Command Center runner supervision summary to Agent Command.
- The latest supported-profile proof now anchors the live beta claim to local-only provider posture, chat completion, image containment, runtime-target alignment, and aligned supported-profile/catalog/health truth on the supported Compose path.
- Document upload/readback remains part of the supported-path evidence after the document identity repair.
- Workspace-local Obsidian retrieval is now live-proven on the current `main` tip: the supported proof showed searchable workspace notes, worker-visible Obsidian selection/injection, assistant reflection of the sentinel, and a debug trace that stayed diagnostic-only.
- The supported live coding proof now shows source-thread `coding_result` delivery, bounded duplicate-free replay, terminal event evidence, and durable terminal run-state convergence. The run's terminal status was `failed` because the Codex adapter timed out, which is acceptable for the control-plane proof but does not prove adapter success.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported beta posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- The supported profile is loaded in the live Compose backend, and `/health`, `/health/chat`, `/api/health/llm`, and `/api/llm/catalog` now agree on the active local-only beta posture.
- Chat completion works on the supported path and persists back into the source thread.
- Upload -> embed -> readback works on the supported path after the document detail route repair.
- Workspace-local Obsidian retrieval now works on the supported path and the worker-visible completion payload is the canonical proof surface.
- Supported-profile, health, and catalog surfaces are aligned on the current `main` tip; `/api/llm/catalog` stays local-only by default while `?include=all` remains diagnostic-only for unauthorized or unavailable cloud providers.
- Image-turn containment on the supported profile remains proven by the latest live proof.
- Graph writes remain default-off on the supported Compose path.
- Command Center has a live-proofed non-dispatch worker-control panel for work-order visibility, create/cancel, and recommendation-only next-task inspection.
- `main` now also shows a runner supervision summary inside Agent Command, but that is a UI/control-plane refinement, not a broader release expansion.
- The supported live coding-worker proof now shows exactly one bounded `coding_result` message injected into the source thread, safe-replay idempotency, and durable terminal `failed` state convergence on the Guardian control plane.
- Campaign Runner MVP control-plane spine exists on backend surfaces for goal/campaign representation and durable execution-attempt ledger evidence, while remaining recommendation-only for next-work selection.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume command bus, delegation, federation, or graph write surfaces are part of the present release promise.
- Do not assume successful Codex adapter completion: the live proof terminal run ended `failed` because the adapter timed out, even though Guardian delivery and terminal-state behavior passed.
- Do not assume UI dispatch, lease allocation, live MiniMax/Codex execution, or merge automation are release-proven; the worker-control Command Center seam is recommendation-only and non-dispatch.
- Do not assume the Agent Command runner supervision summary changes the supported release promise; it is an operator-facing summary, not proof of a wider execution contract.

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
