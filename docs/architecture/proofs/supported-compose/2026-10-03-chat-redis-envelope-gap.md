# Redis child operations escape the accepted chat deadline

Date: 2026-10-03. Evaluated repair-branch source: **53a2b1cfa**.
Classification: PROOF_REQUIRED; architecture-impact, P1; owner: Codex.
The controlled transport gap is confirmed. Full supported qualification remains HOLD.

## Atomic Task Spec and authority

Characterize accepted-worker Redis event publication, cancellation observation
and canonical owner lock release. Use actual helper/library methods in isolated
Python processes, an owned loopback RESP peer, immutable 0.25-second remaining
work/terminal snapshots, and an observation at 0.5 seconds before releasing the
response. Verify healthy actual Redis controls, exact source custody, prior
durable completion, health and fixture cleanup. This receipt is the sole tracked
allowlisted change; private runners and exact owned transport fixtures belong
to this proof. Commit subject: docs(proof): record Redis accepted-deadline gap.

Authority: explicit ordinary-chat reliability Goal, Codex Development Operator
Goal, Chat Runtime Contract and ADR-087. Direct bounded proof is already
authorized; no new architecture, Campaign progression, recovery policy,
runtime source refresh/restart, application message/database mutation, queue
consumption, push, deployment or release promotion occurred.

The original checkout is clean main at e992d8e2b, matching the freshly fetched
remote after the separately authorized branch reconciliation. This proof uses
the isolated repair branch and retained runtime, not that newer mainline source
or migration baseline. The new upstream commits did not change the evaluated
worker, Redis queue/event/lock helpers or accepted-deadline authority; their
task-SSE ingress contract changes retain PostgreSQL resource authorization
before Redis transport. No broader current-main integration claim follows.

## Current causal path

Worker _safe_publish() calls task_events.publish_with_visibility() ->
publish() -> _with_reconnect() -> request-client XADD. Cancellation
observation uses the same reconnect helper for SISMEMBER. Canonical
release_turn_lock() uses it for owner/token-checked EVAL, with its existing
fallback. The worker's PostgreSQL accepted scope does not clip these Redis calls
to the inherited remaining deadline.

Both installed Redis drivers are **7.0.0**. The actual request client's connect
and read socket settings are two seconds; its native Retry object reports
three retries. The application reconnect helper separately permits two attempts
and sleeps after failures. This proof does not derive a combined worst-case
ceiling or exercise the error/retry sequence. The queue-safe client has a
different blocking policy and was not used as the event/lock client.

## Controlled TCP response proof

Each isolated process redirected only its request-client endpoint to its owned
loopback peer and restored that process's endpoint/client afterward. No
production method was patched. The peer answered library handshake commands,
then held the target response. The borrower entered the actual accepted
PostgreSQL scope used by the worker, with a frozen work or terminal remainder.
The controller observed it still live at 0.5 seconds, then released the response.

| Surface / phase | Host return after release | Worker return after release |
| --- | --- | --- |
| Progress XADD / work | 0.5105 s | 0.5005 s |
| Terminal XADD / terminal | 0.5022 s | 0.5003 s |
| Owner release EVAL / terminal | 0.5010 s | 0.5046 s |
| Cancellation SISMEMBER / work | 0.5098 s | 0.5002 s |

All **eight cases** remained blocked beyond the 0.25-second parent remainder
and returned after its frozen deadline. Publication returned ok=true, lock
release true and cancellation false, according to the peer's responses.
These are real library/helper waits with controlled RESP responses: they are
not an actual Redis outage, an application completion, or proof that a real
application lock was removed. They prove that the accepted child wait and its
return are not governed by that parent deadline. All owned borrower/peer threads
joined; pooled sockets closed and peer EOF was confirmed before process exit.

## Actual Redis controls and custody

An isolated worker exec process separately used retained actual Redis. Accepted
work, accepted terminal and legacy publication each succeeded with matching
stream readback and a false cancellation observation, in 0.0001–0.0004 seconds.
Canonical envelope lock acquisition rejected a foreign release, preserved the
lock, then allowed its exact owner/token release; the sequence took 0.0026 seconds.
Only uniquely named owned streams and an absent-before-acquisition random
integer-thread lock were used. Exact cleanup was independently verified with
redis-cli EXISTS; no owned key remains.

The first healthy control assumed byte-keyed fields, but the actual request
client returns decoded string fields. Readback and cleanup raised KeyError,
leaving one owned stream. Its exact key was recovered only after one-entry
readback proved the embedded owned tag matched the key; removal was verified.
The corrected field-normalizing control then passed. Failed harness source,
error note and exact recovery receipt are retained; this was a fixture failure,
not a production source repair.

All **1,135 tracked Guardian/backend Python files** matched the evaluated
checkout, mounted source and both retained containers. The six causal modules
also matched independently in host and worker probe results. Both PostgreSQL
drivers remain 3.3.6. Retained project codexify_chat_branch_proof_896387ad2
remained healthy and idle, chat queue empty, turn locks absent and heartbeat TTL
positive. Evaluation/system queues stayed 28/8.

Fresh SQL/API readback retained thread 31's exact messages 58/59 and single
attempt. Its durable receipt remains task.completed with
durable_completion_recorded, and raw Redis retains exactly one completion,
without another terminal. Requested/attempted/resolved/final provider and model
remain local/local-chat. This is preservation of the preceding browser proof;
no fresh browser turn was submitted in this characterization.

## Validation, follow-through and next obligation

Private host probe.py, worker docker exec Python probe, corrected
healthy-controls.py, source verification, readback and independent
validate.py assertions passed. All probe exec processes reached terminal exit
zero. py_compile checked the private runners; git diff --check passed.
No new automated repository runtime suite applies to this documentation-only
characterization.

Evidence:
 /private/tmp/codexify-chat-redis-envelope-gap-53a2b1cfa-20261003/
contains the bounded Task Spec, exact probes/results, failed control/recovery,
installed driver sources/policy, source matrices, health/state, independent
SQL/API/receipt/event readbacks and validated results. Fresh roots preserved
previous artifacts. Credentials were not printed or committed.

ADR impact: alignment with ADR-087; no new decision or current-state promotion.
Documentation follow-through is this receipt; no memory update is authorized.
Next authorized implementation obligation: inherit the same frozen remaining
work/terminal budget across accepted Redis admission, connection, response waits,
native/application retries and cleanup; preserve owner checks, visibility
results and unrelated request/queue policy. An operation unable to enforce the
bound must fail closed. Its repair and healthy/error controls require a separate
atomic Task Spec, followed by fresh complete-path browser evidence.

The Goal remains active. Redis/outbox/context bounds, exhausted durable terminal
reserves, remote commit ambiguity and active-worker drain/loss recovery remain
unfinished. This evidence does not qualify those surfaces, graceful drain, the
newer mainline integration or complete supported-Compose release readiness.
