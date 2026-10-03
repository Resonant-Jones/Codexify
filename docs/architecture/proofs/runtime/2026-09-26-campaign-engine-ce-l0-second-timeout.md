# CE-L0 second bounded live attempt — 2026-09-26

## Result

`BLOCKED`: the second, separately authorized Guardian/Pi live-rail attempt
timed out without terminal evidence. Do **not** record
`CE-L0_EXIT=GUARDIAN_PI_LIVE_READY`. CE-L1 remains gated. No third call was
made, and no release claim changes.

## Provenance and bounds

| Field | Value |
| --- | --- |
| Branch | `codex/campaign-engine-closure` |
| Clean committed proof-time HEAD | `3de8897c975f90e7ffbf3686e7169ee68186a6b6` |
| Prior attempt | [120-second timeout](2026-09-26-campaign-engine-ce-l0-high-invocation-timeout.md) |
| This attempt's timeout | 300 seconds, selected through the existing `timeout_seconds` invocation parameter |
| Timeout contract | `invoke_guardian_authorized_pi` accepts a positive bounded `timeout_seconds`; the adapter applies it to its subprocess; no source or contract change was made |
| Frozen requested identity | `openai-codex / gpt-5.6-sol / pi-coding-agent / 0.82.1` |
| Explicit requested effort | `high` |
| Guardian permission | `files.read` on `.` only |
| Live prompt | `Reply with exactly: CE_L0_PI_LIVE_OK` |
| Launch guard | `/private/tmp/ce_l0_second_attempt.live_started`, created once immediately before the live-rail call |

The operator first used a dedicated readiness-only driver with no live
invocation path. Its canonical `preflight_guardian_authorized_pi` call
returned `ok=true`, `oauth_available=true`,
`deepest_stage=auth_available`, and actual provider/model/harness identity
equal to the frozen request. It returned `session_initialized=false` and
`provider_request_started=false`. The live driver repeated this same
non-inference readiness check before invoking. Both readiness checks had
zero retry and fallback; neither issued a provider request. The policy
decision validator returned `ok=true`.

An initial attempt to run the combined driver for readiness alone was
rejected by automatic approval review before execution because inherited
environment state could have enabled its live branch. No provider call
occurred. A dedicated readiness-only driver removed that risk. The user
then directly authorized one live attempt with the fixed identity, High
effort, and 300-second bound.

## Live-rail outcome

| Field | Observed value |
| --- | --- |
| `runner_call_count` | `1` |
| `retry_count` / `fallback_count` | `0` / `0` |
| `ok` | `false` |
| `failure_reason` | `adapter_execution_failure` |
| `diagnostic_class` / `diagnostic_stage` | `adapter_timeout` / `adapter_execution` |
| Actual live provider/model/harness identity | unavailable |
| Effective reasoning effort | unavailable |
| Effective automatic-retry and compaction posture | unavailable |
| `provider_request_started` | unknown (`null`) |
| Receipt / Harness Result | absent; canonical validators could not run |

The 300-second timeout did not resolve the previous 120-second boundary.
The adapter discards partial wrapper output on timeout, so its one runner
call cannot prove whether the wrapper reached session initialization or
started provider transport. This is a **runtime/invocation-latency or
terminal-evidence problem**, not a qualified CE-L0 result. The operator made
no provider, model, or harness substitution, no Guardian retry or fallback,
no credential repair, and no third live attempt. The wrapper's effective
internal retry posture remains unverified without terminal evidence. No
matching authorized wrapper process remained after the bounded call.

## Disposable read-only target

The isolated target was
`/var/folders/j7/l5mjdtxn2fj_2sggfbl0407c0000gn/T/ce-l0-second-attempt-nf5qwqj8`.
It had no remotes or credentials. Its pre/post snapshots were equal:

| Field | Before and after |
| --- | --- |
| Git HEAD | `fd70b548aa121beec88d42c2afe405cf5b847e45` |
| `git status --porcelain` | clean |
| `README.md` SHA-256 | `6ec5e753b4aa74710ea2106131d122052894e2006638bef51019e07adef3c675` |
| `src/value.py` SHA-256 | `e13df8c44af5dea1e412403910b99cc5a48f2ccbf68a66b3374d6ab9cef9fc65` |

No credential values, auth file body, raw provider response, assistant
text, reasoning content, or environment dump was retained.

## Smallest next prerequisite

Before another live proof is considered, define and validate a bounded,
credential-safe timeout diagnostic that distinguishes wrapper setup,
session configuration, provider-request start, and terminal response
without retaining prompt, reasoning, tool arguments, or provider payloads.
The current adapter's timeout result lacks that phase evidence. Keep this
as a separate Guardian/Pi diagnostic slice; do not modify Campaign Engine
runtime or treat a longer timeout alone as proof. A future provider-backed
call would need its own explicit authorization and then-current-tip proof.
