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

`main` remains in local-first Beta hardening with a separately gated Private Preview lane. Since the prior audit, mainline merged chat lifecycle/deadline repairs, qualification and operator-inspection scaffolding, bounded Campaign Engine and Codex App Server delivery work, and consent-gated human messaging. The latest complete supported-Compose qualification remains `HOLD`: current-tip proof covered ordinary chat and bounded failure/cancellation cases but found a new-thread browser transcript projection gap and stopped before restart or shutdown qualification. A branch-local first-message route-promotion repair now passes focused tests and retained-stack browser/durable-readback checks; the full qualification remains open.

## What changed recently

- Merged chat stream ownership, queued cancellation, deadline enforcement, fast-mode handoff, and frontend failure-state repairs with focused coverage.
- Recorded current-tip supported-Compose evidence: ordinary API chat, unavailable explicit-model rejection without assistant fallback, durable readback, and in-flight cancellation passed; browser new-thread transcript coherence failed until reload.
- On the active Goal branch, reproduced the new-thread projection gap and deferred visible-route promotion until after the authored-message POST succeeds, so route activation reads the durable first message. Focused tests and retained-stack browser/durable-readback checks pass; see `proofs/supported-compose/2026-10-03-chat-first-message-route-promotion.md`. This is bounded branch-local evidence and does not close the current-main or full Compose gate.
- On the active Goal branch, assistant `message.created` events now request a canonical snapshot refresh for the matching active chat. A sidebar-to-chat event-bridge regression and focused chat lifecycle tests pass; a fresh Vite server serving the changed checkout completed an isolated browser turn whose prompt/reply rendered and survived reload, with the terminal event and durable attempt linked to assistant message `18`. This is retained-stack branch evidence, not current-main integration or full Compose qualification; see `proofs/supported-compose/2026-10-03-chat-terminal-assistant-message-refresh.md`.
- On the active Goal branch, repaired the worker result projection so `task.completed.final_provider` and `final_model` match the resolved values already persisted with the assistant message. A focused regression and fresh retained-stack ordinary turn verified `local` / `local-chat`. At that proof's evaluated revision, the attempt row lacked `completed_message_id`; the later branch-local atomic-link repair is recorded below. The full Compose gate remains open.
- On the active Goal branch, a retained-stack ordinary turn accepted while `worker-chat` was stopped remained in Redis and completed after the worker restarted; its terminal event, assistant metadata, and request/task/thread/turn binding agreed. This covers a queued handoff across an idle worker stop/start only, not an active-task crash or full restart qualification.
- On the active Goal branch, a queued cancellation terminalized without an assistant, then an explicit retry of the same authored turn used a new request/task and produced one matching assistant. Raw Redis evidence confirms `task.created` can be appended after `task.running` because shared acceptance enqueues first, then attempts its best-effort created-event publication. The Command Center projection preserves that breadcrumb without rolling the effective lifecycle back. This is branch-local code/runtime evidence; see `proofs/supported-compose/2026-10-03-chat-command-center-late-created-projection.md` and `2026-10-03-chat-queued-cancel-retry.md`.
- On the active Goal branch, successful assistant persistence and its `completed_message_id` binding to the exact accepted attempt commit in one Postgres transaction. When PostgreSQL accepts the write, worker-controlled `task.failed` and `task.cancelled` event kinds are durably recorded before Redis publication; receipts prefer that durable event kind after Redis evidence expires. If a later worker step throws after the durable assistant link commits, the worker now reprojects completion from that link rather than publishing a conflicting failure. GuardianChat observes bounded receipts without replaying work. Focused backend/frontend tests and both attempt-schema/Postgres integration tests pass against an isolated disposable Postgres 15 instance. The earlier retained-Compose observation used older layered source snapshots and did not prove that branch's live runtime behavior.
- A later fresh ordinary browser turn on retained supported-Compose project `codexify_chat_branch_proof_896387ad2` did prove the current checkout's five changed chat backend runtime files were mounted byte-for-byte, with the database at migration head `d4c69e03a712`. The real UI turn persisted its authored and assistant messages, produced a matching `task.completed` event and durable receipt, and reloaded into the same transcript. The committed route-hydration repair selects an explicit `/chat/:id` on first render and begins transcript loading before paint; its focused regression passes. This proves one successful branch-local supported-profile turn and the route's loading-to-transcript projection only. It does not prove cancellation/retry, worker restart/shutdown, or active-worker-loss recovery; see `proofs/supported-compose/2026-10-03-chat-ordinary-turn-and-route-hydration.md`.
- On the same branch-local retained stack, a newly accepted request for explicit model `codexify_goal_unavailable_20261003` terminalized as `task.failed`: the raw event identified the advertised inventory (`local-chat` only), recorded `executed=false` and `fallback_attempted=false`, and no assistant persisted. After reload, the browser showed the authored prompt and “1 earlier response task failed.” The durable receipt preserves terminal kind and identity; detailed rejection diagnostics were observed in the Redis event payload, not in the durable receipt. See `proofs/supported-compose/2026-10-03-chat-unavailable-model-ui-truth.md`.
- A controlled retained-Compose worker termination after destructive dequeue lost an accepted task: the queue emptied, no terminal event or assistant appeared, the attempt remained only `accepted`, and the turn lock persisted for more than 12 minutes after manual worker restart. Explicit retry was rejected as `turn_in_flight`. The worker was stopped with operator-issued `docker kill`; this proves queue loss and retry blocking, not automatic restart behavior after an unexpected process exit. Safe orphan terminalization/retry semantics are not implemented. See `proofs/supported-compose/2026-10-03-chat-active-worker-crash-loss.md`.
- Merged Private Preview message-request storage, consent, discovery, Inbox, route gating, and an isolated two-browser/durable-readback proof; default Beta remains excluded.
- Merged the qualification registry and onboarding/Tips surfaces, plus the internal Configuration Inspector; these are status or operator capabilities, not release-support expansion.
- Merged native execution-channel/Codex App Server delivery and bounded source-thread return proof; generalized channel support and public Beta support remain unproven.
- Local `main` and live `origin/main` are aligned at `c5c14da8d`. Thirteen unpublished audit commits remain preserved on `backup/weekly-mainline-release-audit-20261002`; they are not part of mainline evidence.

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

- Integrate the branch-local new-thread authored-message and terminal final-model projection repairs, then requalify browser/event/persistence coherence on the resulting current-main tip.
- Run a complete supported-Compose qualification on the frozen current `main`, including health/inventory, exact-model rejection, restart recovery, retry/cancellation, terminal provenance, and graceful shutdown.
- Define and implement the authorized recovery contract for an active chat task lost after Redis dequeue: persist an honest orphan/failure outcome, reconcile assistant persistence, release the lock safely, and permit only an identity-preserving explicit retry. Successful assistant bindings and worker-controlled failure/cancellation event kinds now persist, but the attempt still lacks canonical request-state and diagnostic detail; the observed worker-loss attempt remained accepted without an assistant and blocked retry. The orphan timing and task-scoped worker-loss authority remain undecided.
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
- [x] The branch-local authored-message projection repairs pass regression coverage and retained-stack browser/durable-readback checks.
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
