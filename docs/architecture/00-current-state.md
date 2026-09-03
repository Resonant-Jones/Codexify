## Purpose

This file is the canonical short-form source of truth for Codexify’s current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-03

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a gated private-preview lane. Mainline now contains bounded private-profile People/Share qualification and Pi wrapper/telemetry qualification, but no fresh current-tip supported-Compose closure, CE-L1 live execution/readback, or admitted friends-and-family canary.

## What changed recently

- Requalified private-preview backup/restore, Guardian secret rotation, and Cloudflare single-origin/Access ingress with bounded receipts; guest traffic stayed closed.
- Added private-preview desired-state, restart-policy, tunnel, and LaunchAgent lifecycle tooling; contract coverage is operator evidence, not runtime health proof.
- Runtime-qualified same-node People messaging, the Conversation-first Inbox, and portable floating conversations on `v1-friends-family-web`; no Beta support widening.
- Added person-aware Share routing with explicit copy/send actions; token access remains non-recipient-exclusive and the feature remains private-profile/internal.
- Landed Pi 0.82.1 wrapper framing, tracked fake-fixture reproducibility, and Guardian ten-field telemetry; these remain non-inference qualification only.
- Restored private-preview local provider configuration to `qwen3.8-27b-4bit`; contract coverage changed, but no live provider or canary qualification followed.
- Hardened private-preview import routing and large-upload handling plus share/message idempotency and ownership checks; focused tests passed.
- Proved the account-import Safari `422` is a browser/frontend multipart-envelope failure: valid server replay stages the exact batch, and no repair was made.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The intended Beta Supported boundary remains local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, workspace-local retrieval, identity/ownership, migrations, and operator diagnostics; this is support doctrine, not current-tip qualification.
- Mainline contains focused project lifecycle, conversation-origin, document-artifact preview, Guardian Chat, and account-import repairs with targeted tests; supported-path and authenticated browser proof remain separate gates.
- Authenticated local Settings reads and the read-only Connections catalog retain their existing contracts; catalog visibility does not imply connector sync, provider inference, or cloud support.
- Valid account-import multipart batches are accepted and durably staged on the server path; the Safari envelope failure remains unrepaired.
- Pi 0.82.1 wrapper/API, source-vendor, identity, framing, and telemetry changes are test-backed to the non-inference or OAuth-readiness boundary; Pi execution remains internal and qualification-pending.
- Watchdog, Pi diagnostics, proof tooling, and tester-stack receipts remain internal or proof-only surfaces.
- Private-preview recovery, Guardian secret rotation, and Cloudflare ingress have bounded receipts; lifecycle/configuration checks are not live health or guest-canary proof.
- Private-profile People/Inbox/Share behavior is runtime-qualified on `v1-friends-family-web`; `direct_messages` stays quarantined on the default profile, and these surfaces do not widen Beta support.

## Not yet true / do not assume

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or recovery closure.
- Do not treat CE-L1 OAuth readiness, Pi telemetry, wrapper tests, or source-vendor closure as live provider/model execution, coding-loop completion, persisted-result readback, or Beta proof.
- Do not treat Modal selection or partial read/exec conformance as an implemented adapter, bounded storage posture, supported runtime path, or release support.
- Do not treat E2B’s ordinary writable sandbox as a provider-enforced read-only workspace; its read-only input qualification failed closed.
- Do not treat Agent Skills files, loader tests, focused UI tests, proof receipts, feature branches, or planning language as live supported behavior.
- Do not treat private-preview configuration or bounded recovery/ingress receipts as an admitted canary; DeepSeek execution, tester isolation, and persistence gates remain open.
- Do not infer shipped reality from mutable `latest`, another checkout, local-only artifacts, planning language, or docs alone.
- Do not treat the account-import proof’s classification as a repair; Safari/WebKit request-envelope construction remains unresolved.
- Do not treat Modal or E2B partial conformance as a qualified hosted sandbox, provider-enforced storage/read-only boundary, supported runtime path, or release support.
- Do not assume realtime delivery, read receipts, attachments, Guardian messaging/retrieval, Project invitations, node resolution, federation, or cross-node People messaging; these remain deferred under ADR-079/ADR-080.

## Active blockers

- Fresh supported-Compose closure is missing at the current `main` tip, including health, chat, persistence/readback, retrieval, queue/worker, locks, and terminal events.
- Fresh-state Chroma startup/retrieval qualification remains unresolved; Chroma is derived state and no repair or historical restore is proven.
- CE-L1 still lacks live provider/model execution, terminal durable result, and source-thread readback.
- The friends-and-family canary is blocked on an authorized provisioned non-admin tester set plus reruns of Access, isolation, provider, persistence, and bounded-observability gates.
- Private-preview DeepSeek credential rotation and provider requalification remain open before any external tester execution.
- Modal storage-ceiling, E2B provider-enforced read-only input, Watchdog model/policy, immutable image-retention, and recent supported-path browser gates remain unclosed.
- Safari/WebKit account-import multipart-envelope repair and regression proof remain open; the valid server path is proven separately.

## This week’s priorities

1. Rerun current-main supported-Compose closure with the canonical local profile.
2. Prove health, terminal chat, persistence/readback, retrieval, queue/worker, locks, and terminal events on that profile.
3. Requalify Chroma, then spend the next CE-L1 live attempt on provider/model execution and durable readback.
4. Rotate and requalify the private-preview DeepSeek credential, provision approved non-admin testers, and rerun the gated canary.
5. Repair and browser-regression-test the Safari upload envelope, then close the browser, Watchdog, image-retention, and hosted-sandbox gates.

## Release definition right now

- [x] Supported local Compose path, local-only defaults, and Beta boundary are defined on `main`.
- [x] Internal, bounded/conditional, qualification-pending, and Out-of-Beta surfaces remain separate from Beta Supported claims.
- [x] Private-preview recovery, Guardian secret rotation, Cloudflare ingress, and private-profile People/Share proofs are bounded without guest admission or release widening.
- [ ] Current-tip Compose proves healthy startup, model inventory, terminal chat, persistence/readback, and retrieval.
- [ ] Queue, worker, lock, migration, configuration, recovery, browser, and account-import claimed-path evidence gates are green.
- [ ] CE-L1 and any preview/provider lane being claimed have current-main proof receipts for live execution, durable readback, and their named isolation gates.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
