## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-10-28

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated Private Preview lane. Recent merges harden account authority, consent, terminal-state evidence, transport selection, and Saved Widget persistence, but none establishes fresh supported-path qualification. The release gate remains `HOLD`.

## What changed recently

- Merged account-bound agent run readback and fail-closed cancellation behavior; unsupported cancellation remains unavailable rather than mutating state.
- Added account consent and scoped settings enforcement for automatic personal-fact collection; this is privacy/authority hardening, not a broader memory release claim.
- Reconciled durable chat terminal/readback assertions, Whoosh'd transport-selection checks, and shared evidence release-truth contracts; these are bounded code/test evidence.
- Merged the canonical Saved Widget storage foundation: account-owned identity, immutable revision snapshots, forward-only current revision, and retained provenance. This is storage only, not lifecycle support.
- Unified the mainline Alembic graph with a no-DDL merge revision `7f2c9e1a4b63` joining the Saved Widget head `a6b9d2e4f701` and the automatic-collection consent head `c59e4d1a28f0`, leaving one head. The previous two-head state was not cosmetic: it made every "upgrade to head" test on the Saved Widget and consent surfaces fail with `MultipleHeads`, and the merge repair takes that surface from 13 failed and 45 errors to 153 passed. A full backend suite run on the single-head candidate repairs 595 previously failing node ids against the same-tree baseline, with no regression; 275 pre-existing failures remain inherited. Disposable PostgreSQL 16.2 (a locally patched build) evidence only; see [the promotion proof](./proofs/runtime/2026-10-28-saved-widget-alembic-main-promotion-proof.md) and [the combination proof](./proofs/runtime/2026-10-28-read-state-main-head-merge-proof.md).
- Joined the read-cursor branch to that unified head with a second no-DDL merge revision `3a91d7c4e8b2`, so the mainline carries Saved Widget storage, account consent, and participant-local read state in one Alembic lineage with a single head `3a91d7c4e8b2`. Both `7f2c9e1a4b63` and the read-cursor revision `b3c8d1e5f7a2` remain intact as its parents; see [the read-state integration proof](./proofs/runtime/2026-10-28-read-state-main-head-merge-proof.md).
- Qualified the committed migration chain on the **supported** PostgreSQL path: the pinned `postgres:15` image, PostgreSQL 15.19 — not the locally patched 16.2 build used for the earlier evidence. An empty database and a restored copy of the live Preview database, at its real revision `f0d7c4b2a198`, both upgrade to the single head `3a91d7c4e8b2`; the populated copy preserves every pre-existing row, including 113,498 chat messages and the live direct-messaging conversations, messages, consents, relationships and participants. The Preview database itself was only read. The real deployment mechanism was rehearsed as well, using the actual `codexify-backend-runtime:latest` image and the actual `migrator` command against the restored copy, which exposed two deployment traps now on record: the backend container entrypoint's `alembic` call is a silent no-op because the runtime image has no `alembic` executable on `PATH` (only `python -m alembic`), and the `migrator` service deliberately carries no `guardian/` mount, so it reads migrations from the **baked image** — the currently deployed image holds 123 versions and heads at `f0d7c4b2a198`, with none of the Saved Widget, consent, or read-cursor revisions. A deployment therefore requires, in order: rebuild the backend runtime image from the new source, run `migrator`, then recreate the application containers. This qualifies the migration on the deployed database version; it is not a deployment and not a live feature qualification (see [the runtime qualification proof](./proofs/runtime/2026-10-29-runtime-qualification-postgres15-proof.md)).
- Retained the generated-UI navigation containment repair and Chrome 156 evidence from the prior audit; cross-browser and supported-release equivalence remain unproven.
- Fixed personal-fact candidate listing to use shared SQL filters, deterministic pagination/counting, and batched evidence reads; this remains bounded behavior, not a supported-path qualification.
- Fixed People search handling of the `@` sigil and completed related inbox/share-surface coverage; this remains bounded messaging behavior.
- Qualified same-node private-preview messaging end to end against the running preview at serving commit `57184dfbe`, using synthetic approved test accounts; the proof is same-node only and does not qualify default Beta, cross-node messaging, or share links (see `./proofs/private-preview-direct-messaging-e2e-proof.md`).
- Implemented recipient-local direct-message read state and integrated it onto this mainline: a shared caller-local unread projection, an explicit caller-asserted read watermark, and a monotonic per-participant read cursor whose concurrent updates are serialized against the participant authority row; the projection is shared across the Inbox, the launcher badge, and the floating window rather than duplicated per surface. Focused backend evidence includes the read-cursor concurrency and migration proofs against a disposable PostgreSQL 16.2 (a locally patched build, not the stock container image), with focused frontend suites. The committed migration chain is additionally qualified on the **supported** path — the pinned `postgres:15` image, PostgreSQL 15.19 — by upgrading both an empty database and a restored copy of the live Preview database from its real revision `f0d7c4b2a198` to the single head `3a91d7c4e8b2` with every pre-existing row preserved (see `./proofs/runtime/2026-10-29-runtime-qualification-postgres15-proof.md`). This is test-evidenced on the mainline only — it is not deployed and not live-qualified on the running preview, which still serves `57184dfbe`.
- No fresh integrated-tip supported-Compose qualification, provider inference, or complete export/restore qualification landed.
- Local `main` contains `origin/main` and carries the unified Alembic head and the read-state integration. The read-state combination and its proof receipts were pushed to `origin/main`; no deployment was performed, so origin-only work beyond that point is excluded from shipped claims.

