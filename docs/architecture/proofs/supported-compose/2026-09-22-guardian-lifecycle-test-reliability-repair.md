# Guardian lifecycle test reliability repair — 2026-09-22

## Result

**Bounded result: PASS. F7 frontend lifecycle reliability CLOSED; overall F7
CLOSED.**

The two full-`GuardianChat` lifecycle suites now execute deterministically
under the unchanged ordinary Vitest configuration. The repair stabilizes
test-owned hook identities, bounds event resources, and makes teardown
assertable. It does not modify production runtime source, lifecycle semantics,
global Vitest configuration, worker count, test timeout, or Node heap size.

All original F1-F7 findings are now closed or downstream resolved. This does
not establish release readiness: the supported-Compose posture remains `HOLD`
until a fresh complete qualification bundle runs against the fully repaired
current tip.

## Environment

| Field | Evidence |
| --- | --- |
| Date | 2026-09-22 |
| Repository | `/Volumes/Dev_SSD/Codexify-main` |
| Branch / base commit | `main`; `487b9e076f1e957cb01fd798f95a4e5a464c5607` |
| Upstream / divergence | `origin/main`; ahead 8, behind 0 |
| Initial worktree | One unrelated staged deletion: `docs/DEV_LOG/2026-09-22/Dev Log - 2026-09-22.md`; no unstaged or untracked paths |
| Node / pnpm / Vitest | Node `v25.9.0`; pnpm `9.12.1`; Vitest `4.1.11` |
| Test configuration | Existing `frontend/src/vitest.config.ts`; jsdom; no configuration mutation |

The unrelated staged Dev Log deletion was not restored, unstaged, modified, or
included in this task.

## Pre-repair reproduction

All commands ran from `frontend/src` with the repository's normal config and
without heap, worker, pool, isolation, or timeout overrides.

### Lifecycle timing alone

```text
pnpm exec vitest run --config vitest.config.ts \
  features/chat/__tests__/GuardianChat.lifecycle-timing.test.tsx
```

Result: exit 1 after 33.95 seconds. Vitest collected one file and six tests but
reported `tests 0ms`. The worker reached approximately 4.08 GiB of V8 heap and
terminated with `Ineffective mark-compacts near heap limit` / `JavaScript heap
out of memory`. A targeted run of only the new-thread ordering case reproduced
the same OOM after 33.56 seconds, proving the failure did not depend on test
accumulation or suite order.

### Turn-lock lifecycle alone

```text
pnpm exec vitest run --config vitest.config.ts \
  features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx
```

Result: no test result or trustworthy assertion progress after 74.74 seconds;
the run was interrupted rather than left unbounded. A targeted first-test run
likewise made no result progress and was interrupted after 55.59 seconds.
Read-only process inspection during the stall showed the Vitest worker at
119.8% CPU and 435,584 KiB RSS after 11 seconds, so this was an active render
loop rather than an idle unresolved promise.

### Both files together

```text
pnpm exec vitest run --config vitest.config.ts \
  features/chat/__tests__/GuardianChat.lifecycle-timing.test.tsx \
  features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx
```

One worker reached the same approximately 4.08 GiB heap OOM after about 34
seconds while the other made no trustworthy progress. The combined command was
interrupted at 68.16 seconds. No baseline run completed a lifecycle assertion.

`/usr/bin/time -l` reported the useful wall times but could not emit its macOS
kernel memory summary in the sandbox (`sysctl kern.clockrate: Operation not
permitted`). The V8 fatal output and read-only process sample provide the memory
evidence above. No Vitest worker remained after the bounded diagnostics.

## Root cause

### Lifecycle timing suite

Classification: **REACT RENDER / EFFECT LOOP**, with unstable test mock
identity as the cause. Fake timers were not the initiating cause.

### Turn-lock lifecycle suite

Classification: **REACT RENDER / EFFECT LOOP**, with the same unstable test
mock identity as the cause. The apparent hang was the loop consuming CPU and
memory without reaching a reportable assertion.

Both files mocked `useLiveEvents` by constructing a new `subscribe` function
on every `GuardianChat` render. `GuardianChat` passes that function to
`useCodingLoopRuns`. The hook's lifecycle effect depends on `subscribe` and,
before its disabled early return, resets `runs` and `dispatchErrors` to new
arrays. The causal cycle was therefore:

```text
render
-> new mocked subscribe identity
-> useCodingLoopRuns effect invalidated
-> setRuns([]) and setDispatchErrors([])
-> render
-> repeat
```

