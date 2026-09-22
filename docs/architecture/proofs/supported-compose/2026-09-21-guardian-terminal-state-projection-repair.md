# Guardian terminal task-state projection repair — 2026-09-21

## Result

**Bounded result: HOLD.** F4 **PERSISTS**.

The defect reproduced at the exact current tip, but the visible stale status is
owned by a frontend file outside this task's mutation allowlist. No runtime or
frontend source was changed. The next atomic task must explicitly authorize the
outer Guardian status projection before a repair can be implemented honestly.

## Environment

| Field | Evidence |
|---|---|
| Machine / time | `VaultNode.local`; 2026-09-21 21:55–21:57 UTC |
| Branch / base commit | `main`; `3590076c54739b5fd18be11e49ae0f1275d1e3c1` |
| Upstream / divergence | `origin/main`; ahead 2, behind 0 |
| Initial worktree | Clean |
| Supported topology | `docker-compose.yml` plus `docker-compose.whooshd-smoke.yml`; profile `v1-local-core-web-mcp` |
| Effective route | provider `local`; logical model `local-chat`; runtime Whoosh'd |

## Before repair

A real headed Chrome session submitted `Reply with exactly
F4_BEFORE_20260921_A.` through the local frontend.

| Evidence | Observation |
|---|---|
| Thread | `7` |
| User message | `36` |
| Task | `7423893c-efa1-4e87-83ae-d9cfa2cc7012` |
| Request | `req_847726667a214ce3a81fdf6cf0c1bbef` |
| Run | `fce9b825eeea4605a43c47ab4444822d` |
| Attempt | `attempt_5aa750c01be74a30a01af749fe843a3c` |
| Assistant message | `37`; durable content `F4_BEFORE_20260921_A` |
| Backend terminal evidence | Redis `task.state=COMPLETED` at `2026-09-21T21:56:51.426600+00:00`; Redis `task.completed` at `2026-09-21T21:56:51.758392+00:00`; durable outbox row 87 at `2026-09-21 21:56:51.759684+00` |
| Browser task stream | `GET /api/tasks/7423893c-efa1-4e87-83ae-d9cfa2cc7012/events` returned 200; direct authenticated readback contains the complete lifecycle through `task.completed` |
| Global event lane | `/api/events` delivered the correlated assistant `message.created`; the browser console did not record a global `task.completed` callback for this turn |
| Browser terminal state | Assistant output rendered and the composer was idle, but the outer accessible status remained `Queued` with description `The request is waiting to be processed.` |

The Playwright evidence was moved outside the repository to
`/private/tmp/codexify-f4-before-playwright-20260921/` so it does not widen the
Git artifact scope.

## Root cause

Classification: **C — one lifecycle owner reached terminal truth while another
projection continued to report queued state.**

The task-specific stream and existing lifecycle hooks are not the owner of the
stale outer label:

- `useTaskEvents` owns the task-specific SSE parser/transport used by `useChat`.
- `useChat` owns the correlated completion session, task aliases, streaming
  draft, assistant reconciliation, and completion cleanup.
- `useInferenceRequestState` owns the composer-facing request presentation and
  already has terminal handlers for `task.completed`, `task.failed`,
  `task.cancelled`, and `completion.error`.
- `GuardianChat` coordinates those hooks and global event handling.

The rendered outer label instead comes from
`frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx`. That
component derives a local `requestState` solely from provider state:

```text
provider model_warming -> awaiting_model
every other provider state -> queued
```

It then maps that synthesized value through `mapRuntimeToVisualState` and
renders the result above `GuardianChat`. Consequently a healthy/ready provider
projects `Queued` before a request, during a request, after terminal completion,
after durable assistant rendering, and after reload. No terminal event consumed
inside the authorized lifecycle files can change that parent-owned value.

## Implementation

No implementation change was made. The demonstrated owner,
`frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx`, is not in
the authorized file list. Repairing another authorized hook would either leave
the visible defect intact or require a new cross-component truth channel, which
would violate the prohibition on a third lifecycle state machine.

No backend protocol, Redis behavior, worker behavior, persistence behavior,
provider semantics, timeout, polling, or event transport was changed.

### Required scope expansion

The next atomic task should authorize only:

1. `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx` as the
   actual outer status-projection owner; and
