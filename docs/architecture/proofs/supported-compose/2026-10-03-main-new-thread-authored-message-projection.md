# Current-main new-thread authored-message projection

Date: 2026-10-03. Evaluated `main` baseline: `c5c14da8dca1c161ccffe81374ad804cad98f264`.
Authority: active ordinary-chat reliability Goal and Development Operator Level 0.
This is a narrow UI-truth repair aligned with ADR-001, ADR-003, and the chat
runtime contract. It changes no acceptance, message, request, task, or replay
identity and adds no new runtime token.

## Task Spec

After a new thread's user message is durably posted, refresh that thread's
canonical message snapshot and render the authored message before requesting
completion. Keep queue acceptance distinct from assistant completion. Prove the
ordering with a regression test and a browser turn whose durable readback and
terminal state are independently checked.

## Causal proof and repair

The new-thread branch persisted the user message and incremented
`chatReloadVersion`, but that value is ignored by `ChatView` for message reload.
The existing-thread branch explicitly calls `refreshSnapshot` after persisting
the user message. A regression test failed on current `main` because the
new-thread path never called `refreshSnapshot`.

The new-thread path now awaits `refreshSnapshot(threadId, "user-send")` after
the successful user-message POST and before scheduling completion. The same
reload-version increment remains in place for completion-session ownership.

## Validation

The focused frontend run passed: 38 tests across
`GuardianChat.test.tsx`, `GuardianChat.lifecycle-timing.test.tsx`, and
`useChat.test.ts`. ESLint reported zero errors and 110 warnings across the two
changed TypeScript files. `git diff --check` passed.

The explicit-model regression selection also passed on refreshed current
`main`: 89 tests across the dedicated worker authority, provider-resolution,
completion-semantics, AI-router, and Whoosh'd catalog suites. The documented
test contradiction was not reproduced by these current source suites; this
does not replace the current-state Compose qualification gate.

## Retained-stack browser and durable readback

The isolated project `codexify_chat_proof_f091_20261002` was idle before the
probe: chat queue length `0`, chat worker heartbeat `idle`, no turn locks, and
no active PostgreSQL clients. Only its frontend `GuardianChat.tsx` source mount
was temporarily overlaid. Its SHA-256 matched the current worktree module
(`ed8d8ff60f1cf9dea1b0b841304b5db01a7f98d749251bcfa4eb70ce8be8e84a`). The
original mounted source was restored after the probe; the frontend container
then matched the original snapshot hash again.

Browser thread `25` submitted the exact-response prompt
`Reply with exactly: NEW_THREAD_PROJECTION_MAIN_C5C14DA8_20261003`. While the
task was awaiting its first token, the browser rendered the persisted user
message and a truthful waiting state. The assistant later appeared with the
exact requested response. Reload restored both messages without a second turn.

| Evidence | Result |
| --- | --- |
| Request / task / turn | `req_9964ff2cea8c4328a631cd2d5dba9fba` / `8d56c351-e6da-4743-9c64-eb37d7e385d2` / `2809f6fa-8036-46ef-a648-e27c94b6b548` |
| User / assistant message | `57` / `58`; attempt `completed_message_id=58` |
| Redis terminal event | `task.completed`; stream included queued, running, model-wait, first-token-wait, streaming, and terminal states |
| PostgreSQL transcript / attempts | one user message, one assistant message, one completion attempt |
| Turn lock | `turn_lock:25` absent after completion |
| Browser | authored message visible while waiting; exact assistant response visible after completion and reload |

## Evidence limits

This is a retained-stack current-module check. The frontend container used the
existing dependency volume and prior source snapshot, with only the current
`GuardianChat.tsx` module overlaid. It was not a clean image build or a fresh
full current-tip supported-Compose qualification, and it does not prove restart
recovery, failure injection, or every browser ordering. Shared private-preview
and Whoosh'd services were not restarted. The supported-Compose release
qualification remains `HOLD`.
