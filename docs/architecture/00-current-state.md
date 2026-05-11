## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-05-10

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. The supported path is the local Docker Compose stack, the live runtime still uses the local provider posture, and the current release question is whether the shipped stack stays honest under fresh proof rather than whether the intended architecture exists in docs.

## What changed recently
- Supported-profile live proof on `main` re-validated the local-only provider posture, chat completion, image-turn containment, and runtime-target alignment.
- Document upload/readback was re-proven on the supported path after the document identity contract repair.
- The workspace-local Obsidian E2E harness remains the canonical proof path for workspace-scoped retrieval evidence.
- The coding-result return-path rerun after the packaging fix is now complete: `worker-coding` contains `/app/codex_runner/src/agent-wrapper.js`, but live runs still fail before source-thread `coding_result` injection and durable run-state convergence.
- IDDB policy governance was added as a reference doc, which affects interpretation but not the supported runtime surface.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported beta posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- `/health`, `/health/chat`, `/api/health/llm`, and `/api/llm/catalog` are the primary operator truth surfaces for the supported profile.
- Chat completion works on the supported path and persists back into the source thread.
- Upload -> embed -> readback works on the supported path after the document detail route repair.
- Graph writes remain default-off on the supported Compose path.
- Command Center now has a live-proofed non-dispatch worker-control panel for coding work-order visibility, create/cancel, and recommendation-only next-task inspection (`docs/proofs/2026-05-10-command-center-worker-control-plane-live-proof-rerun-after-null-safety-repair.md`).

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume command bus, delegation, federation, or graph write surfaces are part of the present release promise.
- Do not assume the coding-result return path is release-evidenced: the post-fix rerun still shows missing source-thread delivery and `agent_runs.status='queued'` after `task.failed`.
- Do not assume workspace-local Obsidian retrieval is release signoff without a fresh current-tip proof run.
- Do not assume UI dispatch, lease allocation, live MiniMax/Codex execution, or merge automation are release-proven; the worker-control Command Center seam is recommendation-only and non-dispatch.

## Active blockers
- The coding-result return path still fails release gates after the post-fix rerun: no source-thread `coding_result` and durable run status remains `queued`.
- The bounded tool-loop slice still regresses on the live runtime instead of staying bounded and returning blocked/tool states cleanly.
- Release signoff still depends on keeping supported-profile, catalog, and health surfaces aligned on the current tip.

## This week's priorities
1. Fix the post-rerun runtime failures in the coding-result path: Pi SDK dependency availability, durable terminal run-status writes, and source-thread `coding_result` delivery.
2. Re-check the supported-profile, catalog, and health surfaces on the current `main` tip.
3. Keep workspace-local retrieval proof separate from vector-store searchability and require completion-context influence.

## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
- [x] Fresh live evidence exists on the current `main` tip for the supported path.
- [x] Chat completion and upload -> embed -> readback are proven on the supported stack.
- [ ] Coding results return through Guardian into the source thread without duplicate delivery.
- [ ] Workspace-local Obsidian retrieval has fresh current-tip proof that survives supersession review.
- [ ] No internal-only or quarantined surface is part of the release claim.

- Do not assume any unmerged branch work is shipped.
- Do not assume the public webUI bundle replaces the local Compose path.
- Do not assume docs that mention a surface prove it is live on the current `main` tip.
- Do not assume operator or internal routes are part of the release promise unless this file says so.
- Do not assume release readiness if the live runtime posture has not been rechecked.
- Do not assume coding-result ingestion alone means the full release path is validated.
- Do not assume workspace-local Obsidian retrieval currently works end to end or is release-evidenced; current status is in progress and under active validation.

- The live backend posture is now confirmed against the supported local-only profile on the current `main` tip.
- Fresh live evidence now covers the supported beta path on the exact current `main` tip.
- Any future runtime mismatch between supported profile, catalog, and health surfaces would still be a release hold, but the 2026-05-05 proof window did not show one.
- The coding-result return path now has fresh failing live evidence on the current tip: events reach `task.failed`, but source-thread result delivery and durable terminal run status remain unresolved.

## This week's priorities
1. Keep the fresh supported-path proof artifact synchronized with future runtime changes.
2. Watch for any future drift between supported-profile, catalog, and health surfaces.
3. Preserve the proven coding-result return path and runtime-target contract under regression protection.

## Release definition right now
- [x] Supported-profile flags match the beta contract on the live runtime.
- [x] Fresh live evidence exists on the current `main` tip for the supported path.
- [x] Chat, retrieval, and upload/embedding behavior are proven on the live stack.
- [x] Coding results return through Guardian into the source thread without duplicate delivery.
- [x] Catalog, health, and provider posture agree with the supported profile.
- The live backend posture still needs confirmation against the supported local-only profile before release signoff.
- Fresh live evidence still needs to cover the supported beta path on the exact current `main` tip.
- Any runtime mismatch between supported profile, catalog, and health surfaces remains a release hold.
- A live proof attempt on 2026-05-05 still showed the coding worker failing before returning a `coding_result` because `/app/codex_runner/src/agent-wrapper.js` is missing in the running worker image; backend-seam tests now prove Guardian result persistence, but the live coding-result return path remains not release-ready.

## This week's priorities
1. Re-run live supported-path proof on the current `main` tip.
2. Confirm the backend is in the supported local-only posture.
3. Verify chat completion, retrieval posture, and upload -> embed -> retrieve on the live stack.
4. Repair the worker runtime artifact that provides `/app/codex_runner/src/agent-wrapper.js`, then re-exercise the coding-result return path end to end on the live stack.
5. Re-check the provider catalog and health surfaces against the supported profile.
6. Keep the workspace-local proof artifact synchronized with future runtime changes, and continue to require broker selection plus completion-context injection rather than searchability alone.
7. Capture fresh failing evidence, then a fresh passing run, before restoring any release-evidenced claim for workspace-local Obsidian retrieval.

## Release definition right now
- [ ] Supported-profile flags match the beta contract on the live runtime.
- [ ] Fresh live evidence exists on the current `main` tip for the supported path.
- [ ] Chat, retrieval, and upload/embedding behavior are proven on the live stack.
- [ ] Coding results return through Guardian into the source thread without duplicate delivery.
- [ ] Catalog, health, and provider posture agree with the supported profile.
- [ ] Workspace-local Obsidian retrieval has fresh current-tip live proof that survives supersession review.
- [x] Workspace-local proof evidence shows broker selection and completion-context injection, not just vector-store searchability.
- [ ] No internal-only or quarantined surface is part of the release claim.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
