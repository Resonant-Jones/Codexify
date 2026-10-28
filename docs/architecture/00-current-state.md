## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-10-27

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated Private Preview lane. The latest merged work adds bounded saved-widget artifact validation, repairs a generated-UI navigation containment defect, and lands the canonical Saved Widget storage foundation, but does not establish saved-widget support or fresh supported-path qualification. The current release gate remains `HOLD`.

## What changed recently

- Added server-side saved-widget artifact parsing, provenance checks, Guardian E1-E6 eligibility evaluation, and rejection of unavailable local dependencies; focused tests are merged, not a persistence or release qualification.
- Repaired generated-UI same-frame navigation containment with a trusted outer wrapper and `frame-src 'none'`; Chrome 156 evidence records 24 blocked navigation attempts with zero fixture requests.
- Corrected the committed navigation reproduction after a fixture defect; the pre-repair failure remains recorded separately from the repair result.
- The repair is bounded to Chrome 156 evidence: the Playwright suite cannot launch on this host, and cross-browser, Tauri, and supported-release equivalence remain unproven.
- Implemented the canonical Saved Widget storage foundation for the accepted ADR-102 identity/revision architecture: one account-owned widget record, immutable revision snapshots keyed `(widget_id, revision)`, a forward-only current-revision pointer, and snapshot provenance that survives source-thread deletion. Focused migration and persistence evidence was re-run against a disposable PostgreSQL instance; this is storage only, not a save capability, and it is not a supported-path qualification.
- Fixed personal-fact candidate listing to use shared SQL filters, deterministic pagination/counting, and batched evidence reads; focused tests are merged, not a supported-path qualification.
- Fixed People search handling of the `@` sigil and completed related inbox/share-surface coverage; this remains bounded messaging behavior.
- Qualified same-node private-preview messaging end to end against the running preview at serving commit `57184dfbe`, using synthetic approved test accounts; the proof is same-node only and does not qualify default Beta, cross-node messaging, or share links (see `./proofs/private-preview-direct-messaging-e2e-proof.md`). The running preview is pinned to a tip that predates the `@`-sigil People-search fix, so that miss is still observable on the live origin until the serving worktree is re-reconciled.
- Implemented recipient-local direct-message read state and integrated it onto the reconciled mainline on branch `integrate/read-state-onto-reconciled-main-20261027` (reconciled main `bf9016369`): a shared caller-local unread projection, an explicit caller-asserted read watermark, and a monotonic per-participant read cursor whose concurrent updates are serialized against the participant authority row; the projection is shared across the Inbox, the launcher badge, and the floating window rather than duplicated per surface. Focused backend evidence includes the read-cursor concurrency and migration proofs against a disposable PostgreSQL 16.2 (a locally patched build, not the stock container image), with focused frontend suites. This is test-evidenced on that integration branch only — it is not merged to `main`, not deployed, and not live-qualified on the running preview.
- No fresh integrated-tip supported-Compose qualification, provider inference, or complete export/restore qualification landed on local `main`; the release posture remains unchanged.
- Reconciled local audit history with `origin/main` through `8f764549d` while preserving the local reconciliation history; no push was performed, and the stored `origin/main` is now fully contained in local `main`.
- Restored the four missing UMS ORM mappings and recorded focused evidence: 124 tests passed, with one inherited stale migration-head assertion remaining; Chronicle HTTP cases were collected but not executed.
- Added fail-closed account-boundary checks for the legacy continuity operator surface outside local single-user execution, with focused route coverage.
- Strict account-purpose HTTP and WebSocket boundaries accept the documented HS256 `account_session` JWT shape using the preferred session secret or JWT fallback; Private Preview still requires a live stored session and approved account. This is bounded code/test evidence, not public-ingress or release qualification.
- Recorded bounded private-preview restart, schema, health, and mount evidence; no ordinary chat, browser interaction, provider inference, or full supported-Compose run was performed.
- Merged recent Library, shell, chat/session-rail, task-cancellation, tool-loop, and accepted-turn identity changes; these remain implementation evidence, not integrated-tip release qualification.

## Current supported reality

