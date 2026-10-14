# Current-main deadline failure presentation

Date: 2026-10-02. Baseline: `0798be4eecac395fd71e7c48056ba704a9af9b0e`.
Branch: `main`. Authority: active ordinary-chat reliability Goal and Development
Operator Level 0. Architecture-impact proof before repair, aligned with existing
ADR-001/002/003/038/087 and chat runtime/terminal ownership contracts. No new ADR,
runtime token, budget, or release claim. Current release posture remains HOLD.

## Causal proof

The worker's existing failure path preserves the canonical
`CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED` failure code in `task.failed` and
`completion.error`. Its lifecycle finalizer records `completed_at` for every
terminal outcome, including failed and cancelled attempts.

Frontend presentation discarded that failure code and described the event as a
provider error or provider timeout. Separately, inference diagnostics prioritized
`completed_at` over explicit failure/cancellation, reporting those attempts as
completed. Neither observation implies successful execution or persistence.

An independent archive of the baseline frontend, with only the three scoped
test files overlaid, reproduced **10 failed, 125 passed** across three files:
three deadline presentation cases, three task-stream failure cases, two global
terminal cases using the actual hook, and two failed/cancelled timing controls.
These are controlled jsdom/EventTarget regressions, not browser/runtime proof.

## Repair

Recognize the exact existing server failure code in the shared presentation
helper before considering provider timeout metadata. Describe the exhausted
request time limit without claiming a provider outage, cancellation, or success.

Preserve optional failure-code metadata through owned task-state failure,
task-failed, completion-error, and global terminal handlers. Inference diagnostics
use the already registered `failed_retryable` state for typed deadline failures.
Explicit failure/cancellation takes precedence over generic terminal timing;
terminal failures do not acquire a delayed/in-progress diagnostic. New requests,
successful completion, and cancellation clear prior failure metadata.

Existing stream/task/thread ownership fences, turn lease cleanup, and manual
retry behavior remain authoritative. The global-event regressions confirm one
authored send, no automatic completion retry, and released composer ownership.
Unknown codes/messages do not infer deadline expiry. Genuine provider timeout
and first-token timeout controls retain their existing presentation.

## Validation

From the repository root, assemble the independent baseline archive and overlay
only the seven declared source/test files. Execute:

```sh
pnpm --dir /private/tmp/codexify-main-deadline-ui-0798be4ee-20261002/frontend/src exec vitest run \
  --config vitest.config.ts --no-cache --maxWorkers=1 \
  features/chat/__tests__/requestFailurePresentation.test.ts \
  features/chat/__tests__/useInferenceRequestState.test.tsx \
  features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx \
  features/chat/components/__tests__/InferenceStatusBanner.test.tsx \
  features/chat/__tests__/useChat.test.ts \
  components/persona/layout/__tests__/GuardianChatWithSidebar.terminal-projection.test.tsx \
  test/api.completion-turn-lock.test.ts \
  features/chat/__tests__/GuardianChat.lifecycle-timing.test.tsx \
  features/chat/__tests__/GuardianChat.lifecycle-latency.test.tsx

git diff --check
```

Final result: **166 passed across nine files**, exit 0. The three deadline
stream cases include elapsed request age 721 seconds and the actual status
banner. All seven source/test files were byte-verified against the tested copy.
Diff check passed. Test dependencies use an existing external package-link view;
no repository dependency install or lockfile change was performed.

Scoped ESLint was attempted for those seven source/test files: **unavailable**,
exit 2 before analysis because the existing dependency view lacks
`eslint-plugin-react`. No lint success or full application build is claimed.

External evidence: `/private/tmp/codexify-main-deadline-ui-0798be4ee-20261002/`
contains `before.json`, `before.log`, `after.json`, `after.log`, and `eslint.log`.
No secret, service restart, queue/PG mutation, push, merge, or deploy occurred.

## Remaining limits

This receipt proves controlled frontend projection and ownership behavior only.
Fresh current-source supported Compose, real browser, persistence, provider,
in-flight deadline, and failure/recovery qualification remain necessary for the
larger Goal. Existing `useChat` private session failure classification was not
changed by this task; its completion-error handling needs separate bounded
inspection. No documentation follow-through to release truth is justified by
these tests. No additional Axis KB entry is proposed.
