# Ordinary browser completion after the Redis deadline repair

Date: 2026-10-03. Evaluated source: 05def824a.
Classification: PROOF_REQUIRED; architecture-impact, P1; owner Codex.
Fresh completion/reload passed; full supported qualification remains HOLD.

## Atomic Task Spec and authority

Serve the current frontend, submit exactly one ordinary local-model browser
turn, compare visible completion with SQL, message API, durable task receipt and
raw terminal event, then reload and confirm the same transcript. Capture
read-only active heartbeat/lock/attempt observations when available. Restore
only owned frontend/browser/Vite setup. Allowlist: this receipt only, plus
temporary exact manifest hydration/dependency links restored before staging.
Commit subject: docs(proof): record browser chat after Redis deadline repair.

Authority: explicit ordinary-chat reliability Goal, Codex Development Operator
Goal, Chat Runtime Contract, ADR-087 and current-state qualification gate.
Direct bounded proof; no new architecture, recovery disposition, runtime
refresh/restart, main merge, push, deployment or release promotion.

## Source and runtime custody

Retained project codexify_chat_branch_proof_896387ad2, backend 127.0.0.1:18889,
PostgreSQL 127.0.0.1:55433 and temporary frontend localhost:5181.
Preflight found empty chat queue, no turn locks, positive idle heartbeat TTL,
health ok and valid v1-local-core-web-mcp, local-only/cloud-disabled posture.
SQL independently read migration d4c69e03a712.

All **1,136 tracked Guardian/backend Python files** matched checkout, mounted
snapshot, backend and worker. PostgreSQL drivers remain 3.3.6. The
[Redis repair receipt](./2026-10-03-chat-redis-deadline.md) separately records
122 host checks, 29 worker-container checks and four strengthened visibility
checks per runtime. The preceding repair refreshed exactly three runtime files
and restarted idle backend/worker once; this proof did not restart them again.

Eight frontend LFS manifests were hydrated only after exact pointer OID/size
matched existing checkout bytes. Two owned symlinks reused installed
dependencies; no installation occurred. This evaluates ordinary chat, not a
production build or full installation. Initial connection-delayed UI recovered
automatically before submission; no retry/reset action was taken.

This is the isolated repair branch and retained runtime, not newer-main
integration or public-ingress qualification. Main remains a separate checkout.

## Completion and reload agreement

Submitted once:
Reply with exactly CHAT_REDIS_DEADLINE_SUCCESS_20261003 and no other text.

The fresh thread visibly showed the authored prompt and exactly
CHAT_REDIS_DEADLINE_SUCCESS_20261003. A full reload briefly showed history
loading, then the same authored/assistant pair without resubmission or another
user action. Full accessibility snapshots and before/after screenshots were
saved; the final screenshot was independently inspected.

| Binding | Observed value |
| --- | --- |
| Thread | 32 |
| Authored message | 60 |
| Assistant message | 61 |
| Request | req_6105e622dbab4eca96e6a2c6e9b36377 |
| Backend task | f52eb525-a78f-468a-9204-1415c6b0a0f8 |
| Turn | a779d68a-c4f6-4f16-9841-a17dd1d8ef84 |

SQL found one attempt linked to assistant 61, with no failure/cancellation
terminal type, and exactly two messages. API IDs, roles and content matched.
The durable receipt was terminal task.completed, reason
durable_completion_recorded, with identical identities. Raw Redis contained
exactly one completion terminal and no failure/cancellation terminal.
Persistence outcome was persisted; accepted/attempted/executed/completed were
true and fallback attempted false. Assistant metadata agreed with identities
and final provider/model. Independent readback after reload retained the same
bindings and outcomes.

Requested, attempted, resolved and final values were local/local-chat, explicit
selection with no fallback. The frontend displayed Whoosh'd and Gemma 4 12B IT
QAT 4-bit. Worker-reported duration was **44,052 ms**. This proves one successful
ordinary empty-retrieval/no-tool integration turn, not a controlled performance
comparison or every failure/recovery case.

## Separate active heartbeat observation

At 23:40:42.048046 UTC, the attempt was accepted without a completed-message
binding, turn_lock:32 was present and heartbeat status was idle. The later raw
event snapshot independently records task.running at 23:40:30.052049,
AWAITING_MODEL at 23:40:39.955605, AWAITING_FIRST_TOKEN at 23:40:43.255920,
STREAMING at 23:41:04.846562 and COMPLETED at 23:41:08.266340. Thus the first
idle heartbeat observation falls inside this accepted task's running/model
lifecycle, before its completion.

A second snapshot at 23:41:13.516908 still found idle heartbeat and the turn
lock while the worker was completing terminal work. The snapshots preserve
actual heartbeat payloads, timestamps, owner lock, durable attempt and raw
events; they do not establish worker-loss recovery authority or a new
heartbeat meaning. The next bounded obligation is to trace the heartbeat's
publisher/consumers and governing semantics before correcting operator-visible
idle/busy projection. This observation does not invalidate the completed turn.

## Validation, cleanup and limits

Private preflight/verify/readback/state and independent validate.py passed:
unique identity, SQL/API/event/receipt agreement, explicit model/no fallback,
visible completion/reload, source/migration custody and exact setup cleanup.
No new automated repository runtime suite applies to this documentation-only
proof. git diff --check passed; prior repair suites remain separate evidence.

Final chat queue was empty, turn locks absent and heartbeat idle with positive
TTL. Resolver scans found no owned Redis/PostgreSQL DNS child in backend or
worker. Evaluation queue grew 28 to 29; system queue stayed 9. Queues were
preserved. The owned tab was closed; known Vite session stopped at terminal exit
130 and port closure was verified. Eight manifests were restored to exact HEAD
pointer bytes and only the two verified owned symlinks removed. The checkout
was clean before adding this receipt. Existing Browserslist-age and
SettingsPanelDock duplicate-style warnings remain outside this proof.

Evidence:
 /private/tmp/codexify-chat-redis-browser-05def824a-20261003/
contains fresh Task Spec/runner, source matrices, health/migration/state,
active heartbeat/lock/attempt/event observations, two durable readbacks,
validated results, screenshots/accessibility text and setup/cleanup receipts.
Previous proof roots were preserved. Credentials were not printed or committed.
Documentation follow-through is this receipt; ADR impact is alignment only,
with no current-state promotion or memory update.

The Goal remains active. Heartbeat interpretation, outbox/context bounds,
exhausted durable terminal reserves, remote acknowledgement ambiguity,
active-worker drain/loss recovery and newer-main integration remain unfinished.
Successful chat after an idle restart is not full restart/recovery or release
qualification.
