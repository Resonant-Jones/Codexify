## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-08-26

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` is in local-first Beta hardening. Mainline contains control-plane hardening and bounded tester-stack proofs, but no fresh supported-Compose closure at the current tip. The latest NX-1 observation reached dependencies, migrations / init, model preparation, and backend Guardian import, then stopped during lifespan on local-gateway configuration coherence before healthy HTTP; the later template alignment has not been followed by a proven live rerun.

## What changed recently

- Merged tester runtime recovery, authentication, worker-readiness coverage, and one authenticated local/Gemma completion on the tester proof stack; it did not prove supported-main release readiness.
- Classified a fresh Chroma startup failure after guarded recovery; Postgres remains canonical and Chroma remains derived, with no retry, restore, or repair authorized.
- Merged Guardian-owned GitHub Watchdog control-plane preparation and canonical worker settings; qualification stopped before review receipt creation or model invocation because the required policy/model was unavailable.
- Recorded loss of the previously qualified immutable backend image and replacement of the mutable `latest` tag; deletion mechanism and actor remain unproven.
- Repaired the Pi diagnostic test seam and refreshed DLG metadata hashes; neither change established provider, OAuth, or runtime support.

## Current supported reality

- The supported install path is local Docker Compose using `v1-local-core-web-mcp` with local-only defaults: `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The accepted Beta Supported boundary remains local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, workspace-local retrieval, identity/ownership, migrations, and operator diagnostics; this is support doctrine, not current-tip qualification.
- Authenticated local Settings read surfaces, the read-only Connections catalog, and bounded account-export imports retain their existing contracts; catalog or import presence does not imply generic connector sync, provider inference, or cloud support.
- Watchdog, Pi diagnostics, proof tooling, and tester-stack receipts are Internal or proof-only surfaces. Static validation and tester evidence do not substitute for supported-path live proof.

## Not yet true / do not assume

- Do not assume current-tip Compose startup, health, model inventory, terminal chat, persistence/readback, retrieval, queue/worker, or turn-lock closure.
- Do not treat the authenticated tester Gemma completion as supported-main evidence; it was produced on the tester proof stack.
- Do not assume Watchdog has model execution, review publication, GitHub mutation, fallback, or automatic retry; no ambient chat model may satisfy its missing policy.
- Do not assume the lost qualified image's deletion cause, retention behavior, or actor is known; the immutable replay prerequisite is unavailable.
- Do not assume Pi diagnostic coverage proves OAuth or provider availability, or that feature branches, local work, or proof from another checkout is shipped reality.

## Active blockers

- Fresh supported-Compose closure has not been rerun after the merged local-gateway template alignment; the latest observed attempt stopped before healthy HTTP.
- Current-tip proof is still missing for health, chat, durable assistant readback, retrieval, queue/worker execution, turn locks, terminal events, and recovery behavior on one supported profile.
- Fresh-state Chroma startup / retrieval qualification remains blocked after the classified compatibility failure; no historical restore or implementation repair is proven.
- Watchdog qualification lacks an explicit available provider/model policy and therefore stops before review receipt and model execution.
- The qualified immutable replay image is unavailable, so retention qualification cannot proceed; canonical-versus-legacy configuration paths also leave startup and operator-state drift risk.

## This week’s priorities

1. Rerun current-main supported-Compose closure with the aligned supported profile.
2. Prove health, model inventory, terminal chat, persistence/readback, retrieval, queue/worker, locks, and terminal events on that profile.
3. Requalify Chroma only under an explicitly authorized, newly classified proof path; keep derived state non-canonical.
4. Bind one explicit Watchdog provider/model policy and requalify without ambient-model substitution.
5. Run the disposable image-retention reproduction and reconcile canonical-versus-legacy configuration drift.

## Release definition right now

- [x] Supported local Compose path, local-only defaults, and Beta boundary are defined on `main`.
- [x] Internal, bounded/conditional, and Out-of-Beta surfaces remain explicitly separated from Beta Supported.
- [ ] Current-tip Compose proves healthy startup, health, model inventory, terminal chat, persistence/readback, and retrieval.
- [ ] Queue, worker, lock, migration, configuration, and recovery behavior is green on the supported install path.
- [ ] Qualification-pending lanes have named current-main proof receipts; until then, they remain quarantined.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
