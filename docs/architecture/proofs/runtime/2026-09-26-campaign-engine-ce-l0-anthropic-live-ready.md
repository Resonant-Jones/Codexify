# CE-L0 current-tip Anthropic Guardian/Pi live qualification — 2026-09-26

## Result and scope

`PASS`: one operator-selected, Guardian-authorized live Pi invocation completed
with exact terminal identity, effective High reasoning effort, a validated
Receipt and Harness Result, and an unchanged disposable read-only target.

```text
CE-L0_EXIT=GUARDIAN_PI_LIVE_READY
```

This qualifies the CE-L0 invocation substrate for the bounded Campaign proof.
It does not select Anthropic-through-Pi as Codexify's production Claude
routing architecture, close CE-L1, or change release claims. The earlier
`openai-codex` timeout remains a parked provider-specific transport finding.

## Frozen source and authorization

| Field | Evidence |
| --- | --- |
| Source branch and clean invocation tip | `codex/campaign-engine-closure` at `0ba477a0240f379f7b00610468798f6f2980e2bb` |
| Refreshed `origin/main` | `4041440110a2c9c42fe8898ffafc7eb9b2a4255a`, ancestor of the proof tip |
| Operator-selected identity | `anthropic / claude-sonnet-4-6 / pi-coding-agent@0.82.1` |
| Guardian policy | `allowed`; canonical policy validation `ok=true`; `files.read` on `.` only |
| Explicit reasoning effort | `high` |
| Adapter timeout | 300 seconds |
| Prompt | `Reply with exactly: CE_L0_PI_LIVE_OK` |
| Invocation ID | `invocation-ce-l0-anthropic-0ba477a` |
| Single-call guard | `/private/tmp/ce_l0_anthropic_0ba477a.live_started`, created exclusively before live execution |

The proof used the existing CE-L0 method: a fresh isolated Git fixture,
frozen Guardian envelope and decision, canonical non-inference readiness,
one canonical live rail call with no injected runner, canonical Receipt and
Harness Result validators, and before/after target snapshots. The source
checkout had no uncommitted changes before the call. No provider or model
substitution occurred.

## Non-inference readiness

`preflight_guardian_authorized_pi` returned `ok=true`, deepest stage
`auth_available`, exact actual identity matching all four frozen identity
fields, and structural auth availability. Its counters were one preflight
call, zero retries, and zero fallbacks. It reported
`session_initialized=false` and `provider_request_started=false`.
The target snapshot was unchanged. Readiness did not start a provider request
or attest effective reasoning effort.

## Single live invocation

`invoke_guardian_authorized_pi` was called exactly once with the explicit
`high` effort argument and a 300-second adapter bound. The authorized wrapper
requires Pi automatic retries and compaction recovery to be disabled before
prompting; it fails closed if either setting or effective effort differs.

| Evidence | Terminal result |
| --- | --- |
| `ok` / failure | `true` / none |
| Actual provider/model/harness | `anthropic / claude-sonnet-4-6 / pi-coding-agent@0.82.1`; exact match |
| Requested / effective effort | `high` / `high` |
| Automatic retries disabled | `true` |
| Runner calls / Guardian retries / fallback | `1` / `0` / `0` |
| Runtime identity / session / provider request | established / initialized / started |
| Receipt | present; `validate_receipt_against_envelope` returned `ok=true` |
| Harness Result | present; `validate_harness_result_against_receipt` returned `ok=true` |
| Target unchanged | `true` |

The timeout-only phase recovery fields were null on this successful terminal
result. Terminal identity, effort, retry posture, and provider-request fields
were available and verified. No retry, fallback, repair, or second live call
was made.

## Disposable target and evidence hygiene

The target was `/private/tmp/ce-l0-anthropic-006pyz3k`, an isolated Git
fixture with no remotes, symlinks, or credentials. It contained only
`README.md` and `src/value.py`. Its before/after snapshots matched:

| Field | Before and after |
| --- | --- |
| Git HEAD | `e65f56330903f94332e1ef9561f6dcf455f6d674` |
| `git status --porcelain` | clean |
| `README.md` SHA-256 | `6ec5e753b4aa74710ea2106131d122052894e2006638bef51019e07adef3c675` |
| `src/value.py` SHA-256 | `e13df8c44af5dea1e412403910b99cc5a48f2ccbf68a66b3374d6ab9cef9fc65` |

The proof output and this record contain only bounded identity, status,
configuration, validation, count, and target-hash evidence. They contain no
credential value, provider response, assistant text, reasoning content,
raw stderr, environment dump, or fixture file contents.

## Next gate

CE-L0 is closed at this source tip. Reassess CE-L1 against current repository
truth and continue only with its separately bounded, already-authorized
live Executor slice. CE-L0 alone is not Campaign Engine runtime proof.
