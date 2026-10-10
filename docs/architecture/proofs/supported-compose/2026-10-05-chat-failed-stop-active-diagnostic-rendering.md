# Active failed-Stop diagnostic rendering

Level 0 architecture-impact evidence under ADR-003/038/087. Candidate UI change is limited to rendering the existing Stop failure detail during active observation. No lifecycle, cancellation, persistence, event, API, ADR, protocol-token, or release-claim change. Supported Compose release status remains HOLD.

## Task Spec

Show the existing `CANCEL_FAILED` diagnostic while the response remains active. Keep observing the same task and retain Stop; do not project cancellation or completion from an HTTP 503. Verify the focused component and accessible browser rendering without submitting another chat request or replaying the completed request.

## Implementation and focused check

`InferenceStatusBanner` previously displayed active detail text only when it matched a progress phrase (`still waiting`, `warming up`, or `streaming`). `useInferenceRequestState` already sets the specific detail “The stop request could not be confirmed. Continuing to observe the task.” on Stop request failure while retaining the active task and cancellation capability. The banner now allows that existing Stop diagnostic through its active-detail filter.

The focused regression test supplies a streaming state with the exact diagnostic and `canCancel=true`. It asserts the diagnostic and “Replying…” are rendered, Stop remains enabled, and neither “Reply stopped” nor “Reply failed” is shown. Command:

```text
/Volumes/Dev_SSD/Codexify-main/frontend/node_modules/.bin/vitest run --config vitest.config.ts features/chat/components/__tests__/InferenceStatusBanner.test.tsx
```

Result: 1 file passed, 5 tests passed. The handoff checkout has Git LFS pointer files for frontend package/config files, so the focused check used a temporary hydrated frontend copy and the existing dependency installation; no install was run.

## Accessible browser rendering

An isolated local Vite harness imported the changed `InferenceStatusBanner` component and supplied the active state derived from the prior native 503 proof. Playwright opened `http://127.0.0.1:5184/stop-diagnostic-check.html`. The accessible snapshot contained “Replying…”, “The stop request could not be confirmed. Continuing to observe the task.”, and an enabled Stop button; it contained no stopped or failed terminal label. The harness has no chat API integration, and no Stop control was activated. Its only console error was a missing favicon.

This browser check proves component rendering for the supplied active state. It does not repeat the transport fault, submit an inference task, or establish deployed/runtime behavior. The earlier native browser 503 proof remains in `2026-10-05-chat-failed-stop-observation-second-oom.md`; that request was completed once by the worker and must not be replayed.

## Qualification boundary

This is branch-local UI evidence. It does not qualify full supported-Compose restart or graceful shutdown, current-main behavior, OOM root cause, or release readiness. Durable receipt recovery for the existing task is recorded in `2026-10-05-chat-failed-stop-durable-recovery.md`. No push, merge, deploy, or unrelated runtime mutation occurred.
