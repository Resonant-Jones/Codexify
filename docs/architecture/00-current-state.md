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

`main` remains in local-first Beta hardening. Recent mainline changes strengthen project ownership and lifecycle safety, but current-tip supported-Compose release closure and live CE-L1 executor proof remain unproven.

## What changed recently

- Scoped conversation-origin filtering to the selected project context, with focused frontend tests.
- Added durable `general` and `imports` Project roles, reversible ordinary-project archival, archive-gated deletion, and transactional thread ejection to General; focused backend/frontend tests are merged.
- Added the ADR-076 project-lifecycle contract and aligned the data-and-storage invariants; this records the merged behavior without widening release claims.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The intended Beta Supported boundary remains local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, workspace-local retrieval, identity/ownership, migrations, and operator diagnostics; this is support doctrine, not current-tip qualification.
- Mainline contains focused, account-scoped artifact projection/preview, Guardian Chat project-context, project-scoped conversation-origin, and safe Project lifecycle repairs; focused tests do not substitute for supported-path or authenticated browser proof.
- Authenticated local Settings reads, the read-only Connections catalog, and bounded account-export imports retain their existing contracts; presence does not imply generic connector sync, provider inference, or cloud support.
- Pi 0.82.1 runtime identity, wrapper compatibility, and source-vendor loading are test-backed to the non-inference OAuth-readiness boundary. Pi execution remains internal and qualification-pending.
- Watchdog, Pi diagnostics, proof tooling, and tester-stack receipts remain internal or proof-only surfaces. Static and bounded tester evidence does not substitute for supported-path live proof.

## Not yet true / do not assume

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or recovery closure.
- Do not treat clean CE-L1 OAuth readiness as live provider/model execution, coding-loop completion, persisted-result readback, or supported-Beta proof; `LIVE_EXECUTOR_PROVEN` was not emitted.
- Do not treat Tester Qwen, Whoosh'd, or prior local/Gemma completions as supported-main evidence; they are bounded tester or internal proof surfaces.
- Do not treat focused project, artifact, Guardian Chat, or sidebar tests and code-path repairs as authenticated browser or supported-Compose release proof.
- Do not assume Chroma fresh-state startup/retrieval qualification, Google Drive OAuth, Watchdog model execution, or immutable Docker image-retention behavior is closed.
- Do not infer shipped reality from feature branches, proof from another checkout, planning language, mutable `latest`, or docs alone.

## Active blockers

- Fresh supported-Compose closure has not been rerun at the current `main` tip after the merged local-gateway/profile alignment.
- One supported-profile proof bundle is still missing for health, chat, persistence/readback, retrieval, queue/worker, locks, terminal events, and recovery.
- Fresh-state Chroma startup/retrieval qualification remains unresolved; Chroma is derived state and no repair or historical restore is proven.
- CE-L1 still lacks live provider/model execution, terminal durable result, and source-thread readback despite the OAuth-readiness prerequisite passing.
- Watchdog qualification still requires an explicit available provider/model policy; disposable image-retention replay still requires the intended `desktop-linux` Docker authority.
- Recent project and Guardian Chat changes have focused tests, but supported-path/authenticated browser evidence is still missing where release claims depend on them.

## This week’s priorities

1. Rerun current-main supported-Compose closure with the canonical local profile.
2. Prove health, model inventory, terminal chat, persistence/readback, retrieval, queue/worker, locks, and terminal events on that profile.
3. Requalify Chroma through an authorized fresh-state path, then requalify CE-L1 executor/readback with one explicit provider/model policy.
4. Capture supported-path and authenticated browser evidence for the recent project, artifact, and Guardian Chat flows.
5. Restore the intended Docker authority and rerun immutable image-retention reproduction from observed `main`.

## Release definition right now

- [x] Supported local Compose path, local-only defaults, and Beta boundary are defined on `main`.
- [x] Internal, bounded/conditional, qualification-pending, and Out-of-Beta surfaces are kept separate from Beta Supported claims.
- [ ] Current-tip Compose proves healthy startup, model inventory, terminal chat, persistence/readback, and retrieval.
- [ ] Queue, worker, lock, migration, configuration, and recovery behavior is green on the supported install path.
- [ ] Qualification-pending lanes have current-main proof receipts for their named gates.
- [ ] Recent project, document-artifact, and Guardian Chat flows have current supported-path/browser evidence where release claims depend on them.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
