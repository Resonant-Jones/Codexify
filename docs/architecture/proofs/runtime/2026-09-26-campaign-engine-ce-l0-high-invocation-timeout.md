# CE-L0 current-tip High invocation timeout — 2026-09-26

## Result

`BLOCKED` at the bounded live adapter timeout. Canonical readiness passed
after operator-controlled `pi login openai-codex`, but the one authorized
live-rail attempt did not return a terminal runtime attestation within
120 seconds. This record does **not** emit
`CE-L0_EXIT=GUARDIAN_PI_LIVE_READY`. CE-L1 remains gated. No release claim is
widened.

## Proof provenance

| Field | Value |
| --- | --- |
| Branch | `codex/campaign-engine-closure` |
| Proof-time committed HEAD | `0d971d087cc1c7d7be11237cf3222725b65e25ac` |
| `origin/main` | `4041440110a2c9c42fe8898ffafc7eb9b2a4255a` |
| Working tree before and after | clean; no repository mutation by the live-rail attempt |
| Frozen request identity | `openai-codex / gpt-5.6-sol / pi-coding-agent / 0.82.1` |
| Explicit invocation effort | `high` |
| Guardian permissions | `files.read` on `.` only; no write grant |
| Live entry point | `guardian.pi.invocation.invoke_guardian_authorized_pi` with no injected runner |
| Prompt | `Reply with exactly: CE_L0_PI_LIVE_OK` |

The canonical policy validator returned `ok=true`. The proof used the
existing CE-L0 method: an isolated, credential-free Git fixture, frozen
Guardian identity and permissions, non-inference readiness, one bounded live
call, canonical result validation if available, and before/after target
snapshots. The driver first ran readiness alone; that run did not invoke a
provider. The live driver performed another non-inference readiness check
before its one live call. Neither readiness check started a provider request.

## Readiness

`preflight_guardian_authorized_pi` returned `ok=true`,
`deepest_stage=auth_available`, `oauth_available=true`, and actual identity
equal to all four frozen identity fields. Each readiness call had
`preflight_call_count=1`, `retry_count=0`, `fallback_count=0`,
`session_initialized=false`, and `provider_request_started=false`.
Readiness establishes structural authentication and model availability,
not provider response success. The requested High effort is explicit in the
subsequent live invocation argument; readiness creates no session and cannot
attest an effective effort.

## Single live attempt

| Field | Observed value |
| --- | --- |
| `runner_call_count` | `1` |
| `retry_count` / `fallback_count` | `0` / `0` |
| `ok` | `false` |
| `failure_reason` | `adapter_execution_failure` |
| `diagnostic_class` | `adapter_timeout` |
| `diagnostic_stage` | `adapter_execution` |
| Adapter timeout bound | 120 seconds |
| Actual live identity | unavailable; no terminal wrapper attestation |
| Effective reasoning effort | unavailable; no terminal wrapper attestation |
| Effective retry/compaction posture | unavailable; no terminal wrapper attestation |
| `provider_request_started` | unknown (`null`) |
| Receipt / Harness Result | absent; canonical validators therefore not applicable |

The committed wrapper and focused provider-free tests establish that a
successful authorized session must use the selected effort and disable Pi
retry and compaction recovery before prompting. This timed-out attempt did
not produce evidence that those runtime checks completed. The timeout alone
does not distinguish provider latency, transport failure, or a stalled SDK
session. No second provider invocation, fallback, model substitution,
credential repair, or timeout extension was attempted. No matching
`agent-wrapper.js guardian-authorized-task` process remained after the
bounded attempt.

## Disposable target equality

Target: `/var/folders/j7/l5mjdtxn2fj_2sggfbl0407c0000gn/T/ce-l0-current-tip-6et48h21`.
It had no remotes or credentials.

| Snapshot | Before | After |
| --- | --- | --- |
| Target HEAD | `48d19ac42334d2e7054311d6e71fcc7ffe203a78` | same |
| `git status --porcelain` | clean | clean |
| `README.md` SHA-256 | `6ec5e753b4aa74710ea2106131d122052894e2006638bef51019e07adef3c675` | same |
| `src/value.py` SHA-256 | `e13df8c44af5dea1e412403910b99cc5a48f2ccbf68a66b3374d6ab9cef9fc65` | same |

The target is byte-identical before and after. The proof retained no
credential values, auth file body, raw provider response, assistant text,
reasoning content, or environment dump.

## Gate boundary

CE-L0 remains unqualified at this current tip. A future provider-backed
qualification needs separate authority for another live attempt and must
start from its then-current committed source. Until a successful bounded
invocation returns exact live identity plus a valid Receipt and Harness
Result, CE-L1 cannot consume `GUARDIAN_PI_LIVE_READY`.
