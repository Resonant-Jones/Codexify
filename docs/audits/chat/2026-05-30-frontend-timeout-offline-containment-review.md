# Frontend Timeout vs Offline Containment Review

## Scope

This is a containment review for commit
`bc33d1de01fe1b4648833fdd9858f033c8d383e2`, which repaired frontend
request-failure presentation for provider timeout versus provider offline
semantics.

This review does not change runtime behavior, backend behavior, timeout policy,
provider fallback behavior, Obsidian retrieval behavior, frontend code,
database schema, migrations, supported-profile posture, or release posture.

## Repository Safety

- Working directory: `/Volumes/Dev_SSD/Codexify-main`
- Git root: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `codex/fix-chat-slash-commands`
- Remote: `origin https://github.com/Resonant-Jones/Codexify.git`
- HEAD commit before this review artifact:
  `bc33d1de01fe1b4648833fdd9858f033c8d383e2`
- Dirty/untracked files before review: none; `git status --short` was empty.

Recent commit surface verification:

- `bc33d1de01fe1b4648833fdd9858f033c8d383e2` touched only frontend
  runtime-token, chat request-state presentation, ChatView, and focused
  GuardianChat test surfaces:
  - `frontend/src/contracts/__tests__/runtimeTokens.test.ts`
  - `frontend/src/contracts/runtimeTokens.ts`
  - `frontend/src/features/chat/ChatView.tsx`
  - `frontend/src/features/chat/GuardianChat.tsx`
  - `frontend/src/features/chat/__tests__/GuardianChat.lifecycle-timing.test.tsx`
  - `frontend/src/features/chat/__tests__/GuardianChat.offline-banner.test.tsx`
  - `frontend/src/features/chat/hooks/useInferenceRequestState.ts`
  - `frontend/src/features/chat/requestFailurePresentation.ts`
- `52cba4819280a99f7fc0be5357bcbbce7c3bc3a3` touched only
  `docs/audits/chat/2026-05-30-provider-tokenization-containment-review.md`.
- `e500ac1ec80e28290111e35b9c5cb596c4284a96` touched provider registry and
  catalog validation repair surfaces only.
- `ffff2f30788e326fa43e5d4594c686e603833a87` touched provider/runtime token,
  router, health, worker, and focused tests only.
- `3dff6c5ffd08e97e92f52e08cd80781e5a79e8c0` touched provider timeout
  classification, chat worker, and focused provider/worker/health tests only.
- The scoped real-vault proof and rollback artifacts remain present:
  - `docs/audits/obsidian/2026-05-30-real-vault-scoped-index-proof.md`
  - `docs/audits/obsidian/2026-05-30-real-vault-index-rollback.md`

## Reviewed Change Surface

Files touched by the frontend repair commit:

- `frontend/src/contracts/runtimeTokens.ts`
- `frontend/src/contracts/__tests__/runtimeTokens.test.ts`
- `frontend/src/features/chat/requestFailurePresentation.ts`
- `frontend/src/features/chat/hooks/useInferenceRequestState.ts`
- `frontend/src/features/chat/GuardianChat.tsx`
- `frontend/src/features/chat/ChatView.tsx`
- `frontend/src/features/chat/__tests__/GuardianChat.lifecycle-timing.test.tsx`
- `frontend/src/features/chat/__tests__/GuardianChat.offline-banner.test.tsx`

Summary of frontend token/helper/component changes:

- Added frontend contract constants for provider failure kinds and transport
  classifications aligned with backend protocol-token values.
- Added `requestFailurePresentation.ts` to interpret task failure metadata and
  choose retryable timeout copy without scattering raw provider literals.
- Routed `task.failed` and `completion.error` payload metadata through that
  helper from both the task-event hook and the global GuardianChat event path.
- Changed `ChatView.tsx` so terminal failed request state remains visible in the
  request-state rail.

The wider touched test surface is focused fixture alignment, not broad product
behavior expansion:

- `GuardianChat.lifecycle-timing.test.tsx` was updated to mock the current
  Composer import path and auth/runtime helpers needed to exercise current
  GuardianChat behavior, then added first-token timeout and no-fake-assistant
  assertions.
- `GuardianChat.offline-banner.test.tsx` was updated to mock the current
  Composer import path so the true provider-health offline banner proof remains
  meaningful.
- `runtimeTokens.test.ts` now locks the frontend provider failure and transport
  token domains.

## Timeout vs Offline Semantics Review

Provider timeout after `awaiting_first_token` now renders as timeout/retryable
request failure rather than provider offline when the task failure payload
contains:

