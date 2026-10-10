# Current-main inference stream ownership proof

Date: 2026-10-02. Baseline: `7abaf09027f5335ae9dd57b5a3bf2a1028176690`.
Branch: main. Architecture-impact task under the ordinary-chat Goal and
Development Operator Level 0. Governing: ADR-002/003/038 and chat-runtime request
identity/transport-observation invariants. No new ADR or runtime token.

## Reproduction and repair

The current-stream terminal callbacks had no payload identity checks. Closed
connections retained callbacks capable of changing a replacement request,
resurrecting completed inference, or applying a degraded transport observation.
Malformed terminal JSON also invented completion. An injected terminal during
close caused re-entrant stream closure.

The frozen baseline hook proof produced **28 failed, 15 passed** across 43 cases.
Failures covered contradictory task/thread identity, retired connections with
explicit or omitted identity, transport errors, the same task ID on a replacement
connection, late progress/state after completion, malformed terminal data, and
re-entrant close. These are controlled EventTarget/React hook tests, not evidence
of real transport frequency or live browser delivery.

The repair uses the current stream object, attached task ID, and thread context
as an ownership fence. All progress, lifecycle, terminal, and error callbacks
check it. Object payloads also reject contradictory normalized task/thread IDs;
arrays and malformed/non-object terminal JSON cannot invent completion.

The current task-scoped connection may still accept a valid object with omitted
identity, using its existing connection context. A retired connection cannot use
that omission or a reused task ID to gain ownership. Before calling close(), the
hook clears its owned references, so a callback dispatched while closing cannot
re-enter as a current owner. No new connection, replay, request, provider,
persistence, or observation-state semantics were introduced.

## Validation

External source root:
`/private/tmp/codexify-main-stream-ownership-7abaf0902-20261002/frontend`.
Tracked frontend was exported from the frozen baseline; only the selected hook
and regression were overlaid. Tested bytes matched the repository:

- Hook SHA-256: `22d9f577afc06bbdb2ba095ff3dcd1bfff87e60942b051e59adc6bab433a10b3`.
- Test SHA-256: `5f494bac9290ce3d9468c92d2457fa19e96be42346891edd787b91d24ba4a0a6`.

The owned external dependency view from the preceding terminal-ownership task
was reused: Vitest 3.2.7 and React/ReactDOM 19.2.0. No installation or shared
runtime restart. This does not prove a frozen dependency installation.

From that root's `src` directory:

```sh
pnpm exec vitest run --config vitest.config.ts --no-cache --maxWorkers=1 \
  features/chat/__tests__/useInferenceRequestState.test.tsx \
  features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx \
  features/chat/__tests__/useChat.test.ts \
  components/persona/layout/__tests__/GuardianChatWithSidebar.terminal-projection.test.tsx \
  test/api.completion-turn-lock.test.ts \
  features/chat/__tests__/GuardianChat.lifecycle-timing.test.tsx \
  features/chat/__tests__/GuardianChat.lifecycle-latency.test.tsx
```

Result: **7 files, 103 passed**, exit 0, including all 43 hook regression/control
cases. Valid progress, model-wait, terminal controls, and degraded-observation
behavior remain covered. `git diff --check`: passed. Synthetic/React test logging
is retained. Scoped ESLint remains unavailable in this installed dependency view
because eslint-plugin-react is absent, as established in the preceding task;
no lint pass is claimed.

Artifacts in the external source root's parent: `before.json`, `before.log`,
`after.json`, `after.log`.

## Closeout and re-evaluation

Files: hook, regression suite, this receipt. ADR impact: aligned, no new decision.
Documentation follow-through: this receipt only; current-state HOLD unchanged.
Proof class: mocked/jsdom hook and component evidence. Live task-event delivery,
API/PostgreSQL/provider truth, retrieval scope, finite child/database work, and
restart recovery remain unqualified on the full current tip.

Re-evaluating cancellation found another separate proof candidate: requestCancel
marks inference failed when the cancel HTTP request throws, although that HTTP
failure alone does not establish the backend task's outcome. Stale asynchronous
cancel responses and their component caller also need ownership examination.
No cancellation-HTTP behavior was changed in this task.

The full Goal remains active. No source publication, release readiness, or full
supported-path reliability is claimed.

KB recommendation: callback ownership requires connection identity as well as
attempt identity; revoke ownership before closing the transport.
