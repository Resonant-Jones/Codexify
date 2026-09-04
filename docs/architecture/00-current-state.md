## Purpose

This file is the canonical short-form source of truth for Codexify’s current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-04

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a gated private-preview lane. A bounded live private-preview schema upgrade reached repository Alembic head with data-preservation and immediate runtime-read checks passing, but scheduled reconciliation failed on a stale migrator artifact; no Beta support boundary widened.

## What changed recently

- Qualified the private-preview migration lineage on a disposable clone, then upgraded the live database to `b2c8d0e3f5a7` with preservation, worker recovery, no-op, and authenticated read checks passing.
- Found the post-upgrade scheduled reconciler still fails because its baked migrator image cannot locate `b2c8d0e3f5a7`; lifecycle recovery is not qualified.
- Proved chat-history disappearance is a data-present/API-filter mismatch caused by legacy Project ownership divergence; no canonical chat row loss or runtime database-target drift was found.
- Accepted ADR-081 naming `projects.user_id` as Project ownership authority; runtime normalization and legacy reconciliation remain unfinished.
- Merged phone sidebar/navigation and composer overflow work with focused frontend coverage; this is UI change evidence, not supported-path browser proof.
- Added a metering/billing foundation design sketch; it is explicitly unimplemented and does not affect release scope.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The intended Beta Supported boundary remains local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, workspace-local retrieval, identity/ownership, migrations, and operator diagnostics; this is support doctrine, not current-tip qualification.
- Mainline contains focused project lifecycle, conversation-origin, document-artifact preview, Guardian Chat, account-import, and mobile-shell repairs with targeted coverage; supported-path and authenticated browser proof remain separate gates.
- Valid account-import multipart batches are accepted and durably staged on the server path; the Safari/WebKit envelope failure remains unrepaired.
- Private-preview live migration preservation/readback, Guardian secret rotation, Cloudflare ingress, and private-profile People/Share behavior have bounded evidence; these do not admit guests or widen Beta.
- Pi 0.82.1 wrapper/API, source-vendor, identity, framing, and telemetry changes remain internal, non-inference, or OAuth-readiness qualification.

## Not yet true / do not assume

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or recovery closure.
- Do not treat the live private-preview Alembic target as scheduled-recovery closure: the database is at `b2c8d0e3f5a7`, but the reconciler artifact is stale.
- Do not treat ADR-081 acceptance, chat-history classification, or focused UI tests as runtime Project-ownership convergence or supported browser proof.
- Do not treat CE-L1 OAuth readiness, Pi telemetry, wrapper tests, or source-vendor closure as live provider/model execution, coding-loop completion, persisted-result readback, or Beta proof.
- Do not treat private-preview configuration, bounded recovery/ingress receipts, or a live health/read result as an admitted canary; tester isolation, provider, persistence, and observability gates remain open.
- Do not treat Modal or E2B partial conformance as a qualified hosted sandbox, provider-enforced storage/read-only boundary, supported runtime path, or release support.
- Do not infer shipped reality from mutable `latest`, another checkout, local-only artifacts, planning language, or docs alone; realtime delivery, attachments, federation, and cross-node People messaging remain deferred.

## Active blockers

- Fresh supported-Compose closure is missing at the current `main` tip, including health, chat, persistence/readback, retrieval, queue/worker, locks, and terminal events.
- The private-preview scheduled reconciler must receive a current migrator artifact and pass one scheduled `auto-start` recovery without recreating healthy application containers.
- Fresh-state Chroma startup/retrieval qualification remains unresolved; Chroma is derived state and no repair or historical restore is proven.
- CE-L1 still lacks live provider/model execution, terminal durable result, and source-thread readback.
- The friends-and-family canary is blocked on approved non-admin testers plus reruns of Access, isolation, provider, persistence, and bounded-observability gates; DeepSeek rotation/requalification remains open.
- Project-ownership runtime/data convergence, Safari multipart-envelope repair, Watchdog policy/model, immutable image-retention, hosted-sandbox, and recent supported-path browser gates remain unclosed.

## This week’s priorities

1. Qualify the current private-preview migrator artifact and scheduled reconciliation at live head.
2. Rerun current-main supported-Compose closure with the canonical local profile.
3. Prove health, terminal chat, persistence/readback, retrieval, queue/worker, locks, and terminal events on that profile; requalify Chroma.
4. Requalify CE-L1 live execution/readback and rotate/requalify the private-preview DeepSeek credential before tester execution.
5. Close Project-ownership convergence, Safari upload-envelope regression, and the browser, Watchdog, retention, and hosted-sandbox gates.

## Release definition right now

- [x] Supported local Compose path, local-only defaults, and Beta boundary are defined on `main`.
- [x] Internal, bounded/conditional, qualification-pending, and Out-of-Beta surfaces remain separate from Beta Supported claims.
- [x] Private-preview migration preservation/readback and ingress proofs are bounded without guest admission or release widening.
- [ ] Current-tip Compose proves healthy startup, model inventory, terminal chat, persistence/readback, and retrieval.
- [ ] Queue, worker, lock, migration, configuration, recovery, browser, and account-import claimed-path evidence gates are green.
- [ ] Every claimed preview/provider lane has current-main proof for live execution, durable readback, isolation, and scheduled recovery where applicable.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
