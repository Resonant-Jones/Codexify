## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-10-08

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated Private Preview lane. The 2026-10-06 accounting record reports no new implementation, proof, or qualification work; the latest complete supported-Compose qualification remains `HOLD`.

## What changed recently

- The [2026-10-08 exact-model reconciliation](./proofs/supported-compose/2026-10-08-explicit-model-requalification.md) passed all 23 focused tests at remote-main `5c6e2ca7`; the historical worker/test fixture contradiction was already corrected by `20bf69b88`. Current-tip live rejection and subsequent persisted chat remain unqualified: resource preflight stopped before starting an isolated stack. The exact-model gate and full supported-Compose qualification remain `HOLD`.
- Merged consent-based same-node Private Preview messaging with durable request, consent, idempotency, rate, privacy, and two-account proof; default Beta remains excluded.
- Persisted authenticated account-intake provenance for coding runs so operator-created metadata cannot grant account snapshot access.
- Merged chat-only generic task-event SSE admission through durable completion-attempt and canonical-thread authority; agent/coding uses dedicated readback and other families move or quarantine.
- Closed focused credential-purpose, mixed-principal, Hosted Room invitation, task-event, and agent snapshot authorization cases on `main`.
- The 2026-10-05 and 2026-10-06 mainline records report no new implementation, proof, or qualification work; no release claim widened.
- Local `main` remains the audit source at 3 commits ahead and 34 behind `origin/main`; no push or publication reconciliation was performed.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp`, `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported contract covers local inference, ordinary chat, durable threads/messages/tasks, document upload/embed/readback, workspace retrieval, identity/ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Mainline has bounded evidence for topology, migrations, health, browser cold/warm chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, cancellation, and deadline behavior at evaluated tips.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- Account import remains bounded: isolated evidence covers browser staging, materialization, ownership/readback, and later vector observations, not complete recall.
- Same-node human messaging is enabled only in the opt-in Private Preview profile; it is unavailable in default/public Beta and does not grant project, thread, Guardian, federation, attachment, or realtime authority.

## Not yet true / do not assume

- Do not call the supported path release-ready; the latest complete qualification is `HOLD`.
- Do not infer current-tip restart/shutdown recovery, browser transcript coherence before reload, or a complete natural import-to-recall path.
- Do not infer current-tip live unavailable-model rejection from the passing focused tests. Earlier bounded repair/runtime receipts demonstrated rejection at their evaluated tips, while the latest complete Compose qualification remains `HOLD`; the 2026-10-08 run stopped at resource preflight.
- Do not treat focused auth tests, disposable PostgreSQL, isolated Preview proof, docs, or route presence as deployed/public-ingress qualification.
- Do not treat direct messaging, activation, browser/import, connectors, Watchdog, retention, hosted sandbox, Atlas, Pi, or branch-local work as default Beta support without current-main qualification.
- Do not infer cross-node messaging, federation, or autonomous coding-worker support from the merged contracts or implementation slices.
- Do not treat uncommitted worktree changes or local-only audit commits as synchronized public-main state.

## Active blockers

- Run the complete supported-Compose qualification on current `main`, including exact-model rejection, browser/event/provenance coherence, restart recovery, and ordinary chat after restart.
- Requalify explicit-model rejection and subsequent persisted ordinary chat live on the frozen current tip after safe isolated runtime capacity is available; the historical worker/test contradiction is reconciled by the 2026-10-08 focused tests.
- Reproduce and repair the new-thread authored-message projection gap, then rerun the real browser and durable-readback path.
- Complete a fresh natural import-to-recall run through provider context, answer persistence, and negative scope control.
- Requalify Private Preview activation, Chroma/application, provider/persistence/isolation, approved canary, and public-ingress claims on their intended live paths.
- Reconcile the divergent local `main` and `origin/main` refs before treating local artifacts as published state.

## This week's priorities

1. Freeze current `main` and run the full supported-Compose proof bundle.
2. Complete live exact-model rejection and subsequent ordinary-chat proof on the frozen tip; preserve the passing no-substitution behavior.
3. Repair and reprove browser new-thread transcript projection.
4. Prove uninterrupted account import through retrieval, answer persistence, and scope isolation.
5. Requalify only the Preview and ingress surfaces that have an explicit release claim.

## Release definition right now

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Bounded chat, cancellation, durable readback, retrieval, and authorization evidence exists at evaluated mainline tips.
- [ ] A fresh current-tip Compose run passes health, inventory, chat, durable readback, retrieval, browser projection, event delivery, and restart recovery.
- [ ] An unavailable explicit model fails before provider execution and cannot be silently substituted.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration, browser, account-import recall, and scope-isolation gates are green on one evaluated tip.
- [ ] Each claimed Preview or public-ingress path has current live evidence, with no claim inferred from focused tests alone.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
