## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-21

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated friends-and-family private-preview lane. Recent provider-catalog changes clarify local runtime identity, but only focused code/test evidence exists; no release support claim widened.

## What changed recently

- Mainline merged one-time, recipient-bound account activation and admitted it to the gated private-preview profile; live onboarding proof remains open.
- Mainline separated the stable `local` provider/policy class from local runtime identity and added canonical runtime labels plus inventory display metadata.
- Frontend catalog selection now presents runtime identity while backend model aliases remain non-canonical UI details.
- Focused provider-catalog backend and frontend tests were added/updated; they do not prove live inference, persistence, or release readiness.
- The 2026-09-21 mainline log records no same-day implementation or runtime qualification.

## Current supported reality

- The named supported install path is local Docker Compose with `v1-local-core-web-mcp`, `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The declared Beta Supported contract covers local inference, ordinary chat, durable threads/messages/tasks, document upload/embed/readback, workspace-scoped retrieval, identity/ownership, migrations, and operator diagnostics; current-tip qualification is separate.
- `local` is the stable provider/policy class; the catalog can expose a separate configured local runtime identity and inventory-derived model label.
- The local profile requires live Whoosh'd inventory for physical model availability. `local-chat` is a logical route, not model-runtime proof.
- Private Preview is an opt-in tester lane: Whoosh'd remains the default, DeepSeek is the only admitted cloud lane, and catalog/fallback behavior does not make cloud inference public Beta support.
- Account activation is merged and admitted only as a gated private-preview/tester capability; repository tests do not prove a live preview onboarding path.

## Not yet true / do not assume

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or recovery closure.
- Do not treat provider-catalog tests, logical `local-chat`, runtime labels, inventory metadata, or provider catalog output as live provider execution or persistence proof.
- Do not treat the activation implementation, CLIs, or activation-page tests as live migration, disposable issuance/redemption, replay rejection, or recipient-login proof.
- Do not assume multi-runtime discovery, selection, routing, or persistence among Whoosh'd, LM Studio, Ollama, or other local runtimes.
- Do not promote CE-L1, browser/import, connectors, Watchdog, retention, hosted sandbox, Atlas, Pi, or other local-only/unmerged work into the release promise.

## Active blockers

- Fresh current-tip supported-Compose proof is missing across health, inventory, chat, persistence/readback, retrieval, queue/worker, locks, and events.
- Tester bind-readiness repair and fresh isolated runtime proof remain open; historical diagnosis is static evidence only.
- Private Preview remains blocked on Chroma/application startup, provider/persistence/observability/isolation, live activation/replay/login, and approved non-admin canary proof.
- ADR-087 enforcement and runtime proof remain open for provider/worker cleanup, PostgreSQL persistence, locks, late results, and finite graceful drain.
- Local runtime catalog identity is focused/test-proven only; live Whoosh'd execution and publication-baseline reconciliation remain unqualified.
- CE-L1, browser/import, connector, Watchdog, retention, hosted-sandbox, and local-main publication alignment gates remain open or bounded.

## This week's priorities

1. Run the canonical current-tip Compose proof bundle, including Whoosh'd inventory, chat, persistence/readback, retrieval, queue/worker, locks, and events.
2. Land and qualify the fail-closed Tester bind-readiness predicate on a fresh isolated runtime.
3. Finish ADR-087 enforcement and prove finite drain, graceful stop, late-result handling, and durable terminal truth.
4. Qualify Private Preview activation end to end, then resume provider/persistence/isolation, authenticated browser, and canary gates.
5. Reconcile the intended publication baseline before making release claims; then requalify the catalog/provider, CE-L1, connectors, Watchdog, retention, and hosted-sandbox surfaces.

## Release definition right now

- [x] The supported install path and Beta boundary are defined on `main`.
- [x] Internal, bounded, qualification-pending, and Out-of-Beta surfaces remain distinct from Beta Supported claims.
- [ ] Current-tip Compose proves healthy startup, live model inventory, terminal chat, durable readback, retrieval, and event delivery.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration, recovery, browser, and account-import claimed-path gates are green.
- [ ] Preview activation and provider lanes have current-main evidence for live execution, durable readback, isolation, recovery, and canary behavior where applicable.
- [ ] The release candidate is reconciled to the intended publication baseline.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
