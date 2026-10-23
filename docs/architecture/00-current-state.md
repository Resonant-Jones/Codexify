## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-10-23

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated Private Preview lane. Since the prior audit, mainline changes were documentation and repository cleanup; no new runtime qualification or supported-path widening landed. The current release gate remains `HOLD`.

## What changed recently

- Merged the account recovery, export, archive, and conversation-retention decision brief; it explicitly remains a decision request with no accepted architecture, runtime implementation, or R2 work.
- Added the 2026-10-22 mainline accounting log, which records feature-ref work as unmerged rather than shipped behavior.
- Removed the accidental `Codexify.Space` gitlink; this is repository hygiene, not a product or release change.
- Preserved the reconciled mainline history, UMS ORM restoration, account-boundary fail-closed repair, and bounded Private Preview restart evidence from the preceding audit window.
- No fresh integrated-tip supported-Compose qualification, provider inference, or complete export/restore qualification landed on local `main`.

## Current supported reality

- The named supported install path is local Docker Compose profile `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported envelope covers local inference, ordinary chat, durable threads/messages/tasks, supported document ingestion and retrieval, account ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Mainline has bounded evidence at evaluated tips for topology, health, browser chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, cancellation, and deadline behavior.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- UMS ORM imports and migration-to-ORM parity are recorded; this does not establish complete UMS or supported-Compose qualification.
- Private Preview is opt-in: Whoosh'd remains the default local lane, DeepSeek is the only admitted cloud lane, and same-node human messaging is not default Beta support.
- The legacy continuity operator surface is fail-closed for remote, Preview, and multi-user execution because operator credentials do not establish account authority.

## Not yet true / do not assume

- Do not call the supported path release-ready; the latest complete supported-Compose qualification is `HOLD`.
- Do not infer current-tip restart/shutdown recovery, browser/event/provenance coherence, ordinary chat after restart, or a complete natural import-to-recall path.
- Do not infer exact unavailable-model rejection; the recorded complete Compose proof accepted work with model substitution and no assistant fallback flag.
- Do not treat the delegation canary as successful worker-path execution: it stopped at a `reasoning_effort` mismatch before provider execution, and worker egress was observed despite `allow_network=false`.
- Do not treat the merged recovery/retention decision brief as accepted architecture, implemented export/restore, object-store write-back, or lifecycle-cleanup proof.
- Do not promote account-owned connectors, direct messaging, activation, browser host/import, Watchdog, hosted sandbox, Atlas, Pi, federation, or autonomous coding-worker work to default Beta support without current-main qualification.
- Branch-only implementation, origin-only accounting, uncommitted checkout work, and local-only commits are not shipped `main` reality.
- The current-state knowledge-graph node parses but its freshness is stale; validity is not current release proof.

## Active blockers

- A fresh current-tip supported-Compose qualification is missing, including model rejection, browser/event/provenance coherence, restart recovery, and ordinary chat after restart.
- The UMS/Chronicle lane retains one inherited stale migration-head assertion, and blocked Chronicle HTTP coverage still requires execution against the corrected baseline.
- The explicit-model worker/test contradiction must be resolved with fail-closed behavior and no silent substitution.
- The delegated worker-to-adapter `reasoning_effort` contract mismatch must be resolved and re-proven before any delegation execution claim is accepted.
- The new-thread authored-message projection gap and natural import-to-recall scope proof remain open.
- Export/restore and conversation-lifecycle coverage remains incomplete: v3 is the public export default, v4 compatibility flags conflict with recorded restore evidence, binary write-back is unsupported, and cleanup dependencies lack complete proof.
- Release metadata freshness and local-main publication state must be reconciled before treating them as shared release evidence.

## This week’s priorities

1. Freeze the evaluated local `main` SHA and run the complete supported-Compose proof bundle.
2. Repair the stale migration-head expectation and execute the blocked Chronicle HTTP regression cases.
3. Close the explicit-model rejection contradiction before provider execution.
4. Reprove new-thread projection, browser/event coherence, restart recovery, and ordinary chat on one evaluated tip.
5. Resolve export/restore/retention contract gaps, the delegation adapter contract, and import-to-recall scope proof.

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
