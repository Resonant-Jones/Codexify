## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-18

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated friends-and-family private-preview lane. Mainline has merged Guardian landing/chat/composer refinements and accepted the ADR-088 account-activation boundary, but no fresh supported-Compose or runtime qualification has widened the release promise.

## What changed recently

- Mainline merged Guardian landing, sidebar, composer, and session-continuity refinements with focused frontend test coverage.
- Mainline accepted ADR-088 and added account-activation terrain analysis; this establishes a design boundary, not shipped activation support.
- The 2026-09-17 and 2026-09-18 mainline logs record no additional implementation or runtime qualification.
- Local `main` is eight commits ahead of `origin/main`; no remote publication or reconciliation is evidence of release readiness.

## Current supported reality

- The named supported install path is local Docker Compose with `v1-local-core-web-mcp`, `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The declared Beta Supported contract covers local inference, ordinary chat, durable threads/messages/tasks, document upload/embed/readback, workspace-scoped retrieval, identity/ownership, migrations, and operator diagnostics; current-tip qualification is separate.
- The local profile requires live Whoosh'd inventory for physical model availability. `local-chat` is a logical route, not model-runtime proof.
- Private Preview is an opt-in tester lane: Whoosh'd remains the default, DeepSeek is the only admitted cloud lane, and roster/fallback behavior does not make cloud inference public Beta support.
- Main contains bounded proof for selected migration/recovery, Chroma topology, ingress, Persona, sharing, and UMS-04 export/restore surfaces; these do not establish a running release path.
- Guardian UI refinements and the ADR-088 contract are on main; account-activation implementation and qualification are not part of supported reality.

## Not yet true / do not assume

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or recovery closure.
- Do not treat merged UI changes or focused frontend tests as authenticated browser completion, provider execution, persistence, or release proof.
- Do not treat the ADR-088 contract, dirty-checkout activation code, or focused activation proof as a live tester-account path, replay proof, or release support.
- Do not treat logical `local-chat`, DeepSeek roster discovery, focused tests, or provider catalog output as live provider execution or persistence proof.
- Do not treat private-preview migration/recovery and Chroma topology evidence as application startup, isolation, canary, or release proof.
- Do not promote CE-L1, browser/import, connectors, Watchdog, retention, hosted sandbox, Atlas, Pi, or other local-only/unmerged work into the release promise.

## Active blockers

- Fresh current-tip supported-Compose proof is missing across health, model inventory, chat, persistence/readback, retrieval, queue/worker, locks, and events.
- Tester bind-readiness repair and fresh isolated runtime proof remain open; historical diagnosis is static evidence only.
- Private Preview remains blocked on Chroma/application startup, provider/persistence/observability/isolation, and approved non-admin canary proof.
- ADR-087 enforcement and runtime proof remain open for provider/worker cleanup, PostgreSQL persistence, locks, late results, and finite graceful drain.
- Account activation lacks merged implementation plus frontend, auth-regression, security, disposable-runtime, live-profile, and real-recipient proof.
- CE-L1, browser/import, connector, Watchdog, retention, hosted-sandbox, and local-main publication alignment gates remain open or bounded.

## This week's priorities

1. Run the canonical current-tip Compose proof bundle, including Whoosh'd inventory, chat, persistence/readback, retrieval, queue/worker, locks, and events.
2. Land and qualify the fail-closed Tester bind-readiness predicate on a fresh isolated runtime.
3. Finish ADR-087 enforcement and prove finite drain, graceful stop, late-result handling, and durable terminal truth.
4. Resume Private Preview at Chroma/application, provider/persistence/isolation, authenticated browser, and canary gates.
5. Keep ADR-088 activation out of support claims until its implementation lands on `main` and completes its named proof lane; then requalify CE-L1, connectors, Watchdog, retention, hosted sandbox, and publication alignment.

## Release definition right now

- [x] The supported install path and Beta boundary are defined on `main`.
- [x] Internal, bounded, qualification-pending, and Out-of-Beta surfaces remain distinct from Beta Supported claims.
- [ ] Current-tip Compose proves healthy startup, live model inventory, terminal chat, durable readback, retrieval, and event delivery.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration, recovery, browser, and account-import claimed-path gates are green.
- [ ] Preview/provider lanes have current-main evidence for live execution, durable readback, isolation, and recovery/canary behavior where applicable.
- [ ] The release candidate is reconciled to the intended publication baseline.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
