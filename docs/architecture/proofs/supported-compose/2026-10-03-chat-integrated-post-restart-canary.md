# Integrated ordinary chat after backend and worker restart

Date: 2026-10-03. Classification: `PROOF_REQUIRED`. Evaluated integration
commit: `e1ec21942033534d89d4860c95784f3be5b5af05`. Complete supported-Compose
qualification remains `HOLD`.

## Atomic Task Spec

On the retained `codexify_chat_branch_proof_896387ad2` runtime, prove an
ordinary browser chat after refreshing the four integrated Python repairs and
restarting only the backend and idle chat worker. Require matching event,
durable attempt, receipt, transcript, and reload evidence, then verify chat
queue/lock cleanup. Preserve unrelated services and queue contents. Record a
proof receipt; do not change application semantics or publish the branch.

## Preconditions and evaluated runtime

Before mutation, the chat queue held zero tasks, `turn_lock:*` was empty, and
the chat worker heartbeat was idle with a positive 41-second TTL. Backend
health was `ok`; `v1-local-core-web-mcp` was valid, selected provider was local,
and cloud-capable configuration was absent. Postgres, Redis, and Neo4j were
running and healthy. Eval/system queue depths were 20/1.

The task-owned snapshot at
`/private/tmp/codexify-chat-branch-proof-896387ad2-20261003/source` received only
the current `guardian/core/accepted_deadline_transport.py`,
`guardian/core/ai_router.py`, `guardian/core/chat_completion_service.py`, and
`guardian/workers/chat_worker.py`. `docker restart` restarted only
`codexify_chat_branch_proof_896387ad2-worker-chat-1` and
`codexify_chat_branch_proof_896387ad2-backend-1`. Database/Redis were not
restarted or cleared. Backend startup initially reset the health connection;
the subsequent health response was `ok` with the same valid local-only profile.

After the canary, hashes read inside **each** restarted container matched all
1,134 checked tracked Python files under `guardian` and `backend` against the
integration checkout. This is Python-source identity evidence, not
whole-image/dependency/configuration identity. Hydrated snapshot JSON resources
and image dependencies were retained; no full-image rebuild is claimed.

The frontend was Vite serving this checkout at `http://localhost:5181`, proxying
to `http://127.0.0.1:18889`. The fresh browser initially lacked credentials;
the proof reused the isolated backend's existing development key in the Vite
process environment. It did not create or expand a credential. This canary
does not qualify account-session login, onboarding, or account authority.

## Observed ordinary turn

The browser sent `Reply with exactly this marker:
INTEGRATED_CHAT_AFTER_RESTART_20261003` once on a new thread.

| Surface | Independent evidence |
| --- | --- |
| Thread / authored / assistant | `24` / `44` / `45` |
| Request | `req_4de3fcd36f654210aaa0ab38f7a9c6d9` |
| Task | `0f174ec9-afa7-4d59-b885-fcb52875564d` |
| Turn | `9e9a9ab8-99d0-4455-8516-8d5dac44a830` |
| Redis events | Exactly one terminal event, `task.completed`, with assistant ID `45` |
| Postgres attempt | Same request/task/thread/turn, completed-message binding `45` |
| Durable receipt | `terminal`, `task.completed`, `durable_completion_recorded`, message `45` |
| Transcript API | One authored row and one assistant row; exact marker content |
| Provider/model | Event and assistant metadata both `local` / `local-chat`; no fallback |
| Completion truth | Accepted, attempted, executed, completed true; fallback attempted false |
| Browser / reload | Exact marker reply rendered and remained after reload; no second send |
| Queue / lock / worker | Chat queue zero, no turn locks, fresh idle heartbeat with 44-second TTL |

Reload briefly showed history loading and the backend-connection checking
notice. The notice cleared and the durable transcript rendered. The final
screenshot retains that settled state.

Evidence root: `/private/tmp/codexify-chat-integrated-20261003/`.
`health-before.json`, `health-after.json`, `runtime-source.json`,
`canary-events.json`, `messages.json`, `receipts.json`,
`runtime-readback.json`, `runtime-final.json`, and `browser-reload.jpg`
retain the scoped observations. Readback assertions passed for the single
terminal event, exact assistant content, matching durable/event identities,
provider/model coherence, and completed truth. Source/cleanup assertions passed.

## Whole-path re-evaluation and limits

This adds fresh integrated-source ordinary browser completion and settled
reload evidence after backend/chat-worker restart. It does not prove the
Compose start wrapper, database/Redis/full-stack restart, active-worker crash
recovery, graceful shutdown during generation, actual deadline expiry against
Whoosh'd, tool/non-streaming runtime behavior, or the full supported bundle.

Final eval/system queue depths were 21/2. The canary used ordinary existing
completion behavior; no proof command cleared or consumed either queue.
Their depth changes are observations, not proof that unrelated work completed.

The intermittent cancellation regression failure recorded in the integration
receipt remains unlocalized. Partial-output execution-field meaning and
active-worker-loss reconciliation remain unresolved audit/authority items.
Context/retrieval, tool/cloud children, PostgreSQL, terminal operations,
cleanup, and finite-drain deadline obligations remain unfinished.

No application source changed in this task, no ADR changed, and no release
claim was promoted. Documentation follow-through is this receipt. The temporary
Vite process/browser tab were closed after evidence capture; retained proof
containers remain running. No push, GitHub merge, deployment, or memory update
occurred.
