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

Codexify is still in release-gate remediation on `main` for the local Docker Compose beta profile. Clean-start migration/bootstrap is proven on the supported path, and a synthetic existing-instance upgrade from the recent migration floor is now also proven; broader archived-snapshot coverage remains the remaining upgrade gap.

## What changed recently

- Added a clean-start migration proof artifact on `main` (`docs/architecture/2026-04-04-migration-upgrade-proof.md`).
- Added a synthetic existing-instance upgrade proof artifact on `main` (`docs/architecture/2026-04-04-existing-instance-upgrade-proof.md`) that seeded a populated database at the recent migration floor `d4b7f1a9c3e2` and upgraded it to current HEAD.
- The supported local Docker Compose path was re-proved after migration: backend and workers booted cleanly, `chat_threads.thread_config` persisted, assistant output persisted, document embedding reached `ready`, and supported retrieval succeeded on `GET /api/health/retrieval?q=...`.
- The same seeded thread survived the upgrade run: `chat_threads.thread_config` still read back, a new completion on the upgraded thread persisted a second assistant message, and the seeded document remained retrieval-capable after the upgrade.
- The supported runtime still quarantines the dedicated persona-profile API route under `CODEXIFY_BETA_CORE_ONLY=true`; the supported profile surface remains route-quarantined even though the schema migration landed.
- The runtime health surfaces now reconcile cleanly with the supported local stack after migration, including the migrated chat and retrieval path.

## Current supported reality

- Supported install path remains local Docker Compose with backend, Postgres, Redis, Neo4j, and workers.
- Supported-profile flags were live-verified on current `HEAD`: `CODEXIFY_BETA_CORE_ONLY=true`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`.
- Quarantined non-core routes remain unavailable in the supported profile, including the dedicated persona-profile API route.
- Clean-start migration on empty volumes is now proven on current `HEAD`.
- Synthetic existing-instance upgrade from `d4b7f1a9c3e2` to current `HEAD` is now proven on current `HEAD`.
- Thread creation, `chat_threads.thread_config` persistence, completion persistence, document upload, embed readiness, and supported retrieval all passed on the migrated runtime.
- `/health`, `/health/chat`, `/api/health/llm`, and `/api/health/retrieval` reconcile with the supported local runtime after migration.
- The retrieval runtime reports `same_runtime_as_worker: true`, so backend search and worker write paths are aligned on the supported proof surface.

## Not yet true / do not assume

- Do not assume every historical upgrade class has been proven; the existing-instance proof is synthetic and limited to the recent floor `d4b7f1a9c3e2`.
- Do not assume the dedicated persona-profile API route is part of the supported beta surface; it is still quarantined under the supported profile.
- Do not assume older supported-path proof artifacts still represent current `main` without a fresh rerun.
- Do not assume `/tools` and command-bus surfaces are one finalized release contract unless stated here.

## Active blockers

- Broader archived-snapshot upgrade confidence is still open if release signoff requires more than the recent-floor synthetic fixture.

## This week's priorities

1. If release signoff needs it, extend the upgrade proof to an older archived snapshot rather than the recent synthetic floor.
2. Keep the migration / supported-path proof artifacts current as schema/runtime changes land.
3. Reconcile any future persona-profile release claims with the supported-profile quarantine boundary before widening the surface.

## Release definition right now

- [x] Supported-profile flags are active in live runtime (`CODEXIFY_BETA_CORE_ONLY=true`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`).
- [x] Quarantined non-core routes return the expected unsupported behavior in the running stack.
- [x] One fresh clean-start supported-path run on `main` proves thread create, completion execution, assistant persistence, document upload, embed readiness, and retrieval evidence.
- [x] A synthetic existing-instance upgrade from `d4b7f1a9c3e2` to current `HEAD` proves the supported recent-floor upgrade path.
- [x] Retrieval runtime uses one aligned vector-store backend across backend and embed worker on the supported profile.
- [x] `/health`, `/health/chat`, `/api/health/llm`, and `/api/health/retrieval` are reconciled with the actual supported model/runtime contract.
- [x] No release claim depends on internal-only or dev-only surfaces.
- [ ] Broader archived-snapshot upgrade coverage is still unproven.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
