## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-10-09

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated Private Preview lane. The post-audit mainline delta contains narrow workspace, Memory Vault, and Pi telemetry changes plus release-accounting housekeeping; no fresh supported-path qualification landed, and the latest complete supported-Compose qualification remains `HOLD`.

## What changed recently

- Merged consent-based same-node Private Preview messaging with durable request, consent, idempotency, rate, privacy, and two-account proof; default Beta remains excluded.
- Persisted authenticated account-intake provenance for coding runs so operator-created metadata cannot grant account snapshot access.
- Merged chat-only generic task-event SSE admission through durable completion-attempt and canonical-thread authority; agent/coding uses dedicated readback and other families move or quarantine.
- Closed focused credential-purpose, mixed-principal, Hosted Room invitation, task-event, and agent snapshot authorization cases on `main`.
- Merged a workspace scratchpad save-target capture fix, a bounded Memory Vault request reference, and live-path Pi telemetry test tightening; these are focused changes, not release qualification.
- Removed stale daily logs, added retired-ADR routing, and recorded a 2026-10-07 no-change checkpoint; no release claim widened.
- The audit baseline was 1 commit ahead and 0 behind `origin/main`; this refresh adds one local audit commit and does not publish it.

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
- Do not infer exact unavailable-model rejection: the current complete Compose proof recorded accepted work with model substitution and no assistant fallback flag.
- Do not treat focused auth tests, disposable PostgreSQL, isolated Preview proof, docs, or route presence as deployed/public-ingress qualification.
- Do not treat the focused workspace, Memory Vault, or Pi telemetry changes as evidence of complete supported-path qualification.
- Do not treat the two changed architecture knowledge-graph JSON nodes as valid metadata; committed conflict markers currently make both fail JSON parsing.
- Do not treat direct messaging, activation, browser/import, connectors, Watchdog, retention, hosted sandbox, Atlas, Pi, or branch-local work as default Beta support without current-main qualification.
- Do not infer cross-node messaging, federation, or autonomous coding-worker support from the merged contracts or implementation slices.
- Do not treat uncommitted worktree changes or local-only audit commits as synchronized public-main state.

## Active blockers

- Run the complete supported-Compose qualification on current `main`, including exact-model rejection, browser/event/provenance coherence, restart recovery, and ordinary chat after restart.
- Resolve the explicit-model worker/test contradiction and retain fail-closed behavior with no silent substitution.
- Reproduce and repair the new-thread authored-message projection gap, then rerun the real browser and durable-readback path.
- Complete a fresh isolated natural import-to-recall run through provider context, answer persistence, and negative scope control.
- Requalify Private Preview activation, Chroma/application, provider/persistence/isolation, approved canary, and public-ingress claims on their intended live paths.
- Repair and validate the conflict-marked architecture knowledge-graph metadata before relying on those nodes.
- Publish or explicitly reconcile the local-only `main` commits before treating local artifacts as published state.

## This week's priorities

1. Freeze current `main` and run the full supported-Compose proof bundle.
2. Repair and validate the conflict-marked architecture knowledge-graph metadata.
3. Close the explicit-model rejection contradiction before provider execution.
4. Repair and reprove browser new-thread transcript projection.
5. Prove uninterrupted account import, then requalify only explicitly claimed Preview or ingress surfaces.

## Release definition right now

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Bounded chat, cancellation, durable readback, retrieval, and authorization evidence exists at evaluated mainline tips.
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
