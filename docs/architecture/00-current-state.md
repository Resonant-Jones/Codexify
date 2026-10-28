## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-10-28

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated Private Preview lane. Recent merges harden account authority, consent, terminal-state evidence, transport selection, and Saved Widget persistence, but none establishes fresh supported-path qualification. The release gate remains `HOLD`.

## What changed recently

- Merged account-bound agent run readback and fail-closed cancellation behavior; unsupported cancellation remains unavailable rather than mutating state.
- Added account consent and scoped settings enforcement for automatic personal-fact collection; this is privacy/authority hardening, not a broader memory release claim.
- Reconciled durable chat terminal/readback assertions, Whoosh'd transport-selection checks, and shared evidence release-truth contracts; these are bounded code/test evidence.
- Merged the canonical Saved Widget storage foundation: account-owned identity, immutable revision snapshots, forward-only current revision, and retained provenance. This is storage only, not lifecycle support.
- Retained the generated-UI navigation containment repair and Chrome 156 evidence from the prior audit; cross-browser and supported-release equivalence remain unproven.
- No fresh integrated-tip supported-Compose qualification, provider inference, or complete export/restore qualification landed.
- Local `main` is 25 commits ahead and 4 commits behind the stored `origin/main` ref; no fetch or push was performed, so origin-only work is excluded from shipped claims.

## Current supported reality

- The named supported install path is local Docker Compose profile `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported envelope covers local inference, ordinary chat, durable threads/messages/tasks, supported document ingestion and retrieval, account ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Mainline has bounded evidence at evaluated tips for topology, health, browser chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, cancellation, and deadline behavior.
- Mainline now has account-scoped run-readback and consent-gated personal-fact code/test coverage, plus Saved Widget eligibility/provenance and storage evidence; none is a default Beta expansion.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- UMS ORM imports and migration-to-ORM parity are recorded; this does not establish complete UMS or supported-Compose qualification.
- Private Preview is opt-in: Whoosh'd remains the default local lane, DeepSeek is the only admitted cloud lane, and its profile admits bounded same-node messaging plus share routes; neither is default Beta support or end-to-end qualified here.
- The legacy continuity operator surface is fail-closed for remote, Preview, and multi-user execution because operator credentials do not establish account authority.

## Not yet true / do not assume

- Do not call the supported path release-ready; the latest complete supported-Compose qualification is `HOLD`.
- Do not infer current-tip restart/shutdown recovery, browser/event/provenance coherence, ordinary chat after restart, or a complete natural import-to-recall path.
- Do not infer exact unavailable-model rejection; the recorded complete Compose proof accepted work with model substitution and no assistant fallback flag.
- Do not treat the delegation canary as successful worker-path execution: it stopped at a `reasoning_effort` mismatch before provider execution, and worker egress was observed despite `allow_network=false`.
- Do not treat merged regression suites, bounded evidence contracts, or focused database tests as live runtime qualification.
- Do not treat the merged recovery/retention decision brief as accepted architecture, implemented export/restore, object-store write-back, or lifecycle-cleanup proof.
- Do not treat Saved Widget validation, storage, or ADR-102 acceptance as lifecycle implementation: promotion, listing, invocation, editing, deletion, export/restore, Library Widgets filtering, Web Audio, and canvas qualification remain open.
- Do not treat Chrome 156 containment evidence as cross-browser, Tauri, Playwright, or supported-Compose proof; the committed Playwright suite remains blocked by browser launch failure on the reported host.
- Do not promote connectors, direct messaging/share, activation, browser host/import, Watchdog, hosted sandbox, Atlas, Pi, federation, or autonomous coding-worker work to default Beta support without current-main qualification.
- Share links in the private-preview route are bearer credentials; links without `expires_in_days` do not expire and no revocation endpoint exists.
- Branch-only implementation, origin-only accounting, uncommitted checkout work, and local-only commits are not shipped `main` reality.
- The current-state knowledge-graph node parses but its freshness is stale; validity is not current release proof.

## Active blockers

- A fresh current-tip supported-Compose qualification is missing, including model rejection, browser/event/provenance coherence, restart recovery, and ordinary chat after restart.
- Cross-browser qualification of the integrated generative-UI containment repair is missing; Chrome 156 is the only reported browser-specific result and Playwright cannot launch on the reported host.
- The UMS/Chronicle lane retains one inherited stale migration-head assertion, and blocked Chronicle HTTP coverage still requires execution against the corrected baseline.
- The explicit-model worker/test contradiction and delegated worker-to-adapter `reasoning_effort` mismatch remain unresolved before provider execution claims.
- New-thread authored-message projection, natural import-to-recall, and complete scope-isolation proof remain open.
- Export/restore and conversation-lifecycle coverage remains incomplete: v3 is the public export default, v4 compatibility flags conflict with recorded restore evidence, binary write-back is unsupported, and cleanup dependencies lack complete proof.
- Private-preview messaging/share admission has route-mount and focused-test evidence but lacks current end-to-end live proof; bearer-link expiry and revocation remain unresolved risks.
- Saved Widget remains blocked on authorized promotion, authoritative listing, lifecycle operations, and complete browser qualification.
- Release metadata freshness and local-main publication state must be reconciled before treating them as shared release evidence.

## This week’s priorities

1. Freeze the evaluated local `main` SHA and run the complete supported-Compose proof bundle.
2. Repair the stale migration-head expectation and execute the blocked Chronicle HTTP regression cases.
3. Close the explicit-model rejection and delegated adapter contract contradictions before provider execution.
4. Reprove new-thread projection, browser/event coherence, restart recovery, and ordinary chat on one evaluated tip.
5. Resolve export/restore, import-to-recall, private-preview messaging/share, and Saved Widget qualification gaps.

## Release definition right now

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Bounded chat, cancellation, durable readback, retrieval, and authorization evidence exists at evaluated mainline tips.
- [ ] A fresh current-tip Compose run passes health, inventory, chat, durable readback, retrieval, browser projection, event delivery, and restart recovery.
- [ ] An unavailable explicit model fails before provider execution and cannot be silently substituted.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration, browser, import-recall, and scope-isolation gates are green on one evaluated tip.
- [ ] Delegated execution has a passing worker-to-adapter reasoning-effort contract and live proof.
- [ ] Claimed Preview or public-ingress paths have current live evidence, and changed release metadata points to the evaluated mainline.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
