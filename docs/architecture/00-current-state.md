## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-10-03

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated Private Preview lane. Since the prior audit, mainline merged chat lifecycle/deadline repairs, qualification and operator-inspection scaffolding, bounded Campaign Engine and Codex App Server delivery work, and consent-gated human messaging. The latest complete supported-Compose qualification remains `HOLD`: current-tip proof covered ordinary chat and bounded failure/cancellation cases but found a new-thread browser transcript projection gap and stopped before restart or shutdown qualification. A branch-local refresh repair now passes focused tests and a retained-stack browser/durable-readback case; the full qualification remains open.

## What changed recently

- Merged chat stream ownership, queued cancellation, deadline enforcement, fast-mode handoff, and frontend failure-state repairs with focused coverage.
- Recorded current-tip supported-Compose evidence: ordinary API chat, unavailable explicit-model rejection without assistant fallback, durable readback, and in-flight cancellation passed; browser new-thread transcript coherence failed until reload.
- On the active Goal branch, reproduced that new-thread projection gap, refreshed the canonical transcript snapshot after authored-message persistence, and verified the message before completion plus durable reload/readback. This is bounded retained-stack evidence; it does not close the current-main or full Compose gate.
- Merged Private Preview message-request storage, consent, discovery, Inbox, route gating, and an isolated two-browser/durable-readback proof; default Beta remains excluded.
- Merged the qualification registry and onboarding/Tips surfaces, plus the internal Configuration Inspector; these are status or operator capabilities, not release-support expansion.
- Merged native execution-channel/Codex App Server delivery and bounded source-thread return proof; generalized channel support and public Beta support remain unproven.
- The audit base was clean at `c5c14da8d` and aligned with `origin/main`; this audit commit is local, and only committed mainline evidence counts.

## Current supported reality

- The named supported install path is local Docker Compose with `v1-local-core-web-mcp`, `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported contract covers local inference, ordinary chat, durable threads/messages/tasks, document upload/embed/readback, workspace retrieval, identity/ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Mainline has bounded proof for topology, migrations, health, durable readback, retrieval provenance, queue/worker lifecycle, locks, and declared static suites at their evaluated tips.
- The current-tip chat proof observed local provider/runtime identity, exact ordinary API completion, fail-closed unavailable-model behavior, cancellation, and no assistant persistence on failure/cancel paths.
- Private Preview messaging is enabled only on its admitted profile with explicit request consent; the isolated proof does not qualify the user's live Preview, provider execution, federation, or public Beta.

## Not yet true / do not assume

- Do not call the supported path release-ready; the latest complete qualification is `HOLD`.
- Do not infer broad browser transcript coherence, restart recovery, graceful drain, or full retry/event persistence from the bounded current-tip and branch-local proofs.
- Do not infer complete account-import recall, provider context, answer persistence, or negative scope control from partial import evidence.
- Do not treat focused tests, isolated proofs, Campaign Engine, Codex App Server, Configuration Inspector, onboarding, sidebar, messaging, activation, connectors, Watchdog, retention, hosted sandbox, Atlas, or Pi work as public Beta support without current-main qualification.
- Do not treat architecture contracts, qualification scaffolding, or branch-local/runtime-intent evidence as shipped behavior beyond the committed mainline scope.

## Active blockers

- Integrate the branch-local new-thread authored-message projection repair, then requalify browser/event/persistence coherence on the resulting current-main tip.
- Run a complete supported-Compose qualification on the frozen current `main`, including health/inventory, exact-model rejection, restart recovery, retry/cancellation, terminal provenance, and graceful shutdown.
- Complete an uninterrupted natural account-import run through retrieval, provider context, answer persistence, and a negative scope control.
- Requalify Private Preview activation, Chroma/application, provider/persistence/isolation, non-admin canary, and the merged messaging path on the intended deployed tip.
- Close remaining bounded gates for Tester bind-readiness, connectors, Watchdog, retention, hosted sandbox, and other claimed non-default paths before promoting them.

## This week's priorities

1. Integrate and requalify the browser projection repair, then run the full current-tip Compose proof bundle.
2. Freeze the evaluated `main` tip and close exact-model, retry, restart, and shutdown evidence.
3. Prove account import through recall, provider input, answer persistence, and scope isolation.
4. Requalify the intended Private Preview deployment, including consent-gated messaging and its provider/persistence boundaries.
5. Update qualification status and release claims only from those results.

## Release definition right now

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Mainline has bounded evidence for chat terminal ownership, retrieval provenance, queue/deadline/cancellation boundaries, and partial account import.
- [x] The branch-local new-thread authored-message projection repair passes a regression test and one retained-stack browser/durable-readback case.
- [ ] A fresh current-tip Compose run passes health, inventory, chat, durable readback, retrieval provenance, browser transcript, event delivery, restart recovery, and graceful shutdown.
- [ ] An unavailable explicit model fails before provider execution and cannot be silently substituted on the evaluated tip.
- [ ] Queue/worker, lock, migration, account-import recall, and every claimed Preview or non-default path are green under their own current evidence.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
