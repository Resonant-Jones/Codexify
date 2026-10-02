## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-24

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated private-preview lane. Mainline now has bounded account-import evidence through staging, canonical materialization, owner-visible readback, and automatic embedding/vector parity in isolated runtimes. The latest natural import-to-recall attempt stopped before recall after proof-environment interruption; the latest complete supported-Compose qualification remains `HOLD`. No 2026-09-24 implementation or qualification changed that posture.

## What changed recently

- Merged account-import browser staging, queue/worker materialization, ownership/provenance readback, and focused regression coverage.
- Added bounded live evidence for imported-message embedding handoff and backend/worker vector parity; no provider completion was established.
- Natural import-to-recall R3 was blocked at folder upload; R4 reached materialization and vector parity but was interrupted before recall.
- Fixed the newest-message history window and canonicalized inline chat-document context; the continuity probe keeps reported runtime symptoms unlocalized.
- Merged Guardian/Persona surface and canonical UI-geometry repairs with focused frontend tests; no release claim widened.
- The 2026-09-24 mainline accounting log records no same-day implementation or qualification work.
- On `feature/ums-continued`, UMS-05A through UMS-05C6 are closed: the branch adds the internal Memory Vault read surface and qualified pin, hold, Project-scope, Persona-attribution, and direct-creation mutations. UMS-05C7 is authorized; UMS-05C8+, UMS-05D+, and UMS-06+ remain unauthorized. These results are branch-local and do not change current-`main`, Preview, Beta, or release qualification.

## Current supported reality

- The named supported install path is local Docker Compose with `v1-local-core-web-mcp`, `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported contract covers local inference, ordinary chat, durable threads/messages/tasks, document upload/embed/readback, workspace retrieval, identity/ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Mainline contains bounded proof for topology, migrations, health, browser cold/warm chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, and the declared static suites at evaluated tips.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical display metadata remains inventory observation.
- Account import is bounded, not fully supported: isolated proof covers browser-to-materialization and presentation/readback, with later embedding/vector observations.
- Private Preview is opt-in: Whoosh'd remains default, DeepSeek is the only admitted cloud lane, and account activation/direct messaging remain gated; these are not public Beta support.

## Not yet true / do not assume

- Do not call the supported path release-ready: the latest complete qualification is `HOLD`.
- Do not infer a complete account-import recall path, provider injection, persisted answer, or negative scope control from the partial R4 proof.
- Do not treat focused tests, isolated import proofs, UI geometry repairs, direct messaging, activation, browser/import, connectors, Watchdog, retention, hosted sandbox, Atlas, or Pi work as public Beta support without current-main qualification.
- Do not infer restart/post-restart proof from the pre-repair supported-Compose qualification.
- Do not treat local `main` being 14 commits ahead of `origin/main`, or the staged unrelated dev-log deletion, as release or runtime evidence.

## Active blockers

- Run the complete supported-Compose qualification against repaired current `main`, including exact-model rejection, restart recovery, browser/event/provenance coherence, and ordinary chat after restart.
- Resolve the neighboring explicit-model worker-test contradiction and retain fail-closed behavior with no silent substitution.
- Complete a fresh isolated natural import-to-recall run through provider context, answer persistence, and a negative scope control.
- Requalify private-preview activation, Chroma/application, provider/persistence/isolation, and approved non-admin canary paths.
- Reconcile a clean intended publication baseline; no push or remote publication is implied by this audit.
- ADR-087 graceful shutdown/finite drain, Tester bind-readiness, browser/import, connector, Watchdog, retention, hosted-sandbox, and other bounded gates remain open where not directly covered above.

## This week's priorities

1. Freeze repaired current `main` and run the full supported-Compose proof bundle.
2. Close the explicit-model test contradiction and verify rejection before provider execution.
3. Prove uninterrupted account import through retrieval, provider input, answer persistence, and scope isolation.
4. Requalify the gated private-preview and remaining release-boundary paths on the same intended tip.
5. Reconcile publication baseline and update release claims only from resulting evidence.

## Release definition right now

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Mainline has bounded repair and qualification evidence for terminal projection, retrieval provenance, static lifecycle reliability, and partial account import.
- [ ] A fresh current-tip Compose run passes health, inventory, chat, durable readback, retrieval provenance, browser terminal state, event delivery, and restart recovery.
- [ ] An unavailable explicit model fails before provider execution and cannot be silently substituted.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration, browser, account-import recall, and claimed-path gates are green on the same evaluated tip.
- [ ] Preview lanes and the intended publication baseline have current evidence where claimed.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
