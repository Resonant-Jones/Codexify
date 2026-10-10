# Independent bounded chat worker heartbeat

Date: 2026-10-04; this atomic slice began on 2026-10-03.
Evaluated base: 2c243390347cb521b82d8be1445cd9a1bd3df39c plus the scoped repair.
Classification: AUTHORIZED_IMPLEMENTATION; architecture-impact, repair and bounded proof.
Priority: P1. Owner: Codex. Full supported qualification remains HOLD.

## Atomic Task Spec and authority

Keep the chat worker heartbeat fresh while the dispatcher owns inline work or
waits during pre-dispatch observation, dequeue or the existing executor drain.
This change belongs in guardian/workers/chat_worker.py. The explicit ordinary-chat
reliability Goal, Development Operator Level 0 protocol, current-state gate,
Chat Runtime Contract, Completion Pipeline and ADR-001/002/003/038/069/087
authorize the bounded repair. Campaign Engine does not prove ownership of this
local runtime-maintenance proof lifecycle.

The allowlist is the worker, chat_redis_deadline.py, redis_queue.py, existing
heartbeat-activity and Redis-deadline test files, this receipt and private
evidence/owned probe resources. No request/attempt/envelope, queue acceptance,
provider, persistence, canonical token, heartbeat payload/TTL/classifier or
stale-lock recovery policy changed. No new ADR or migration is required.
Main, publication, release claims and memory are outside this Task.

The prior [native characterization](./2026-10-03-chat-inline-heartbeat-gap.md)
proved that a held inline lifecycle kept the runner alive while the heartbeat
became stale at 12 seconds and disappeared by 47 seconds.

## Repair and ownership

The worker keeps its existing count of entire owned lifecycles. Queued executor
work, running work and terminal cleanup remain active until the same worker
lifecycle returns or raises. Ownership changes wake one managed heartbeat
publisher; periodic publication has a five-second wait. The initial idle sample
precedes ownership. The dispatch loop and pre-dispatch task scope no longer
publish competing samples.

The reporter stays alive through the native executor's existing context-manager
drain. After that context exits, the stop/wake events are set and the reporter
joins. Inline cancellation retains priority over occupied completion slots and
still uses the same authoritative lifecycle. Dispatch and submission errors
retain their existing propagation and ownership cleanup.

Each heartbeat publication now owns a physical Redis operation scope using the
existing REDIS_OPERATION_TIMEOUT_SECONDS policy, two seconds on this retained
profile. It reuses the qualified native DNS/socket/RESP/retry transport bounds
and closes its private pool before returning. A maintenance scope rejects
replacing an inherited budget; it creates no AcceptedChatTaskDeadline. Expiry
uses Redis TimeoutError, while accepted-task expiry retains its canonical
deadline error and immutable work/terminal envelope. The operation has no
additional terminal reserve; switching phase cannot extend its end.

The publisher remains best effort when Redis is unavailable. Its finite wait
cannot abandon a helper thread or leave an owned DNS child running. Timestamped
heartbeat samples indicate process liveness and owned activity at publication;
they do not establish task-specific progress or grant new recovery authority.

## Validation and actual transport

The repo-root targeted host suite passed 79 tests with zero failures, errors
or skips in 5.866 seconds. The same 79 cases passed under the actual worker
Python 3.11.14 and Redis 7.0.0 in 9.379 seconds. Coverage includes held terminal
cleanup, success/failure, queued and overlapping executor lifecycles, inline
cancellation priority, dispatch/submission errors, repeated publication during
four held seams, accepted-deadline/cancellation/dequeue regressions, and physical
Redis waits.

With real owned TCP peers and a 0.25-second operation ceiling, native worker
SETEX response withholding returned in 0.251 seconds and closed before peer
release. Stopping the dispatcher while the reporter held the second SETEX
joined the reporter in 0.253 seconds, with both peer connections independently
observed closed. A held native DNS child returned in 0.252 seconds and was
killed/reaped with pipes closed. Retry/backoff consumed one ceiling; saved clients
could not escape or borrow another scope; maintenance could not replace an
accepted budget or extend itself through the terminal switch. These are
controlled physical transport proofs, not provider-backed cancellation proofs.

