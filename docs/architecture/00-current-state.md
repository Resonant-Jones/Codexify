## Purpose

This file is the canonical short-form source of truth for Codexify’s current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-10

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a gated private-preview lane. Recent commits added bounded Chroma topology governance, provider-free Pi required-tool/compaction proof, and a read-only legacy-General partition preflight. None establishes a new release-ready runtime path or widens the Beta support boundary.

## What changed recently

- Frozen private-preview Chroma handling under ADR-067: one Docker-managed named volume is the approved derived-store topology; the diagnosed host bind remains rejected. Implementation, fresh initialization, retirement/recovery, and authenticated deployment proof are pending.
- Added focused proof that Guardian required-tool selection is applied once and compaction continuation is suppressed for the required-tool turn. This remains internal/provider-free evidence; CE-L1 live execution and readback remain open.
- Added a read-only Project `1` partition preflight. Eight threads span three account owners, the legacy `local` General cannot be assigned to one account, and no mutation or new General Project was authorized.
- Landed the unified legacy-memory compatibility read surface and the UMS-04A export/restore contract. The former is read-only; the latter has no export/restore implementation or round-trip qualification.
- Persona Studio and ADR canonicalization work is present on `main`; it does not prove deployed private-preview Persona runtime or authenticated browser save/readback.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- `main` contains focused code and tests for ordinary chat, durable threads/messages/tasks, projects, document artifacts, account-import staging, Persona Profile authority, and same-node People/Share behavior.
- Private-preview migration preservation/readback, scheduled reconciliation, Guardian secret rotation, and Cloudflare ingress have bounded evidence; they do not admit guests or widen Beta.
- The UMS compatibility reader is explicitly read-only and fail-closed for unsupported source families; canonical memory export/restore is contract-only at UMS-04A.
- Pi 0.82.1 wrapper, identity, framing, telemetry, required-tool, and compaction work remains internal or qualification evidence, not a user-facing release promise.

## Not yet true / do not assume

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or recovery closure.
- Do not assume a fresh Tester bind-readiness repair or isolated runtime qualification; the historical diagnosis remains static.
- Do not assume private-preview Chroma startup/retrieval, matching application deployment, provider execution, persistence, observability, account isolation, or non-admin canary readiness.
- Do not assign Project `1` by majority thread ownership, chronology, display name, operator identity, or the legacy `local` value; ADR-081 requires exact owner evidence and the preflight found none.
- Do not treat Persona persistence, acceptance snapshots, focused UI tests, UMS contracts/readers, Pi proofs, CE-L1 wiring, hosted-sandbox partial conformance, Watchdog contracts, or connector consent code as live release qualification.
- Do not infer shipped reality from another checkout, local-only artifacts, mutable `latest`, planning language, or docs alone. Browser proof, Safari multipart repair, federation, attachments, and cross-node People messaging remain deferred or unproven.

## Active blockers

- Fresh supported-Compose closure is missing at the current `main` tip: startup, model inventory, terminal chat, persistence/readback, retrieval, queue/worker, locks, and terminal events.
- Tester worker bind-readiness repair and fresh isolated runtime proof remain open.
- Private-preview Chroma topology implementation/qualification and matching application deployment remain blocked; provider, persistence, isolation, observability, and approved canary gates remain open.
- Project `1` legacy-General ownership is unresolved; any partition, General creation, thread remap, or dependent-row treatment requires separate repair authorization and proof.
- CE-L1 live provider execution, durable result, source-thread readback, and private-preview DeepSeek rotation/requalification remain open.
- Authenticated browser/Safari import, trusted connector live proof, Watchdog policy/model, immutable image retention, and hosted-sandbox qualification remain unclosed.

## This week’s priorities

1. Land the fail-closed Tester bind-readiness predicate and run fresh isolated proof.
2. Re-run current-tip supported-Compose health, chat, persistence, retrieval, queue/worker, lock, and event proof.
3. Implement and qualify the ADR-067 named-volume Chroma path before any private-preview application restart.
4. Resolve Project `1` ownership through accepted evidence, then separately rehearse and authorize the partition repair.
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
