# Inline chat lifecycle can outlive its heartbeat

Date: 2026-10-03 local; observations are UTC on 2026-10-04.
Evaluated source: 544c8a22d.
Classification: PROOF_REQUIRED; proof lane, architecture-impact assessment, P1.
Owner: Codex. Full supported qualification remains HOLD.

## Atomic Task Spec and authority

Characterize heartbeat freshness while the existing dispatcher owns a held inline
chat lifecycle. Use actual run_forever, task parsing, pre-dispatch helper,
heartbeat publisher, native Redis transport, real time and health classifier in
one owned worker-container subprocess. Supply one inert fixture through a
replaced dequeue, make only that fixture cancellation-positive, and hold only
its lifecycle body. Inspect the actual TTL and age thresholds, then release and
join the runner. Remove only the random owned heartbeat key and verified probe
folder after result export.

This change belongs in this receipt. Authority: the explicit ordinary-chat
reliability Goal, Codex Development Operator protocol, current-state gate,
Chat Runtime/Completion Pipeline worker-liveness contracts and ADR-087.
Allowlist: this receipt plus private evidence/scripts and the owned probe
resources. No production code, app task/message/attempt/queue/cancellation/lock
mutation, provider invocation, restart, source refresh, main change, push, merge,
release promotion or new recovery disposition is included.

## Source and preconditions

The repair checkout was clean at 544c8a22d. All 1,136 tracked Guardian/backend
Python files matched checkout, retained snapshot, backend and worker containers.
The probe independently read worker SHA-256
b965e95921c5a20beb7e4032fa8f9bc05c270d9541e48e4a1027e4fb18eb2fde
and actual Redis driver 7.0.0.

Retained project codexify_chat_branch_proof_896387ad2 reported health ok.
Chat queue was empty, locks absent and the application heartbeat fresh idle with
positive TTL. Evaluation/system queues were 30/10. Migration remained d4c69e03a712.
The preceding browser proof still owns thread 33 messages 62/63 and its successful
receipt; that independent SQL/API readback was preserved.

## Controlled native observation

The owned subprocess used a previously absent random key under
codexify:proof:inline-heartbeat. It changed only its own in-process publisher key
and fixture boundaries; the retained application's canonical heartbeat was not
redirected or modified.

The fixture carried the existing 720/780-second accepted-envelope shape through
the actual parser/helper. It was not an app acceptance or durable attempt.
No accepted app-task result is inferred. The held inline body used one owned
Event with a 60-second safety wait; the observer used the real clock and native
Redis, without clock patching, a fake socket or a fake heartbeat publisher.

The existing defaults were independently verified: heartbeat TTL 45 seconds,
freshness threshold 10 seconds, dead threshold 60 seconds.

| Elapsed inside held inline work | Heartbeat / TTL | Actual classifier | Runner / body |
| --- | --- | --- | --- |
| 0.000 s | active / 45 s | fresh, age 0.977 s | alive / unfinished |
| 12.002 s | active / 33 s | stale, age 12.979 s | alive / unfinished |
| 47.002 s | absent / -2 | dead, reason missing | alive / unfinished |

Observations were at 00:41:30.976911, 00:41:42.978755 and 00:42:17.978021 UTC.
After release, the same dispatcher returned from its one inline lifecycle,
published fresh idle, then reached the controlled stop. Exactly one lifecycle and
two fixture dequeue calls occurred. The runner and its native executor context
joined before the subprocess returned exit 0.

## Cause and consumer boundary

run_forever refreshes the heartbeat at the top of the dequeue loop. Pre-dispatch
observation publishes active. Its cancellation/expired/malformed path then calls
run_owned_task inline; no further loop pulse occurs until that lifecycle returns.
The process-local activity count added in fbb9f249d retains accurate ownership,
but does not independently schedule freshness publication while the dispatcher
is inside inline work.

The health classifier therefore can report stale or missing/dead for this
still-live controlled runner. /health/chat and the shared acceptance stale-lock
probe use the same presence/age meaning, as separately traced in
[the publisher/consumer receipt](./2026-10-03-chat-heartbeat-activity-gap.md).
This probe did not change the public endpoint's canonical key, mutate an app
lock, or demonstrate an actual recovery/retry decision.

The finding is controlled native process/transport characterization, not a
provider-backed cancellation or complete supported failure/recovery proof.
It does not invalidate the preceding ordinary browser completion. It establishes
the publisher's inline coupling and expiry consequence while Redis is healthy.

## Validation, cleanup and next obligation

The native probe and independent artifact verifier passed: exact source/driver,
real elapsed observations, active stale then missing/dead while the runner/body
remained live, exact one lifecycle, fresh idle after release and terminal joined
runner. The exact tagged key was read back, deleted once and independently found
absent. Two copied files were hash-checked before removing the owned container
folder, after all results had been exported and the process was terminal.

Final application health remained ok, chat queue empty, locks absent and its
canonical heartbeat fresh idle with positive TTL. Evaluation/system queues stayed
30/10. Independent SQL/API readback preserved thread 33 messages 62/63 and its
task.completed receipt. No previous proof artifacts were overwritten.
git diff --check passed. No new repository automated runtime suite applies to
this documentation-only characterization.

Evidence: /private/tmp/codexify-chat-inline-heartbeat-gap-544c8a22d-20261003/
contains the complete Task Spec, source matrix, native probe/log/header, real
clock observations, process/result receipts, validators, exact key/folder cleanup
and retained runtime/health/migration/readback. Documentation follow-through is
this receipt; ADR impact is alignment only. No current-state or memory update.

The next already-implied repair is to decouple process-liveness publication from
inline lifecycle waits while preserving activity ownership, timestamp/TTL
classification, queue/cancellation semantics and recovery policy. Publication
must own bounded Redis I/O and clean shutdown; moving the same unbounded wait to
an unmanaged reporter would not complete that repair. Do not manufacture an
accepted task/deadline merely for worker maintenance.

The Goal remains active. That publisher repair, remaining accepted-child bounds,
terminal reserve exhaustion/acknowledgement ambiguity, active-worker drain/loss
recovery and newer-main integration remain unfinished.
