# Chat heartbeat activity mismatch: publisher and consumer trace

Date: 2026-10-03. Evaluated repair branch: 6665b2b11.
Classification: PROOF_REQUIRED; proof lane; architecture-impact assessment.
Owner: Codex. Full supported qualification remains HOLD.

## Atomic Task Spec and authority

Trace the canonical chat heartbeat publisher, consumers and governing meanings,
then exercise the actual dispatcher with one held inert executor lifecycle.
Compare activity labels at identical timestamps through the actual health and
acceptance freshness functions. Read retained runtime health, source custody and
the preceding successful browser turn. Restore only owned proof setup.

This change belongs in this receipt. Authority is the explicit ordinary-chat
reliability Goal, Codex Development Operator Goal, AGENTS current-truth hierarchy,
Chat Runtime Contract and accepted ADR-087. The allowlist is this receipt plus
private evidence/scripts and owned copied test setup. No production edit, model
invocation, application queue/lock/message mutation, restart, source refresh,
main change, push, merge, recovery disposition or release promotion is included.

## Verified source and runtime

The repair checkout was clean at 6665b2b11; the independent main checkout remains
on e992d8e2b. All 1,136 tracked Guardian/backend Python files matched the checkout,
retained source snapshot, backend and worker containers.

Retained project codexify_chat_branch_proof_896387ad2 reported health ok and
/health/chat healthy. Chat queue was empty, no turn locks existed, and the idle
heartbeat had positive TTL. Evaluation/system queues stayed 29/9. SQL messages
60 and 61 and the terminal durable receipt for thread 32 remained intact, with
the exact CHAT_REDIS_DEADLINE_SUCCESS_20261003 assistant reply. This was readback
of the preceding turn, not a new model invocation.

## Publisher cause

guardian/workers/chat_worker.py publishes starting during initialization.
_chat_task_cancelled_before_dispatch publishes active before observing accepted
task cancellation. run_forever then submits ordinary work to a native
ThreadPoolExecutor and immediately returns to its queue loop. Each loop
unconditionally publishes idle before the five-second dequeue wait; executor
work does not participate in that status selection.

The controlled probe used the actual dispatcher, task parser, pre-dispatch
helper and native executor. It intercepted heartbeat writes, replaced dequeue
with one inert payload, and held only the worker lifecycle with owned Events.
It observed idle, active, then idle while the executor had entered but had not
finished. Exactly one lifecycle ran. Releasing the owned Event allowed the
executor context to join before the probe returned. No live Redis heartbeat or
application task was written by this controlled probe.

This explains the independent browser observation in
[the preceding receipt](./2026-10-03-chat-redis-browser-integration.md): an idle
heartbeat timestamp fell after task.running and AWAITING_MODEL but before the
same task's COMPLETED state. The controlled probe is causal code/runtime
characterization; the browser observation supplies supported-profile evidence.

## Consumer and authority boundaries

guardian/routes/health.py::_resolve_chat_worker_heartbeat derives fresh, stale
or dead from timestamp presence and age. It does not read the payload's
idle/active/starting label. /health/chat reports that freshness together with
Redis and queue-probe results; its worker status is a liveness classification,
not an idle/busy or completion assertion.

guardian/core/chat_completion_service.py::_chat_worker_heartbeat_evidence also
uses presence and timestamp age, through the same classifier. The stale-lock
recovery contract in completion_pipeline.md permits recovery only after the
lock is stale and terminal task evidence or stale/dead/missing worker evidence
satisfies its existing gate; unknown evidence blocks recovery. Raw idle is not
recovery authority.

Both functions produced identical evidence for idle, active and starting at
each controlled age: 1 second fresh, 11 seconds stale and 61 seconds dead.
That equivalence passed on both host and worker-container source. Frontend
runtime health uses the health API; its Command Center Heartbeat panel reads
the separate reporting-artifact API, not this Redis activity label.

The bounded repair obligation is to make the existing activity label follow
work owned by this worker process, including executor and inline terminal work,
while preserving timestamp classification, identity, payload shape and recovery
policy. A truthful active label does not establish task-scoped worker-loss,
orphan timing, completion, retry or new lock-release authority. Those decisions
remain separate. Inline-path heartbeat freshness and shutdown behavior were
not characterized by this held-executor probe.

## Validation, cleanup and limits

The private controlled suite passed 3 host and 3 worker-container checks, with
zero failures, errors or skips. XML, full logs and actual observations were
independently inspected. These checks cover dispatcher causality and classifier
invariance; they are not provider-backed completion or failure/recovery proof.
The existing browser/durable-readback evidence remains separate.

The first artifact parser rejected pytest's progress-dot-prefixed PROOF lines.
No cleanup had begun and no production test failed. Parsing those prefixes was
corrected; the successful independent XML/observation validation and initial
parser-error record were retained.

Six copied container files were hash-checked before removing the owned suite
root and its verified /app links. The runner was terminal before removal; XML
had already been exported. Final runtime state retained empty chat queue, no
locks, positive heartbeat TTL and unchanged evaluation/system queues. No
previous proof artifacts were overwritten. git diff --check passed. No new
repository runtime test suite applies to the documentation-only receipt.

Evidence: /private/tmp/codexify-chat-heartbeat-trace-6665b2b11-20261003/
contains the complete Task Spec, source matrices/search, controlled suite,
host/worker logs and XML, live health/readback, parser record, validation and
cleanup receipts. ADR impact is alignment only. Documentation follow-through
is this receipt; no current-state promotion or memory update occurred.

The Goal remains active. Aggregate activity reporting, remaining accepted-child
deadline bounds, terminal reserve exhaustion/acknowledgement ambiguity,
active-worker drain/loss recovery and newer-main integration remain unfinished.
