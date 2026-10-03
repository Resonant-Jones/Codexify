# New-thread first-message route-promotion proof

Date: 2026-10-03. Repair commit: `888b19223fdb69b4646d153f5850a3b95e74c248`.
Authority: ordinary-chat reliability Goal and Development Operator Level 0.
Classification: bounded frontend coherence repair; no acceptance, queue, message,
request, task, turn, provider, or persistence identity semantics changed.
Current-main integration and complete supported-Compose qualification remain open.

## Finding and repair

The draft send path promoted a newly created thread into the active route before
posting its first authored message. Route activation could therefore fetch an
empty transcript while the original send continuation later refreshed a
different `useChat` instance. The durable user row existed, but the visible
transcript remained empty until a later refresh or reload.

For the first ordinary send, thread creation now records pending promotion
metadata. GuardianChat posts the authored user message first, then promotes the
thread to its visible route and sidebar. A failed configuration sync or message
post still promotes the created thread so the user can inspect or retry it. The
chat hook also joins an in-flight activation for the same thread instead of
aborting and replacing an empty first snapshot.

Governing sources: ADR-001 (acceptance differs from completion), ADR-003
(message and request identity remain distinct), ADR-038 (transport visibility
is not execution truth), ADR-087 (accepted task deadlines), and the Chat Runtime
Contract. The repair does not add a state token or alternate persistence path.

## Validation

- Focused Vitest: `useChat.test.ts` and `GuardianChat.test.tsx`; 33 tests passed.
- The GuardianChat regression verifies `onThreadPersisted` runs after the
  authored-message POST.
- Targeted ESLint completed with zero errors and 141 existing warnings across
  the four changed source/test files.
- `git diff --check` passed.
- TypeScript validation was unavailable because `tsc` is not installed in this
  workspace.

## Retained-stack browser and durable readback

The frontend was served from the repair checkout by a fresh Vite server, with
API traffic proxied to the retained chat proof stack. On thread `20`, the
browser submitted `Reply with exactly: durable row now visible.` The visible
route showed the authored prompt before the assistant reply. The assistant
reply then appeared without a reload.

The browser console trace recorded the author POST returning before deferred
thread promotion. An authenticated read of `/api/chat/20/messages` returned
HTTP 200 with exactly two rows: user message `37` and assistant message `38`,
both on thread `20`, with matching content. This verifies the first-message
projection and resulting transcript readback on the retained stack.

## Evidence limits

The backend and worker came from retained Compose source snapshots; only the
frontend was served directly from this repair checkout. This is branch-local
frontend/runtime evidence, not current-main integration or a clean full
supported-Compose qualification. It does not resolve active worker-loss
recovery, restart recovery, graceful shutdown, or the separate worker-result
projection gate. The supported-path qualification remains `HOLD`.