## Current supported reality

- The named supported install path is local Docker Compose profile `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported envelope covers local inference, ordinary chat, durable threads/messages/tasks, supported document ingestion and retrieval, account ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Mainline has bounded evidence at evaluated tips for topology, health, browser chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, cancellation, and deadline behavior.
- Mainline now has account-scoped run-readback and consent-gated personal-fact code/test coverage, plus Saved Widget eligibility/provenance and storage evidence; none is a default Beta expansion.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- UMS ORM imports and migration-to-ORM parity are recorded; this does not establish complete UMS or supported-Compose qualification.
- Private Preview is opt-in: Whoosh'd remains the default local lane, DeepSeek is the only admitted cloud lane, and its profile admits bounded same-node messaging plus share routes. Same-node messaging now carries live end-to-end evidence on the running preview (see `./proofs/private-preview-direct-messaging-e2e-proof.md`); that proof qualifies same-node messaging only, and share-link bearer expiry/revocation, cross-node discovery and transport, unread indicators and persisted read state, and default Beta support remain unqualified. Recipient-local read state is implemented, test-evidenced, and integrated onto this mainline; because it is not deployed, the running preview does not serve it and no live read-state evidence exists.
- The legacy continuity operator surface is fail-closed for remote, Preview, and multi-user execution because operator credentials do not establish account authority.

## Not yet true / do not assume

- Do not call the supported path release-ready; the latest complete supported-Compose qualification is `HOLD`.
- Do not infer current-tip restart/shutdown recovery, browser/event/provenance coherence, ordinary chat after restart, or a complete natural import-to-recall path.
- Do not infer exact unavailable-model rejection; the recorded complete Compose proof accepted work with model substitution and no assistant fallback flag.
- Do not treat the delegation canary as successful worker-path execution: it stopped at a `reasoning_effort` mismatch before provider execution, and worker egress was observed despite `allow_network=false`.
- Do not treat merged regression suites, bounded evidence contracts, or focused database tests as live runtime qualification.
- Do not treat the merged recovery/retention decision brief as accepted architecture, implemented export/restore, object-store write-back, or lifecycle-cleanup proof.
- Do not treat Saved Widget validation, storage, or ADR-102 acceptance as lifecycle implementation: promotion, listing, invocation, editing, deletion, export/restore, Library Widgets filtering, Web Audio, and canvas qualification remain open.
- Do not treat Chrome 156 containment evidence as cross-browser, Tauri, Playwright, or supported-Compose proof; the committed Playwright suite remains blocked by browser launch failure on the reported host.
- Do not promote connectors, direct messaging/share, activation, browser host/import, Watchdog, hosted sandbox, Atlas, Pi, federation, or autonomous coding-worker work to default Beta support without current-main qualification.
- Share links in the private-preview route are bearer credentials; links without `expires_in_days` do not expire and no revocation endpoint exists.
- Branch-only implementation, origin-only accounting, uncommitted checkout work, and local-only commits are not shipped `main` reality.
- Do not read the recipient-local read state as shipped or live-qualified behavior: it is implemented, test-evidenced, and integrated onto this mainline, but the running preview serves commit `57184dfbe` without it, and no live read-state or unread-indicator evidence exists.
- The current-state knowledge-graph node parses but its freshness is stale; validity is not current release proof.

## Active blockers

- A fresh current-tip supported-Compose qualification is missing, including model rejection, browser/event/provenance coherence, restart recovery, and ordinary chat after restart.
- Cross-browser qualification of the integrated generative-UI containment repair is missing; Chrome 156 is the only reported browser-specific result and Playwright cannot launch on the reported host.
- The UMS/Chronicle lane retains one inherited stale migration-head assertion, and blocked Chronicle HTTP coverage still requires execution against the corrected baseline.
- The explicit-model worker/test contradiction and delegated worker-to-adapter `reasoning_effort` mismatch remain unresolved before provider execution claims.
- New-thread authored-message projection, natural import-to-recall, and complete scope-isolation proof remain open.
- Export/restore and conversation-lifecycle coverage remains incomplete: v3 is the public export default, v4 compatibility flags conflict with recorded restore evidence, binary write-back is unsupported, and cleanup dependencies lack complete proof.
- Private-preview same-node messaging is live end-to-end qualified on the running preview (two approved synthetic test accounts on one node: search, request, acceptance, reply, read-back, second message, reload persistence, decline, and prevented further contact). Still open: share-link bearer expiry and revocation, cross-node discovery/transport, and live qualification of the unread indicator and persisted read state. Recipient-local read state is implemented, test-evidenced, and integrated onto this mainline — unread projection, explicit read watermark, and a monotonic per-participant read cursor with serialized concurrent updates — but it is not deployed and not live-qualified; the running preview still serves commit `57184dfbe` without it.
- Saved Widget remains blocked on authorized promotion, authoritative listing, lifecycle operations, and complete browser qualification; current evidence proves bounded validation, the canonical storage foundation, and a Chrome 156 containment repair.
- Release metadata freshness and local-main publication state must be reconciled before treating them as shared release evidence.

## This week’s priorities

1. Freeze the evaluated local `main` SHA and run the complete supported-Compose proof bundle.
2. Repair the stale migration-head expectation and execute the blocked Chronicle HTTP regression cases.
3. Close the explicit-model rejection and delegated adapter contract contradictions before provider execution.
4. Reprove new-thread projection, browser/event coherence, restart recovery, and ordinary chat on one evaluated tip.
5. Resolve export/restore/retention and import-to-recall proof gaps; private-preview same-node messaging is closed by live proof, while share-link expiry/revocation, cross-node messaging, live read-state qualification, and saved-widget qualification gaps remain open.

## Release definition right now

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Bounded chat, cancellation, durable readback, retrieval, and authorization evidence exists at evaluated mainline tips.
- [ ] A fresh current-tip Compose run passes health, inventory, chat, durable readback, retrieval, browser projection, event delivery, and restart recovery.
- [ ] An unavailable explicit model fails before provider execution and cannot be silently substituted.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration, browser, import-recall, and scope-isolation gates are green on one evaluated tip.
- [ ] Delegated execution has a passing worker-to-adapter reasoning-effort contract and live proof.
- [ ] Claimed Preview or public-ingress paths have current live evidence, and changed release metadata points to the evaluated mainline.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
