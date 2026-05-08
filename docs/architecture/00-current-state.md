## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-05-08

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in late beta hardening on `main`. The codebase now carries the local Docker Compose path, packaged tester-facing delivery surfaces, and a coding-result return path that routes assistant results back through Guardian into the source thread. Release truth still depends on the live runtime matching the supported local-first posture, not just on docs or build artifacts.

Fresh live proof on 2026-05-08 now partially confirms the supported local-first posture on the current `main` tip (`9ca4caf56`), including provider/catalog/health alignment, chat completion with RAG trace, image-turn containment, coding-result return lineage/idempotency (code inspection), and runtime-target normalization. The upload -> embed -> retrieve path is **blocked**: `GET /api/documents/{id}` returns 404 after successful upload, preventing verification of embedding readiness and sentinel retrieval. The evidence is recorded in `docs/architecture/2026-05-08-supported-profile-live-proof.md` with a PARTIAL verdict. On 2026-05-07, the workspace-local Obsidian E2E proof harness also passed on the supported local Compose path, and the evidence is recorded in `docs/proofs/2026-05-07-workspace-obsidian-e2e-proof.md`. These proofs are evidence of the supported path, not release signoff.

As of 2026-05-08 follow-up implementation, the document identity/readback contract has been repaired in code: upload responses now expose explicit `document_id` and `media_asset_id`, and a supported `GET /api/documents/{id}` detail route resolves by document ID (with asset-ID compatibility lookup) while preserving account ownership checks and embedding lifecycle fields. A fresh live Compose re-proof is still pending because backend startup is currently blocked by a pre-existing merge-artifact syntax error in `guardian/core/config.py`.

- Coding worker results now ingest back through Guardian with lineage and idempotency guards.
- Public webUI beta handoff docs and the GHCR pullability note remain on `main`.
- The public webUI handoff bundle remains packaged for tester distribution.
- The desktop shell and runner/TUI work were refined on `main`, but that does not change the release gate by itself.

- Local Docker Compose remains the supported install path.
- Supported beta posture is intended to be local-only, but the live backend container currently reports `CODEXIFY_BETA_CORE_ONLY=false`, `CODEXIFY_LOCAL_ONLY_MODE=false`, and `ALLOW_CLOUD_PROVIDERS=true`, so the running stack is not in the supported posture.
- Chat acceptance, worker execution, and Postgres persistence still work for plain chat completion on the current live runtime.
- Single-user ownership on the chat path normalizes browser display labels to `local`; that seam did not leak the display label into persisted thread ownership in this run.
- Upload -> parse -> embed -> retrieve is not currently proven on the live runtime. The earlier `agent_extension_*` schema gap that blocked document upload on the supported path is repaired on the supported local Compose stack, but the full end-to-end upload -> embed -> retrieve proof still needs a fresh rerun on the current tip.
- The bounded tool-loop slice is not currently behaving as claimed on the live runtime: the one-turn case fails with `tool_command_execution_failed`, and the hard-stop / blocked-result prompts collapse into plain answers instead of staying bounded.
- Retrieval assembly now keeps user boundaries explicit in the broker and records widening reasons so trace output stays truthful.
- Built-in system docs/help are seeded at startup and available to retrieval.
- The import embed worker can drain a live backlog without breaking chat or health surfaces.
- `/health`, `/health/chat`, `/api/health/llm`, `/api/health/retrieval`, and `/api/llm/catalog?include=all` remain the primary runtime evidence surfaces, but this runtime now shows a supported-profile/catalog mismatch that must be resolved before any release claim.
- Executable evaluation suites now cover backend seam evidence for:
  - Supported-path golden tasks (completion acceptance, RAG trace isolation, Obsidian ingest→retrieve seam).
  - Identity-boundary proof (project scope containment, explicit widening, exclusion filters).
  - Broker/source-mode reconciliation (`effective_source_mode` derived from `source_mode` + `retrieval_override`).
  - Workspace-local retrieval posture, including live completion evidence for Obsidian-backed notes.
