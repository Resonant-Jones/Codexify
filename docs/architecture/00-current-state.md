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

`main` remains in local-first Beta hardening with a separately gated Private Preview lane. The 2026-10-21 local reconciliation combines the local audit/log history with origin/main through `f7e6a7f48`, including the merged runtime and UI changes below; reconciliation alone establishes no supported-path qualification. The latest complete supported-Compose qualification remains `HOLD`.

## What changed recently

- PR #870 simplified Persona Studio into the Lens editor, retired obsolete guidance and diagnostics surfaces, and restored the frontend typecheck command; this is implementation evidence, not release qualification.
- PR #869 merged a bounded authenticated, local-only, ephemeral Chronicle preview and removed the persistent Coding Loop composer toggle; neither widens default Beta support.
- PR #868 merged the Unified Memory Store foundation integration; it does not establish a new supported runtime or qualification result.
- Imported-history inspection and synthetic import qualification remain bounded evidence; they do not prove a complete natural import-to-recall path.
- Reconciled the local documentation series with refreshed `origin/main`; the original local tip `5c8a8ecd9` is retained on `codex/backup-main-before-reconcile-20261021`. This local merge is not publication.
- Integrated PR #871 invocation-scoped coding credentials, PR #872 durable chat tool-decision checkpoints and replay-safe Command Bus idempotency, and PR #874 bounded tool-loop/accepted-turn identity integration. These are implementation changes, not fresh integrated-tip runtime qualification.
- Integrated the merged shell geometry repairs, selectable glass treatments and radio navigation, Library projection/navigation, task cancellation ownership authorization, and narrow-Guardian session-rail contract through PR #884. Generative UI remains behind its existing opt-in gates; implementation presence does not widen Beta support.
- Historical PR #865 proof records remain limited to their recorded revisions and runtime paths; this reconciliation does not establish fresh integrated-tip Compose qualification or candidate-adoption authority.

- The approved 2026-10-21 private-preview restart integrated reconciled main plus the UMS ORM restoration. Canonical missing-table repair retained the migration head and user/thread/message counts; bounded UI/core/chat health checks passed. See [restart receipt](proofs/runtime/2026-10-21-main-reconciliation-private-preview-restart.md). This does not change the supported-Compose HOLD.

## Current supported reality

- The named supported install path is local Docker Compose profile `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported envelope covers local inference, ordinary chat, durable threads/messages/tasks, supported document ingestion and retrieval, account ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Mainline has bounded evidence for topology, health, browser chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, cancellation, and deadline behavior at evaluated tips.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- Account import is bounded to staging, materialization, ownership/readback, and vector-observation paths; complete recall is not established.
- Private Preview is opt-in: Whoosh'd remains the default local lane, DeepSeek is the only admitted cloud lane, and same-node human messaging is not default Beta support.
- Same-node direct messaging is also mounted as an internal experimental capability (`internal_only`) on `v1-local-core-web-mcp`, and is `enabled` on opted-in Preview/tester profiles; mounting grants no cross-node, attachment, Guardian, or release-qualification authority.

## Not yet true / do not assume

- Do not call the supported path release-ready; the latest complete supported-Compose qualification is `HOLD`.
- Focused tests, docs, routes, disposable databases, or Chronicle preview proof do not establish current live-runtime or public-ingress qualification.
- Do not infer current-tip restart/shutdown recovery, browser transcript projection coherence, or a complete natural import-to-recall path.
- Do not infer exact unavailable-model rejection: the complete Compose proof recorded accepted work with model substitution and no assistant fallback flag.
- Do not treat the 2026-10-21 delegation canary as successful worker-path execution: it stopped at a `reasoning_effort` contract mismatch before a provider request and remains `HOLD`.
- Do not treat `allow_network=false` in that canary as network isolation; outbound worker connectivity was observed.
- Do not promote direct messaging, activation, browser host/import, connectors, Watchdog, hosted sandbox, Atlas, Pi, federation, or autonomous coding-worker work to default Beta support without current-main qualification.
- The account-owned connector and delegation canary described in the 2026-10-21 log remain branch evidence; merged chat/session and shell-geometry changes are implementation evidence, not current runtime qualification.
- The current-state knowledge-graph node parses but its freshness is stale; validity is not current release proof.
- Uncommitted checkout work and local-only commits are not synchronized public-main state.

## Active blockers

- A fresh current-tip supported-Compose qualification is missing, including model rejection, browser/event/provenance coherence, restart recovery, and ordinary chat after restart.
- The four missing UMS ORM mappings are restored. Focused validation records 124 passes and one inherited stale migration-head assertion; blocked Chronicle HTTP coverage and complete supported-Compose qualification still require separate proof.
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
