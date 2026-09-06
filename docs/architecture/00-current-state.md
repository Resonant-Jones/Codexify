## Purpose

This file is the canonical short-form source of truth for Codexify’s current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-06

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a gated private-preview lane. Recent mainline work improved bounded profile, sharing, and worker-diagnosis seams, but established no new release-ready runtime path or wider Beta support boundary.

## What changed recently

- Persona Profile authority, account-scoped persistence, export coverage, acceptance-time snapshots, and five-field runtime application landed with focused tests; broad Studio controls remain outside runtime enforcement.
- ShareSheet async handling now rejects stale search/send completions and surfaces relationship-load failure with retry coverage.
- A proof-only Tester worker lineage bridge confirmed that the historical bind/import race still applies to `main`; the fail-closed readiness predicate and fresh Tester runtime proof remain absent.
- Pi’s Anthropic coding default was reconciled to `claude-sonnet-4-6` with contract/proof coverage; this remains internal coding-worker qualification.
- Private-preview migration/recovery evidence and one-slot local chat-worker admission remain bounded prerequisites, not provider or persistence closure.
- The 2026-09-06 mainline log records no additional implementation or runtime qualification today.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The intended Beta Supported boundary covers local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, workspace-local retrieval, identity/ownership, migrations, and operator diagnostics; this doctrine is not current-tip qualification.
- Mainline has focused coverage for project lifecycle, conversation origin, document artifacts, Guardian Chat, account import, mobile shell, Persona Profile, and ShareSheet paths; authenticated supported-path browser proof remains separate.
- Persona Studio persistence is account-scoped and runtime-active only through the current five-field projection; broad voice, tools, permissions, retrieval, and connector fields remain inert or local.
- Valid account-import multipart batches are accepted and durably staged on the server path; the Safari/WebKit envelope failure remains unrepaired.
- Private-preview migration preservation/readback, scheduled reconciliation, Guardian secret rotation, Cloudflare ingress, and private-profile People/Share behavior have bounded evidence without guest admission or Beta widening.

## Not yet true / do not assume

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or recovery closure.
- Do not treat the Tester lineage bridge as a startup repair or fresh runtime qualification; no current bind-readiness predicate has landed.
- Do not treat private-preview admission serialization, migration/recovery, or health/read results as live provider, persistence, observability, isolation, or canary proof.
- Do not treat Persona Profile persistence, acceptance snapshots, ADR-082, or focused UI tests as broad configuration enforcement or browser proof.
- Do not treat CE-L1/Pi qualification, Chroma state, hosted-sandbox partial conformance, or Watchdog contracts as release-supported runtime behavior.
- Do not infer shipped reality from another checkout, local-only artifacts, mutable `latest`, planning language, or docs alone; attachments, federation, and cross-node messaging remain deferred.

## Active blockers

- Fresh supported-Compose closure is missing at the current `main` tip, including health, chat, persistence/readback, retrieval, queue/worker, locks, and terminal events.
- The Tester worker bind-readiness repair and fresh isolated runtime proof remain open; the historical diagnosis is applicable but static.
- Private-preview provider execution, persistence, observability, tester isolation, approved non-admin canary, and DeepSeek requalification remain open.
- Fresh-state Chroma startup/retrieval qualification remains unresolved; it is derived state, not canonical data.
- CE-L1 still lacks live provider/model execution, terminal durable result, and source-thread readback.
- Project-ownership convergence, Safari upload repair, authenticated browser gates, Watchdog policy/model, immutable image retention, and hosted-sandbox qualification remain unclosed.

## This week’s priorities

1. Land the bounded fail-closed Tester bind-readiness predicate, then run fresh isolated Tester proof.
2. Run current-main supported-Compose closure for health, chat, persistence/readback, retrieval, queue/worker, locks, and events; requalify Chroma.
3. Requalify private-preview provider/persistence/canary and CE-L1 live execution/readback with current credentials and source-thread evidence.
4. Close Project ownership, Safari upload, authenticated browser, Watchdog, retention, and hosted-sandbox gates.

## Release definition right now

- [x] Supported local Compose path and Beta boundary are defined on `main`.
- [x] Support doctrine, bounded/internal surfaces, qualification-pending work, and unproven evidence remain distinct.
- [ ] Current-tip Compose proves healthy startup, model inventory, terminal chat, persistence/readback, retrieval, and event delivery.
- [ ] Queue, worker bind readiness, locks, migrations, configuration, recovery, browser, and account-import claimed-path gates are green.
- [ ] Every claimed preview/provider lane has current-main proof for execution, durable readback, isolation, and recovery where applicable.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
