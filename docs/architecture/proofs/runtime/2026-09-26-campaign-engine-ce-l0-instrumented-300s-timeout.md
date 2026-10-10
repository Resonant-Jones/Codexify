# CE-L0 controlled 300-second instrumented timeout — 2026-09-26

## Result

`BLOCKED`: the one newly authorized current-tip Guardian/Pi live attempt
timed out. Its bounded phase trail positively reached Pi's first provider
payload handoff. No terminal result, Receipt, or Harness Result was produced.
CE-L0 is still unqualified, CE-L1 remains gated, and release claims are
unchanged. No second call or timeout increase followed this result.

## Frozen comparison

| Field | This attempt |
| --- | --- |
| Branch and clean pre-invocation HEAD | `codex/campaign-engine-closure` at `cfd5de65bac3778e0455370d1871565f6b460e79` |
| Relevant implementation commit | `adc750a4ddbab53751fe1f35dd725e68026e7577` |
| Prior 300-second comparison | [Second CE-L0 timeout](2026-09-26-campaign-engine-ce-l0-second-timeout.md) |
| Frozen provider/model/harness | `openai-codex / gpt-5.6-sol / pi-coding-agent@0.82.1` |
| Requested effort | `high` via the explicit Guardian live parameter |
| Adapter deadline | 300 seconds; unchanged from the prior 300-second attempt |
| Guardian permission | `files.read` on `.` only |
| Live prompt | `Reply with exactly: CE_L0_PI_LIVE_OK` |
| Single-call guard | `/private/tmp/ce_l0_controlled_cfd5de65.live_started`, created exclusively immediately before invocation |

The canonical non-inference readiness run in the preceding operator turn
was performed on this same clean source commit. It returned `ok=true`,
`deepest_stage=auth_available`, `oauth_available=true`, and exact frozen
provider/model/harness identity, with a valid Guardian policy decision,
one preflight call, zero retry/fallback, no session, no provider request,
and an unchanged disposable readiness target. The source tip and local
harness selection remained unchanged, so readiness was not repeated.
Readiness does not attest effective reasoning effort; the live wrapper owns
that pre-prompt check.

## Live outcome

| Field | Bounded observation |
| --- | --- |
| `ok` / failure | `false` / `adapter_execution_failure` |
| Diagnostic class / stage | `adapter_timeout` / `adapter_execution` |
| Runner calls | `1` |
| Guardian retries / fallback | `0` / `0` |
| Ordered observed phases | `wrapper_started` → `runtime_identity_established` → `session_initialized` → `provider_request_started` |
| Highest observed phase | `provider_request_started` |
| Phase ordering / highest consistency | valid / valid |
| Effective effort from verified session phase | `high` |
| Terminal actual provider/model/harness identity | unavailable |
| Terminal retry-suppression boolean | unavailable |
| Receipt / Harness Result | absent / absent; canonical validators not applicable |

The `session_initialized` phase is emitted only after the wrapper verifies
effective effort and disabled Pi retry/compaction settings. The timeout
outcome therefore retains the bounded `high` effort token from that phase,
while the separate terminal retry-suppression field remains unavailable.
The intermediate `runtime_identity_established` phase does not substitute
for terminal actual identity attestation.

`provider_request_started` means the first Pi provider payload reached the
wrapper's `onPayload` handoff after required payload processing. It does
**not** prove external provider receipt, acceptance, processing, response,
or completion. The smallest newly isolated uncertainty is downstream of
that handoff and before a terminal authorized result. No later phase is
inferred from elapsed time.

## Read-only target and evidence hygiene

The live target was `/private/tmp/ce-l0-controlled-kti0x9wl`, an isolated
Git fixture with no remotes or credentials. Before and after snapshots were
equal:

| Field | Before and after |
| --- | --- |
| Git HEAD | `d5f19efd4e1100413b31dc3e3ebffec91bee90ef` |
| `git status --porcelain` | clean |
| `README.md` SHA-256 | `6ec5e753b4aa74710ea2106131d122052894e2006638bef51019e07adef3c675` |
| `src/value.py` SHA-256 | `e13df8c44af5dea1e412403910b99cc5a48f2ccbf68a66b3374d6ab9cef9fc65` |

The guarded driver reported only allowlisted phase, configuration, identity,
count, validation-presence, and target-hash fields. This record contains no
auth material, provider response, assistant text, reasoning content, raw
stderr, environment dump, or file contents.

## Boundary and next action

This was a proof-only invocation under the existing ADR-068 Guardian/Pi
boundary. It changed no Campaign Engine runtime, Pi contract, UMS document,
or release claim. The controlled comparison resolved the earlier unknown
launch/session phase: Pi reached its first provider payload handoff before
the 300-second adapter deadline. Any downstream transport/response diagnosis
or another provider-backed attempt requires its own bounded task and
authorization. This timeout is not a successful CE-L0 exit.
