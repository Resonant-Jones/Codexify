# Ordinary browser chat after PostgreSQL query bounds

Date: 2026-10-03. Evaluated source: `1e66f88427dd5ed6866be7e94ac7a112f3564945`.
Classification: `PROOF_REQUIRED`; architecture-impact, P1; owner: Codex.
This ordinary completion passed. Full supported qualification remains `HOLD`.

## Atomic Task Spec and authority

Prove ordinary browser chat after the accepted-task PostgreSQL query repair.
Verify the retained isolated Compose project is idle, refresh exactly the three
changed backend files, restart only its backend and idle chat worker, and verify
source bytes in both containers. Serve the evaluated frontend, submit one real
local-model turn, and compare the visible result before/after reload with SQL,
message API, durable task receipts, and raw task events. Preserve application
data and other queues. Remove only owned temporary browser/frontend setup.

Authority: the explicit ordinary-chat reliability Goal, Codex Development
Operator Goal, Chat Runtime Contract, ADR-087, Runtime Protocol Token Contract,
and current-state release gate. This is direct operator proof work; Campaign
Engine was not used. No new architecture, recovery policy, or token was selected.

Repository allowlist: this receipt only. Commit subject:
`docs(proof): record browser chat after PostgreSQL query bounds`.
No main merge, push, deployment, or current-state promotion is part of this task.
Acceptance requires one durable linked assistant, matching request/task/turn
identities, real local-model execution without fallback, a truthful completion,
reload persistence, and an idle worker without a retained turn lock afterward.

## Runtime and source custody

Project: `codexify_chat_branch_proof_896387ad2`; backend `127.0.0.1:18889`,
PostgreSQL `127.0.0.1:55433`, temporary frontend `localhost:5181`.
The task-owned mounted source is
`/private/tmp/codexify-chat-branch-proof-896387ad2-20261003/source`.
The preflight chat queue was empty, there were no turn locks, and the worker
heartbeat was idle with a positive TTL. Only these stale files were copied:

- `guardian/core/chat_postgres_deadline.py`
- `guardian/core/pgdb.py`
- `guardian/workers/chat_worker.py`

Only this project's backend and chat worker were restarted from that idle state.
All **1,135 tracked Guardian/backend Python files** matched byte-for-byte between
the evaluated checkout, mounted source, backend, and worker. Both containers use
**psycopg 3.3.6**. The preceding query-contention regression used host driver
3.2.10; this ordinary success does not establish deadline-failure compatibility
on the container driver. Independent SQL read back migration head `d4c69e03a712`.

Health reported `ok`, supported profile `v1-local-core-web-mcp` valid with no
mismatches, selected provider `local`, and cloud-capable configuration absent.
Those health reports identify posture; the turn below supplies execution proof.

The new worktree contained LFS pointer manifests. Eight needed files were
temporarily hydrated from the existing checkout only after matching their exact
pointer SHA-256, and two dependency-directory symlinks reused existing installs.
No dependency install occurred. Other unavailable LFS assets were not hydrated;
this is core chat proof, not full asset or production-build qualification.

## Observed turn and durable agreement

The real browser submitted once:
`Reply with exactly CHAT_POSTGRES_QUERY_SUCCESS_20261003 and no other text.`
The real provider returned exactly `CHAT_POSTGRES_QUERY_SUCCESS_20261003`.
The visible assistant remained after a full browser reload.

| Binding | Observed value |
| --- | --- |
| Thread | `28` |
| Authored message | `52` |
| Assistant message | `53` |
| Request | `req_d5321f7672d1469a92b68fb56c7f8d6d` |
| Backend task | `aa989fda-60a1-42f4-96f0-ce0d469da1f4` |
| Turn | `bc1cdda4-1633-43b9-a502-acc847e776a6` |
| Attempt event identity | `attempt_926e5c4b5f1c4b559f3faac74cbb5634` |

Independent SQL found one attempt linked to assistant `53`, with no failure or
cancellation terminal type, and exactly the authored/assistant pair in this
thread. The message API returned the same two IDs, roles, and contents.
The durable task receipt reported `task.completed`,
`reason=durable_completion_recorded`, and the same request/task/thread/turn/link.
Raw Redis held exactly one completion terminal and no failure/cancellation
terminal for this task. Its `persistence_outcome=persisted` and completion truth
reported accepted, attempted, executed, and completed true; fallback attempted
false. Requested, attempted, resolved, and final provider/model were consistently
`local` / `local-chat`, with explicit selection and no fallback. The inventory's
display name was Gemma 4 12B IT QAT 4-bit; the logical model identity was
`local-chat`. No tools were advertised/dispatched for this ordinary answer.

The recorded duration was 62,537 ms. SQL assistant `created_at` was
`20:37:32.943902Z`; the raw `task.state=COMPLETED` stream entry was
`1791059852974-0`, and the richer `task.completed` entry was
`1791059861784-0`. Both carry assistant `53`; the latter retains the lifecycle
`completed_at=20:37:32.974596Z`. Source inspection confirms the state callback
follows atomic assistant persistence returning, with metadata work before the
later rich event/log. The later persistence log alone is not evidence of an
earlier false-success state. Remote commit ambiguity was not injected or proved.

Retrieval ran with no injected candidates; graph was disabled. This does not
qualify nonempty retrieval, graph behavior, tool execution, or their failures.

## Validation, cleanup, and remaining gates

`proof.py preflight`, `refresh`, `verify`, `readback 28 progress/success/reload`,
and `validate.py` passed their final assertions. The latter independently checked
message/attempt/event/receipt agreement, exact model identity, reload transcript,
migration, source matrix, health, and final idle state. Its initial accessibility
assertion used a diff-only saved snapshot; saving the full snapshot corrected the
evidence collection, and the final assertion passed. No new automated runtime
test suite applies to this documentation-only task; `git diff --check` passed.

Final chat queue: zero; turn locks: none; worker: idle, heartbeat TTL 41 seconds.
Evaluation/system queues changed from 24/4 to 25/5 and were preserved. Application
data, stored messages, and other containers remain available. The owned browser
tab was closed, Vite was interrupted and its port verified closed, the eight
manifests were restored to exact HEAD pointer bytes, and only the two owned
symlinks were unlinked. Existing Browserslist age and SettingsPanelDock duplicate
style warnings were observed without expanding this proof into frontend repair.

Evidence root:
`/private/tmp/codexify-chat-postgres-runtime-1e66f8842-20261003/`.
It contains the runner, source/hash matrix, health/runtime snapshots, SQL/API
readbacks, raw Redis stream IDs, assertion receipt, screenshots before/after
reload, full reload accessibility text, and scoped cleanup receipt. Existing
credentials stayed in private runner environment and were not printed/committed.

This receipt is the documentation follow-through; ADR impact is alignment with
accepted contracts. No release claim or memory update occurred. Original checkout
`7d94` remains clean on `main`, equal to fetched `origin/main` at `c5c14da8d`;
the audit's 13 local commits remain on its backup branch and its checkout detached.

Ordinary successful integration at this evaluated source is now fresh. Database
DNS/connect and pool admission bounds, actual container-driver contention,
exhausted durable terminal reserves, Redis/outbox publication bounds, remote
commit ambiguity, non-database context work, and shutdown/worker-loss recovery
remain separate proof/repair obligations. Restarting an idle worker here does
not qualify active-worker restart or drain. The Goal remains active.
