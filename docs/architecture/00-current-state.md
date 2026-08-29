## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-08-29

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening. Mainline now contains bounded Pi 0.82.1 runtime repairs and clean CE-L1 OAuth credential-readiness evidence, but no current-tip supported-Compose release closure or live CE-L1 executor proof.

## What changed recently

- Merged Pi 0.82.1 wrapper/API repairs, canonical `ModelRuntime` use, and the complete source-vendored locked runtime closure; source-relative smoke now reaches the OAuth-absent boundary.
- Cleanly requalified `openai-codex / gpt-5.6-sol / pi-coding-agent / 0.82.1` credential readiness without provider inference or prompt execution; CE-L1 remains open.
- Added bounded tester/Whoosh'd runtime evidence, but the latest Tester Qwen completion attempt stopped at `TESTER_QWEN_BACKEND_UNHEALTHY`; these artifacts do not qualify supported-main release behavior.
- Requalified the OpenSSL tracer capsule and merged the expandable Composer and canonical SVG mark assets; neither widens the release promise.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The intended Beta Supported boundary remains local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, workspace-local retrieval, identity/ownership, migrations, and operator diagnostics; this is support doctrine, not current-tip qualification.
- Authenticated local Settings reads, the read-only Connections catalog, and bounded account-export imports retain their existing contracts; presence does not imply generic connector sync, provider inference, or cloud support.
- Pi 0.82.1 runtime identity, wrapper compatibility, and source-vendor loading are test-backed to the non-inference OAuth-readiness boundary. Pi execution remains internal and qualification-pending.
- Watchdog, Pi diagnostics, proof tooling, and tester-stack receipts remain internal or proof-only surfaces. Static and bounded tester evidence does not substitute for supported-path live proof.

## Not yet true / do not assume

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or recovery closure.
- Do not treat the clean CE-L1 OAuth prerequisite as live executor, coding-loop, persisted-result, or supported-Beta proof; `LIVE_EXECUTOR_PROVEN` was not emitted.
- Do not treat Tester Qwen, Whoosh'd, or prior local/Gemma completions as supported-main evidence; they are bounded tester or internal proof surfaces.
- Do not assume Chroma fresh-state startup/retrieval qualification, Google Drive OAuth, Watchdog model execution, or immutable Docker image-retention behavior is closed.
- Do not infer shipped reality from feature branches, local work, proof from another checkout, planning language, mutable `latest`, or docs alone.

## Active blockers

- Fresh supported-Compose closure has not been rerun at the current `main` tip after the merged local-gateway/profile alignment.
- One supported-profile proof bundle is still missing for health, chat, persistence/readback, retrieval, queue/worker, locks, terminal events, and recovery.
- Fresh-state Chroma startup/retrieval qualification remains unresolved; Chroma is derived state and no repair or historical restore is proven.
- CE-L1 still lacks live provider/model execution, terminal durable result, and source-thread readback despite the OAuth-readiness prerequisite passing.
- Watchdog qualification still requires an explicit available provider/model policy; disposable image-retention replay still requires the intended `desktop-linux` Docker authority.

## This week’s priorities

1. Rerun current-main supported-Compose closure with the canonical local profile.
2. Prove health, model inventory, terminal chat, persistence/readback, retrieval, queue/worker, locks, and terminal events on that profile.
3. Requalify Chroma only through an authorized fresh-state path; keep Postgres canonical and Chroma derived.
4. Requalify CE-L1 through one explicit provider/model policy, then prove executor and persisted source-thread readback.
5. Restore the intended Docker authority and rerun immutable image-retention reproduction from observed `origin/main`.

## Release definition right now

- [x] Supported local Compose path, local-only defaults, and Beta boundary are defined on `main`.
- [x] Internal, bounded/conditional, qualification-pending, and Out-of-Beta surfaces are kept separate from Beta Supported claims.
- [ ] Current-tip Compose proves healthy startup, model inventory, terminal chat, persistence/readback, and retrieval.
- [ ] Queue, worker, lock, migration, configuration, and recovery behavior is green on the supported install path.
- [ ] Qualification-pending lanes have current-main proof receipts for their named gates.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
