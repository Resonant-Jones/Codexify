## Purpose

This file is the canonical short-form source of truth for Codexify’s current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-01

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening. Mainline has advanced private-preview database migration and recovery tooling, but current-tip supported-Compose closure, live CE-L1 execution, and private-preview recovery qualification remain unproven.

## What changed recently

- Merged bounded Pi assistant-response telemetry instrumentation and regression coverage; it is observational and does not prove CE-L1 execution.
- Added the provider-neutral sandbox authority boundary, live E2B/Modal conformance evidence, and selected Modal as the initial hosted implementation target; neither provider is release-supported.
- Proved the preserved private-preview database migration to Alembic head with retained external backup evidence.
- Requalified private-preview recovery through the repaired restore-helper boundary, then stopped before live execution because Docker Desktop was unavailable; guest traffic remains closed.
- Merged the Agent Skills loader and prompt-exposure seam with focused tests; no runtime caller is wired yet.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The intended Beta Supported boundary remains local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, workspace-local retrieval, identity/ownership, migrations, and operator diagnostics; this is support doctrine, not current-tip qualification.
- Mainline contains focused project lifecycle, project-scoped conversation-origin, document-artifact preview, and Guardian Chat repairs with focused tests; supported-path and authenticated browser proof remain separate gates.
- Authenticated local Settings reads, the read-only Connections catalog, and bounded account-export imports retain their existing contracts; presence does not imply generic connector sync, provider inference, or cloud support.
- Pi 0.82.1 wrapper/API, source-vendor, identity, and telemetry changes are test-backed only to the non-inference or OAuth-readiness boundary; Pi execution remains internal and qualification-pending.
- Watchdog, Pi diagnostics, proof tooling, and tester-stack receipts remain internal or proof-only surfaces.
- Private-preview database migration is proven as a prerequisite. The recovery, guest-canary, cloud-preview, and provider-execution lanes remain conditional or qualification-pending.

## Not yet true / do not assume

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or recovery closure.
- Do not treat clean CE-L1 OAuth readiness or telemetry instrumentation as live provider/model execution, coding-loop completion, persisted-result readback, or Beta proof.
- Do not treat Modal selection or partial read/exec conformance as an implemented adapter, bounded storage posture, supported runtime path, or release support.
- Do not treat E2B’s ordinary writable sandbox as a provider-enforced read-only workspace; its read-only input qualification failed closed.
- Do not treat Agent Skills files, loader tests, focused UI tests, proof receipts, feature branches, or planning language as live supported behavior.
- Do not invite private-preview guests or infer shipped reality from mutable `latest`, another checkout, or docs alone.

## Active blockers

- Fresh supported-Compose closure is missing at the current `main` tip, including health, chat, persistence/readback, retrieval, queue/worker, locks, and terminal events.
- Fresh-state Chroma startup/retrieval qualification remains unresolved; Chroma is derived state and no repair or historical restore is proven.
- CE-L1 still lacks live provider/model execution, terminal durable result, and source-thread readback.
- Private-preview recovery must be rerun after Docker Desktop `desktop-linux` is restored; the latest attempt created no checkpoint and did not touch source persistence.
- Modal lacks a proven provider-enforced storage ceiling, while E2B lacks the required provider-enforced read-only input mechanism; no hosted sandbox adapter is qualified.
- Watchdog model/policy qualification and immutable Docker image-retention replay remain unclosed; the latter requires the intended `desktop-linux` Docker authority.
- Recent project, artifact, and Guardian Chat changes still need supported-path/authenticated browser evidence where release claims depend on them.

## This week’s priorities

1. Restore the authorized Docker Desktop engine and rerun private-preview recovery with a new external checkpoint.
2. Rerun current-main supported-Compose closure with the canonical local profile.
3. Prove health, terminal chat, persistence/readback, retrieval, queue/worker, locks, and terminal events on that profile.
4. Requalify Chroma, then spend the next CE-L1 live attempt on provider/model execution and durable readback.
5. Capture supported-path/browser evidence for recent UI flows, then close any claimed Watchdog, image-retention, or hosted-sandbox qualification gates.

## Release definition right now

- [x] Supported local Compose path, local-only defaults, and Beta boundary are defined on `main`.
- [x] Internal, bounded/conditional, qualification-pending, and Out-of-Beta surfaces remain separate from Beta Supported claims.
- [ ] Current-tip Compose proves healthy startup, model inventory, terminal chat, persistence/readback, and retrieval.
- [ ] Queue, worker, lock, migration, configuration, recovery, and browser evidence gates are green on the claimed path.
- [ ] CE-L1 and any preview/provider lane being claimed have current-main proof receipts for their named gates.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