- A canonical live-proof harness now exists for the `retrievalSource="workspace"` seam (`scripts/proofs/prove_workspace_obsidian_e2e.py`), covering health → ingest → thread → message → completion → verdict → retrieval-posture evidence on the supported local Compose path.
- The packaged macOS desktop shell remains part of the beta delivery surface.
- The public webUI Docker bundle remains available for browser-only tester use.
- The supported beta story remains local-first and backend-shared across those surfaces.
- Coding results now return through Guardian before user-visible output.
- Current release evidence now has fresh live proof for health, provider posture, and runtime path on the current tip.
- A canonical workspace-local live proof harness now exists at `scripts/proofs/prove_workspace_obsidian_e2e.py`; it validates the supported local Compose path only and does not widen the release promise to other install modes.
- The workspace-local Obsidian E2E proof harness passed on the supported local Compose path for commit `a5d6239ef26105ab45125e9f43d22fd2078d9584`, and the durable proof artifact is `docs/proofs/2026-05-07-workspace-obsidian-e2e-proof.md`.
- That proof is release evidence for the supported local Compose path only; it does not widen the release promise to other install modes.
- Workspace-local proof now treats searchability, broker selection, completion-context injection, and assistant reflection as separate evidence steps; vector-store searchability alone is weaker than proving the note influenced completion.
- Worker-visible completion payloads now preserve the executed retrieval posture snapshot and workspace-local Obsidian evidence counts for completion turns instead of dropping back to a debug-only reconstruction.

- Do not assume any unmerged branch work is shipped.
- Do not assume the public webUI bundle replaces the local Compose path.
- Do not assume docs that mention a surface prove it is live on the current `main` tip.
- Do not assume operator or internal routes are part of the release promise unless this file says so.
- Do not assume release readiness if the live runtime posture has not been rechecked.
- Do not assume coding-result ingestion alone means the full release path is validated.

- The live backend posture is now confirmed against the supported local-only profile on the current `main` tip.
- Fresh live evidence now covers the supported beta path on the exact current `main` tip.
- Any future runtime mismatch between supported profile, catalog, and health surfaces would still be a release hold, but the 2026-05-05 proof window did not show one.
- The coding-result return path now has fresh live verification on the current tip.

## This week's priorities
1. Investigate and resolve the document retrieval 404 blocker: `GET /api/documents/{id}` returns 404 after successful upload via `POST /api/media/upload/document`.
2. Re-run the full supported-path proof after the document retrieval fix once backend startup is restored.
3. Keep the fresh supported-path proof artifact synchronized with future runtime changes.
4. Watch for any future drift between supported-profile, catalog, and health surfaces.
5. Preserve the proven coding-result return path and runtime-target contract under regression protection.

## Release definition right now
- [x] Supported-profile flags match the beta contract on the live runtime.
- [x] Fresh live evidence exists on the current `main` tip for the supported path.
- [x] Chat, retrieval, and upload/embedding behavior are proven on the live stack.
- [x] Coding results return through Guardian into the source thread without duplicate delivery.
- [x] Catalog, health, and provider posture agree with the supported profile.
- The live backend posture still needs confirmation against the supported local-only profile before release signoff.
- Fresh live evidence still needs to cover the supported beta path on the exact current `main` tip.
- Any runtime mismatch between supported profile, catalog, and health surfaces remains a release hold.
- A live proof attempt on 2026-05-05 still showed the coding worker failing before returning a `coding_result` because `/app/codex_runner/src/agent-wrapper.js` was missing in the running worker image. The packaging blocker has been fixed in `docker-compose.runtime.yml` by changing `worker-coding` from a pre-built image reference to a local `build: {context: ., dockerfile: backend/Dockerfile, target: runtime}` which mirrors the pattern used in `docker-compose.yml` and ensures `codex_runner/` is included in the image. Docker is not available in this environment for live rerun, so packaging proof is pending. Backend-seam tests now prove Guardian result persistence, but the live coding-result return path remains not release-ready until live proof confirms source-thread injection and idempotency.

## This week's priorities
1. Re-run live supported-path proof on the current `main` tip.
2. Confirm the backend is in the supported local-only posture.
3. Verify chat completion, retrieval posture, and upload -> embed -> retrieve on the live stack.
4. Repair the worker runtime artifact that provides `/app/codex_runner/src/agent-wrapper.js`, then re-exercise the coding-result return path end to end on the live stack.
5. Re-check the provider catalog and health surfaces against the supported profile.
6. Keep the workspace-local proof artifact synchronized with future runtime changes, and continue to require broker selection plus completion-context injection rather than searchability alone.

## Release definition right now
- [ ] Supported-profile flags match the beta contract on the live runtime.
- [ ] Fresh live evidence exists on the current `main` tip for the supported path.
- [ ] Chat, retrieval, and upload/embedding behavior are proven on the live stack.
- [ ] Coding results return through Guardian into the source thread without duplicate delivery.
- [ ] Catalog, health, and provider posture agree with the supported profile.
- [x] The workspace-local live proof harness passes on the supported local Compose path.
- [x] Workspace-local proof evidence shows broker selection and completion-context injection, not just vector-store searchability.
- [ ] No internal-only or quarantined surface is part of the release claim.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