Running a targeted test with console interception disabled exposed a continuous
stream of React `Maximum update depth exceeded` diagnostics. Stabilizing the
mocked `subscribe` identity made the same targeted tests complete immediately:
the turn-lock start-failure case passed in 89 ms, and the lifecycle new-thread
case passed in 117 ms. That direct before/after result identifies the causal
mechanism.

The audit also found other render-created composite mock values in `useChat`,
`useInferenceRequestState`, and `useLlmCatalog`. They were not needed to trigger
the loop independently, but they caused avoidable dependency invalidation and
listener churn. The repair stabilizes those test hook values as well.

## Repair

Changed test-owned infrastructure only:

- `GuardianChat.lifecycle-timing.test.tsx` now returns stable `useLiveEvents`,
  `useChat`, and catalog hook values across renders.
- `GuardianChat.turn-lock-lifecycle.test.tsx` now returns stable live-event,
  chat, inference, and catalog hook values across renders.
- The lifecycle suite explicitly unmounts each tree, requires every mocked task
  event source to close exactly once, verifies its closed state, clears the
  instance registry, clears pending fake timers, and restores real timers.
- The turn-lock suite explicitly unmounts each tree and requires the live-event
  handler map to be empty after effect cleanup.
- The provider-switch case now also proves the visible lock is released and
  the composer send control remains usable.

No shared harness file was needed. The defect was two small identity violations,
and extracting a larger fixture would have widened the change without improving
the authority boundary.

### Fake-timer audit

The lifecycle suite retains fake time because it proves the 60-second warmup,
first-token, and streaming boundaries without real sleeps and deterministically
crosses the delayed completion-start timer. Every advancement is owned by the
test helper inside React `act`; no test waits for real wall-clock time while
fake time is frozen. Teardown clears remaining intervals/timeouts before
restoring real timers. The repaired full suite completes in about 1.25-1.40
seconds rather than sleeping through the modeled intervals.

The turn-lock suite uses real timers and creates no fake-timer ownership.

### Listener, event-source, and mutable-state audit

- Mock `GuardianEventSource` instances are reset before each lifecycle test and
  asserted closed exactly once after unmount; stale sources cannot receive a
  later test's events.
- Turn-lock live-event handlers unsubscribe on unmount, and the handler map must
  be empty after every test.
- The turn-lock completion-in-flight `Set`, completion-state object, inference
  fields, API implementations, and event handler map are restored before every
  test. `vi.clearAllMocks()` is supplemented by explicit data resets rather
  than treated as a mutable-state reset.
- Testing Library roots are explicitly cleaned up even though the global setup
  also supplies cleanup.

## Coverage ledger

### Lifecycle timing

| Contract | Preserved test evidence |
| --- | --- |
| New-thread ordering | `resolves a new-thread composer send after authored persistence without waiting for completion` proves message persistence and composer resolution precede the delayed completion request. |
| Queued state | `keeps queued, warmup, first-token, and generating states visible until terminal completion` observes `Queued…` before later phases. |
| Model warming | The same test emits `AWAITING_MODEL`, observes `Warming model…`, advances 60 seconds, and proves the state remains truthful. |
| First-token wait | The same test emits `AWAITING_FIRST_TOKEN`, observes `Waiting for first token…`, and retains it across 60 seconds. |
| Streaming | The same test emits `STREAMING`, observes `Generating…`, and retains it across 60 seconds. |
| Terminal completion | The same test emits `task.completed`, proves generating clears, and keeps existing assistant content. |
| Timeout failure | `renders provider first-token timeout as retryable timeout instead of offline` proves timeout-specific detail, no offline projection, no raw sentinel leak, and no fabricated assistant message. |
| Thread switching | `preserves the task stream across thread switches` proves the source remains open off-thread, does not project into the wrong thread, and restores generating/Stop presentation on re-entry. |
| Generic failure | `renders generic provider failures as failed request state without adding an assistant message` preserves failure projection and transcript integrity. |
| Cancellation | `clears generating when the request is cancelled` preserves terminal cancellation cleanup. |

### Turn lock

| Contract | Preserved test evidence |
| --- | --- |
| Start failure | `clears the lock when completion start fails with backend error` observes unlocked -> locked -> unlocked. |
| Successful terminal event | `clears the lock on successful terminal events even without turn_id and stays idempotent` proves `task.completed` unlocks. |
| Duplicate terminal delivery | The same test emits `task.completed` twice and proves the lock remains validly unlocked. |
| Error without task ID | `clears the lock on completion.error when task_id is missing but active thread matches` preserves thread-correlated cleanup. |
| Cancellation | `cancelling inference releases lock and clears request-scoped state` proves unlock, cancel request, and inference reset. |
| Provider switch | `provider switch during active request unwinds lock and keeps composer usable` proves cancellation/reset, provider selection, unlocked state, and enabled send control. |

