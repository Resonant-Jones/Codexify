## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-08-31

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening. Mainline now contains bounded Pi 0.82.1 runtime repairs and clean CE-L1 OAuth credential-readiness evidence, but no current-tip supported-Compose release closure or live CE-L1 executor proof.

The audited local `main` tip is two commits ahead of `origin/main`; the latest two Guardian Chat fixes are therefore current-checkout evidence, not remote-main release evidence.

## What changed recently

- Merged Pi 0.82.1 wrapper/API repairs, canonical `ModelRuntime` use, and the complete source-vendored locked runtime closure; source-relative smoke now reaches the OAuth-absent boundary.
- Cleanly requalified `openai-codex / gpt-5.6-sol / pi-coding-agent / 0.82.1` credential readiness without provider inference or prompt execution; CE-L1 remains open.
- Restored account-scoped project/thread document-artifact listing and generated-artifact preview paths with focused backend/frontend coverage; no migration or retrieval-policy change was made.
- Added the Node-addressed social identity and direct-messaging substrate (ADR-077): deliberate Node-scoped usernames, email-private discovery, canonical one-to-one conversations, durable plain-text messaging with idempotent retries, and participant-scoped authorization. Same-node path is focused-test-proven and live-two-user-proven on a scratch hosted runtime; the `direct_messages` route label is enabled only on `v1-friends-family-web` and quarantined on every other supported profile.
- Promoted direct-message pairs into canonical Relationships with multiple Conversations and durable Project/Thread origin provenance (ADR-078): one Relationship per unordered addressed Profile pair, Relationship membership as the sole participant authority, immutable Conversation origin (`created_by_profile_id` / `origin_project_id` / `origin_thread_id`), and participant-local Project placement. Existing Conversation/Message IDs and payloads survive the migration with origin honestly unknown (NULL). Focused route tests and a real-Postgres migration round-trip prove backfill, coexistence, and downgrade; no Project membership, invitation, retrieval, ambient-context, or Beta-claim widening occurs.
- Added the private-profile direct-message Inbox frontend projection over the ADR-077/078 model: a `/inbox` surface gated by the accepted `direct_messages` runtime route capability, Conversation-first listing with relationship-backed person filtering, General same-node conversation creation, bounded latest-message previews from an additive read projection (no schema change), and message read/send with stable idempotency keys. Focused backend and frontend tests pass; the surface stays confined to `v1-friends-family-web` and does not widen Beta support.
- Runtime-qualified same-node People messaging on `v1-friends-family-web` (see `proofs/2026-09-01-people-messaging-runtime-qualification-proof.md`): two real authenticated Profiles communicated through the UI; the global People overlay opened/closed from Guardian, Documents, and Settings without changing the underlying route; the Inbox rendered one row per Conversation (never collapsed into Relationships) and the person filter exposed all four Conversations under one Relationship; General and Project/Thread-origin Conversations were created from the integrated UI (origin captured from the active thread route, immutable across navigation); modal and floating sends persisted once each to their original `Conversation_ID`; the floating Conversation survived close-People, cross-AppShell navigation, minimize/restore with draft preservation, and backend restart; closing deleted nothing; the quarantined default profile failed closed with zero messaging network calls. Two narrow proof-blocking frontend repairs landed: the Guardian tools-menu launcher click no longer leaks into the menu container, and the People state owner now lives in AppShell so the floating window survives chrome switches. No backend or schema change.
- Preserved selected project context through new Guardian threads, tabs, and draft/rendering paths; the two latest fixes remain local to `main` pending remote-main integration.
- Added bounded tester/Whoosh'd runtime evidence, but the latest Tester Qwen completion attempt stopped at `TESTER_QWEN_BACKEND_UNHEALTHY`; these artifacts do not qualify supported-main release behavior.
- Requalified the OpenSSL tracer capsule and merged the expandable Composer and canonical SVG mark assets; neither widens the release promise.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The intended Beta Supported boundary remains local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, workspace-local retrieval, identity/ownership, migrations, and operator diagnostics; this is support doctrine, not current-tip qualification.
- Current `main` contains focused, account-scoped artifact projection/preview and Guardian Chat project-context repairs; focused tests do not substitute for supported-path or authenticated browser proof.
- Authenticated local Settings reads, the read-only Connections catalog, and bounded account-export imports retain their existing contracts; presence does not imply generic connector sync, provider inference, or cloud support.
- Pi 0.82.1 runtime identity, wrapper compatibility, and source-vendor loading are test-backed to the non-inference OAuth-readiness boundary. Pi execution remains internal and qualification-pending.
- Watchdog, Pi diagnostics, proof tooling, and tester-stack receipts remain internal or proof-only surfaces. Static and bounded tester evidence does not substitute for supported-path live proof.
- Stable local social addressing exists at Node_ID + Profile_ID, with deliberate Node-scoped usernames; peer-facing DM discovery never exposes account email; same-node direct messaging persists with Postgres authority and idempotent retries. Canonical Relationships support multiple Conversations, participant-local Project placement, and durable Project/Thread origin provenance (origin grants no Project/Thread access; placement grants no retrieval authority). A private-profile frontend Inbox projection exists at `/inbox` (relationship-backed person filtering, Conversation-first rows, General conversation creation, bounded previews) and is gated by the same route capability. This surface is quarantined on the default supported profile (`v1-local-core-web-mcp`) and enabled only on the hosted/private test profile `v1-friends-family-web`; it does not widen the Beta support boundary. On the private profile, same-node People messaging is runtime-qualified end-to-end (two-profile UI communication, portable floating Conversation across AppShell navigation with draft preservation, origin stability, restart persistence, and fail-closed unsupported-profile behavior); realtime delivery, read receipts, attachments, Guardian retrieval/authorship, Project invitations, and federation remain unimplemented.