- `failure_kind="provider_timeout"`
- `transport_classification="timeout"`
- `failed_after_state="awaiting_first_token"`
- `provider_request_started=true`
- `first_output_observed=false`

True provider-health offline remains health-driven. `GuardianChat.tsx` still
derives the offline banner from `/health/llm` state:

- `llmHealth.status === "offline"`
- `llmHealth.status === "misconfigured"`
- `llmHealth.modelsAvailable === false`

The frontend interprets timeout evidence only in request-failure presentation.
It does not convert task-failure metadata into provider-health offline status.

Backend token values are represented through frontend contract constants in
`frontend/src/contracts/runtimeTokens.ts` and consumed by
`requestFailurePresentation.ts`. The stable metadata field names
`failed_after_state`, `provider_request_started`, and `first_output_observed`
remain JSON payload keys rather than token domains, which matches the prior
metadata-key decision.

No reviewed timeout evidence still collapses into offline. The remaining caveat
is live-provider proof: the current repair is proven with frontend task-event
fixtures, not a live synthetic slow-provider run.

## Transcript Integrity Review

The timeout failure path does not fabricate an assistant message in the focused
test proof. The first-token timeout test asserts the existing transcript still
contains only the prior user and assistant messages after `task.failed`.

The UI only displays assistant output when it is already present in the message
list or when normal completion/streaming paths provide real output. The repair
changes failure detail text and failure visibility only; it does not add a new
assistant-message construction path.

Message rendering assumptions did not change beyond keeping the terminal
failure rail visible. `ChatView.tsx` continues to render messages from the
existing message props and streaming draft state.

## Hook and State Review

`useInferenceRequestState.ts` preserved the normal lifecycle model:

- `task.state` still drives queued, model-warming, first-token wait, streaming,
  completed, failed, and cancelled state.
- `task.completed` still marks completion.
- `task.cancelled` still marks cancellation.
- `task.failed` and `completion.error` now choose detail copy from structured
  payload metadata, but still mark the attempt failed.

Terminal failure state became visible through `ChatView.tsx` without masking
later successful turns. Visibility remains scoped to the active thread/request
state, and stale-thread handling in the focused lifecycle test remains green.

Lifecycle timing remains consistent with the Chat Runtime Contract: provider
runtime health, request lifecycle, and lifecycle visibility remain distinct.
Retry/replay linkage was not proven by this slice and remains a hardening
follow-up.

## ChatView Review

`ChatView.tsx` changed only the completion-indicator visibility condition:
failed request state now keeps the status rail visible.

No layout, navigation, thread selection, composer behavior, or assistant-message
rendering code was changed by this file. The change is presentation-adjacent
because it exposes a terminal failure already present in request state.

Caveat: making terminal failure visible can surface pre-existing fixture
expectations that assumed failed state disappeared immediately. The updated
focused test asserts the newer, more truthful behavior.

## GuardianChat Broader Suite Review

Exact broader diagnostic command run:

```bash
cd frontend && pnpm test -- GuardianChat
```

Result:

- Failed.
- Console summary: 7 failed files, 4 passed files, 18 failed tests, 64 passed
  tests.

Failure classification:

| File | Failed tests | Class | Review |
| --- | ---: | --- | --- |
| `GuardianChat.catalog-options.test.tsx` | 2 | Fixture/query drift | Fails on duplicate model-label text. The file still mocks `@/features/chat/components` rather than the current `@/features/guardian/components/Composer`, so the real current Composer surface is active. Not introduced by `bc33d1de`; this file was not touched by the repair. |
| `GuardianChat.lifecycle-latency.test.tsx` | 4 | Fixture missing helper contract | The `@/lib/api` mock omits `buildAuthenticatedFetchInit`, which `useInferenceRequestState.ts` already imported before `bc33d1de`. Not introduced by the timeout/offline repair. |
| `GuardianChat.session-shortcuts.test.tsx` | 1 | Stale Composer fixture | The test expects `composer-input` from a stale mock path. GuardianChat already imported Composer from `@/features/guardian/components/Composer` before `bc33d1de`. |
| `GuardianChat.session-tabs.test.tsx` | 1 | Stale Composer fixture | The test expects `composer-stub` from a stale mock path. Not introduced by the timeout/offline repair. |
| `GuardianChat.test.tsx` | 1 | Unrelated voice fixture/behavior drift | Fails because no `input[type="file"]` is present for the voice-turn test. The timeout/offline repair did not touch voice upload code or this test file. |
| `GuardianChat.thread-config.test.tsx` | 4 | Stale Composer fixture | The test expects `provider-value` from a stale mock path. Not introduced by the timeout/offline repair. |
| `GuardianChat.turn-lock-lifecycle.test.tsx` | 5 | Fixture missing helper contract | The mocked `useInferenceRequestState` omits `describeInferenceRequestState`, which GuardianChat already used before `bc33d1de`. Not introduced by the timeout/offline repair. |