## Repeated execution

All acceptance runs used the unchanged normal configuration and no heap,
worker, pool, serialization, or timeout overrides. The only recurring output
was the existing Node warning that `--localstorage-file` lacked a valid path.

### Lifecycle timing alone

| Run | Result | Vitest duration | Wall time | Exit |
| --- | --- | --- | --- | --- |
| 1 | 6/6 passed | 1.25 s | 1.79 s | 0 |
| 2 | 6/6 passed | 1.34 s | 1.82 s | 0 |
| 3 | 6/6 passed | 1.40 s | 2.12 s | 0 |

### Turn-lock lifecycle alone

| Run | Result | Vitest duration | Wall time | Exit |
| --- | --- | --- | --- | --- |
| 1 | 5/5 passed | 0.89 s | 1.47 s | 0 |
| 2 | 5/5 passed | 0.89 s | 1.50 s | 0 |
| 3 | 5/5 passed | 0.97 s | 1.59 s | 0 |

### Both files together

| Run | Result | Vitest duration | Wall time | Exit |
| --- | --- | --- | --- | --- |
| 1 | 11/11 passed | 1.45 s | 2.08 s | 0 |
| 2 | 11/11 passed | 1.27 s | 1.76 s | 0 |
| 3 | 11/11 passed | 1.28 s | 1.85 s | 0 |

Read-only process inspection after the repeated runs found no Vitest, worker,
or tinypool process other than the inspection command itself.

Targeted `-t` runs also passed for the full lifecycle-transition case (1 passed,
5 skipped) and terminal/idempotent turn-lock case (1 passed, 4 skipped), proving
the suites remain independently addressable by test name.

## Neighboring regression coverage

The focused neighboring group covered provider catalog/select, Guardian sidebar
terminal projection and stability, `useChat`, `useInferenceRequestState`,
`useTaskEvents`, and both runtime-health test surfaces:

```text
7 files passed / 83 tests passed / 0 failed
```

Focused ESLint over the two changed test files passed with zero errors and 23
existing permissive-type/import-order warnings. No narrow repository TypeScript
command exists that isolates these two test files from the known project-wide
baseline, so broad TypeScript debt was not made part of this repair.

## Finding disposition

| Finding | Disposition | Evidence |
| --- | --- | --- |
| F4 — outer terminal/request projection disagreement | **CLOSED — unchanged** | No production or F4 test source changed; neighboring sidebar terminal and stability coverage remains green. |
| F5 — durable document/chunk retrieval provenance | **CLOSED — unchanged** | No retrieval, persistence, or provenance source changed. |
| F7 backend static | **CLOSED — unchanged** | The prior governing backend suite remains 157/157; it was not modified in this task. |
| F7 frontend lifecycle reliability | **CLOSED** | Both suites pass independently and together across three consecutive runs with bounded time, explicit teardown, and no residual worker. |
| Overall F7 | **CLOSED** | Both the governing backend static and frontend lifecycle reliability portions are green. |

## ADR impact and invariants

**ADR impact: aligned with ADR-069, ADR-087, the Chat Runtime Contract, Request
State Machine, and Completion Pipeline. No ADR change.**

- Production runtime behavior and canonical lifecycle tokens are unchanged.
- Assertions continue to prove queued, warming, first-token, streaming,
  completion, failure, cancellation, lock-release, and thread-ownership
  behavior through observable UI state.
- No test is skipped, excluded, or weakened.
- No heap increase, global serialization, worker reduction, timeout expansion,
  or Vitest configuration change was used.
- Fake time has explicit ownership and cleanup.
- Event sources, listeners, rendered roots, and mutable lifecycle state are
  bounded at every test boundary.
- Overall supported-Compose remains `HOLD`; this test repair is not live runtime
  or release qualification.

## Documentation follow-through

This artifact records the bounded F7 frontend reliability repair and closes
overall F7. `docs/architecture/00-current-state.md` remains unchanged as
required. The governing backend static gate passes, and both Guardian lifecycle
suites now execute deterministically, but no release/current-state claim is
widened here.

The next single prerequisite is to **rerun the complete current-tip
supported-Compose qualification bundle against the fully repaired current
tip**. This task does not begin that rerun.
