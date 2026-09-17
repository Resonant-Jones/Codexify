## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-17

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated friends-and-family private-preview lane. Recent mainline work is Guardian landing/chat/composer presentation and interaction refinement with focused frontend tests; it does not establish live supported-Compose closure, provider execution, or a wider Beta claim. Local `main` is two commits ahead of its local `origin/main` ref, so publication alignment remains a separate release gate.

## What changed recently

- Mainline merged Guardian chat/sidebar/composer interaction refinements and prompt-first landing/composer layout changes with focused frontend test coverage.
- The 2026-09-17 mainline accounting log records no same-day implementation or runtime qualification; the release boundary did not widen.
- Local `main` is two commits ahead of `origin/main`; no push or remote reconciliation is part of this audit.

## Current supported reality

- The named supported install path is local Docker Compose with `v1-local-core-web-mcp`, `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The declared Beta Supported contract covers local inference, ordinary chat, durable threads/messages/tasks, document upload/embed/readback, workspace-scoped retrieval, identity/ownership, migrations, and operator diagnostics; current-tip qualification is a separate gate.
- The local profile requires live Whoosh'd inventory for physical model availability. The tracked `local-chat` value is a logical route, not model-runtime proof.
- Private Preview is an opt-in tester lane: Whoosh'd remains the default, DeepSeek is the only admitted cloud lane, and the live roster/fallback behavior does not make cloud inference public Beta support.
- Main contains bounded proof for selected migration/recovery, Chroma topology, ingress, Persona, sharing, and UMS-04 export/restore surfaces; those proofs do not establish a running release path.
- Guardian landing/chat/composer refinements are merged with focused frontend tests; they do not change the supported install path or Beta boundary.

## Not yet true / do not assume

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or recovery closure.
- Do not treat merged landing/composer UI changes or focused frontend tests as authenticated browser completion, provider execution, persistence, or release proof.
- Do not treat logical `local-chat`, DeepSeek roster discovery, focused tests, or provider catalog output as live provider execution or persistence proof.
- Do not treat the private-preview migration/recovery and Chroma topology evidence as application startup, retrieval, authenticated browser, isolation, canary, or release proof; the matching Persona application remains blocked.
- Do not treat merged ADR-087 deadline snapshots and lock renewal as end-to-end provider/tool cancellation, graceful shutdown, finite drain, or cleanup proof.
- Do not promote CE-L1, browser/import, connectors, Watchdog, retention, hosted sandbox, Atlas, Pi, or other local-only/unmerged work into the release promise without its named proof.
- Do not infer publication from another checkout, dirty working-tree changes, local-only artifacts, planning language, or the two-commit local-main publication gap.

## Active blockers

- Fresh current-tip supported-Compose proof is missing across health, local model inventory, chat, persistence/readback, retrieval, queue/worker, locks, and terminal events.
- Tester bind-readiness repair and fresh isolated runtime proof remain open; the historical diagnosis is static evidence only.
- Private Preview remains blocked on Chroma startup/retrieval qualification, matching application deployment, provider/persistence/observability/isolation proof, and approved non-admin canary execution.
- DeepSeek credential rotation/requalification, authenticated browser save/readback, Safari multipart repair, and live provider-specific persistence remain open.
- ADR-087 enforcement and runtime proof remain open for worker/provider/child cleanup, PostgreSQL persistence, lock handling, late results, and finite graceful drain.
- CE-L1 live execution/readback, connector qualification, Watchdog policy/model proof, immutable image-retention replay, hosted-sandbox qualification, and local-main publication alignment remain open.

## This week's priorities

1. Land and qualify the fail-closed Tester bind-readiness predicate on a fresh isolated runtime.
2. Re-run the canonical local Compose proof bundle and requalify Whoosh'd inventory, chat, persistence/readback, retrieval, queue/worker, locks, and events.
3. Finish ADR-087 enforcement and prove finite drain, graceful stop, late-result handling, and durable terminal truth.
4. Resume Private Preview at Chroma/application startup, provider/persistence/isolation, authenticated browser, and canary gates.
5. Requalify CE-L1, browser/import, connectors, Watchdog, retention, and hosted sandbox; reconcile the publication baseline before release decisions.

## Release definition right now

- [x] The supported install path and Beta boundary are defined on `main`.
- [x] Internal, bounded, qualification-pending, and Out-of-Beta surfaces remain distinct from Beta Supported claims.
- [ ] Current-tip Compose proves healthy startup, live model inventory, terminal chat, durable readback, retrieval, and event delivery.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration, recovery, browser, and account-import claimed-path gates are green.
- [ ] Every preview/provider lane has current-main evidence for live execution, durable readback, isolation, and recovery/canary behavior where applicable.
- [ ] The release candidate is reconciled to the intended publication baseline.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
