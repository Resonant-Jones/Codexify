## Purpose

This file is the canonical short-form source of truth for Codexify’s current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-11

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a gated private-preview lane. Recent local-main work completed the legacy Project and Persona retirements and proved Private Preview database migration/bootstrap recovery at `7e5a5fccf253`. Private Preview application runtime recovery is not yet proven. No new release-ready runtime path or Beta support claim was established.

## What changed recently

- Completed Project `1` partition/retirement under ADR-081/ADR-085 and profiles `profile-1`, `profile-2`, `profile-3` retirement under ADR-086. Project `1`, retired profiles, and retired-profile bindings/subjects remain absent after migration.
- Implemented and proved account-scoped default Project seeding. The live canonical migrator completed Alembic traversal from `d4e0f2a5b7c9` to `7e5a5fccf253` and post-Alembic seeding with exit zero. A second complete run exited zero with all 119 table manifests identical. General Project IDs are `6,7,8,9,10`; ownerless Projects and `local` Generals are zero.
- Preserved 72 threads, 805 messages, all eight repaired thread placements, all 20 affected messages, canonical account ownership, and replacement Project ownership. Normal traversal performed the disclosed single legacy Project-3 owner reconciliation and Project-2 description normalization; unexpected owner changes were zero. All 17 Project FK checks found zero orphans. A verified read-only post-migration backup is retained.
- The recovery regression gate is green after the separate stale-head test correction: 91 distinct tests passed, zero failed; targeted/full follow-through totals 109 successful executions. The test correction changes no runtime semantics. See the [live canonical migration/bootstrap recovery proof](./proofs/runtime/2026-09-11-private-preview-live-canonical-alembic-recovery-proof.md) for the artifact chain, backup metadata, preservation, and idempotence evidence.
- **Private Preview database migration/bootstrap recovery: proven. Private Preview application runtime recovery: not yet proven.** Application writers remain quiesced at the retained proof boundary; no startup or release qualification is inferred.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- `main` contains focused code and tests for ordinary chat, durable threads/messages/tasks, projects, document artifacts, account-import staging, Persona Profile authority, and same-node People/Share behavior.
- Private-preview migration preservation/readback, scheduled reconciliation, Guardian secret rotation, and Cloudflare ingress have bounded evidence; they do not admit guests or widen Beta.
- The UMS compatibility reader is explicitly read-only and fail-closed for unsupported source families; canonical memory export/restore is contract-only at UMS-04A.
- Pi 0.82.1 wrapper, identity, framing, telemetry, required-tool, and compaction work remains internal or qualification evidence, not a user-facing release promise.

## Not yet true / do not assume

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or application runtime recovery closure.
- Do not assume a fresh Tester bind-readiness repair or isolated runtime qualification; the historical diagnosis remains static.
- Do not assume private-preview Chroma startup/retrieval, matching application deployment, provider execution, persistence, observability, account isolation, or non-admin canary readiness.
- Do not treat completed database migration/bootstrap recovery as backend health, authenticated route availability, worker health, chat completion, Chroma/provider integration, post-repair authenticated account-isolation proof, or release readiness.
- Do not treat Persona persistence, acceptance snapshots, focused UI tests, UMS contracts/readers, Pi proofs, CE-L1 wiring, hosted-sandbox partial conformance, Watchdog contracts, or connector consent code as live release qualification.
- Do not infer shipped reality from another checkout, local-only artifacts, mutable `latest`, planning language, or docs alone. Browser proof, Safari multipart repair, federation, attachments, and cross-node People messaging remain deferred or unproven.

## Active blockers

- Current-tip supported-Compose closure is missing: startup, model inventory, terminal chat, persistence/readback, retrieval, queue/worker, locks, and terminal events.
- At recovery documentation start `0cdf7618cabd1cc07f976ff188fc19a6db322e6d`, local `main` was 15 commits ahead and 4 behind fetched `origin/main` (`cb551de1866715ef421026203ffe2a87cec8aaca`). Remote reconciliation and publication remain open.
- Tester worker bind-readiness repair and fresh isolated runtime proof remain open.
- Private-preview Chroma topology implementation/qualification and matching application deployment remain blocked; provider, persistence, isolation, observability, and approved canary gates remain open.
- Private Preview application writers remain quiesced at the retained recovery boundary, with live Alembic revision `7e5a5fccf253` and complete database/bootstrap recovery proven. Application startup, authenticated account-isolation proof, worker coherence, CE-L1 provider readback, Chroma qualification, browser/import, trusted connector, Watchdog, immutable image retention, and hosted-sandbox qualification remain unclosed.

## This week’s priorities

1. Reconcile the local-main publication baseline before using remote state for release accounting.
2. Run fresh current-tip supported-Compose and isolated Tester proof across health, chat, persistence, retrieval, queue/worker, locks, and events.
3. Implement and qualify the ADR-067 named-volume Chroma path before any private-preview application restart.
4. Separately authorize **Start and qualify Private Preview after database recovery** after the required Chroma/deployment prerequisites: prove backend startup, service health, authenticated account-scoped reads, worker coherence, and minimum deployed runtime behavior. Database recovery documentation does not authorize startup.
5. Requalify CE-L1/provider readback and close the canary, browser/import, connector, Watchdog, retention, and hosted-sandbox gates.

## Release definition right now

- [x] The local-only Compose path and present Beta boundary are defined on `main`.
- [x] Internal, bounded, qualification-pending, and out-of-Beta surfaces remain separate from supported claims.
- [ ] Current-tip Compose proves healthy startup, model inventory, terminal chat, persistence/readback, and retrieval.
- [ ] Queue, worker readiness, locks, migrations, configuration, recovery, browser, and claimed import-path evidence gates are green.
- [ ] Every claimed preview/provider lane has current-main proof for execution, durable readback, isolation, and recovery where applicable.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
