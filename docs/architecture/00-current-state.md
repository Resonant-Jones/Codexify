## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-04-10

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-beta hardening on `main`. The supported path is still the local Docker Compose stack with a local-only provider policy, while recent merged work tightened startup ingestion and retrieval sharing. Quarantined surfaces remain outside the beta promise.

## What changed recently
- Three new executable backend-seam evaluation suites landed:
  - Identity-boundary suite (`tests/identity/`) covers project-scope containment, explicit-widen behavior, and exclusion filters (archived, other-user, modeling-excluded threads) at the broker level.
  - Supported-beta golden-task suite (`tests/golden/`) covers completion acceptance contract, RAG trace per-thread isolation, and the Obsidian ingest→retrieve seam at the backend route level.
  - Broker/source-mode matrix reconciled (`tests/routes/test_chat_source_mode.py`, `tests/routes/test_chat_profile_trace.py`) with `effective_source_mode` now derived from `source_mode` and `retrieval_override` via `_effective_source_mode_for_broker_assembly`.
- The Obsidian ingest→retrieve seam is proven at the backend route level (in-memory fixture); this is scoped backend seam proof, not a full connector sync or live runtime proof.
- Live import catch-up re-proven on `main` remains stale — fresh live release evidence on the exact current `main` tip still needs to be rerun.
- Frontend-only layout polish (Dashboard, Documents, Settings panels) landed, but does not change the release contract.

## Current supported reality
- Local Docker Compose remains the supported install path.
- Supported beta posture is still local-only: `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`.
- Chat acceptance, worker execution, and Postgres persistence remain the core validated loop.
- Upload -> parse -> embed -> retrieve remains supported, with one shared runtime vector store.
- Built-in system docs/help are seeded at startup and available to retrieval.
- The import embed worker can drain a live backlog without breaking chat or health surfaces.
- `/health`, `/health/chat`, `/api/health/llm`, `/api/health/retrieval`, and `/api/llm/catalog?include=all` remain the primary runtime evidence surfaces.
- Executable evaluation suites now cover backend seam evidence for:
  - Supported-path golden tasks (completion acceptance, RAG trace isolation, Obsidian ingest→retrieve seam).
  - Identity-boundary proof (project scope containment, explicit widening, exclusion filters).
  - Broker/source-mode reconciliation (`effective_source_mode` derived from `source_mode` + `retrieval_override`).

## Not yet true / do not assume
- Do not assume the supported-path golden tasks or identity-boundary suites replace the need for fresh live release evidence on the exact current `main` tip; these are backend seam tests, not full live Compose runtime proof.
- Do not assume the Obsidian ingest→retrieve seam proof constitutes a full connector sync or live runtime validation; it uses an in-memory fixture at the backend route level.
- Do not assume `personal_facts` is part of the supported beta surface; the supported profile quarantines it.
- Do not assume delegation or autonomous coding-agent execution is shipped; the current release promise still excludes that loop.
- Do not assume internal operator surfaces or quarantined routes represent the supported beta contract.
- Do not assume older proof docs alone describe the current tip if a newer merge changed runtime wiring.

## Active blockers
- Fresh live release evidence on the exact current `main` tip is stale and needs to be rerun; backend-seam eval suites (golden tasks, identity boundaries, source-mode matrix) reduce ambiguity in scope boundaries but do not substitute for live runtime proof.
- Release signoff still depends on the supported-profile, provider registry, and health surfaces staying aligned.

## This week's priorities
1. Re-run the supported local Compose beta proof on the current `main` tip; backend-seam eval suites have reduced scope-boundary ambiguity but live proof is still required before release signoff.
2. Keep the supported-profile contract, catalog, and health surfaces aligned with the local-only provider posture.
3. Leave `personal_facts` out of the beta claim unless the supported profile is explicitly changed.
4. Keep delegation excluded from the shipped promise unless the executor/result-return path is made explicit and proven.

## Release definition right now
- [ ] Supported-profile flags and mounted routes still match the beta contract.
- [ ] Fresh live evidence exists on the current `main` tip for clean start, assistant completion, upload -> embed -> retrieve, and health surfaces.
- [ ] Backend-seam eval suites (golden tasks, identity boundaries, source-mode matrix) are passing on the current `main` tip — this reduces scope-boundary ambiguity but does not replace the live proof requirement above.
- [ ] The release promise does not include `personal_facts` unless the supported profile is updated.
- [ ] Delegation is either explicitly excluded or implemented with a real executor plus source-thread result return.
- [ ] No internal-only or quarantined surface is part of the release claim.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
