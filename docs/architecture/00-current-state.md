## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-10-10

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated Private Preview lane. Since the prior refresh, mainline added bounded authenticated imported-history inspection; no supported install or release gate widened. The latest complete supported-Compose qualification remains `HOLD`.

## What changed recently

- Added a Chronicle readiness audit that separates authenticated history inspection from natural import-to-recall and defers synthesis.
- Merged a bounded read-only imported-history evidence reader with account, Project, thread, origin, provenance, coverage, and no-write boundaries.
- Merged an authenticated HTTP inspection route and access resolver with fail-closed ownership checks, existing account authentication, bounded errors, and `no-store` responses.
- Recorded bounded proof at the reader baseline: 83 HTTP cases, 74 reader cases, and 28 migration-route cases passed against disposable PostgreSQL; this is test evidence, not supported-runtime qualification.
- Local `main` is five commits ahead and 131 commits behind the stored `origin/main` ref; no reconciliation or push occurred.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp`, `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported contract covers local inference, ordinary chat, durable threads/messages/tasks, document upload/embed/readback, workspace retrieval, identity/ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Mainline has bounded evidence for topology, migrations, health, browser cold/warm chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, cancellation, and deadline behavior at evaluated tips.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- Account import has bounded account-scoped staging, materialization, canonical history, and read-only inspection paths; complete recall is not part of that claim.
- Same-node human messaging is enabled only in the opt-in Private Preview profile; it does not grant project, thread, Guardian, federation, attachment, or realtime authority.

## Not yet true / do not assume

- Do not call the supported path release-ready; the latest complete qualification is `HOLD`.
- Do not infer current-tip restart/shutdown recovery, browser transcript coherence before reload, or a complete natural import-to-recall path.
- Do not infer exact unavailable-model rejection; the current complete Compose proof recorded accepted work with model substitution and no assistant fallback flag.
- Do not treat the imported-history route as a supported Chronicle, provider-recall, frontend, deployment, or public-ingress feature.
- Do not treat focused tests, disposable PostgreSQL, route presence, docs, or isolated Preview proof as supported-Compose or public qualification.
- Do not treat the two changed architecture knowledge-graph JSON nodes as valid metadata; committed conflict markers make both fail JSON parsing.
- Do not treat direct messaging, activation, browser/import, connectors, Watchdog, retention, hosted sandbox, Atlas, Pi, or branch-local work as default Beta support without current-main qualification.
- Do not treat uncommitted worktree changes or local-only audit commits as synchronized public-main state.

## Active blockers

- Run the complete supported-Compose qualification on current `main`, including exact-model rejection, browser/event/provenance coherence, restart recovery, and ordinary chat after restart.
- Resolve the explicit-model worker/test contradiction and retain fail-closed behavior with no silent substitution.
- Reproduce and repair the new-thread authored-message projection gap, then rerun the real browser and durable-readback path.
- Complete a fresh natural import-to-recall run through provider context, answer persistence, and negative scope control.
- Keep imported-history inspection out of the release promise until frontend initiation, deployment, consumer behavior, and Chronicle/recall boundaries are separately proven.
- Requalify Private Preview activation, Chroma/application, provider/persistence/isolation, approved canary, and public-ingress claims on intended live paths.
- Repair and validate conflict-marked architecture metadata, then reconcile local-only `main` commits before treating them as published state.

## This week's priorities

1. Freeze current `main` and run the full supported-Compose proof bundle.
2. Close the explicit-model rejection contradiction and browser new-thread projection gap.
3. Repair and validate the conflict-marked architecture knowledge-graph metadata.
4. Prove uninterrupted natural import-to-recall without widening scope from the new reader.
5. Reconcile local `main` with the stored remote ref under an explicit Git policy.

## Release definition right now

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Bounded chat, cancellation, durable readback, retrieval, authorization, and imported-history inspection evidence exists at evaluated mainline tips.
- [ ] A fresh current-tip Compose run passes health, inventory, chat, durable readback, retrieval, browser projection, event delivery, and restart recovery.
- [ ] An unavailable explicit model fails before provider execution and cannot be silently substituted.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration, browser, account-import recall, and scope-isolation gates are green on one evaluated tip.
- [ ] Each claimed Preview or public-ingress path has current live evidence, with no claim inferred from focused tests alone.
- [ ] Changed release metadata parses cleanly and its freshness points to the evaluated mainline.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
