## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-10-26

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated Private Preview lane. Since the prior audit, only saved-widget architecture review and acceptance changes landed; no fresh supported-path runtime qualification or default Beta widening is established. The current release gate remains `HOLD`.

## What changed recently

- Admitted the existing `share` route alongside `direct_messages` in the private-preview profile; this does not widen default Beta support.
- Fixed personal-fact candidate listing to use shared SQL filters, deterministic pagination/counting, and batched evidence reads; focused tests are merged, not a supported-path qualification.
- Fixed People search handling of the `@` sigil and completed related inbox/share-surface coverage; this remains bounded messaging behavior.
- Accepted the saved-widget identity/revision architecture (ADR-102, accepted 2026-10-25); acceptance is architecture only, with no saved-widget persistence, listing, invocation, editing, deletion, or export path implemented and the Library Widgets filter still unavailable.
- Resolved the saved-widget contract review findings and synchronized the accepted ADR, contract, ADR index, and KB projections; this remains architecture-only evidence.
- Added personal-fact pipeline baseline documents; they are proposals and analysis, not accepted runtime scope.
- No fresh integrated-tip supported-Compose qualification, provider inference, or complete export/restore qualification landed on local `main`; the release posture is unchanged since the prior audit.

## Current supported reality

- The named supported install path is local Docker Compose profile `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported envelope covers local inference, ordinary chat, durable threads/messages/tasks, supported document ingestion and retrieval, account ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Mainline has bounded evidence at evaluated tips for topology, health, browser chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, cancellation, and deadline behavior.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- UMS ORM imports and migration-to-ORM parity are recorded; this does not establish complete UMS or supported-Compose qualification.
- Private Preview is opt-in: Whoosh'd remains the default local lane, DeepSeek is the only admitted cloud lane, and its profile admits bounded same-node messaging plus share routes; neither is default Beta support or end-to-end qualified here.
- The legacy continuity operator surface is fail-closed for remote, Preview, and multi-user execution because operator credentials do not establish account authority.

## Not yet true / do not assume

- Do not call the supported path release-ready; the latest complete supported-Compose qualification is `HOLD`.
- Do not infer current-tip restart/shutdown recovery, browser/event/provenance coherence, ordinary chat after restart, or a complete natural import-to-recall path.
- Do not infer exact unavailable-model rejection; the recorded complete Compose proof accepted work with model substitution and no assistant fallback flag.
- Do not treat the delegation canary as successful worker-path execution: it stopped at a `reasoning_effort` mismatch before provider execution, and worker egress was observed despite `allow_network=false`.
- Do not treat the merged recovery/retention decision brief as accepted architecture, implemented export/restore, object-store write-back, or lifecycle-cleanup proof.
- Do not treat the accepted saved-widget architecture (ADR-102) as implemented, runtime-qualified, or release-supported: Saved Widget storage, authoritative listing, cross-thread invocation, conversational revision editing, deletion behavior, widget export/restore, and Library Widgets filter availability do not exist, and Web Audio or canvas widget compatibility remains unqualified pending real-browser proof.
- Do not promote account-owned connectors, direct messaging/share, activation, browser host/import, Watchdog, hosted sandbox, Atlas, Pi, federation, or autonomous coding-worker work to default Beta support without current-main qualification.
- Do not treat the saved-widget contract or personal-fact pipeline baseline as accepted product scope, or focused candidate/search tests as live release proof.
- Share links in the private-preview route are bearer credentials; links without `expires_in_days` do not expire and no revocation endpoint exists.
- Branch-only implementation, origin-only accounting, uncommitted checkout work, and local-only commits are not shipped `main` reality.
- The current-state knowledge-graph node parses but its freshness is stale; validity is not current release proof.

## Active blockers

- A fresh current-tip supported-Compose qualification is missing, including model rejection, browser/event/provenance coherence, restart recovery, and ordinary chat after restart.
- The UMS/Chronicle lane retains one inherited stale migration-head assertion, and blocked Chronicle HTTP coverage still requires execution against the corrected baseline.
- The explicit-model worker/test contradiction must be resolved with fail-closed behavior and no silent substitution.
- The delegated worker-to-adapter `reasoning_effort` contract mismatch must be resolved and re-proven before any delegation execution claim is accepted.
- The new-thread authored-message projection gap and natural import-to-recall scope proof remain open.
- Export/restore and conversation-lifecycle coverage remains incomplete: v3 is the public export default, v4 compatibility flags conflict with recorded restore evidence, binary write-back is unsupported, and cleanup dependencies lack complete proof.
- Private-preview messaging/share admission has route-mount and focused-test evidence but lacks current end-to-end live proof; bearer-link expiry and revocation remain unresolved risks.
- Release metadata freshness and local-main publication state must be reconciled before treating them as shared release evidence.

## This week’s priorities

1. Freeze the evaluated local `main` SHA and run the complete supported-Compose proof bundle.
2. Repair the stale migration-head expectation and execute the blocked Chronicle HTTP regression cases.
3. Close the explicit-model rejection and delegated adapter contract contradictions before provider execution.
4. Reprove new-thread projection, browser/event coherence, restart recovery, and ordinary chat on one evaluated tip.
5. Resolve export/restore/retention, import-to-recall, and private-preview messaging/share proof gaps.

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
