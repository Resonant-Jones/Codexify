## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-22

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated friends-and-family private-preview lane. The current-tip supported-Compose rerun proves substantial local runtime behavior, but release qualification remains `HOLD`.

## What changed recently

- Merged one-time, recipient-bound account activation and admitted it only to the gated private-preview/tester lane.
- Separated stable provider identity, configured local runtime identity, logical model route, and inventory display metadata.
- Repaired the supported Whoosh'd Compose projection so required services use local-only, cloud-disabled `local-chat`; added focused regression coverage.
- Current-tip rerun proved health, migrations, inventory, cold/warm chat, document upload, project retrieval, persistence, queue/worker execution, locks, reload, and narrow restart recovery.
- The rerun still records `HOLD`; the 2026-09-22 mainline log records no additional implementation or runtime qualification.

## Current supported reality

- The named supported install path is local Docker Compose with `v1-local-core-web-mcp`, `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The declared Beta Supported contract covers local inference, ordinary chat, durable threads/messages/tasks, document upload/embed/readback, workspace-scoped retrieval, identity/ownership, migrations, and operator diagnostics; current-tip qualification is separate.
- Mainline proof establishes a bounded working local path: Whoosh'd advertises executable `local-chat`, two-turn chat persists assistant rows, project retrieval returns the test fact, and readback survives reload and narrow service restart.
- `local` is the stable provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical display metadata remains inventory observation.
- Private Preview is opt-in: Whoosh'd remains default, DeepSeek is the only admitted cloud lane, and account activation is gated; none of this is public Beta support.

## Not yet true / do not assume

- Do not call the supported path release-ready: the rerun is `HOLD`.
- Do not treat a durable successful task as browser completion proof; the top-level UI remains `Queued` after success, reload, and restart.
- Do not treat correct retrieval output as document-level provenance; terminal and assistant records lack the contributing document/chunk attribution.
- Do not treat the focused model-projection test as full release validation; the governing backend suite remains 151 passed / 5 failed, and two large frontend lifecycle files OOM or hang.
- Do not promote unmerged or untracked terminal-state repair work, activation CLIs/tests, CE-L1, browser/import, connectors, Watchdog, retention, hosted sandbox, Atlas, or Pi into the release promise.

## Active blockers

- Guardian terminal-task/session projection must clear stale `Queued` state and agree with durable terminal truth for success and failure.
- Retrieval must persist attributable document/chunk provenance, not only project scope and a correct answer.
- Governing static validation remains open: stale backend expectations and frontend lifecycle OOM/hang behavior need scoped resolution.
- Private Preview still lacks live activation/replay/login, Chroma/application, provider/persistence/isolation, and approved non-admin canary proof.
- ADR-087 graceful shutdown/finite drain, Tester bind-readiness, browser/import, connector, Watchdog, retention, hosted-sandbox, and publication-baseline gates remain open or bounded.

## This week's priorities

1. Repair and requalify terminal task-state projection on the supported browser path.
2. Re-run retrieval with durable document/chunk provenance and close the attribution gap.
3. Resolve the scoped backend assertions and frontend lifecycle OOM/hang without weakening release contracts.
4. Qualify Private Preview activation, provider/persistence/isolation, and non-admin canary behavior end to end.
5. Reconcile the intended publication baseline, then rerun the complete supported-Compose release bundle.

## Release definition right now

- [x] The supported install path and Beta boundary are defined on `main`.
- [x] Provider/runtime identity, local-only posture, and fail-closed boundaries are explicit.
- [ ] Current-tip Compose proves coherent health, inventory, chat, durable readback, retrieval provenance, browser terminal state, and event delivery.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration, recovery, browser, and account-import claimed-path gates are green.
- [ ] Preview activation and provider lanes have current-main evidence for live execution, durable readback, isolation, recovery, and canary behavior where applicable.
- [ ] Governing static checks and the intended publication baseline are reconciled.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