## Not yet true / do not assume

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or recovery closure.
- Do not treat the clean CE-L1 OAuth prerequisite as live executor, coding-loop, persisted-result, or supported-Beta proof; `LIVE_EXECUTOR_PROVEN` was not emitted.
- Do not treat Tester Qwen, Whoosh'd, or prior local/Gemma completions as supported-main evidence; they are bounded tester or internal proof surfaces.
- Do not treat focused artifact or Guardian Chat tests, local-only `main` commits, or UI code-path repairs as authenticated browser or supported-Compose release proof.
- Do not assume Chroma fresh-state startup/retrieval qualification, Google Drive OAuth, Watchdog model execution, or immutable Docker image-retention behavior is closed.
- Do not infer shipped reality from feature branches, local work, proof from another checkout, planning language, mutable `latest`, or docs alone.
- Do not assume cross-node private messaging, node resolution/trust, Guardian messaging, or DM attachments: all remain unproven and explicitly deferred by ADR-077. The Inbox frontend projection is implemented but is private-profile-gated internal capability, not Beta-supported surface, and has no authenticated browser or live-UI proof yet. Do not assume Project invitation acceptance, Guardian Conversation retrieval, retrieval/disclosure scope policy, ambient DM context, Share Sheet UX, realtime delivery, read/unread state, or agent-authored peer messages: all remain unproven and explicitly deferred by ADR-078. The direct-messaging surface must not be treated as Beta-supported on the default profile.

## Active blockers

- Fresh supported-Compose closure has not been rerun at the current `main` tip after the merged local-gateway/profile alignment.
- One supported-profile proof bundle is still missing for health, chat, persistence/readback, retrieval, queue/worker, locks, terminal events, and recovery.
- Fresh-state Chroma startup/retrieval qualification remains unresolved; Chroma is derived state and no repair or historical restore is proven.
- CE-L1 still lacks live provider/model execution, terminal durable result, and source-thread readback despite the OAuth-readiness prerequisite passing.
- Watchdog qualification still requires an explicit available provider/model policy; disposable image-retention replay still requires the intended `desktop-linux` Docker authority.
- The audited `main` tip is two commits ahead of `origin/main`; remote-main release interpretation does not yet include the latest Guardian Chat fixes.

## This week’s priorities

1. Integrate and re-audit the two Guardian Chat fixes on shared `origin/main` before treating them as remote release state.
2. Rerun current-main supported-Compose closure with the canonical local profile.
3. Prove health, model inventory, terminal chat, persistence/readback, retrieval, queue/worker, locks, and terminal events on that profile.
4. Requalify Chroma through an authorized fresh-state path, then requalify CE-L1 executor/readback with one explicit provider/model policy.
5. Restore the intended Docker authority and rerun immutable image-retention reproduction from observed `origin/main`.

## Release definition right now

- [x] Supported local Compose path, local-only defaults, and Beta boundary are defined on `main`.
- [x] Internal, bounded/conditional, qualification-pending, and Out-of-Beta surfaces are kept separate from Beta Supported claims.
- [ ] Current-tip Compose proves healthy startup, model inventory, terminal chat, persistence/readback, and retrieval.
- [ ] Queue, worker, lock, migration, configuration, and recovery behavior is green on the supported install path.
- [ ] Qualification-pending lanes have current-main proof receipts for their named gates.
- [ ] Recent document-artifact and Guardian Chat flows have current supported-path/browser evidence where release claims depend on them.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
