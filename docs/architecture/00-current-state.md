## Purpose

This file is the canonical short-form source of truth for Codexify’s current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-02

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a gated private-preview lane. Mainline now has bounded proof for private-preview backup/restore recovery, Guardian secret rotation, and Cloudflare ingress, but current-tip supported-Compose closure, live CE-L1 execution/readback, and an admitted friends-and-family canary remain unproven.

## What changed recently

- Requalified private-preview backup/restore after Docker recovery with a fresh external checkpoint, exact media/database reconciliation, source preservation, and loopback restart reachability; guest traffic stayed closed.
- Rotated private-preview Guardian session/JWT/API secrets and proved old-session invalidation plus new-session roundtrip; DeepSeek credential rotation remains open.
- Corrected and live-proved the private-preview Cloudflare single-origin router and Access boundary; ingress now reaches the Guardian login/workspace path without widening the release claim.
- Stopped the first friends-and-family canary before admission because external ingress was unavailable at that attempt and no provisioned non-admin tester set existed; the canary remains a separate gate.
- Added private-preview desired-state, restart-policy, tunnel, and LaunchAgent lifecycle tooling with focused contract coverage; this is operator tooling, not runtime health proof.
- Runtime-qualified same-node People messaging on `v1-friends-family-web` under ADR-079 and ADR-080 (see `proofs/2026-09-01-people-messaging-runtime-qualification-proof.md`): the Node_ID + Profile_ID social identity, deliberate Node-scoped usernames, email-private discovery, durable plain-text messages with idempotent retries, Relationship → multiple Conversation semantics, Project/Thread origin provenance, participant-local placement, conversation-first Inbox rows, relationship-backed person filtering, and portable Floating Conversation behavior are proven on the private-preview profile. Realtime delivery, Project invitations, Guardian retrieval, and federation remain unimplemented; the Beta support boundary is unchanged.
- Runtime-qualified the person-aware Share Sheet (see `proofs/2026-09-01-share-sheet-person-routing-qualification-proof.md`): explicit `Copy Link` and `Send to Person` actions resolve a Profile and Relationship, offer existing/new Conversation choices, reuse the same tokenized read-only link across partial-failure retry and idempotent send, preserve Thread-origin provenance, and fail closed on the unsupported profile. The operator-approved Dev posture enables the `share` route label on `v1-friends-family-web` and `v1-local-core-web-mcp`; share remains token-based and recipient-exclusive access is not claimed.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The intended Beta Supported boundary remains local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, workspace-local retrieval, identity/ownership, migrations, and operator diagnostics; this is support doctrine, not current-tip qualification.
- Mainline contains focused project lifecycle, project-scoped conversation-origin, document-artifact preview, and Guardian Chat repairs with focused tests; supported-path and authenticated browser proof remain separate gates.
- Authenticated local Settings reads, the read-only Connections catalog, and bounded account-export imports retain their existing contracts; presence does not imply generic connector sync, provider inference, or cloud support.
- Pi 0.82.1 wrapper/API, source-vendor, identity, and telemetry changes are test-backed only to the non-inference or OAuth-readiness boundary; Pi execution remains internal and qualification-pending.
- Watchdog, Pi diagnostics, proof tooling, and tester-stack receipts remain internal or proof-only surfaces.
- Private-preview recovery, Guardian secret rotation, and Cloudflare ingress each have bounded receipts; the guest canary, DeepSeek execution, and external tester isolation remain conditional or qualification-pending.
- Private-preview lifecycle commands are available as an operator path, with volumes preserved by the intentional-down contract; status output is not a substitute for live release qualification.
- The private-profile People/Inbox projection is runtime-qualified on `v1-friends-family-web`: same-node Node_ID + Profile_ID messaging, one Relationship with multiple Conversations, Project/Thread origin provenance, participant-local placement, conversation-first rows, person filtering, and portable Floating Conversation behavior. The `direct_messages` route label remains quarantined on the default `v1-local-core-web-mcp` profile and enabled only on `v1-friends-family-web`; this is private-profile capability, not Beta-supported behavior.

## Not yet true / do not assume

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or recovery closure.
- Do not treat clean CE-L1 OAuth readiness or telemetry instrumentation as live provider/model execution, coding-loop completion, persisted-result readback, or Beta proof.
- Do not treat Modal selection or partial read/exec conformance as an implemented adapter, bounded storage posture, supported runtime path, or release support.
- Do not treat E2B’s ordinary writable sandbox as a provider-enforced read-only workspace; its read-only input qualification failed closed.
- Do not treat Agent Skills files, loader tests, focused UI tests, proof receipts, feature branches, or planning language as live supported behavior.
- Do not treat private-preview recovery or Cloudflare ingress receipts as a completed guest canary; do not invite guests until the separate admission, isolation, provider, and persistence gates pass.
- Do not infer shipped reality from mutable `latest`, another checkout, or docs alone.
- Do not assume cross-node private messaging, node resolution/trust, or Guardian messaging; federation is not implemented. Project invitations and Guardian Conversation/origin retrieval are not implemented, and realtime delivery remains unimplemented. These messaging capabilities remain explicitly deferred under ADR-079 and ADR-080; the People/Inbox and Share surfaces do not widen Beta support, and share links remain token-based rather than recipient-exclusive.

## Active blockers

- Fresh supported-Compose closure is missing at the current `main` tip, including health, chat, persistence/readback, retrieval, queue/worker, locks, and terminal events.
- Fresh-state Chroma startup/retrieval qualification remains unresolved; Chroma is derived state and no repair or historical restore is proven.
- CE-L1 still lacks live provider/model execution, terminal durable result, and source-thread readback.
- The friends-and-family private-preview canary remains blocked on an authorized provisioned tester set and a rerun of external Access, account-isolation, provider, persistence, and bounded-observability gates; the recovery prerequisite and ingress boundary are now proven separately.
- Private-preview DeepSeek credential rotation and provider requalification remain open before any external tester execution.
- Modal lacks a proven provider-enforced storage ceiling, while E2B lacks the required provider-enforced read-only input mechanism; no hosted sandbox adapter is qualified.
- Watchdog model/policy qualification and immutable Docker image-retention replay remain unclosed.
- Recent project, artifact, and Guardian Chat changes still need supported-path/authenticated browser evidence where release claims depend on them.

## This week’s priorities

1. Rerun current-main supported-Compose closure with the canonical local profile.
2. Prove health, terminal chat, persistence/readback, retrieval, queue/worker, locks, and terminal events on that profile.
3. Requalify Chroma, then spend the next CE-L1 live attempt on provider/model execution and durable readback.
4. Rotate and requalify the private-preview DeepSeek credential, provision two or three approved non-admin testers, and rerun the gated canary.
5. Capture supported-path/browser evidence for recent UI flows, then close the Watchdog, image-retention, and hosted-sandbox qualification gates.

## Release definition right now

- [x] Supported local Compose path, local-only defaults, and Beta boundary are defined on `main`.
- [x] Internal, bounded/conditional, qualification-pending, and Out-of-Beta surfaces remain separate from Beta Supported claims.
- [x] Private-preview recovery, Guardian secret rotation, and Cloudflare ingress have bounded proof without guest admission or release widening.
- [ ] Current-tip Compose proves healthy startup, model inventory, terminal chat, persistence/readback, and retrieval.
- [ ] Queue, worker, lock, migration, configuration, recovery, and browser evidence gates are green on the claimed path.
- [ ] CE-L1 and any preview/provider lane being claimed have current-main proof receipts for live execution, durable readback, and their named isolation gates.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
