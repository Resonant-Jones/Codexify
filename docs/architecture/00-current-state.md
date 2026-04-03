## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-04-03

## Interpretation rule

This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

Codexify is in post-merge release revalidation on `main` for the local Docker Compose beta profile. `main` absorbed major chat runtime, thread-config, and persona-profile changes on 2026-04-02, while the latest full live supported-path proof artifact on `main` remains 2026-04-01 (`docs/architecture/2026-04-01-current-head-supported-path-proof.md` at commit `2226d833...`).

## What changed recently

- Merged thread-config runtime contract work: `chat_threads.thread_config`, create/update/read surfaces, and completion precedence coverage on `main`.
- Merged latest-turn completion targeting changes: prompt assembly, retrieval targeting, queued-task identity propagation, and trace visibility.
- Merged lifecycle observability changes: first-output timing, lifecycle latency display, and assistant chunk streaming over task events.
- Merged first-wave Persona Studio runtime wiring: persona profile storage/routes/runtime resolver integration plus frontend wiring/tests.
- Merged account export/restore improvements: canonical export zip bundling and metadata account-restore route/tests.
- Added architecture artifacts on `main`: current-head supported-path proof (2026-04-01) and capabilities audit (2026-04-02).

## Current supported reality

- Supported install path remains local Docker Compose with backend, frontend, Postgres, Redis, and workers.
- Thread chat is the core supported flow, with queue-backed completion and persisted task/message state.
- Latest live proof artifact on `main` (2026-04-01 current-head run) validated supported-profile flags, cloud-route quarantine, reconciled health surfaces, accepted-then-persisted completion, and upload -> embed -> retrieval via `GET /api/health/retrieval?q=...`.
- Backend retrieval seam behavior is validated by tests/artifacts on `main` (`tests/core/test_context_broker_source_mode.py`, `tests/routes/test_chat_profile_trace.py`, `docs/architecture/2026-04-01-deterministic-retrieval-proof.md`).
- Thread configuration is now persisted and consumed as completion input on `main`, with route/service coverage for create, update, read, and precedence behavior.
- Chat lifecycle status now includes first-output and latency instrumentation with backend/frontend test coverage on `main`.
- Persona profile runtime surfaces exist on `main` (DB/model/routes/resolver/frontend wiring), with test coverage for persistence and runtime integration.

## Not yet true / do not assume

- Do not assume 2026-04-01 live proof coverage still holds unchanged on current `main` after 2026-04-02 runtime merges; it has not been re-run on latest HEAD.
- Do not assume the legacy standalone retrieval route (`POST /api/retrieve`) is part of the current supported contract; the latest supported-path proof uses `GET /api/health/retrieval?q=...`.
- Do not assume newly merged Persona Studio profile wiring is release-ready end-to-end in the supported Compose path without fresh live validation.
- Do not assume new lifecycle streaming/latency UX implies proven operator SLOs; current evidence is code/test-level plus pre-merge live proof.
- Do not assume unmerged branches, local-only runs, or draft audit notes change release truth until reflected on `main` and repeated here.

## Active blockers

- No fresh supported-path rerun exists on current `main` HEAD after the 2026-04-02 runtime merges; release readiness is currently unproven for latest HEAD.
- Supported retrieval contract is still boundary-sensitive (`/api/health/retrieval` proven, legacy `/api/retrieve` not mounted in latest artifact) and must be explicitly locked for release language.
- Migration and upgrade confidence is incomplete for latest schema changes (`thread_config`, `persona_profiles`, recent alembic head merge) without a fresh clean-start verification on current HEAD.

## This week's priorities

1. Re-run and publish a fresh supported-path proof on current `main` HEAD (create -> complete -> upload -> embed -> retrieve) using the supported Compose profile.
2. Re-verify health/catalog/retrieval surfaces from one runtime session and record exact release contract endpoints.
3. Run clean migration + startup validation on current `main` for new schema heads and document pass/fail evidence.
4. Confirm thread-config + latest-turn behavior in a live run (not only tests) and record trace evidence.
5. Reconcile Persona Studio profile runtime scope with release promise (supported now vs present-but-not-committed-to-support).

## Release definition right now

- [ ] Supported-profile flags are active in live runtime (`CODEXIFY_BETA_CORE_ONLY=true`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`).
- [ ] Quarantined non-core routes return the expected unsupported behavior in the running stack.
- [ ] One fresh supported-path run on current `main` HEAD proves thread create, completion execution, assistant persistence, document upload, embed readiness, and retrieval evidence.
- [ ] Retrieval contract is explicit for release (mounted endpoint(s), expected status codes, and proof path) and matches runtime wiring.
- [ ] `/health`, `/health/chat`, `/api/health/llm`, `/api/llm/catalog`, and retrieval health are reconciled in the same runtime session.
- [ ] Latest schema migrations apply cleanly on a fresh database and the stack reaches healthy state without manual repair.
- [ ] No release claim depends on internal-only or dev-only surfaces.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
