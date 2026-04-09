## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-04-08

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
- Built-in help is now bundled and re-seeded into documents and RAG at backend startup.
- API and worker retrieval now share one runtime vector store instead of drifting by path.
- Personal-facts routes were wired into the Postgres chatlog adapter and covered by runtime route tests, but the supported profile still quarantines that surface.
- Live import catch-up was re-proven on `main`: the embed backlog drained while chat stayed healthy.
- Frontend-only chat/sidebar polish landed, but it does not change the release contract.

## Current supported reality
- Local Docker Compose remains the supported install path.
- Supported beta posture is still local-only: `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`.
- Chat acceptance, worker execution, and Postgres persistence remain the core validated loop.
- Upload -> parse -> embed -> retrieve remains supported, with one shared runtime vector store.
- Built-in system docs/help are seeded at startup and available to retrieval.
- The import embed worker can drain a live backlog without breaking chat or health surfaces.
- `/health`, `/health/chat`, `/api/health/llm`, `/api/health/retrieval`, and `/api/llm/catalog?include=all` remain the primary runtime evidence surfaces.

## Not yet true / do not assume
- Do not assume the current tip has been re-proven end-to-end after the latest runtime-adjacent merges.
- Do not assume `personal_facts` is part of the supported beta surface; the supported profile quarantines it.
- Do not assume delegation or autonomous coding-agent execution is shipped; the current release promise still excludes that loop.
- Do not assume internal operator surfaces or quarantined routes represent the supported beta contract.
- Do not assume older proof docs alone describe the current tip if a newer merge changed runtime wiring.

## Active blockers
- Fresh live release evidence on the exact current `main` tip is stale and needs to be rerun.
- Release signoff still depends on the supported-profile, provider registry, and health surfaces staying aligned.

## This week’s priorities
1. Re-run the supported local Compose beta proof on the current `main` tip.
2. Keep the supported-profile contract, catalog, and health surfaces aligned with the local-only provider posture.
3. Leave `personal_facts` out of the beta claim unless the supported profile is explicitly changed.
4. Keep delegation excluded from the shipped promise unless the executor/result-return path is made explicit and proven.

## Release definition right now
- [ ] Supported-profile flags and mounted routes still match the beta contract.
- [ ] Fresh live evidence exists on the current `main` tip for clean start, assistant completion, upload -> embed -> retrieve, and health surfaces.
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
