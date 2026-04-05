## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-04-05

## Interpretation rule

This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

Codexify is in supported-local-beta hardening on `main`. The shipped baseline is still the local Docker Compose stack and supported-profile contract, but `main` now also carries a delegation backbone (draft/approve/cancel/event stream) that is stubbed at execution time. Treat the release as partial delegation plumbing plus the existing chat/ingestion runtime, not a finished autonomous coding-agent product.

## What changed recently

- Delegation runtime docs and operator manual landed on `main`, with validation updated for the new delegation slice.
- Backend delegation backbone merged: packet draft/approve/cancel routes, persisted packet/job/summary rows, explicit delegation statuses, and task-event reuse for delegation runs.
- Task lifecycle states and event metadata are now explicit in shared task/protocol tokens; terminal cancel visibility is emitted from the delegation path.
- Unassigned threads now default to the `General` project, and frontend project controls were aligned with that scope.
- The web runtime startup path now uses an explicit startup gate, and the ChatGPT import sweep moved off the critical path.
- Delegation worker migration handling was reanchored so terminal jobs are guarded instead of being reprocessed.

## Current supported reality

- Local Docker Compose remains the supported install path on `main`.
- The supported beta profile still uses `CODEXIFY_BETA_CORE_ONLY=true`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- `General` is now the default project for unassigned threads.
- Delegation can draft, approve, queue, cancel, and stream run events, with packet/job/summary state persisted in Postgres.
- Delegation execution is still stubbed, so the backbone does not yet prove a real external coding-agent loop.
- `/health`, `/health/chat`, `/api/health/llm`, and `/api/health/retrieval` remain the main runtime evidence surfaces.
- The clean-start, existing-instance upgrade, and archived-snapshot proof artifacts are still on `main` as historical evidence.

## Not yet true / do not assume

- Do not assume delegation can run real external coding-agent work yet; the worker still returns a stub result.
- Do not assume delegation result injection back into the source thread exists.
- Do not assume this tip of `main` has a fresh live end-to-end proof after the latest runtime changes.
- Do not assume older proof docs alone represent the current runtime tip after later merges.
- Do not assume internal-only or dev-only surfaces are part of the supported beta surface unless this file says so.

## Active blockers

- Fresh live beta proof on the current `main` tip is still missing after the latest runtime changes.
- Any release milestone that includes autonomous delegation is blocked; the executor is stubbed and the return path is not shipped.
- Release signoff still depends on the supported-profile / provider / health contract staying aligned.

## This week's priorities

1. Re-run the supported local Compose beta proof on current `main` and refresh the evidence pack.
2. Decide whether delegation stays a stubbed internal backbone or needs a real executor and source-thread return path for the next milestone.
3. Keep the supported-profile, provider registry, and health surfaces aligned before widening any release claim.
4. Update the KB again only after the next merged proof or runtime change, not local intent.

## Release definition right now

- [ ] Supported-profile flags and mounted routes still match the beta contract.
- [ ] Fresh live evidence exists on current `main` for clean start, assistant completion, upload -> embed -> retrieve, and health surfaces.
- [ ] Delegation is either explicitly excluded from the shipped promise or implemented with a real executor plus source-thread result return.
- [ ] No internal-only or quarantined surface is part of the release claim.
- [ ] The blockers above are closed or consciously deferred.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
