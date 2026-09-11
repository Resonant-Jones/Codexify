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

`main` remains in local-first Beta hardening with a gated private-preview lane. Recent mainline work completed the evidence-bounded partition and retirement of legacy Project `1`, then defined a narrow disposition policy for globally seeded unbound Persona Profile debt. No new release-ready runtime path or Beta support claim was established.

## What changed recently

- Completed the separately authorized ADR-081/ADR-085 preservation repair for legacy Project `1`: eight canonically owned threads and their dependencies were deterministically partitioned into account-owned General Projects, preservation and zero-reference gates passed on a restored copy and live PostgreSQL, and the obsolete shared source was retired without assigning it an owner. Project `1` remains absent; the live Alembic revision remains `d4e0f2a5b7c9`.
- Accepted [ADR-086](./adr/086-legacy-unbound-persona-profile-retirement.md) after canonical traversal then exposed three historical globally seeded, unbound Persona Profiles (`profile-1`, `profile-2`, and `profile-3`). Exhaustive admissible ownership reconstruction for `profile-1` proved no canonical owner. ADR-086 permits retirement evaluation only for proven legacy seed rows with zero canonical owner evidence, zero references and dependencies, complete preservation, and a successful restored-copy rehearsal. It creates no owner fallback, permanent ownerless profile class, system-profile conversion, automatic delete rule, migration skip, or live mutation authority.
- Added repository migration and PostgreSQL proof for account-scoped Project display-name uniqueness: `UNIQUE (user_id, name)` replaces global name uniqueness. Static Alembic head is `7e5a5fccf253`; the live preview database remains at blocked revision `d4e0f2a5b7c9`.
- Added a tested account-owned `General` provisioning helper that requires an explicit canonical `user_id`, reuses or creates one structural General, fails closed on missing/duplicate state, and leaves commit control to the caller. It is not integrated into Private Preview repair or startup.
- The 2026-09-11 mainline log records no additional implementation or runtime qualification. Chroma topology and provider-free Pi required-tool/compaction evidence remain bounded.

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
- Do not treat the completed Project `1` partition/retirement, ADR-086 disposition policy, repository migration, or provisioning helper as Alembic completion, Persona retirement eligibility, Private Preview recovery, post-repair account-isolation proof, or release readiness.
- Do not treat Persona persistence, acceptance snapshots, focused UI tests, UMS contracts/readers, Pi proofs, CE-L1 wiring, hosted-sandbox partial conformance, Watchdog contracts, or connector consent code as live release qualification.
- Do not infer shipped reality from another checkout, local-only artifacts, mutable `latest`, planning language, or docs alone. Browser proof, Safari multipart repair, federation, attachments, and cross-node People messaging remain deferred or unproven.

## Active blockers

- Current-tip supported-Compose closure is missing: startup, model inventory, terminal chat, persistence/readback, retrieval, queue/worker, locks, and terminal events.
- Local `main` is 8 commits ahead and 4 commits behind `origin/main`; no remote reconciliation or publication proof exists for this audit baseline.
- Tester worker bind-readiness repair and fresh isolated runtime proof remain open.
- Private-preview Chroma topology implementation/qualification and matching application deployment remain blocked; provider, persistence, isolation, observability, and approved canary gates remain open.
- Canonical Alembic traversal is blocked at `e5a9c2f7b4d1` by `profile-1`, `profile-2`, and `profile-3`, three historical globally seeded Persona Profiles with no canonical bindings. Ownership reconstruction for `profile-1` is exhausted with no proven canonical owner. ADR-086 resolves the disposition-policy question, but all three candidates still require individual provenance, owner-evidence, FK and semantic dependency, preservation, and restored-copy rehearsal proof before any live retirement.
- Private Preview application writers remain quiesced at Alembic revision `d4e0f2a5b7c9`. Project `1` remains retired, but Persona retirement, complete Alembic traversal, startup, account-isolation proof, CE-L1 provider readback, Chroma qualification, browser/import, trusted connector, Watchdog, immutable image retention, and hosted-sandbox qualification remain unclosed.

## This week’s priorities

1. Reconcile the local-main publication baseline before using remote state for release accounting.
2. Run fresh current-tip supported-Compose and isolated Tester proof across health, chat, persistence, retrieval, queue/worker, locks, and events.
3. Implement and qualify the ADR-067 named-volume Chroma path before any private-preview application restart.
4. Qualify `profile-1`, `profile-2`, and `profile-3` individually under ADR-086, preserve and rehearse any eligible retirement on a restored copy, and perform no live retirement or resumed Alembic traversal without separate explicit authorization. Do not assign an inferred owner or silently skip an unbound source.
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
