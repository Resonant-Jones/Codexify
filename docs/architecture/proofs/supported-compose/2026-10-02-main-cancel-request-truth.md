# Current-main cancellation request and observation truth

Date: 2026-10-02. Baseline: `d1b95e0f7706c093a2175f9b82d12edd96144f4b`.
Branch: `main`. Authority: active ordinary-chat reliability Goal and Development
Operator Level 0. Architecture-impact; proof before scoped repair. Governing
sources: current-state HOLD, ADR-001/002/003/038, and chat-runtime identity,
observation, terminal, and turn-lease contracts. No new ADR.

## Causal evidence

The cancellation endpoint returns `cancel_requested=true` after requesting
cancellation; that response is not the task's terminal outcome. The frontend
hook instead called `markFailed` on any rejected stop POST. This closed the
current stream, erased task identity, and invented provider/task failure. An
old POST rejection could similarly overwrite a completed/cancelled/failed task,
a replacement connection with the same task ID, a newer task, or reset state.

GuardianChat's Stop and provider-change handlers also called `releaseTurnLease`
with `clearInference=true` immediately after starting the POST. This discarded
observation and request-scoped state without waiting for either the POST or a
terminal event. Existing tests expected that premature reset and were replaced
with authoritative-terminal expectations.

Red proof: **23 failed, 77 passed** across the two changed suites. Fourteen
component cases reproduced premature reset; nine hook cases reproduced false
failure, stale rejection corruption, or overlapping stop-request corruption.
Three accepted-POST terminal controls passed on the baseline.

## Repair and preserved boundaries

A failed stop POST leaves task identity, phase, provider status, stream, and
turn lease intact. Its explanatory detail says the stop request could not be
confirmed and observation continues. It clears the pending-cancel indicator
without assigning task/provider failure or an authoritative terminal token.
Error text is not used because the existing presentation classifies it as
provider failure.

A local stop-request object, stream object, task ID, and thread ID fence error
projection. Closing/replacing observation invalidates request ownership before
closing the stream. An older stop failure cannot clear a newer pending request.
A successful POST retains observation until actual task terminal evidence.

Stop and provider changes no longer reset inference or release the lease early.
Provider selection still updates for future requests; the accepted attempt keeps
its original identity. Matching completion, cancellation, and failure continue
to release the lease through existing terminal handling. A second send while
waiting cannot start another completion.

The existing fast-mode caller additionally clears pending retry intent on a
failed POST only when that intent belongs to the same caller. This identity
check is source-path evidence; fast-mode retry execution is not qualified by
this task and remains a separate proof obligation.

No backend, queue, model resolution, accepted-request identity, persistence,
protocol token, automatic replay, or transport architecture changed.

## Validation

An external `git archive` of the exact baseline received only the four declared
source/test overlays. Byte equality with the working tree was verified. The
existing task-owned dependency view supplied installed frontend dependencies;
Vite caches and reports remained outside the repository.

From repository root:

```sh
pnpm --dir /private/tmp/codexify-main-cancel-truth-d1b95e0f7-20261002/frontend/src exec vitest run \
  --config vitest.config.ts --no-cache --maxWorkers=1 \
  features/chat/__tests__/useInferenceRequestState.test.tsx \
  features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx \
  features/chat/__tests__/useChat.test.ts \
  components/persona/layout/__tests__/GuardianChatWithSidebar.terminal-projection.test.tsx \
  test/api.completion-turn-lock.test.ts \
  features/chat/__tests__/GuardianChat.lifecycle-timing.test.tsx \
  features/chat/__tests__/GuardianChat.lifecycle-latency.test.tsx \
  --reporter=json \
  --outputFile=/private/tmp/codexify-main-cancel-truth-d1b95e0f7-20261002/after.json

git diff --check
```

Result: **127 passed in seven files**, exit 0. Hook: 55; component ownership: 45;
useChat: 10; sidebar terminal projection: 6; API turn-lock: 1; lifecycle timing:
6; lifecycle latency: 4. Diff check passed. Scoped ESLint remains unavailable:
the same installed dependency view lacks `eslint-plugin-react`; no new lint
success is claimed and dependency installation was outside this task.

Artifacts: `/private/tmp/codexify-main-cancel-truth-d1b95e0f7-20261002`, including
`before.json`, `before.log`, `after.json`, `after.log`, and the external frontend
copy. Local proof artifacts are not published records.

## Closeout and remaining qualification

Files changed: inference hook, GuardianChat, their two regression suites, and
this receipt. Documentation follow-through: scoped receipt only. No ADR,
current-state, or release-claim changes. No push, merge, deployment, or runtime
restart performed.

Evidence class: controlled HTTP promises, task event dispatch, rendered mocked
component, and jsdom hook tests. This does not prove real cancellation HTTP,
provider termination, PostgreSQL state, live browser rendering, or supported
Compose recovery on the current source tip. Earlier runtime receipts remain
bound to the source actually evaluated.

Path re-evaluation found a separate fast-mode candidate: `releaseTurnLease`
clears `pendingFastRetryRef` before the global cancellation handler checks it.
Its user-visible consequence requires a bounded reproduction before repair.
Fresh current-tip end-to-end success, important live failure/retry cases,
immutable accepted-task/child deadlines, and safe restart/drain qualification
remain outstanding. The Goal stays active and incomplete.

KB recommendation: a cancellation request result is not a task terminal result;
retain attempt observation and ownership until independently correlated terminal
evidence, and fence delayed HTTP errors to the request and stream that issued
those errors.
