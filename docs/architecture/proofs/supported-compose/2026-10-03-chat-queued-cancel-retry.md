# Queued chat cancellation and explicit retry proof

Date: 2026-10-03. Evaluated code: active Goal branch `1e328e7d6`. Authority:
ordinary-chat reliability Goal and Development Operator Level 0. Classification:
`PROOF_REQUIRED`; no source behavior changed during this proof. The current-main
and full supported-Compose gates remain open.

## Atomic Task Spec

On the retained supported-Compose stack, stop the idle chat worker, accept one
ordinary user turn, and request cancellation while its task remains queued.
Require the restarted worker to terminalize that attempt as cancelled without
assistant persistence and to clear only its cancellation marker and canonical
turn lock. Then explicitly retry the same authored turn with a new request/task
identity and the same turn identity. Require one successful assistant message
whose terminal provider/model agrees with durable metadata. Independently read
the raw SSE events, Redis queue/lock/cancel state, and PostgreSQL message and
attempt rows.

Governing sources: ADR-001 (acceptance is distinct from completion), ADR-003
(message and request identities remain distinct), ADR-038 (transport
observation is distinct from execution), ADR-087 (deadline failures and
retries require new attempt identity), ADR-091 (durable attempt binding), and
the Chat Runtime Contract. The task introduces no new retry state or identity
rule.

## Queue cancellation

Project: `codexify_chat_proof_f091_20261002`, API `127.0.0.1:18888`. The worker
was healthy/fresh, queue depth zero, and the canonical `turn_lock:*` set empty
before the test. Only `worker-chat` was stopped; backend, Redis, Postgres,
frontend, and model runtime remained running.

An ordinary API turn was accepted while the worker was stopped. The cancel API
returned `cancel_requested=true`. Before restart, Redis showed queue length
`1`, `turn_lock:30` present, and the task ID in
`codexify:queue:cancelled`; Postgres held its matching accepted attempt.

After the worker restarted, its persisted event stream reached
`task.cancelled`. The transcript still contained exactly user message `68` and
no assistant. The chat queue was empty, `turn_lock:30` was absent, and the
cancellation marker had been cleared.

| Cancelled attempt | Value |
| --- | --- |
| Thread / user message | `30` / `68` |
| Request / task / turn | `req_6787e0bb6b7d4c0481e9d370bd28d6dd` / `991118ef-340e-44f8-83a8-d1e993fc2e34` / `13c35a08-6764-4569-af4b-8eeed37cd8b4` |
| Event sequence | `task.created`, `task.state`, `task.running`, `task.cancelled` |
| Assistant persistence | None |
| Queue / lock / cancel marker | `0` / absent / cleared |

## Explicit retry of the same authored turn

After cancellation terminalized and the lock was released, the same thread was
explicitly retried with the original turn ID and a new request ID. Acceptance
returned a different task ID. PostgreSQL showed two distinct request/task
attempt bindings for the same thread and turn. The retry produced one assistant
message, ID `69`, containing the unique requested marker; the durable metadata
request ID and final provider/model matched the raw `task.completed` event.

| Retry evidence | Value |
| --- | --- |
| Request / task / turn | `req_0d7bea3c4ac14e428d15273e56c71b39` / `9246a6fc-a59b-42a4-95c9-7abe44725771` / `13c35a08-6764-4569-af4b-8eeed37cd8b4` |
| Terminal | `task.completed`; `provider=local`, `model=local-chat`, `final_provider=local`, `final_model=local-chat` |
| Nested model selection | `local` / `local-chat`, source `LOCAL_CHAT_MODEL` |
| Transcript | One authored message and one assistant message; no duplicate assistant |
| Durable attempt completion link | Both attempts still had null `completed_message_id` |
| Final Redis state | Queue empty, no `turn_lock:*` keys, neither cancellation marker remained |

## Evidence limits and follow-up

This is API/SSE plus independent Redis/PostgreSQL evidence on retained data; it
does not prove the browser's visible cancel/retry controls, retry after provider
failure or authoritative deadline failure, active-task crash recovery, or
graceful shutdown.

The retry stream delivered `task.state` and `task.running` before
`task.created`. All three events were present, and the terminal event and
durable transcript agreed, but this observed event chronology is not yet
explained or qualified. The `chat_completion_attempts` rows also still lack
terminal status and `completed_message_id`; the full backend request/replay
lifecycle remains unimplemented per the Chat Runtime Contract. Do not treat
this proof as closing either follow-up.