2. one narrow regression test proving the outer label is absent/terminal after
   matching success and failure while remaining unaffected by a wrong-task
   terminal event.

The repair should consume an existing lifecycle authority rather than create a
new store. The exact prop/callback boundary remains an implementation decision
for that separately authorized task.

## Focused tests

Pre-repair focused validation completed successfully:

```text
cd frontend/src
npm test -- --run \
  features/chat/__tests__/useInferenceRequestState.test.tsx \
  features/chat/__tests__/useChat.test.ts
```

Result: **2 test files passed; 15 tests passed**. This confirms the existing
focused hook coverage is green while not exercising the actual outer status
projection. The task-specified path
`frontend/src/features/chat/hooks/useInferenceRequestState.test.tsx` does not
exist at this revision; the existing test is under `features/chat/__tests__/`.

No new successful-terminal, failed-terminal, cancellation,
duplicate-terminal, stale-event, or wrong-task regression test was added because
the responsible component was out of scope. The known large OOM/hang lifecycle
suites were not invoked.

## Live browser proof

This run is a **pre-repair reproduction**, not post-repair qualification.

- Active execution was observable through task-specific lifecycle records from
  `QUEUED` through `AWAITING_MODEL`, `AWAITING_FIRST_TOKEN`, and `STREAMING`.
- Backend terminal completion occurred at 21:56:51.758392 UTC.
- Assistant message 37 was persisted once and rendered in the browser.
- The outer browser projection still read `Queued` after completion.
- Terminal-to-correct-browser-projection delay is therefore not measurable;
  the projection did not converge during observation.
- Reload was not repeated because the governing rerun had already shown this
  parent projection survives reload, and the source inspection proves it is
  recomputed from provider state rather than durable active-task truth.
- Browser console observations relevant to the request were one existing
  15-second slow-path warning and the correlated assistant `message.created`;
  favicon 404s were unrelated.

## F4 disposition

**PERSISTS.** Backend terminal truth, task-specific event history, durable
assistant persistence, and inner chat usability agree. The outer Guardian
status projection independently and incorrectly reports `Queued`.

F5 remains **PERSISTS** and was not touched. F7 remains **PERSISTS** and was not
touched.

## Validation and command ledger

| Command / action | Result | Interpretation |
|---|---:|---|
| `git status --porcelain=v2 --branch`; revision/upstream checks | 0 | Exact clean base established; ahead 2 / behind 0. |
| Supported Compose `ps`; frontend and runtime health probes | 0 | Existing supported stack remained available; no destructive restart or volume action. |
| Headed Playwright Chrome send/snapshot/network/console inspection | reproduced | Real assistant output rendered while outer status remained `Queued`. |
| Playwright response readback for completion request | 0 | Captured task/request/turn correlation. |
| Read-only Redis `XRANGE` for the task stream | 0 | Complete lifecycle includes `task.state=COMPLETED` and `task.completed`. |
| Read-only PostgreSQL chat/outbox queries | 0 after correcting an exploratory outbox column name | Assistant row 37 and durable terminal outbox row 87 independently proved completion. |
| Focused Vitest command above | 0 | 2 files / 15 tests passed. |

## ADR impact and invariants

**ADR impact: aligned with ADR-069 and ADR-087; no ADR change.** The accepted
terminal semantics are coherent. The blocker is a presentation owner outside
the authorized file scope, not an architectural contradiction.

- Backend terminal truth remained authoritative.
- PostgreSQL remained durable message/event truth.
- Redis remained operational queue/event infrastructure.
- Task, thread, turn, request, attempt, and message identities remained
  distinguishable and correlated.
- No false assistant row was created.
- No duplicate lifecycle store, polling loop, timeout reduction, or backend
  semantic change was introduced.
- No F5, F7, provider, retrieval, queue, worker, lock, or release behavior was
  changed.

## Documentation follow-through

This HOLD does not support a current-state or release-claim update.
`docs/architecture/00-current-state.md` remains unchanged. There is no repair
commit in this bounded run; only this evidence artifact is eligible for the
task-scoped proof commit.

The single first-prerequisite next task is to authorize and repair the outer
Guardian status projection in
`frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx`, with one
narrow terminal-correlation regression file. Do not begin F5 or F7 work.