- The named supported install path is local Docker Compose profile `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported envelope covers local inference, ordinary chat, durable threads/messages/tasks, supported document ingestion and retrieval, account ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Mainline has bounded evidence at evaluated tips for topology, health, browser chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, cancellation, and deadline behavior.
- Mainline has bounded saved-widget eligibility/provenance code, the canonical Saved Widget storage foundation with focused disposable-PostgreSQL evidence, and generated-UI containment evidence; this is not saved-widget lifecycle support or a default Beta claim.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- UMS ORM imports and migration-to-ORM parity are recorded; this does not establish complete UMS or supported-Compose qualification.
- Private Preview is opt-in: Whoosh'd remains the default local lane, DeepSeek is the only admitted cloud lane, and its profile admits bounded same-node messaging plus share routes. Same-node messaging now carries live end-to-end evidence on the running preview (see `./proofs/private-preview-direct-messaging-e2e-proof.md`); that proof qualifies same-node messaging only, and share-link bearer expiry/revocation, cross-node discovery and transport, unread indicators and persisted read state, and default Beta support remain unqualified. Recipient-local read state is implemented and test-evidenced on the read-state integration branch; because it is neither merged to `main` nor deployed, the running preview does not serve it and no live read-state evidence exists.
- The legacy continuity operator surface is fail-closed for remote, Preview, and multi-user execution because operator credentials do not establish account authority.

## Not yet true / do not assume

- Do not call the supported path release-ready; the latest complete supported-Compose qualification is `HOLD`.
- Do not infer current-tip restart/shutdown recovery, browser/event/provenance coherence, ordinary chat after restart, or a complete natural import-to-recall path.
- Do not infer exact unavailable-model rejection; the recorded complete Compose proof accepted work with model substitution and no assistant fallback flag.
- Do not treat the delegation canary as successful worker-path execution: it stopped at a `reasoning_effort` mismatch before provider execution, and worker egress was observed despite `allow_network=false`.
- Do not treat the merged recovery/retention decision brief as accepted architecture, implemented export/restore, object-store write-back, or lifecycle-cleanup proof.
- Do not treat saved-widget artifact validation, the canonical storage foundation, or the accepted saved-widget architecture (ADR-102) as lifecycle implementation, runtime qualification, or release support: an authenticated save API, explicit human promotion, authoritative listing, cross-thread invocation, conversational revision editing, deletion and archive transition APIs, widget export/restore, and Library Widgets filter availability remain unimplemented; Web Audio and canvas compatibility remain unqualified.
- Do not treat the Chrome 156 containment repair as cross-browser, Tauri, Playwright, or supported-Compose proof; Chrome 156 is the only reported browser-specific containment qualification, the committed Playwright suite remains blocked by browser launch failure on the previously reported macOS host, and a launch failure is not a containment failure.
- Do not promote account-owned connectors, direct messaging/share, activation, browser host/import, Watchdog, hosted sandbox, Atlas, Pi, federation, or autonomous coding-worker work to default Beta support without current-main qualification.
- Do not treat the saved-widget contract or personal-fact pipeline baseline as accepted product scope, or focused candidate/search tests as live release proof.
- Share links in the private-preview route are bearer credentials; links without `expires_in_days` do not expire and no revocation endpoint exists.
- Branch-only implementation, origin-only accounting, uncommitted checkout work, and local-only commits are not shipped `main` reality.
- Do not read the branch-only recipient-local read state as shipped or live-qualified behavior: it is implemented and test-evidenced on the read-state integration branch, the running preview serves commit `57184dfbe` without it, and no live read-state or unread-indicator evidence exists.
- The current-state knowledge-graph node parses but its freshness is stale; validity is not current release proof.

## Active blockers

- A fresh current-tip supported-Compose qualification is missing, including model rejection, browser/event/provenance coherence, restart recovery, and ordinary chat after restart.
- Cross-browser qualification of the integrated generative-ui containment repair is missing: the Chrome 156 CDP proof covers its evaluated revision, and the committed Playwright suite cannot launch Chromium in the reported host, so the repair is not qualified beyond the single evaluated browser.
- The UMS/Chronicle lane retains one inherited stale migration-head assertion, and blocked Chronicle HTTP coverage still requires execution against the corrected baseline.
- The explicit-model worker/test contradiction must be resolved with fail-closed behavior and no silent substitution.
- The delegated worker-to-adapter `reasoning_effort` contract mismatch must be resolved and re-proven before any delegation execution claim is accepted.
- The new-thread authored-message projection gap and natural import-to-recall scope proof remain open.
- Export/restore and conversation-lifecycle coverage remains incomplete: v3 is the public export default, v4 compatibility flags conflict with recorded restore evidence, binary write-back is unsupported, and cleanup dependencies lack complete proof.
- Private-preview same-node messaging is live end-to-end qualified on the running preview (two approved synthetic test accounts on one node: search, request, acceptance, reply, read-back, second message, reload persistence, decline, and prevented further contact). Still open: share-link bearer expiry and revocation, cross-node discovery/transport, and live qualification of the unread indicator and persisted read state. Recipient-local read state is implemented and test-evidenced on the read-state integration branch — unread projection, explicit read watermark, and a monotonic per-participant read cursor with serialized concurrent updates — but it is not merged to `main`, not deployed, and not live-qualified; the running preview still serves commit `57184dfbe` without it.
- The saved-widget lane remains blocked on an authorized human-promotion operation, authoritative listing, and complete browser qualification; current evidence proves bounded validation, the canonical storage foundation, and a Chrome 156 containment repair.
- Release metadata freshness and local-main publication state must be reconciled before treating them as shared release evidence.

## This week’s priorities

1. Freeze the evaluated local `main` SHA and run the complete supported-Compose proof bundle.
2. Repair the stale migration-head expectation and execute the blocked Chronicle HTTP regression cases.
3. Close the explicit-model rejection and delegated adapter contract contradictions before provider execution.
4. Reprove new-thread projection, browser/event coherence, restart recovery, and ordinary chat on one evaluated tip.
5. Resolve export/restore/retention and import-to-recall proof gaps; private-preview same-node messaging is closed by live proof, while share-link expiry/revocation, cross-node messaging, and saved-widget qualification gaps remain open.

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
