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
Codexify is in local-beta hardening on `main`. The supported path is the local Docker Compose stack under the v1 local-only profile. Recent mainline work improved identity boundaries, retrieval proofing, and the operator-facing frontend, but the release promise is still narrow and quarantined surfaces remain out of scope.

## What changed recently
- Built-in help is seeded at backend startup and is now part of the supported retrieval proof pack.
- Live import catch-up was re-proven on `main`; the backlog drained while chat stayed healthy.
- An executable identity-boundary suite landed for project scope, explicit widening, and exclusion filters.
- Identity precedence is now documented as `actor_plus_role`; Guardian remains the stable first-person actor.
- Personal-facts route/runtime proof landed, but the live Postgres chatlog adapter still cannot satisfy the route and the surface remains quarantined.
- Frontend polish landed: split command-center observability, settings dock/data-tab fixes, mobile viewport stabilization, and Documents/Dashboard parity.

## Current supported reality
- Local Docker Compose remains the supported install path.
- Supported beta posture is still local-only: `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`.
- Chat acceptance, worker execution, and Postgres persistence remain the core validated loop.
- Upload -> parse -> embed -> retrieve remains supported, with one shared runtime vector store.
- Built-in system docs/help are seeded at startup and available to retrieval.
- The import embed worker can drain a live backlog without breaking chat or health surfaces.
- The supported profile still treats `command_bus` as internal-only and quarantines `personal_facts` plus other non-beta surfaces.
- `/health`, `/health/chat`, `/api/health/llm`, `/api/health/retrieval`, and `/api/llm/catalog?include=all` remain the primary runtime evidence surfaces.

## Not yet true / do not assume
- Do not assume `personal_facts` is part of the supported beta surface; the supported profile quarantines it and the live route proof exposed a missing adapter method.
- Do not assume delegation or autonomous coding-agent execution is shipped in the release promise.
- Do not assume internal operator surfaces such as the Command Center / Observability Deck are the released beta operator surface.
- Do not assume catalog presence alone means runtime support; the supported profile and provider registry still gate the beta promise.
- Do not assume the latest `main` tip is fully re-proven end to end unless the current audit window has fresh live evidence.

## Active blockers
- Fresh live proof on the exact current `main` tip is stale and must be rerun before signoff.
- Release signoff still depends on the supported-profile, provider-registry, catalog, and health surfaces agreeing in the live runtime.

## This week’s priorities
1. Re-run the supported Compose beta proof on the current `main` tip.
2. Keep the supported-profile contract, provider registry, and health surfaces aligned.
3. Keep `personal_facts`, delegation, and internal operator surfaces out of the release promise unless they are freshly proven and explicitly promoted.
4. Preserve the current chat and retrieval path while validating any further UI polish on the same release gate.

## Release definition right now
- [ ] Current `main` has fresh live evidence for chat completion, upload -> embed -> retrieve, and the health surfaces.
- [ ] The supported profile still matches the mounted route and provider posture.
- [ ] Quarantined and internal-only surfaces remain outside the release promise.
- [ ] Any promoted surface such as `personal_facts` is fully wired and proven before inclusion.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
