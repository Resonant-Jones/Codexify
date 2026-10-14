# Browser chat after independent heartbeat repair

Date: 2026-10-04. Evaluated source: 1d2543a6cf164a0d4dbf56581a3d3e805de66dca.
Classification: PROOF_REQUIRED; proof lane with architecture-impact assessment.
Owner: Codex. Priority: P1. Full supported qualification remains HOLD.

## Atomic Task Spec and authority

Verify one ordinary browser turn and reload after the
[independent publisher repair](./2026-10-03-chat-independent-heartbeat.md).
This change belongs in this receipt. Authority is the explicit ordinary-chat
reliability Goal, Development Operator Level 0 protocol, AGENTS current-truth
hierarchy, Chat Runtime Contract, Completion Pipeline and ADR-001/002/003/038/069/087.

Allowlist: this receipt, private evidence, eight exactly checked temporary
frontend manifest hydrations, two owned dependency links, one Vite process,
one owned browser tab and one read-only sampler. No package installation,
runtime refresh/restart, cancellation/retry, application record deletion, main
change, publication, deployment, new ADR or release promotion occurred.

## Frozen runtime and frontend

The repair checkout was clean at 1d2543a6c. All 1,136 tracked Guardian/backend
Python files matched checkout, retained source snapshot, backend and worker.
The actual health response identifies v1-local-core-web-mcp version 1, local
Docker Compose WebUI, valid configuration and no mismatches. Local provider,
local-only mode and disabled cloud providers were read from the retained
backend environment. Migration remains d4c69e03a712 and both containers use
psycopg 3.3.6. Initial chat queue was empty, locks absent, heartbeat idle with
positive TTL, evaluation queue 30 and system queue 11.

Eight tracked JSON manifests were hydrated only after all original-checkout
bytes matched this HEAD's LFS pointer OID and size. Two previously absent
node_modules links used the original checkout's corresponding installed
dependency directories. A new Vite process served this repair checkout on
127.0.0.1:5181 with the retained backend proxy. No source refresh was allowed.

## One browser turn and durable identity

Owned IAB tab 8 submitted exactly once:

Reply with exactly CHAT_INDEPENDENT_HEARTBEAT_SUCCESS_20261004 and no other text.

The authored prompt rendered during execution. The exact assistant marker
appeared after completion, and reload returned the same prompt/reply pair.
Before/after accessibility snapshots and PNGs are saved. The final screenshot
was independently inspected from disk.

| Binding | Observed value |
| --- | --- |
| Thread | 34 |
| Authored / assistant message | 64 / 65 |
| Request | req_d5e542fc803943129d5e53ebd9e5821a |
| Backend task | 4b5b6242-d51a-4bb2-b5ca-551545cf8de7 |
| Turn | 9dab370f-885c-490d-873a-6e6ebe828929 |
| Accepted at | 15:35:00.007406 UTC |
| task.running | 15:35:00.116053 UTC |
| task.completed | 15:36:33.881152 UTC |
| Reported duration | 93,795 ms |

SQL attempts, canonical SQL/API messages, durable receipts, raw task events
and assistant metadata agree on those identities and one assistant.
completed_message_id is 65. The receipt is terminal task.completed with
reason durable_completion_recorded. The one raw terminal event records
persisted, accepted/attempted/executed/completed true and fallback_attempted
false. Requested, attempted, resolved and final provider/model are local /
local-chat, with explicit selection. This verifies the canonical logical
model identity; it does not independently measure physical model execution.

The immediate reload observation showed loading history and a backend-connection
checking banner, then recovered automatically into the transcript. No retry,
reset or second submission was performed. The intermediate observation and
successful final state are retained.

## Heartbeat evidence and sampling limits

The sampler collected 63 real-clock aggregates through acceptance, execution
and terminal/lock cleanup. Its reads are separate: authored-message SQL,
attempt SQL, Redis state and events. observed_at is the aggregate's completion
time, not the exact heartbeat GET time.

The first aggregate completed at 15:35:00.183433 UTC, shortly after the later
task.running timestamp, but contained zero attempts and zero task events.
Its idle heartbeat was published at 15:34:56 UTC, before the accepted task.
This aggregate spans the handoff and cannot be assigned a task-running phase
from its final timestamp alone. It is preserved as unbound evidence.

The next 61 aggregates bound to the exact task while its running interval was
open and all read active heartbeats. The final aggregate at 15:36:35.010193 UTC
read idle, observed task.completed and found the lock absent. Every aggregate
read positive TTL and a heartbeat timestamp within the ten-second freshness
window. No new idle publication during running was observed. These are
timestamped liveness/activity samples, not instantaneous task-specific progress
or new recovery authority. One-second heartbeat timestamps cannot establish
subsecond publication ordering.

The first validator assumed every aggregate already had an attempt and failed
on that initial unbound read. The corrected validator preserves and checks the
unbound aggregate separately, then correlates activity only where the accepted
task identity was actually observed. Original validator/error and all raw
samples remain. It does not silently discard an idle observation or claim every
aggregate was active. An earlier readback taken while the task was still
nonterminal was retained under inflight filenames before separate complete and
reload readbacks were created.

## Validation, cleanup and limits

The independent verifier passed exact prompt/reply, one-attempt/two-message
SQL/API/receipt/event agreement, no fallback, canonical provider/model,
before/after reload UI, all source hashes, profile/migration, timestamped
heartbeat evidence and cleanup. The repair's separate 79 host and 79 native
worker checks are recorded in its receipt; no new repository automated runtime
suite applies to this docs-only browser proof.

Only owned tab 8 was closed, with independent inventory absence. The sampler
returned exit 0. Known Vite handle 73653 received Ctrl-C and returned actual
exit 1; the port was independently closed. Eight exact HEAD pointer byte
sequences were restored and two verified owned links removed. The checkout was
clean before this receipt. Existing Browserslist-age and SettingsPanelDock
duplicate-style warnings were retained without unrelated edits.

Final application health is ok and chat health healthy. Chat queue is empty,
locks absent and canonical heartbeat fresh idle with positive TTL.
Evaluation queue advanced 30 to 31 after the successful assistant; system
queue remained 11. Both queues and all application records were preserved.
Independent final readback also preserves thread 33 messages 62/63 and its
durable completion receipt.

Evidence: /private/tmp/codexify-chat-independent-heartbeat-browser-1d2543a6c-20261004/
contains the full Task Spec, source/profile/migration/health records, exact
frontend setup and cleanup, UI snapshots/PNGs, inflight/complete/reload durable
readbacks, raw events, real heartbeat aggregates, original/final validators,
process records and validated results. Documentation follow-through is this
receipt only. docs validation and git diff --check pass.

This is one successful branch-local supported-profile browser turn after the
heartbeat repair. It does not close current-main integration, accepted
outbox/context blocking bounds, terminal reserve/acknowledgement ambiguity,
active-worker drain/loss recovery, or full failure/restart qualification.
The Goal remains active.
