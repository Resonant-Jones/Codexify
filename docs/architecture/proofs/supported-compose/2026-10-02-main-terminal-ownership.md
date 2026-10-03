# Current-main global terminal ownership proof

Date: 2026-10-02. Baseline: `1d1fe36a8a82070f9b2a54be18967865343b1d8e`.
Branch: main. Architecture-impact task under the active ordinary-chat Goal and
Development Operator Level 0. Governing contracts: ADR-001/002/003/038 and
chat-runtime identity/observation boundaries. No new ADR, state, token, or replay.

## Reproduction

A rendered GuardianChat with controlled hook/API/live-event seams processed
explicit task terminals without comparing task/thread ownership. The initial
foreign-thread, stale same-thread task, and contradictory-thread/current-task
matrix produced **12 failed, 9 passed**. Completed, failed/error, and cancelled
events changed the unrelated active inference phase.

An expanded matrix exercised a completion tracker still naming a prior task
while a newer inference was active on the same or another thread. All eight
such cases also failed. Four completion-owned/inactive-inference controls passed.
Expanded baseline: **20 failed, 13 passed**. This proves handler behavior for
controlled divergent store states; it does not prove their frequency in a live
browser. Source acceptance updates completion and inference separately, and
neither store's prior identity may authorize changing a newer active attempt.

## Repair

Before session updates, finalization, lease release, retry clearing, or inference
mutation, an explicit event must match task AND thread in the current completion
or inference. When inference is active, its identity takes precedence: an event
that matches only a prior completion tracker returns without mutation.

Matching terminals retain normal behavior. A matching completion tracker can
still terminalize when inference is inactive. Existing duplicate idempotence,
backend-error unwinding, provider-switch behavior, and the weaker legacy
same-thread path without a task ID remain covered and unchanged.

## Validation and environment

External source root:
`/private/tmp/codexify-main-terminal-ownership-1d1fe36a8-20261002/frontend`.
Tracked frontend was exported from frozen HEAD; the selected regression and
repaired component were copied explicitly. Both tested files matched host bytes:

- GuardianChat SHA-256: `9d057571f3f76212711ba8acaf0e914312683352469b145d01c193b27097b9d5`.
- Regression SHA-256: `2e2484feabcda27b42b93554628f81235a60fc8f3c04ab6f79031f197982942f`.

Installed dependencies were reused through external package links: Vitest 3.2.7,
React/ReactDOM 19.2.0. No install or shared runtime restart occurred. External
node_modules directories own Vite temporary files; caching was disabled. This is
an installed dependency view, not frozen-lockfile installation proof.

From that source root's `src` directory:

```sh
pnpm exec vitest run --config vitest.config.ts --no-cache --maxWorkers=1 \
  features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx \
  features/chat/__tests__/useChat.test.ts \
  features/chat/__tests__/useInferenceRequestState.test.tsx \
  components/persona/layout/__tests__/GuardianChatWithSidebar.terminal-projection.test.tsx \
  test/api.completion-turn-lock.test.ts \
  features/chat/__tests__/GuardianChat.lifecycle-timing.test.tsx \
  features/chat/__tests__/GuardianChat.lifecycle-latency.test.tsx
```

Result: **7 files, 65 passed**, exit 0. Includes all 33 regression/control cases.
`git diff --check`: passed. Existing synthetic/React test logging remains visible.

Setup limitations: the initially reused nested pnpm binary view could not resolve
Vitest; Vite's experimental runner loader rejected this config's `__dirname`.
An external package-link view and normal bundled config resolved test setup.
The initial `useChatMessages` validation shorthand was corrected to the existing
`useChat.test.ts` suite before validation.

Optional scoped ESLint was attempted and exited 2 before analysis because
`eslint-plugin-react` was absent in both available dependency directories. It is
unavailable, not green. No dependency installation or unrelated lint repair was
performed.

Artifacts in the external root's parent: `before.json`, `before.log`,
`before-expanded.json`, `before-expanded.log`, `after.json`, `after.log`.

## Closeout limits

Files: component, regression suite, this receipt. ADR impact: aligned, no change.
Documentation follow-through: this receipt only; release truth remains HOLD.
Evidence: mocked/jsdom component and hook tests, not live browser/API/PostgreSQL,
provider, restart, or complete supported-Compose proof. The no-task-ID legacy
path retains its weaker correlation. Per-task callback ownership still needs its
own proof; immutable child deadlines and full current-tip qualification remain
unfinished. The full ordinary-chat Goal remains active.

KB recommendation: terminal identity must be checked before any UI mutation;
a prior completion tracker cannot authorize changing a newer active inference.
