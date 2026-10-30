## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-10-30

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` is in local-first Beta hardening with a separately gated Private Preview lane. The current local `main` tip is `a5d871a0c`; it is two commits behind the stored `origin/main` ref, and origin-only work is excluded from shipped claims. Private Preview read state is live-qualified at `5569f3f34`, while the serving source has advanced to `c8e72ef86` without a fresh 20-check run. The supported runtime remains unqualified and the release gate is `HOLD`.

## What changed recently

- Unified the Saved Widget, automatic-consent, and read-state migration graph at Alembic head `3a91d7c4e8b2`.
- Passed 149 focused Saved Widget, consent, validation, and migration checks against disposable PostgreSQL 16.15; this is database evidence, not supported-Compose qualification.
- Executed the Private Preview deployment sequence: rebuilt the runtime image, applied `f0d7c4b2a198` → `3a91d7c4e8b2`, recreated containers, and retained existing rows.
- Live-tested recipient-local read state with two synthetic accounts: 20 of 20 checks passed at serving revision `5569f3f34`, including restart recovery and account isolation.
- Recorded post-qualification serving revision `c8e72ef86` observations, Docker build-context secret/scratch exclusions, and the remaining proof boundaries.

## Current supported reality

- The named supported install path is local Docker Compose profile `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported envelope covers local inference, ordinary chat, durable threads/messages/tasks, supported document ingestion and retrieval, account ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Mainline has bounded evidence for topology, health, browser chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, cancellation, deadlines, and authorization; bounded evidence is not complete runtime qualification.
- The current migration graph has one head, and focused PostgreSQL evidence passed; no current-tip Docker Compose qualification is established.
- Private Preview same-node read state is deployed and live-qualified at `5569f3f34`; `c8e72ef86` has health/schema/mount observations only, not a fresh feature run.
- Private Preview same-node messaging has live end-to-end evidence for approved synthetic accounts; this does not qualify share links, cross-node transport, or default Beta support.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- Connectors, activation, browser host/import, Watchdog, hosted sandbox, Atlas, Pi, federation, autonomous coding-worker work, and Saved Widget lifecycle are not default Beta support without current-main qualification.

## Not yet true / do not assume

- Do not call the supported path release-ready or treat migration qualification as deployment.
- Do not infer a fresh integrated-tip Compose run, restart recovery, browser/event/provenance coherence, ordinary chat after restart, or a complete natural import-to-recall path.
- Do not infer exact unavailable-model rejection; the recorded complete Compose proof accepted work with model substitution and no assistant fallback flag.
- Do not treat the delegated worker canary as successful provider execution; the `reasoning_effort` contract still fails before provider execution, and worker egress was observed despite `allow_network=false`.
- Do not treat focused suites, migration receipts, deployment rehearsal, or a healthy Private Preview as product qualification.
- Do not treat Saved Widget storage, validation, or unmerged promotion work as user-facing promotion, listing, invocation, editing, deletion, export/restore, or Library Widgets support.
- Do not treat `c8e72ef86` source equivalence as a re-run of the 20 live read-state checks; browser unread badges and the consent HTTP surface remain unverified.
- Share links remain bearer credentials; links without `expires_in_days` do not expire and no revocation endpoint exists.
- Branch-only, origin-only, uncommitted, and local-only work is not shipped `main` reality. Capabilities without current-main qualification are not default Beta support.
- The current-state knowledge-graph node parses but has stale freshness metadata; it is not current release proof.

## Active blockers

- A fresh current-tip supported-Compose qualification is missing, including model rejection, browser/event/provenance coherence, restart recovery, and ordinary chat after restart.
- Frontend frozen-lockfile installation on the supported path remains unrehearsed.
- Cross-browser qualification of the generative-UI containment repair is missing; Chrome 156 is the only reported browser result and Playwright cannot launch on the reported host.
- The UMS/Chronicle lane retains an inherited stale migration-head assertion, and blocked Chronicle HTTP coverage still needs execution against the corrected baseline.
- The explicit-model rejection and delegated worker-to-adapter contract remain unresolved before provider execution claims.
- New-thread projection, natural import-to-recall, scope isolation, export/restore/retention, and complete conversation-lifecycle proof remain open.
- Private Preview still lacks share-link expiry/revocation, cross-node messaging proof, browser-verified unread badges, and consent-enforcement coverage at a profile that mounts `iddb`; Saved Widget lifecycle and complete browser qualification also remain open.

## This week’s priorities

1. Freeze the evaluated local `main` SHA and run the complete supported-Compose proof bundle.
2. Complete the supported deployment sequence's frontend frozen-lockfile installation step.
3. Resolve the explicit-model/delegated-adapter contradictions and execute the blocked Chronicle HTTP cases.
4. Reprove new-thread projection, browser/event coherence, restart recovery, ordinary chat, and scope isolation on one evaluated tip.
5. Close the highest-risk Preview and lifecycle gaps: revocation, export/restore, browser unread badges, consent endpoint behavior, and Saved Widget operations.

## Release definition right now

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Bounded chat, cancellation, durable readback, retrieval, authorization, and migration-chain evidence exists.
- [ ] A fresh current-tip Compose run passes health, inventory, chat, durable readback, retrieval, browser projection, event delivery, and restart recovery.
- [ ] An unavailable explicit model fails before provider execution and cannot be silently substituted.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration deployment, browser, import-recall, and scope-isolation gates are green on one evaluated tip.
- [ ] Delegated execution has a passing worker-to-adapter `reasoning_effort` contract and live proof.
- [ ] Any claimed Preview or public-ingress path has current live evidence tied to the evaluated mainline.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
