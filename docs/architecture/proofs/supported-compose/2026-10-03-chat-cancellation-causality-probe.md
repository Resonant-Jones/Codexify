# Bounded cancellation retry causality probe

Date: 2026-10-03. Baseline: `85c325a31` on
`codex/chat-integrated-runtime-proof-20261003`. Classification:
`PROOF_REQUIRED` under the ordinary chat reliability Goal. Release posture
remains `HOLD`.

## Atomic Task Spec

Trace the initially failing global accepted-stop cancellation case from the
integration regression run. Distinguish original-send completion dispatch from
fast retry dispatch, observe cancellation callbacks and retry scheduling, and
tag component instances. Perform at most two traced runs with neighboring
frontend suites; restore all temporary diagnostics before closeout. Do not
change cancellation, identity, retry, or acceptance semantics without a
reproduced causal seam and a separate implementation Task Spec.

## Evidence and outcome

Temporary observation-only logs recorded completion POST call stacks,
cancellation callback stacks, retry-scheduling stacks, reasoning mode, and
component-instance identity. The production source was not served to a browser
or copied to runtime containers during the probe.

- First traced frontend group: **205 passed across 11 files**.
- Second traced frontend group, concurrent with the original backend
  regression group: **205 passed across 11 files**. Concurrent backend result:
  **144 passed, 3 skipped**, with 20 existing warnings. Those database checks
  already have passing disposable-Postgres evidence in the integration receipt;
  this run was a timing/reproduction probe, not a new migration qualification.
- In the implicated global accepted-stop case, both traces recorded one
  original-send dispatch, an owned cancellation callback, one fast retry
  schedule, duplicate cancellation observations, and one `no_think` retry
  dispatch. The second run attributed all of these to component instance `32`.
- The original dispatch came from the deferred ordinary-send call site; the
  replacement dispatch came from `retryWithoutThinkingAfterCancel`.
  No retry dispatch appeared before the cancellation callback in either trace.

Evidence root:
`/private/tmp/codexify-chat-cancel-causality-85c325a31-20261003/`.
`trace-group.log` / `.json`, `trace-concurrent.log` / `.json`, and
`concurrent-backend.log` retain results and call-site records. Baseline and
instrumented source copies are retained there for review.

The temporary diagnostics were removed. Restored `GuardianChat.tsx` is
byte-identical to the baseline Git object, with SHA256
`c20069797695ee3b1d37bcf21731eb1ee327585a2ec7a5fdc6bf624dc8c28d93`.
`git diff -- frontend/src/features/chat/GuardianChat.tsx` is empty, and
`git diff --check` passes.

## Interpretation and remaining work

The initial early-second-call failure was not reproduced. The two new traces
qualify the tested successful cancellation ordering, but they do not identify
the initial failure's cause, prove deterministic scheduling, or justify closing
the intermittent failure. A deferred prior send remains an unproven candidate;
no production repair was made on that hypothesis.

This task changes only this proof receipt. No ADR changed, no runtime container
changed, and no push, merge to main, deployment, or memory update occurred.
Documentation follow-through is this receipt. Full supported-path qualification,
active-worker-loss authority, partial-output execution truth, and finite
accepted-deadline child/terminal/drain coverage remain unfinished.
