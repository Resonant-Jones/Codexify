# Ordinary browser completion with truthful worker activity samples

Date: 2026-10-03 local; runtime observations are in UTC on 2026-10-04.
Evaluated source: fbb9f249d. Classification: PROOF_REQUIRED.
Proof lane, architecture-impact assessment; P1; owner Codex.
Fresh completion/reload and active-to-idle observations passed.
Full supported qualification remains HOLD.

## Atomic Task Spec and authority

Serve the repaired frontend, submit exactly one inert ordinary local-model turn,
sample the same task's heartbeat/lock/attempt/events, compare visible completion
with SQL, message API, durable receipt and raw terminal event, and reload the
same transcript without resubmission. Restore only owned frontend/browser setup.

This change belongs in this receipt. Authority: the explicit chat reliability
Goal, Codex Development Operator protocol, Chat Runtime Contract, ADR-087 and
[the completed worker activity repair](./2026-10-03-chat-heartbeat-activity.md).
Allowlist: this receipt, private proof/evidence, eight temporary exact LFS
hydrations and two owned dependency links restored before staging. No install,
source refresh, runtime restart, main mutation, push, merge, new recovery meaning
or release promotion is included.

## Source and runtime custody

Retained project codexify_chat_branch_proof_896387ad2, backend 127.0.0.1:18889,
PostgreSQL 127.0.0.1:55433 and temporary frontend localhost:5181.
Preflight found empty chat queue, no turn locks, positive idle heartbeat TTL,
health ok and valid v1-local-core-web-mcp, local-only/cloud-disabled posture.
Migration remained d4c69e03a712.

All 1,136 tracked Guardian/backend Python files matched checkout, mounted
snapshot, backend and worker. PostgreSQL drivers remained 3.3.6. The preceding
repair separately records 64 host and 14 worker checks and one idle backend/
worker restart after refreshing only the worker file. This browser Task did not
refresh or restart the runtime again.

Eight frontend manifests were hydrated only after exact HEAD pointer OID/size
matched existing donor checkout bytes. Two owned symlinks reused installed
dependencies; no installation occurred. Initial connection-delayed UI recovered
automatically before submission; no retry/reset action was taken. This is one
ordinary integration proof, not a production build or full installation.

## Completion, identity and reload

Submitted once:
Reply with exactly CHAT_HEARTBEAT_ACTIVE_SUCCESS_20261003 and no other text.

The new thread visibly showed that authored prompt and exactly
CHAT_HEARTBEAT_ACTIVE_SUCCESS_20261003. Full reload briefly showed history
loading, then the same authored/assistant pair without resubmission or another
user action. Full accessibility snapshots and before/after screenshots were
saved; the final screenshot was independently inspected.

| Binding | Observed value |
| --- | --- |
| Thread | 33 |
| Authored message | 62 |
| Assistant message | 63 |
| Request | req_ff61ff2cddb74e6893fc536a60c70ade |
| Backend task | e7449f19-2843-4587-bce9-71a723b7a2a4 |
| Turn | 1a7b3ae6-dd5b-4d4e-9935-05f7ea06cf55 |

SQL found one attempt linked to assistant 63, no failure/cancellation terminal
type, and exactly two messages. API IDs, roles and content matched. The durable
receipt was terminal task.completed, reason durable_completion_recorded, with
the same identities. Raw Redis contained exactly one completion terminal and
no failure/cancellation terminal. Completion truth recorded accepted, attempted,
executed and completed true; fallback attempted false; persistence persisted.
Assistant metadata agreed on request, turn and final provider/model. Independent
readback after reload retained the same identities and outcomes.

Requested, attempted, resolved and final provider/model were local/local-chat,
with explicit selection and no fallback. The UI displayed Whoosh'd and Gemma 4
12B IT QAT 4-bit. Worker-reported duration was 27,024 ms. This is an ordinary
empty-retrieval/no-tool turn; duration is not a controlled performance comparison.

## Activity evidence and limits

The read-only sampler retained 20 observations tied to the one attempt, including
19 active heartbeat observations. task.running was recorded at
00:21:09.177850 UTC and task.completed at 00:21:36.186728 UTC. All 17 observations
inside that interval reported active, with positive heartbeat TTL; none reported
idle. The first and last active observations were at 00:21:09.849636 and
00:21:38.751352 UTC.

Two active observations occurred after task.completed before the next heartbeat
sample. The heartbeat retains its timestamped sampled meaning; it is not an
instantaneous task-completion assertion. The final idle publication timestamp
was later than task.completed, and its observation found no turn lock. This
proves the observed process activity trajectory for this turn, not task-scoped
worker-loss authority, per-task progress or every concurrency/failure case.
The narrow native-executor/concurrency tests remain separate repair evidence.

## Validation, cleanup and follow-through

Private preflight/source/health, two durable readbacks and independent validate.py
passed: unique identity, SQL/API/receipt/event agreement, explicit local model,
completion/reload, active observations inside the running lifecycle, later idle
with lock cleanup, migration/source custody and exact setup restoration.
No new repository automated runtime suite applies to this docs-only proof.
git diff --check passed. Earlier worker Ruff remains limited by the two
pre-existing F601 findings documented in the repair receipt.

Final chat queue was empty, locks absent and heartbeat idle with positive TTL.
Evaluation queue grew 29 to 30; system queue stayed 10. Queues were preserved.
No owned Redis/PostgreSQL DNS child remained in backend or worker.
Owned tab 7 was closed. Known Vite session was stopped by Ctrl-C; its wrapper
returned terminal exit 1 and port closure was independently verified. Eight
manifests were restored to exact HEAD pointers and only the two verified owned
links removed. The checkout was clean before adding this receipt.
Existing Browserslist-age and SettingsPanelDock duplicate-style warnings remain
outside this proof.

Evidence: /private/tmp/codexify-chat-heartbeat-browser-fbb9f249d-20261003/
contains Task Spec/runner, source matrices, health/migration/state, live activity
samples, two SQL/API/receipt/event readbacks, validation, screenshots/accessibility
and cleanup receipts. Earlier proof roots were preserved. Credentials were not
printed or committed. ADR impact is alignment only; documentation follow-through
is this receipt, with no current-state promotion or memory update.

The Goal remains active. Inline-path heartbeat freshness, remaining accepted-child
bounds, exhausted terminal reserves/remote acknowledgement ambiguity,
active-worker drain/loss recovery and newer-main integration remain unfinished.
This successful branch-local browser turn does not close full failure/recovery,
current-main, public-ingress or release qualification.
