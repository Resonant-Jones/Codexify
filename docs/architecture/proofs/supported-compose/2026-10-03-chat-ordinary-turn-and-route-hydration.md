# Ordinary chat turn and explicit-route hydration proof

Date: 2026-10-03. Evaluated code: active Goal branch commit `e62109e39`.
Classification: `PROOF_REQUIRED` for the bounded supported-path runtime check;
the route projection repair is `AUTHORIZED_IMPLEMENTATION` under the ordinary
chat reliability Goal. Supported-Compose qualification remains `HOLD`.

## Atomic Task Spec

Prove one ordinary supported browser chat turn through durable assistant
completion and reload, then close the observed first-render gap for direct
`/chat/:id` navigation. During session-spine hydration, an explicit URL thread
must remain the selected thread and its history must enter a loading state
before paint rather than briefly presenting an empty/new-chat surface.

The implementation changes only route selection and transcript activation
timing. It adds no lifecycle token or authority and does not change request,
task, turn, message, queue, provider/model, cancellation, or retry semantics.

## Runtime conditions and source identity

The retained supported-profile project was
`codexify_chat_branch_proof_896387ad2`, with API at `127.0.0.1:18889` and a
Vite frontend serving this checkout. The backend health endpoint returned
HTTP 200; the profile was `v1-local-core-web-mcp`, release hold was false, and
the selected provider was local. The model health projection reported
`local` / `local-chat` online. PostgreSQL reported Alembic head
`d4c69e03a712`.

Before the browser turn, the chat queue was empty, there were no
`turn_lock:*` keys, and `worker-chat` was running with a fresh heartbeat. The
mounted copies of these five changed backend runtime files matched the
worktree byte-for-byte: `guardian/core/db.py`, `guardian/core/pgdb.py`,
`guardian/db/models.py`, `guardian/routes/chat.py`, and
`guardian/workers/chat_worker.py`. This comparison is limited to those files;
it does not establish whole-directory or whole-image identity.

## Ordinary browser turn

The browser submitted the unique prompt `Reply with exactly this marker:
BRANCH_CHAT_E2E_OK_20261003` in thread `21`.

| Evidence | Result |
| --- | --- |
| Authored / assistant messages | `39` / `40` |
| Request / task / turn | `req_f88d8c4a97ef468b95dc7a33ce80caf9` / `242ecd23-f918-4eb2-a95f-f8cab0dbc61d` / `20ce8abd-fb78-433e-8f23-e94b1e023a6f` |
| Task receipt | `task.completed`, `completed_message_id=40`, reason `durable_completion_recorded` |
| Redis terminal event | `task.completed` bound to the same request, task, thread, turn, and assistant message |
| Provider/model | `local` / `local-chat`; `fallback_triggered=false` |
| Durable transcript | Authored row `39` and assistant row `40` read back; assistant metadata matched the request, turn, provider, and model |
| Browser | Prompt and exact marker reply rendered; after reload the same transcript was visible |

## Explicit-route hydration repair

The first-render inspection showed `/chat/21` could render an empty chat while
session hydration had not yet selected the explicit URL thread. The shell now
initializes selection from the explicit route and the chat begins activating
that selected thread in a layout effect, so the history-loading state is
rendered before the browser paints. The focused regression holds session
hydration unresolved and verifies that the route's transcript is already
selected.

Validation after the repair:

- `pnpm exec vitest run --config vitest.config.ts components/persona/layout/__tests__/GuardianChatWithSidebar.terminal-projection.test.tsx` from `frontend/src`: 8 passed.
- Focused frontend regression group and lint had passed earlier in this task; lint reported existing warnings and no errors.
- Live reload on the Vite-served checkout showed `Loading Guardian chat` while history loaded, followed by the persisted prompt and assistant reply. The temporary backend-connection notice cleared after the API responded.
- `git diff --check` passed before commit. Repair commit: `e62109e39ad184e0a82a38719f1da27155b0cade`.

## Limits and remaining gate

This is one successful ordinary branch-local turn plus direct-route hydration
evidence. It does not establish the full supported-Compose gate, current-main
integration, unavailable explicit-model behavior, cancellation/retry,
worker restart or graceful shutdown, or active worker-loss recovery. A
controlled worker-loss proof found that destructive dequeue can leave an
accepted attempt without terminal evidence and block explicit retry. The
policy choice remains at the authority frontier: wait for the accepted task
deadline before terminal reconciliation, or add task-scoped worker ownership
and confirmed-loss orphaning. Automatic replay remains disabled pending that
decision. Release readiness remains `HOLD`.
