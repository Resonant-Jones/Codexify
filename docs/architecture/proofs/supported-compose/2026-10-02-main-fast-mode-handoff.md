# Current-main explicit fast-mode cancellation handoff

Date: 2026-10-02. Baseline: `0755503ec85390d57b5204aa554fabd334738ec9`.
Branch: `main`. Authority: active ordinary-chat reliability Goal and Development
Operator Level 0. Architecture-impact, proof before repair; aligned with existing
ADR-001/002/003/038 and chat-runtime identity, terminal, and observation contracts.
No new ADR or release claim.

## Causal proof

The explicit Fast action stored a pending retry intent. The global cancellation
handler called `releaseTurnLease` before inspecting that intent; lease release
unconditionally erased it. The independent inference hook cleared terminal task
identity without notifying the component, so task-stream-only cancellation also
could not resume the selected action.

Initial regression: **nine failed, 107 passed**. Seven component cases reproduced
missing fast handoff or its backoff; two hook cases demonstrated the missing
correlated cancellation callback. Completion/failure-wins, foreign cancellation,
stop-rejection, and newer-turn controls remained green.

The final component tests also use the actual inference hook with a controlled
EventTarget transport and controlled API promises. With only the final test file
overlaid on an independent archive of the baseline production source, both
actual-hook cases failed: the fast task never attached. The stop POST was
verified before cancellation was injected. Sixty-three other cases were skipped
by the focused test-name filter; they were not new green baseline evidence.

## Repair

Bind the existing user-requested intent to both task ID and thread ID, retaining
its provider/model snapshot. An owned cancellation observed through either the
global feed or existing task stream confirms the intent and schedules one
handoff. The hook relays task/thread identity before clearing it. Foreign and
retired stream events retain their existing ownership rejection.

Lease cleanup preserves only a confirmed handoff. Duplicate observations
coalesce; acceptance of the stop POST alone cannot schedule completion. An old
stop failure cannot erase an intent whose task cancellation is already known.
Completion or failure clears the intent without retry. Legacy global
cancellation lacking task identity cannot authorize this handoff.

The scheduled handoff checks object ownership, reacquires the local turn lease,
and uses the existing completion endpoint with `reasoning_mode=no_think` and
the selected provider/model. No authored message is inserted again. A newer
request, later explicit Stop/provider change, or unmount invalidates scheduled
work. The existing bounded 429 backoff remains: a rejected admission can retry
within its existing limit without claiming that an attempt was accepted.
Failed admission retains the existing failure projection and lease cleanup.

No backend, queue, persistence, request-identity generation, canonical runtime
token, provider resolution, transport, or automatic replay policy changed.
The API interceptor still creates a per-request turn ID; the completion route
and queue retain request/task identity authority. This task does not qualify
backend attempt identity or durable readback through a live runtime.

## Validation

An exact baseline archive received only the four declared source/test overlays.
The existing task-owned dependency view supplied installed frontend libraries.
Caches and reports remained external. Final source/test byte equality was
verified against the working tree.

From repository root:

```sh
pnpm --dir /private/tmp/codexify-main-fast-handoff-0755503ec-20261002/frontend/src exec vitest run \
  --config vitest.config.ts --no-cache --maxWorkers=1 \
  features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx \
  features/chat/__tests__/useInferenceRequestState.test.tsx \
  features/chat/__tests__/useChat.test.ts \
  components/persona/layout/__tests__/GuardianChatWithSidebar.terminal-projection.test.tsx \
  test/api.completion-turn-lock.test.ts \
  features/chat/__tests__/GuardianChat.lifecycle-timing.test.tsx \
  features/chat/__tests__/GuardianChat.lifecycle-latency.test.tsx \
  --reporter=json \
  --outputFile=/private/tmp/codexify-main-fast-handoff-0755503ec-20261002/after-clean.json

git diff --check
```

Final result: **150 passed in seven files**, exit 0. Component: 65; hook: 58;
useChat: 10; sidebar projection: 6; API turn-lock: 1; lifecycle timing: 6;
lifecycle latency: 4. Diff check passed. Scoped ESLint remains unavailable in
the unchanged dependency view because `eslint-plugin-react` is missing.

Intermediate expanded runs exposed harness timing errors: a real-hook test
clicked Fast before task identity rendered, and two older tests injected
terminal events before waiting for task acceptance, allowing their pending
admission timers to leak into later tests. Strengthen these waits rather than
weakening terminal or duplicate-request assertions. The initial attribution of
one integration failure to production cleanup timing was not established; the
final independent baseline comparison uses corrected acceptance waits.

Artifacts: `/private/tmp/codexify-main-fast-handoff-0755503ec-20261002`, including
`before.json/log`, `after-narrow.json/log`, intermediate `after`, `after-final`,
`after-verified`, `isolated` reports, final `after-clean.json/log`, and independent
`before-integration.json/log` with its baseline archive.

## Closeout and limits

Files changed: GuardianChat, inference hook, their two regression suites, and
this receipt. Documentation follow-through: scoped receipt only; no current-state
or ADR updates. No push, merge, deployment, or service restart.

Evidence class: controlled HTTP/event and jsdom component/hook proof. Two cases
exercise the actual hook inside GuardianChat, while transport, API, chat store,
and child rendering are controlled. This is not real provider termination,
PostgreSQL persistence, live browser rendering, or supported-Compose recovery.
Persistent 429 exhaustion and backend identity/readback require further proof.

The supported-path re-evaluation still requires fresh current-tip runtime
success and important failure/recovery evidence. Immutable accepted queue-age,
blocking child-call bounds, and safe worker shutdown/drain remain unqualified on
this branch. Delayed admission responses and callbacks also need ownership proof
across request replacement and component unmount. Current-state remains HOLD;
the full Goal stays active and incomplete.

KB recommendation: capture authoritative cancellation identity before clearing
observation, retain an explicit retry intent through terminal cleanup, and keep
request acceptance, task cancellation, and subsequent attempt admission distinct.
