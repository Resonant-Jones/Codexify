# Delayed `task.created` Command Center projection proof

Date: 2026-10-03. Evaluated repair: `eb4d88115` on the active Goal branch.
Classification: `AUTHORIZED_IMPLEMENTATION`, aligned with ADR-001 and the Chat
Runtime Contract. This is bounded event-stream and frontend-reducer evidence;
it is not current-main qualification or a live-browser proof.

## Atomic Task Spec

Workflow lane: `architecture-impact`.

Context: retained supported-Compose evidence showed a successful chat retry's
Redis event stream append `task.running` before `task.created`. The accepted
producer order enqueues before publishing the best-effort `task.created`
acceptance breadcrumb, so a fast worker may publish execution evidence first.
The Command Center aggregation code applies events in stream order and was
projecting the delayed breadcrumb as the current state.

Goal: retain the observed event and its chronology while preventing a delayed
`task.created` breadcrumb from regressing a running or terminal Command Center
projection.

Files:
- `frontend/src/features/commandCenter/commandCenterRunAggregation.ts`
- `frontend/src/features/commandCenter/__tests__/commandCenterRunAggregation.test.tsx`
- `docs/architecture/00-current-state.md`
- `docs/architecture/proofs/supported-compose/2026-10-03-chat-command-center-late-created-projection.md`

This change belongs in `frontend/src/features/commandCenter/commandCenterRunAggregation.ts`.

Acceptance criteria:
- A late `task.created` remains in the observed event list and as the last observed event.
- A late `task.created` does not replace an existing running or terminal state, status, summary, or terminal outcome.
- The lifecycle summary does not append a regressive `QUEUED` state for a delayed created breadcrumb.
- No producer ordering, queue acceptance, task identity, or release claim changes.

Source evidence:
- `docs/architecture/adr/001-queue-based-completion-acceptance-model.md`
- `docs/architecture/chat-runtime-contract.md`
- `guardian/core/chat_completion_service.py::enqueue_chat_completion`
- `guardian/workers/chat_worker.py::_run_chat_task`
- Retained Compose project `codexify_chat_proof_f091_20261002`, task `9246a6fc-a59b-42a4-95c9-7abe44725771`

## Runtime observation

The retained retry stream was read directly from Redis with `XRANGE`:

| Stream ID | Event | `created_at` |
| --- | --- | --- |
| `1791021230596-0` | `task.state` (`QUEUED`) | `2026-10-03T09:53:50.596085+00:00` |
| `1791021230596-1` | `task.running` | `2026-10-03T09:53:50.596724+00:00` |
| `1791021230597-0` | `task.created` | `2026-10-03T09:53:50.597026+00:00` |

The task completed successfully afterward. The event order follows the
producer contract: queue insertion precedes the best-effort created-event
publication, while the worker can begin as soon as the queue entry is visible.
The runtime observation proves the ordering can occur; it does not prove a
browser projection.

## Regression and repair evidence

Before the repair, the focused test suite reproduced two projection failures:

- After `task.running`, a later `task.created` changed the projected state and
  summary to `created` while status remained `running`.
- After `task.completed`, a later `task.created` changed the projected state
  and summary to `created` while status and terminal outcome remained
  `completed`.

The reducer now retains the late event in the bounded event history and as the
last observed event, but leaves the effective state, status, summary, and
terminal outcome unchanged. Lifecycle-state derivation ignores only a later
`task.created` `QUEUED` breadcrumb after an earlier lifecycle state.

Validation:

- `cd frontend/src && pnpm exec vitest run --config vitest.config.ts features/commandCenter/__tests__/commandCenterRunAggregation.test.tsx` — passed, 6 tests.
- `cd frontend/src && pnpm exec eslint features/commandCenter/commandCenterRunAggregation.ts features/commandCenter/__tests__/commandCenterRunAggregation.test.tsx` — 0 errors; 3 import-order warnings in the two files.
- `git diff --check` — passed.

## Limits

The retained frontend container is mounted from
`/private/tmp/codexify-main-explicit-model-cd75ec6bd-20261003/source/frontend`,
not the active Goal worktree. The fixed reducer was therefore not exercised by
the retained browser or Compose frontend. The evidence combines the actual
Redis event order with focused reducer regressions; live UI confirmation and
current-main requalification remain open. The retry attempt also still has a
null `completed_message_id`, as recorded in the queued-cancel-and-retry proof.
