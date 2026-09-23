## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-23

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated private-preview lane. Mainline has merged the supported-path repair set, but the last complete supported-Compose qualification ended `HOLD` and no complete post-repair rerun is recorded. The 2026-09-23 mainline log records no new implementation or qualification work.

## What changed recently

- Merged Guardian terminal-task projection repairs; the complete qualification recorded browser `Ready` convergence, no stale `Queued`, and agreement with durable terminal truth.
- Merged durable retrieval provenance for contributing document/chunk identities; the qualification recorded exact equality between assistant and terminal-outbox provenance.
- Merged explicit local-model authority and fail-closed handling; focused tests and a bounded live rejection passed, but full post-repair qualification is still pending.
- Reconciled the backend release-boundary suite and Guardian lifecycle-test reliability; the declared bundles recorded 157/157 backend and 11/11 lifecycle tests.
- Enabled direct messages only in the gated private-preview profile and polished the Guardian shell; no public Beta support claim widened.
- Recorded a no-change mainline day for 2026-09-23.

## Current supported reality

- The named supported install path is local Docker Compose with `v1-local-core-web-mcp`, `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported contract covers local inference, ordinary chat, durable threads/messages/tasks, document upload/embed/readback, workspace retrieval, identity/ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Mainline contains bounded proof for topology, migrations, health, browser cold/warm chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, and the declared static suites at the evaluated frozen tip.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical display metadata remains inventory observation.
- Private Preview is opt-in: Whoosh'd remains default, DeepSeek is the only admitted cloud lane, and account activation/direct messaging remain gated; these are not public Beta support.

## Not yet true / do not assume

- Do not call the supported path release-ready: the latest complete qualification is `HOLD`.
- Do not claim the explicit unavailable-model path is fully requalified: the repair is merged and bounded tests pass, but the full current-tip bundle has not been rerun.
- Do not infer restart/post-restart proof from the pre-repair qualification; those rows were blocked after the fail-closed contradiction.
- Do not treat focused tests, UI polish, direct messaging, activation, browser/import, connectors, Watchdog, retention, hosted sandbox, Atlas, or Pi work as public Beta support without current-main qualification.
- Do not treat local `main` being one commit ahead of `origin/main`, or the staged unrelated dev-log deletion, as release or runtime evidence.

## Active blockers

- Run the complete supported-Compose qualification against the repaired current `main`, including exact-model rejection, restart recovery, and post-restart ordinary chat.
- Resolve the remaining neighboring explicit-model worker-test contradiction and keep the fail-closed contract authoritative.
- Reconcile a clean intended publication baseline before making a release claim; no push or remote publication is implied by this audit.
- Private Preview still lacks live activation/replay/login, Chroma/application, provider/persistence/isolation, and approved non-admin canary proof.
- ADR-087 graceful shutdown/finite drain, Tester bind-readiness, browser/import, connector, Watchdog, retention, hosted-sandbox, and other bounded qualification gates remain open where not directly covered above.

## This week's priorities

1. Freeze the repaired current `main` and run the full supported-Compose proof bundle.
2. Close the explicit-model test contradiction and verify no substitution before provider execution.
3. Confirm browser terminal convergence, durable provenance, queue/worker/lock behavior, and restart recovery on that same tip.
4. Qualify the gated private-preview activation, provider/persistence/isolation, and non-admin canary path.
5. Reconcile the publication baseline and update release claims only from the resulting evidence.

## Release definition right now

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Mainline has bounded repair and qualification evidence for terminal projection, retrieval provenance, and static lifecycle reliability.
- [ ] A fresh current-tip Compose run passes health, inventory, chat, durable readback, retrieval provenance, browser terminal state, event delivery, and restart recovery.
- [ ] An unavailable explicit model fails before provider execution and cannot be silently substituted.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration, browser, and account-import claimed-path gates are green on the same evaluated tip.
- [ ] Preview lanes and the intended publication baseline have current evidence where claimed.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