No failure was classified as introduced by this slice. The broader suite is not
green, so this review cannot use `PASS`; however, the failures are fixture drift
or unrelated existing behavior drift, not evidence that timeout now renders as
offline, true offline broke, or assistant output is fabricated.

## Normal Behavior Preservation

Focused timeout/offline validation is green:

- Provider first-token timeout renders as retryable timeout, not offline.
- True provider-health offline still renders the offline banner and provider
  switch affordance.
- Generic provider failures remain failed request states, not successful
  completions.
- Timeout failure does not add a fake assistant message.

Runtime token validation is green and locks the frontend provider
failure/transport token domains.

Normal chat rendering assumptions are preserved for this slice: the repair did
not alter message construction, thread routing, persistence assumptions,
provider selection policy, or backend task semantics. The broad GuardianChat
suite still needs fixture cleanup before it can serve as an all-clear signal.

## Real-Vault Safety

This review did not run real-vault indexing and did not call
`/api/obsidian/index`.

This review did not inspect, print, summarize, or commit vault contents.

No vault files or raw note text were committed by the reviewed frontend repair.
The scoped proof and rollback artifacts remain intact.

## Findings

### High

None.

### Medium

None for the timeout/offline repair.

### Low

- The broader `GuardianChat` test target is not a clean containment signal yet.
  It fails because several fixtures have not caught up with current Composer,
  API, and inference-state helper contracts.
- The focused repair is fixture-proven, not live-provider-proven.

### Non-blocking follow-ups

- Clean up stale GuardianChat fixtures so the broad `pnpm test -- GuardianChat`
  target can become a trustworthy regression gate again.
- Run a synthetic slow-provider/warmup proof without real-vault expansion.
- Add retry/replay linkage proof for timeout followed by a later completion.
- Revisit task-event metadata-key formalization only if those metadata fields
  become a formal frontend/backend event schema.

## Required Fixes Before Next Phase

None for the timeout/offline repair.

## Recommended Follow-Up Tasks

1. Repair GuardianChat fixture drift in a separate frontend-test cleanup slice.
2. Run a synthetic slow-provider or warmup proof that does not use real-vault
   content.
3. Add a retry/replay linkage proof for provider timeout followed by a later
   successful turn.

## Feature Completion Estimate

Estimated completion for the frontend timeout-vs-offline presentation feature:
`80%`.

What is complete:

- Backend timeout metadata is represented by frontend contract constants.
- First-token provider timeout renders as retryable timeout in focused tests.
- True provider-health offline still renders as offline in focused tests.
- Timeout failure does not fabricate assistant output in focused tests.

What remains before calling the feature fully sealed:

- Broad GuardianChat fixture cleanup so the full `GuardianChat` test target is
  green.
- Synthetic slow-provider/warmup proof outside frontend mocks.
- Retry/replay linkage proof for a later successful attempt after timeout.

Remaining work is hardening and proof cleanup, not a blocking defect in the
reviewed timeout/offline repair.

## Validation

Focused frontend validation:

- `cd frontend && pnpm test -- GuardianChat.lifecycle-timing.test.tsx GuardianChat.offline-banner.test.tsx`
  - passed, 2 test files, 6 tests.
- `cd frontend && pnpm test -- runtimeTokens`
  - passed, 1 test file, 6 tests.

Broader frontend diagnostic:

- `cd frontend && pnpm test -- GuardianChat`
  - failed, 7 failed files, 4 passed files, 18 failed tests, 64 passed tests.
  - Failure classes are recorded in `GuardianChat Broader Suite Review` above.
  - No failure was classified as introduced by `bc33d1de`.

Additional diagnostic used for classification:

- `pnpm --dir frontend/src exec vitest run --config vitest.config.ts GuardianChat --reporter=json --outputFile=/private/tmp/guardianchat-report.json`
  - failed as expected while writing a local temporary JSON report for failure
    classification.
  - The report was written outside the repository and was not committed.

Documentation and diff validation:

- `python3 scripts/validate_docs.py` - passed.
- `git diff --check` - passed.

## Final Verdict

`PASS WITH FOLLOW-UPS`

The frontend timeout-vs-offline repair is safely contained. It preserves the
distinction between provider-health offline and per-request provider timeout,
keeps transcript integrity intact, and limits code changes to frontend
presentation and contract constants. The broader GuardianChat target remains
red, but the failures are stale fixture contracts or unrelated existing drift,
not regressions introduced by the timeout/offline repair.