Initial host runs exposed errors in the new test fixtures: an incorrect deadline
accessor, then reuse of the first connection's EOF signal. Correcting them made
the complete suite pass. The initial container run stopped during collection
because the copied rescue test lacked its existing streaming-harness helper;
adding that exact helper made all 79 cases pass. Original logs/XML remain in the
evidence root. No production failure is hidden by these corrected fixtures.

py_compile passed for all five changed Python files. Focused Ruff passes for the
core helper and both tests. Full queue/worker Ruff still fails with the exact
baseline findings: one unused Optional import and two duplicate dictionary keys
(model_selection and retrieval_provenance). Logical-path baseline comparisons
confirm zero new findings; those unrelated lines were preserved. The initial
temporary-path lint comparison omitted per-file rules; the corrected
stdin-filename comparison and both diagnostics are retained.

## Native real-time inline proof

An owned worker-container subprocess used actual run_forever, task parsing,
pre-dispatch observation, native Redis publication and the real health
classifier. Only the fixture dequeue/cancellation/body and initialization seam
were replaced. One inert inline body waited on an owned Event with a 60-second
safety limit. Its 720/780-second envelope shape was a fixture, not application
acceptance or a durable attempt.

The process used a previously absent tagged private heartbeat key. The canonical
application key was not redirected. No fake clock, socket or publisher was used.
Actual defaults remained TTL 45, fresh threshold 10, dead threshold 60,
publication interval 5 and operation budget 2 seconds.

| Real elapsed held inline work | Status / TTL | Classifier / age | Runner / body |
| --- | --- | --- | --- |
| 0.000 s | active / 45 s | fresh / 1.019 s | alive / unfinished |
| 12.002 s | active / 43 s | fresh / 2.021 s | alive / unfinished |
| 47.001 s | active / 43 s | fresh / 2.020 s | alive / unfinished |

Observations were 15:16:53.019490, 15:17:05.020834 and 15:17:40.019952 UTC.
After release, the publisher reported fresh idle. Exactly one inline lifecycle
and two fixture dequeues occurred. Runner, reporter and native executor context
joined before exit 0. The private key was deleted once and independently absent.

## Retained runtime and custody

With chat queue empty, locks absent and idle heartbeat TTL positive, exactly
the three scoped runtime files were copied into the retained source snapshot.
Backend and worker restarted once. All 1,136 tracked Guardian/backend Python
files matched checkout, snapshot and both containers afterwards and again at
closeout. Actual drivers remain Python 3.11.14, Redis 7.0.0 and psycopg 3.3.6;
migration is d4c69e03a712. The branch worker source SHA-256 is
73d647807c85678363ac5591751dd1db32722ffce8320b7df0e4e686d890ecdb.

Final health is ok, canonical heartbeat fresh idle with positive TTL, chat queue
zero and locks absent. Evaluation queue stayed 30; system queue advanced from
10 to 11 because of the backend's startup warmup and was preserved. Independent
SQL/API readback retains thread 33 messages 62/63, its completed_message_id 63,
and matching task.completed durable receipt. No application record was removed.

Fourteen copied files were verified against their final manifest, including the
added existing test helper and corrected runner. Results were exported before
the exact tagged container folder and its owned generated files/links were
removed. Independent readback confirms the folder and private key are absent.
Every test/probe/refresh handle is terminal. Earlier evidence roots were not
overwritten.

Evidence: /private/tmp/codexify-chat-independent-heartbeat-2c2433903-20261003/
contains the full Task Spec, original/final tests and XML, source/lint matrices,
restart and driver records, native real-time observations/results, process
results, SQL/API readback, independent verifier and cleanup receipts.
Documentation follow-through is this receipt; contracts/current-state remain
unchanged. git diff --check and docs validation pass.

The next Task is fresh ordinary browser completion/reload against the repaired
runtime. Current-main integration, accepted outbox/context blocking bounds,
terminal reserve exhaustion/acknowledgement ambiguity and active-worker
drain/loss recovery remain unfinished. This repair does not close those gates.
The Goal remains active.
