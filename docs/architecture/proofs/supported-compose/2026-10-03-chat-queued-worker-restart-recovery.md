# Queued chat recovery after worker restart

Date: 2026-10-03. Evaluated code: active Goal branch `8eef04032`. Authority:
ordinary-chat reliability Goal and Development Operator Level 0. Classification:
`PROOF_REQUIRED`; no source behavior changed during this proof. Current-main
and full supported-Compose qualification remain open.

## Atomic Task Spec

On the retained supported-Compose stack, stop the idle chat worker, submit one
ordinary API turn, and independently prove queue and attempt acceptance while
the worker is unavailable. Start the worker and require the queued task to
reach one successful terminal event with one durable assistant message and
matching provider/model truth. Check lock ownership using the canonical
`turn_lock:<thread_id>` key. Limit the claim to queued handoff across an idle
worker stop/start; do not infer active-task crash recovery or Redis/backend
restart durability.

Governing sources: ADR-001 (queue acceptance is distinct from completion),
ADR-003 (authored-message and attempt identity remain distinct), ADR-038
(transport observation is distinct from execution), ADR-087 (accepted task
deadline), ADR-091 (durable attempt binding), and the Chat Runtime Contract.

## Preconditions and recovery sequence

Project: `codexify_chat_proof_f091_20261002`, API `127.0.0.1:18888`. Immediately
before stopping the worker, health was `healthy`, the heartbeat was `fresh`,
and the chat queue depth was zero. The worker container had restart policy
`unless-stopped`. Only `worker-chat` was stopped; backend, Redis, Postgres,
frontend, and model runtime remained running. The worker source overlay was
the active Goal branch source and was hash-checked after start.

With the worker stopped, one normal turn was accepted with
`acceptance_status=accepted`. The chat queue depth was `1`. Postgres contained
the matching accepted attempt before execution:

| Evidence | Result |
| --- | --- |
| Thread / user message | `29` / `66` |
| Request / task / turn | `req_4e42fc1e49354814910e37f2722d6391` / `87ecae23-4ebb-4e13-a9cc-f6a69468f580` / `5f54788b-edfe-478f-ae7e-216db8dd0178` |
| Queued lock | Redis `turn_lock:29` existed while the worker was stopped and the accepted task remained queued |
| Queue while stopped | `codexify:queue:chat` length `1` |

After starting the worker, health returned to `healthy` with a fresh heartbeat.
The persisted event stream replayed `task.created`, running/state/progress/chunk
events, then one `task.completed`. The API transcript contained one assistant
message, ID `67`, with the unique requested response marker.

| Completion evidence | Result |
| --- | --- |
| Terminal aliases and final selection | `provider=local`, `model=local-chat`, `final_provider=local`, `final_model=local-chat` |
| Nested selection | `local` / `local-chat`, source `LOCAL_CHAT_MODEL` |
| Durable assistant metadata | Request ID and final provider/model matched the terminal event; turn ID matched the accepted attempt |
| Attempt binding | Request, task, thread, and turn matched; `completed_message_id` remained null |
| Queue after completion | `codexify:queue:chat` length `0` |
| Lock after completion | `turn_lock:29` absent; global `turn_lock:*` scan empty |

The source overlay was restored to its original hash after the probe and only
`worker-chat` was restarted again. The stack returned to healthy/fresh/idle.

## Evidence limits and correction

This proves an accepted task survives an idle chat-worker stop/start because
Redis retains the queue entry, the restarted worker executes it, and durable
transcript plus terminal readback agree. It does not prove recovery after
worker death during provider execution, Redis/backend/host restart, retry
semantics, graceful shutdown, browser rendering for this turn, or complete
supported-Compose qualification. The attempt's `completed_message_id` remains
null, consistent with the separately documented incomplete backend lifecycle
state machine.

An earlier exploratory lock scan in this session used `codexify:turn_lock:*`,
which does not match the implementation's `turn_lock:<thread_id>` key. That
scan is excluded. This proof used the canonical key directly while queued and
after completion.
