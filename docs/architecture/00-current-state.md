## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-08-21

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` is in local-first Beta hardening. The audited implementation baseline is `e35de71c6`, including bounded Settings/Connections route promotion, Anthropic account-export import reconciliation, Guardian Pi readiness diagnostics, and Settings dock UI polish. The Beta boundary remains governed by ADR-069; fresh current-tip supported-Compose proof is still open.

## What changed recently

- Promoted authenticated identity/prompt/system-document routes and the read-only Connections catalog under ADR-072; generic connector mutation/sync remains quarantined.
- Merged Connections browser QA: 57 catalog entries exercised with `PASS WITH FINDINGS`; one P3 light-theme disabled-label contrast issue remains.
- Canonized Anthropic / Claude account-export conversation import as Beta Bounded / Conditional after the R2 proof recorded 63 threads and 784 messages through the durable worker path.
- Canonicalized Guardian Pi authorized-readiness diagnostics and regression coverage; no live provider or OAuth support was established.
- Repaired and requalified migration, psycopg3, Chroma-retirement, and supported-Compose proof seams; the current Compose closure receipt remains blocked at runtime selection/source provenance.
- Merged Settings dock material and active-selector polish; this changes presentation, not release capability.

## Current supported reality

- Local Docker Compose is the supported install path, using `v1-local-core-web-mcp` with local-only defaults: `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- Whoosh'd / local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, and workspace-local retrieval are in the Beta envelope.
- `/health`, `/health/chat`, and `/api/health/llm` are the primary operator checks; route inventory is published by startup for frontend capability gating.
- Authenticated local Settings routes and the read-only `/api/connections` catalog are bounded Beta surfaces; catalog visibility does not imply setup, authorization, credentials, or health.
- OpenAI and bounded Anthropic account-export conversation import, Task Prompt Archive, and owner-scoped zero-write retry/recovery are present only within their existing contracts.
- Persona Studio core and repository intelligence are Beta Bounded / Conditional; authority remains Guardian-owned and scope-limited.
- Architecture, schema, DLG, focused test, and proof-validation tooling is present on `main`; these checks do not substitute for live-service proof.

## Not yet true / do not assume

- Do not assume a fresh current-tip Compose run proves health, model inventory, chat completion, persisted output, or retrieval.
- Do not assume green unit tests, route registration, health responses, or proof receipts establish end-to-end runtime readiness.
- Do not assume Coding Loop, provider/tool turns, DeepSeek/private-preview execution, Hosted Rooms, Browser Host, or packaged desktop distribution are release-supported.
- Do not assume Anthropic import includes Projects, `memories.json`, `users.json`, binary media reconstruction, arbitrary export shapes, or Anthropic inference.
- Do not assume Connections catalog visibility provides a working adapter, configured credential, authorization, or live provider health; generic connector sync/mutation remains quarantined.
- Do not assume TTS/voice execution, federation, graph writes, generic shell/filesystem tools, recursive agents, public Command Bus, or unattended automation are in Beta.
- Do not count local branches, unmerged work, origin-only commits, or proof from another checkout as shipped reality.

## Active blockers

- Fresh supported-Compose proof at current `main` is blocked: the latest closure receipt found no eligible target and rejected a cloud-capable, differently mounted Tester runtime as a substitute.
- Queue/worker/turn-lock/terminal-event behavior still lacks current-tip end-to-end proof with durable output and readback.
- Canonical and legacy configuration paths coexist, leaving startup and operator-state drift risk.
- Coding Loop and tool-enabled provider lanes lack current supported-profile proof of adapter execution, terminal completion, continuation, and durable source-thread readback.
- DeepSeek/private-preview credentials and authenticated persisted turns remain unproven; Hosted Rooms still lack clean startup plus owner/guest semantic proof.

## This week's priorities

1. Capture current-tip supported-Compose proof for health, model inventory, chat, persistence, and retrieval.
2. Validate queue completion, turn locking, migrations, configuration, and import recovery on that same supported profile.
3. Reprove Coding Loop and provider/tool-turn lanes end to end, or keep them quarantined.
4. Reconcile canonical-versus-legacy configuration paths and retain explicit operator diagnostics.
5. Fix the Connections P3 light-theme contrast defect without widening its capability claim.

## Release definition right now

- [x] The supported profile, local-only defaults, Beta envelope, and release classes are defined on `main`.
- [x] Settings/Connections boundaries, generic connector quarantine, and Out-of-Beta surfaces are explicit.
- [x] Every claimed capability is merged to `main` and classified by its evidence/support boundary.
- [ ] Current-tip live proof confirms supported Compose health, model inventory, terminal chat, persistence, and retrieval.
- [ ] Queue, worker, lock, migration, configuration, and recovery behavior is green on the supported install path.
- [ ] Qualification-pending lanes either have their named proof or remain visibly quarantined.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
