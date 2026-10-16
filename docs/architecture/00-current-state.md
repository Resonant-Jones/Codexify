## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-10-16

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` is in local-first Beta hardening with a separately gated Private Preview lane. Recent merges changed product and bounded-preview surfaces, but no fresh supported-Compose qualification landed. The current release gate remains `HOLD`.

## What changed recently

- PR #870 simplified Persona Studio into the Lens editor, removed retired guidance and diagnostics surfaces, and restored the frontend typecheck command; this is implementation evidence, not release qualification.
- PR #869 merged a bounded authenticated, local-only, ephemeral Chronicle preview and removed the persistent Coding Loop composer toggle; neither widens default Beta support.
- PR #868 merged the Unified Memory Store foundation integration; it does not establish a new supported runtime or qualification result.
- Imported-history inspection/authorization and synthetic import qualification remain bounded evidence; they do not prove a complete natural import-to-recall path.
- The 2026-10-16 mainline log recorded no new implementation commit; active-checkout work remains outside `main` truth, and local `main` remains divergent from the stored remote-tracking ref.

## Current supported reality

- The named supported install path is local Docker Compose profile `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported envelope covers local inference, ordinary chat, durable threads/messages/tasks, supported document ingestion and retrieval, account ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Recorded mainline evidence covers topology, health, browser chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, cancellation, and deadline behavior at evaluated tips.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- Account import is bounded to the implemented staging, materialization, ownership/readback, and vector-observation paths; complete recall is not established.
- Same-node human messaging is opt-in Private Preview only and does not grant project, Guardian, federation, attachment, or realtime authority.

## Not yet true / do not assume

- Do not call the supported path release-ready; the latest complete supported-Compose qualification is `HOLD`.
- Focused tests, docs, routes, disposable databases, or Chronicle preview proof do not establish current live-runtime or public-ingress qualification.
- Do not infer current-tip restart/shutdown recovery, browser transcript projection coherence, or a complete natural import-to-recall path.
- Do not infer exact unavailable-model rejection: the complete Compose proof recorded accepted work with model substitution and no assistant fallback flag.
- Do not promote direct messaging, activation, browser host/import, connectors, Watchdog, hosted sandbox, Atlas, Pi, federation, or autonomous coding-worker work to default Beta support without current-main qualification.
- The current-state knowledge-graph node parses but its freshness is stale; validity is not current release proof.
- Uncommitted checkout work and local-only commits are not synchronized public-main state.

## Active blockers

- A fresh current-tip supported-Compose qualification is still missing, including model rejection, browser/event/provenance coherence, restart recovery, and ordinary chat after restart.
- Migration-route collection is blocked by missing UMS revision models; the disposable evidence-reader migration is blocked by multiple Alembic heads.
- The explicit-model worker/test contradiction must be resolved with fail-closed behavior and no silent substitution.
- The new-thread authored-message projection gap must be repaired and re-proven through the browser and durable-readback path.
- Natural import-to-recall still needs provider-context, answer-persistence, and negative-scope proof on one isolated run.
- Current release metadata freshness and local-main publication state must be explicitly reconciled before relying on them as shared release evidence.

## This week's priorities

1. Freeze current `main` and run the complete supported-Compose proof bundle.
2. Repair the migration baseline and rerun blocked Chronicle HTTP regression coverage.
3. Close the explicit-model rejection contradiction before provider execution.
4. Repair and reprove new-thread projection, restart recovery, and browser/event coherence.
5. Complete import-to-recall scope proof, refresh release metadata, and reconcile publication state.

## Release definition right now

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Bounded chat, cancellation, durable readback, retrieval, and authorization evidence exists at evaluated mainline tips.
- [ ] A fresh current-tip Compose run passes health, inventory, chat, durable readback, retrieval, browser projection, event delivery, and restart recovery.
- [ ] An unavailable explicit model fails before provider execution and cannot be silently substituted.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration, browser, import-recall, and scope-isolation gates are green on one evaluated tip.
- [ ] Each claimed Preview or public-ingress path has current live evidence; focused tests alone do not qualify it.
- [ ] Changed release metadata parses cleanly and its freshness points to the evaluated mainline.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
