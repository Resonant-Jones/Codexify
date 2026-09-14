## Purpose

This file is the canonical short-form source of truth for Codexify’s current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-14

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a gated private-preview lane. Recent mainline work added bounded deadline/lock implementation and Chroma topology changes, but no release-ready runtime path or new Beta support claim was established. Private Preview application runtime recovery remains unproven.

## What changed recently

- ADR-087 implementation landed on `main` for acceptance-time deadline snapshots and deadline-aware turn-lock renewal; provider/worker/tool/PostgreSQL enforcement, finite drain, and runtime proof remain open.
- Private Preview named-volume Chroma topology landed with contract coverage; bounded single-backend storage recovery remains distinct from queue/worker, multiprocess, retrieval, or application qualification.
- Persona/turn-lock recovery fixture alignment and DLG verification-ancestry checks landed; these are test/provenance maintenance and do not widen release support.
- The Atlas architecture-map prototype landed on `main`; it remains a prototype surface, not a supported release path.
- The 2026-09-14 mainline accounting record reports no same-day implementation or proof work.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- `main` contains focused code and tests for ordinary chat, durable threads/messages/tasks, projects, document artifacts, account-import staging, Persona Profile authority, and same-node People/Share behavior.
- Private-preview migration preservation/readback, scheduled reconciliation, Guardian secret rotation, Cloudflare ingress, and bounded named-volume Chroma storage recovery have evidence; they do not admit guests or widen Beta.
- The UMS compatibility reader is read-only and fail-closed for unsupported source families; canonical memory export/restore remains contract-only at UMS-04A.
- Pi 0.82.1 wrapper, identity, framing, telemetry, required-tool, and compaction work remains internal or qualification evidence, not a user-facing release promise.

## Not yet true / do not assume

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or application runtime recovery closure.
- Do not treat merged ADR-087 acceptance-time fields and lock renewal as end-to-end deadline enforcement, graceful stop, finite drain, or provider/tool cancellation proof.
- Do not assume fresh Tester bind-readiness repair or isolated runtime qualification; the historical diagnosis remains static.
- Do not infer semantic retrieval, multiprocess Chroma concurrency, queue/worker safe-start, matching application deployment, provider execution, persistence, observability, account isolation, or approved canary readiness from bounded storage recovery.
- Do not treat Persona persistence, acceptance snapshots, focused tests, Pi proofs, CE-L1 wiring, connector consent, Watchdog contracts, Atlas prototype work, or hosted-sandbox partial conformance as live release qualification.
- Do not infer shipped reality from another checkout, local-only artifacts, mutable `latest`, planning language, or docs alone. Browser proof, Safari multipart repair, federation, attachments, and cross-node People messaging remain deferred or unproven.

## Active blockers

- ADR-087 graceful operator shutdown remains blocked pending end-to-end worker, provider streaming, child execution, PostgreSQL persistence/cleanup, turn-lock, and finite-drain enforcement plus runtime proof.
- Current-tip supported-Compose closure is missing across startup, model inventory, terminal chat, persistence/readback, retrieval, queue/worker, locks, and terminal events.
- Checked-out `main` is 27 commits ahead and 13 commits behind the local `origin/main` ref; publication and remote reconciliation remain open.
- Tester worker bind-readiness and fresh isolated runtime proof remain open.
- Private Preview still lacks queue/worker safe-start, multiprocess Chroma, semantic retrieval, matching application deployment, provider-backed chat, authenticated persistence/isolation, observability, and approved canary proof.
- CE-L1/provider readback, browser/import, trusted connector, Watchdog, immutable Docker image retention, hosted sandbox, and private-preview application startup qualification remain unclosed.

## This week’s priorities

1. Reconcile the local-`main` publication baseline before using remote state for release accounting.
2. Run fresh current-tip supported-Compose and isolated Tester proof across health, chat, persistence, retrieval, queue/worker, locks, and events.
3. Complete ADR-087 enforcement and qualify finite drain, graceful stop, late-result handling, and durable terminal truth.
4. Resume Private Preview qualification at queue/worker safe-start and multiprocess named-volume Chroma use, then prove authenticated persistence and isolation.
5. Requalify CE-L1/provider, browser/import, connector, Watchdog, retention, and hosted-sandbox gates separately.

## Release definition right now

- [x] The local-only Compose path and present Beta boundary are defined on `main`.
- [x] Internal, bounded, qualification-pending, and out-of-Beta surfaces remain separate from supported claims.
- [ ] Current-tip Compose proves healthy startup, model inventory, terminal chat, persistence/readback, and retrieval.
- [ ] Queue, worker, deadline, graceful-stop, lock, migration, configuration, recovery, browser, and claimed import-path evidence gates are green.
- [ ] Every claimed preview/provider lane has current-main proof for execution, durable readback, isolation, and recovery where applicable.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
