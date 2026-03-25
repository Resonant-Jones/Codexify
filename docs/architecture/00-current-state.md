## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-03-25

## Interpretation rule

This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

Codexify is in a stabilization-and-proof phase for the local Docker Compose beta path on `main`. Merged work this week tightened chat loop behavior, provider/runtime handling, and diagnostics, but release posture remains `hold` until supported-profile and end-to-end supported-path evidence are freshly re-proven on the live stack.

## What changed recently

- Beta stabilization campaign work merged on `main` for chat turn-lock lifecycle, default inference mode handling, health-route alignment, thread/project mutation recovery, and provider runtime hardening.
- Local Ollama Docker connectivity was fixed, including router/catalog/config updates and backend tests.
- Provider visibility/governance moved forward with expanded Groq catalog coverage and stronger Minimax/Alibaba failure handling.
- Obsidian allowlist indexer foundation landed for CLI ingest (`guardian/obsidian/indexer.py` plus tests).
- `useChat` refresh behavior iterated quickly on `main` (contract added, rate-limited, then removed) to reduce UI loop instability.
- Chat payload summary diagnostics landed with backend/worker test coverage.
- Daily audit artifacts were refreshed under `docs/audits/daily/evening/` and `docs/audits/latest.*`.

## Current supported reality

- Supported install path is local Docker Compose with backend, frontend, Postgres, Redis, and required workers.
- Core released interaction remains thread chat with queue-backed completion and persisted task/message state.
- Chat runtime and frontend loop stability improved on `main` through lock lifecycle, route alignment, and payload diagnostics hardening.
- Provider runtime posture is clearer than last week: local Ollama connectivity is fixed for Docker flow, Groq catalog visibility expanded, and Minimax/Alibaba failures are handled more defensively.
- Project and thread mutation paths were repaired on `main` and backed by frontend tests.
- Obsidian support on `main` is local CLI ingest plus indexer foundation, not a shipped continuous connector sync path.
- Current validation evidence is primarily targeted backend/frontend tests and audit artifacts; release signoff still requires fresh integrated runtime proof.

## Not yet true / do not assume

- Do not assume supported-profile flags are freshly validated on the current release Compose stack.
- Do not assume quarantined non-core routes are consistently excluded without explicit live verification.
- Do not assume provider catalog presence means the path is supported for release.
- Do not assume legacy `/tools` and command bus behavior are fully unified.
- Do not assume queue acceptance, queue progress, or task events prove eventual completion in the UI.
- Do not assume Redis dependency for chat coordination is removed.
- Do not assume federation/sync durability is part of the present beta release promise.
- Do not assume Obsidian connector sync is shipped; only local CLI ingest/indexing is evidenced on `main`.

## Active blockers

- Fresh supported-path proof on `main` is still missing for thread -> completion and upload -> embed -> retrieve in one passing run.
- Supported-profile contract must be re-verified live to confirm route posture and runtime flags match release expectations.
- Provider governance, catalog, and runtime health still require manual cross-reading rather than one release-grade gate.
- Legacy `/tools` duality with command bus behavior remains unresolved in release-facing contract terms.
- Redis-backed queue/worker dependency remains a central coordination risk for chat completion behavior.

## This week's priorities

1. Run and publish one fresh supported-path evidence pass on `main` (thread, completion, upload, embed, retrieval).
2. Re-verify supported-profile runtime flags and quarantined-route behavior on the actual release Compose stack.
3. Align release gate language across `/health`, `/health/llm`, `/health/chat`, and `/api/llm/catalog`.
4. Reduce `/tools` vs command bus release-surface ambiguity and document the enforced contract.
5. Lock Obsidian beta promise wording to what is currently shipped (`CLI ingest/indexer` only unless new proof lands).

## Release definition right now

- [ ] Supported-profile flags are active in live runtime (`CODEXIFY_BETA_CORE_ONLY=true`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`).
- [ ] Quarantined non-core routes match the supported-profile contract in the running stack.
- [ ] One fresh supported-path smoke on `main` proves thread create, assistant completion, document upload, embed readiness, and retrieval evidence.
- [ ] `/health/chat`, `/health/llm`, `/health`, and `/api/llm/catalog` agree with supported-profile and provider-governance expectations.
- [ ] No release claim depends on internal-only or dev-only surfaces.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
