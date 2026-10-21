## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-10-21

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated Private Preview lane. Since the 2026-10-20 audit, only the 2026-10-21 mainline accounting record landed; no implementation or supported-path qualification changed. The latest complete supported-Compose qualification remains `HOLD`.

## What changed recently

- PR #870 simplified Persona Studio into the Lens editor, retired obsolete guidance and diagnostics surfaces, and restored the frontend typecheck command; this is implementation evidence, not release qualification.
- PR #869 merged a bounded authenticated, local-only, ephemeral Chronicle preview and removed the persistent Coding Loop composer toggle; neither widens default Beta support.
- PR #868 merged the Unified Memory Store foundation integration; it does not establish a new supported runtime or qualification result.
- Imported-history inspection and synthetic import qualification remain bounded evidence; they do not prove a complete natural import-to-recall path.
- The 2026-10-21 mainline log records feature-branch connector, chat/session, shell-geometry, and delegation work as unmerged; none changes `main` support. Local `main` is 13 commits ahead and 61 behind the stored remote-tracking snapshot; no fetch or reconciliation was performed.

## Current supported reality

- The named supported install path is local Docker Compose profile `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported envelope covers local inference, ordinary chat, durable threads/messages/tasks, supported document ingestion and retrieval, account ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Mainline has bounded evidence for topology, health, browser chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, cancellation, and deadline behavior at evaluated tips.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- Account import is bounded to staging, materialization, ownership/readback, and vector-observation paths; complete recall is not established.
- Private Preview is opt-in: Whoosh'd remains the default local lane, DeepSeek is the only admitted cloud lane, and same-node human messaging is not default Beta support.

## Not yet true / do not assume

- Do not call the supported path release-ready; the latest complete supported-Compose qualification is `HOLD`.
- Focused tests, docs, routes, disposable databases, or Chronicle preview proof do not establish current live-runtime or public-ingress qualification.
- Do not infer current-tip restart/shutdown recovery, browser transcript projection coherence, or a complete natural import-to-recall path.
- Do not infer exact unavailable-model rejection: the complete Compose proof recorded accepted work with model substitution and no assistant fallback flag.
- Do not treat the 2026-10-21 delegation canary as successful worker-path execution: it stopped at a `reasoning_effort` contract mismatch before a provider request and remains `HOLD`.
- Do not treat `allow_network=false` in that canary as network isolation; outbound worker connectivity was observed.
- Do not promote direct messaging, activation, browser host/import, connectors, Watchdog, hosted sandbox, Atlas, Pi, federation, or autonomous coding-worker work to default Beta support without current-main qualification.
- The account-owned connector, chat/session rail, top-chrome geometry, and delegation changes described in the 2026-10-21 log are feature-branch work, not shipped `main` state.
- The current-state knowledge-graph node parses but its freshness is stale; validity is not current release proof.
- Uncommitted checkout work and local-only commits are not synchronized public-main state.

## Active blockers

- A fresh current-tip supported-Compose qualification is missing, including model rejection, browser/event/provenance coherence, restart recovery, and ordinary chat after restart.
- Migration-route collection is blocked by missing UMS revision models; the disposable evidence-reader migration is blocked by multiple Alembic heads.
- The explicit-model worker/test contradiction must be resolved with fail-closed behavior and no silent substitution.
- The delegated worker-to-adapter `reasoning_effort` contract mismatch must be resolved and re-proven before any delegation execution claim is accepted.
- The new-thread authored-message projection gap must be repaired and re-proven through browser and durable-readback paths.
- Natural import-to-recall still needs provider-context, answer-persistence, and negative-scope proof on one isolated run.
- Release metadata freshness and local-main publication state must be reconciled before relying on them as shared release evidence.

## This week’s priorities

1. Freeze current `main` and run the complete supported-Compose proof bundle.
2. Repair the migration baseline and rerun blocked Chronicle HTTP regression coverage.
3. Close the explicit-model rejection contradiction before provider execution.
4. Repair and reprove new-thread projection, restart recovery, and browser/event coherence; keep delegation execution at HOLD.
5. Complete import-to-recall scope proof, refresh release metadata, and reconcile publication state.

## Release definition right now

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Bounded chat, cancellation, durable readback, retrieval, and authorization evidence exists at evaluated mainline tips.
- [ ] A fresh current-tip Compose run passes health, inventory, chat, durable readback, retrieval, browser projection, event delivery, and restart recovery.
- [ ] An unavailable explicit model fails before provider execution and cannot be silently substituted.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration, browser, import-recall, and scope-isolation gates are green on one evaluated tip.
- [ ] Any delegated execution claim has a passing worker-to-adapter reasoning-effort contract and live proof; the current canary does not satisfy this.
- [ ] Each claimed Preview or public-ingress path has current live evidence; focused tests alone do not qualify it.
- [ ] Changed release metadata parses cleanly and its freshness points to the evaluated mainline.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
