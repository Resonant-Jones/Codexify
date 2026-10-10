# Chat assistant-message event refresh and browser projection proof

Date: 2026-10-03. Evaluated commit: `896387ad2999d2aaffbfeae83a492b6fb4235653`
plus the active Goal branch's uncommitted frontend change. Authority: ordinary-chat
reliability Goal and Development Operator Level 0. Classification: `PROOF_REQUIRED`;
no queue, acceptance, identity, provider-selection, or retry semantics changed.
Current-main integration and complete supported-Compose qualification remain open.

## Atomic Task Spec

When the live event stream reports a persisted assistant message, pass its thread
identity to the chat surface and refresh the canonical snapshot only when that
thread is active. Preserve authored-message, request, task, turn, and assistant
message identities. Prove the sidebar event bridge, chat refresh behavior, and
one ordinary browser turn against independently read event and Postgres state.

Governing sources: ADR-001 (acceptance differs from completion), ADR-003
(message and request identity remain distinct), ADR-038 (transport visibility is
not execution truth), ADR-091 (durable attempt binding), and the Chat Runtime
Contract. The update introduces no state token or alternate persistence path.

## Validation

The sidebar regression emits an assistant `message.created` event for thread 7
through the parent's registered subscription and asserts that the active
`GuardianChat` receives `{threadId: 7, sequence: 1}`. The chat lifecycle test
asserts that this signal calls `refreshSnapshot(1, "assistant-message-created")`.
The related frontend run passed 24 tests across:

- `components/persona/layout/__tests__/GuardianChatWithSidebar.terminal-projection.test.tsx`
- `features/chat/__tests__/GuardianChat.lifecycle-timing.test.tsx`
- `features/chat/__tests__/useChat.test.ts`

## Isolated browser turn and durable readback

The isolated Compose project `codexify_chat_branch_proof_896387ad2` supplied the
backend, worker, Redis, and Postgres. A new Vite server was started from the
active checkout at `127.0.0.1:15176`, with its proxy pointed to that isolated
backend. Direct module responses contained the changed
`assistantMessageRefresh` and `assistant-message-created` code markers; the
other running Vite server did not contain them. The browser submitted:

`Reply with exactly: ACTIVE_BRANCH_TERMINAL_REFRESH_896387AD2_20261003`

The browser rendered the user prompt and exact assistant response in thread 9.
After reload, both messages were still visible. Postgres and the Redis task
stream independently agreed:

| Evidence | Result |
| --- | --- |
| User / assistant messages | Thread `9`; user message `17`; assistant message `18`; exactly two transcript rows for the probe |
| Request / task / turn | `req_24ac6a3fb5604bca903031d8689e6962` / `48153894-f899-4160-a7ae-023b124ec48c` / `58484751-5b63-46b9-a72c-9c9f5978e9a4` |
| Redis terminal | `task.completed`; `message_id=18`; `latest_turn_message_id=17`; final provider/model `local` / `local-chat` |
| Durable attempt | Same request, task, thread, and turn; `completed_message_id=18`; linked assistant metadata agrees on provider/model |
| Browser reload | The same user prompt and assistant response rendered; no duplicate turn was created |

The automated event-bridge regression establishes delivery of the assistant
thread signal, while the browser and durable readback establish the resulting
transcript projection. The browser observation was made after terminal
completion; it does not measure the exact interval between `message.created`
and `task.completed`.

## Evidence limits

This is a branch-local source-overlay proof on a retained isolated stack. The
frontend was served directly from the checkout rather than built into the
Compose frontend image. It does not establish current-main integration, clean
volume/image qualification, unavailable-model or failure projection, active
worker-loss recovery, restart durability, or graceful shutdown. The full
supported-Compose qualification remains `HOLD`.
