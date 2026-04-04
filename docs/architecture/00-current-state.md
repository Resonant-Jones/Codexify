## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-04-04

## Interpretation rule

This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

Codexify is still in release-gate remediation on `main` for the local Docker Compose beta profile. A fresh clean-start migration proof on current `HEAD` now closes the empty-database bootstrap question on the supported path, but upgrade-from-existing-instance evidence remains open.

## What changed recently

- Added a fresh clean-start migration / upgrade proof on current `HEAD` (`docs/architecture/2026-04-04-migration-upgrade-proof.md`) with explicit pass/fail evidence.
- The supported local Docker Compose path was re-proved after migration: backend and workers booted cleanly, `chat_threads.thread_config` persisted, assistant output persisted, document embedding reached `ready`, and supported retrieval succeeded on `GET /api/health/retrieval?q=...`.
- The supported runtime still quarantines the dedicated persona-profile API route under `CODEXIFY_BETA_CORE_ONLY=true`; the supported profile surface remains route-quarantined even though the schema migration landed.
- The runtime health surfaces now reconcile cleanly with the supported local stack after migration, including the migrated chat and retrieval path.

## Current supported reality

- Supported install path remains local Docker Compose with backend, Postgres, Redis, Neo4j, and workers.
- Supported-profile flags were live-verified on current `HEAD`: `CODEXIFY_BETA_CORE_ONLY=true`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`.
- Quarantined non-core routes remain unavailable in the supported profile, including the dedicated persona-profile API route.
- Clean-start migration on empty volumes is now proven on current `HEAD`.
- Thread creation, `chat_threads.thread_config` persistence, completion persistence, document upload, embed readiness, and supported retrieval all passed on the migrated runtime.
- `/health`, `/health/chat`, `/api/health/llm`, and `/api/health/retrieval` reconcile with the supported local runtime after migration.
- The retrieval runtime reports `same_runtime_as_worker: true`, so backend search and worker write paths are aligned on the supported proof surface.

## Not yet true / do not assume

- Do not assume upgrade-from-existing-instance has been proven; the fresh proof is clean-start only.
- Do not assume the dedicated persona-profile API route is part of the supported beta surface; it is still quarantined under the supported profile.
- Do not assume older supported-path proof artifacts still represent current `main` without a fresh rerun.
- Do not assume `/tools` and command-bus surfaces are one finalized release contract unless stated here.

## Active blockers

- Existing-instance upgrade confidence is still open; the current proof does not cover a pre-migration snapshot upgrade.

## This week's priorities

1. If release signoff needs it, run a snapshot-based upgrade proof from an existing populated database state.
2. Keep the migration / supported-path proof artifact current as schema/runtime changes land.
3. Reconcile any future persona-profile release claims with the supported-profile quarantine boundary before widening the surface.

## Release definition right now

- [x] Supported-profile flags are active in live runtime (`CODEXIFY_BETA_CORE_ONLY=true`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`).
- [x] Quarantined non-core routes return the expected unsupported behavior in the running stack.
- [x] One fresh clean-start supported-path run on `main` proves thread create, completion execution, assistant persistence, document upload, embed readiness, and retrieval evidence.
- [x] Retrieval runtime uses one aligned vector-store backend across backend and embed worker on the supported profile.
- [x] `/health`, `/health/chat`, `/api/health/llm`, and `/api/health/retrieval` are reconciled with the actual supported model/runtime contract.
- [x] No release claim depends on internal-only or dev-only surfaces.
- [ ] Existing-instance upgrade from a pre-migration snapshot is still unproven.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
