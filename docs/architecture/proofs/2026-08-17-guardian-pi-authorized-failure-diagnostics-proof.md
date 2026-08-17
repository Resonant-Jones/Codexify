# Guardian Pi authorized failure diagnostics proof — 2026-08-17

## 1. Scope

This proof covers one bounded diagnostic seam:

```text
authorized Pi wrapper -> PiCodexRunnerAdapter -> PiHarnessRuntimeEvidence
  -> Guardian PiLiveInvocationOutcome
```

It adds no provider, model, OAuth, Campaign Engine, queue, worker, database,
frontend, or release behavior. The previously consumed live qualification was
not retried.

## 2. Workflow classification

- Execution lane: `architecture-impact`
- Task kind: `implementation + proof`
- Evidence posture: redacted deterministic diagnostics plus one real
  non-inference preflight

## 3. ADR impact

Aligned with existing accepted ADRs. The change makes an already-authorized
fail-closed result more legible; it does not change who may execute, what may
execute, provider authority, identity matching, filesystem posture, Git
posture, retry policy, fallback policy, or release claims.

## 4. Governing ADRs/contracts

- ADR-020: Guardian Mediated Coding Agent Execution Contract
- ADR-066: Campaign Engine Runtime Recovery Contract
- ADR-068: Campaign Engine Live Role Execution Contract
- Pi Invocation Boundary Contract
- Agent Tool Loop Contract
- Runtime Protocol Token Contract
- Guardian delegation contracts

## 5. Task base HEAD

The task branch was created from the observed `origin/main`:

```text
TASK_BASE_HEAD: eb6bdc530245fdffeff23589c98389be4102b564
BRANCH: codex/pi-authorized-failure-diagnostics
```

The managed Git metadata prevented `git fetch origin main` from writing
`FETCH_HEAD`; the existing observed `origin/main` ref was already the required
`eb6bdc5...` and was used for the ancestry/drift gate.

## 6. Canonical Pi seam merge

```text
eb6bdc530245fdffeff23589c98389be4102b564
```

The seam is an ancestor of the observed `origin/main`.

## 7. Prior live qualification evidence commit

```text
0a5f125f987594278e71f63a903b709b6f2c68b6
```

The relevant prior proof artifact was discovered from that prerequisite
history at:

```text
docs/architecture/proofs/2026-08-17-openai-codex-executor-live-qualification-proof.md
```

The preceding OAuth and runtime evidence commits were
`be0ddd905e2806846e486ad5ff68176d58a68457` and
`954ada259ccef247002c6df12f73f4948d93bf1d`; their proof paths were discovered
from the commits before being used as evidence.

## 8. Integration/drift result

`PASS`. The affected-path diff from the canonical seam merge to observed
`origin/main` was empty for `guardian/pi/`, `guardian/agents/adapters/`, the
wrapper, the governing ADRs, and the Pi Invocation Boundary.

## 9. Prior terminal result

The prior one-attempt live qualification ended with:

```text
failure_reason: adapter_execution_failure
actual provider/model/harness identity: unavailable
PiInvocationReceipt: none
PiHarnessResult: none
```

The raw underlying adapter error was not preserved, so this task does not
claim to identify the exact stage of that historical attempt.

## 10. Prior call-count invariants

```text
runner_call_count: 1
retry_count: 0
fallback_count: 0
```

Those counts remain historical evidence. No new inference was issued by this
task.

## 11. Information-loss seam before change

`PiCodexRunnerAdapter.execute_authorized(...)` returned an
`AgentRunEnvelope`, but `_run_with_pi_adapter(...)` copied only status and
runtime identity fields into `PiHarnessRuntimeEvidence`. Adapter error detail
was discarded. `invoke_guardian_authorized_pi(...)` then collapsed runner
exceptions, missing evidence, and non-success evidence into the generic
`adapter_execution_failure` reason.

## 12. Diagnostic owner

The authorized adapter/wrapper boundary owns stage classification because it
can observe wrapper launch, runtime loading, identity verification, provider
and model resolution, auth readiness, session construction, and provider
request/transport failures. Guardian owns redacted propagation and retains the
architectural `adapter_execution_failure` category.

## 13. Canonical diagnostic vocabulary

The canonical bounded classes added in `guardian/pi/tokens.py` are:

```text
adapter_timeout
wrapper_unavailable
runtime_module_unavailable
authorized_identity_rejected
provider_unresolved
model_unresolved
oauth_auth_unavailable
session_initialization_failed
provider_request_failed
provider_transport_failed
wrapper_protocol_failed
actual_identity_missing
target_posture_violation
unknown_adapter_failure
```

The bridge accepts only this vocabulary. Unknown or untrusted class values
normalize to `unknown_adapter_failure`.

## 14. Raw-error suppression rule

Authorized failures never return raw stderr, stdout, exception messages,
stacks, headers, cookies, auth objects, request/response bodies, or environment
dumps. stderr is inspected only in-process for bounded token matching and is
then discarded. Legacy non-authorized adapter behavior remains unchanged.

## 15. Adapter structured-failure path

`AgentRunEnvelope` now carries optional bounded failure class/stage, return code,
runtime-identity-established, session-initialized, provider-request-started,
and OAuth-available fields. `execute_authorized(...)` maps timeout and missing
wrapper exceptions directly, parses only structured authorized JSON, and
redacts non-zero authorized subprocess output. The legacy `execute(...)` path
continues to preserve its existing output behavior.

## 16. Wrapper structured-failure path

`guardian-authorized-task` now emits a bounded JSON failure object for owned
stages. The new `guardian-authorized-readiness` mode loads the pinned runtime,
resolves the explicitly supplied provider/model, verifies harness identity,
checks local OAuth availability, and stops without constructing a session or
calling `session.prompt(...)`. Legacy `audit`, `compile`, `task`, and
`readiness` modes remain backward compatible.

## 17. Guardian bridge propagation

`PiHarnessRuntimeEvidence` carries the adapter's bounded fields. A failed
authorized adapter result returns `failure_reason=adapter_execution_failure`
plus the bounded `diagnostic_class` and `diagnostic_stage` on
`PiLiveInvocationOutcome`. This preserves the architectural result category
and exposes the operator diagnostic additively. Missing actual identity and
target-posture violations retain their fail-closed Guardian reasons and also
carry the corresponding bounded diagnostic class.

## 18. Unknown-failure behavior

Unknown adapter exceptions, unknown structured class values, and unmatched
stderr classify as `unknown_adapter_failure`. They remain failed, carry no raw
text, and preserve `runner_call_count=1` when execution was attempted.

## 19. Legacy compatibility

The existing legacy Pi adapter test and existing successful Guardian receipt /
HarnessResult tests pass. Direct Codex remains unsupported. No Coding Worker,
Campaign Engine, provider registry, OAuth configuration, migration, queue, or
frontend file was changed.

## 20. Deterministic failure-class tests

`tests/pi/test_pi_authorized_failure_diagnostics.py` covers timeout, missing
wrapper, missing runtime module, authorized identity rejection, provider and
model resolution, OAuth readiness, session initialization, provider request,
provider transport, wrapper protocol, actual-identity absence, unknown
failure, call counts, retry/fallback invariants, success receipts, preflight,
and filesystem/Git posture precedence. All use fake runners or mocked
subprocess results; none calls a provider.

## 21. Secret-shaped negative tests

The deterministic suite covers raw exception text, token-shaped stderr,
Bearer-shaped stderr, cookie-shaped stderr, and malformed wrapper JSON. The
returned authorized envelope/outcome contains none of those values.

## 22. Non-inference authorized preflight design

The preflight is Guardian-authorized, tools-disabled, and provider-prompt-free.
It can stop at runtime loading, exact identity verification, provider/model
resolution, or OAuth readiness. It does not call `session.prompt(...)`, create
a durable session, initiate login, retry, or fall back. Deterministic tests
also prove that the preflight request has an empty prompt and reports zero
provider-request/session flags.

## 23. Installed runtime identity

The real preflight used the existing ignored materialization from the runtime
proof worktree:

```text
@mariozechner/pi-coding-agent: 0.72.1
@mariozechner/pi-ai: 0.72.1
harness_id: pi-coding-agent
harness_version: 0.72.1
```

No dependency was installed, modified, or added to a tracked artifact.

## 24. Provider/model used for preflight

```text
provider: openai-codex
model: gpt-5.3-codex
```

These were passed explicitly through the authorized environment. No provider
or model switch occurred.

## 25. OAuth readiness

The real runtime reached exact provider/model/harness identity and then
reported:

```text
failure_class: oauth_auth_unavailable
failure_stage: oauth_readiness
```

Only the non-secret readiness result was observed. No auth-file contents,
credential object, token, header, cookie, login flow, or refresh operation was
read or initiated. This result is not interpreted as a repair authorization.

## 26. Deepest non-inference stage reached

```text
runtime_loaded: yes
identity_verified: yes
provider_resolved: yes
model_resolved: yes
auth_available: no
session_initialized: no
provider_request_started: no
deepest_stage: identity_verified
```

## 27. Preflight failure class, if any

`oauth_auth_unavailable` at `oauth_readiness`. The preflight itself completed
as a bounded fail-closed diagnostic result.

## 28. New provider prompt count

```text
AUTHORIZED_PREFLIGHT_MODEL_PROMPTS: 0
NEW_LIVE_MODEL_PROMPTS: 0
```

## 29. New inference-session count

```text
NEW_PROVIDER_INFERENCE_SESSIONS: 0
GUARDIAN_AUTHORIZED_INFERENCE_INVOCATIONS: 0
```

## 30. Retry count

```text
AUTOMATIC_RETRIES: 0
```

## 31. Fallback count

```text
AUTOMATIC_FALLBACKS: 0
```

## 32. Prior-failure bounded classification

The previous consumed attempt remains:

```text
PREVIOUS_FAILURE_BOUNDED_CLASSIFICATION: PREVIOUS_FAILURE_REMAINS_UNRESOLVED
```

The prior artifact preserved only the generic terminal adapter failure and no
raw stage evidence. The new rail is proven to classify future failures; it
does not retroactively recover information that was discarded.

## 33. Classification confidence

```text
confidence: HIGH for the new diagnostic rail
confidence: LOW for the exact historical failure stage
```

## 34. Credential exposure review

`RAW_STDERR_EXPOSURE: NONE`, `RAW_EXCEPTION_EXPOSURE: NONE`, and
`CREDENTIAL_SHAPED_ERROR_EXPOSURE: NONE` in the authorized path. No secret
scanner output containing suspect values was emitted. `gitleaks` and
`pre-commit` availability are reported separately in validation; neither is
treated as a passing scanner result unless installed and run.

## 35. What this proves

The Guardian-authorized Pi rail now preserves a bounded, machine-readable
failure class and stage from wrapper/adapter ownership through Guardian
outcome, suppresses raw error material, retains exact call counts, and keeps
unknown failures fail-closed. A non-inference preflight path is available and
the current exact runtime was exercised without a model prompt.

## 36. What this does not prove

This does not prove a successful OpenAI Codex Executor invocation, provider
entitlement, provider request reachability, a valid inference session, a
successful receipt/result for the consumed attempt, Campaign Engine live
execution, mutation capability, MiniMax readiness, or release support.

## 37. Final classification

```text
REDACTED_FAILURE_CLASSIFICATION: PASS
RAW_STDERR_EXPOSURE: NONE
RAW_EXCEPTION_EXPOSURE: NONE
CREDENTIAL_SHAPED_ERROR_EXPOSURE: NONE
UNKNOWN_FAILURE_FAIL_CLOSED: PASS
AUTHORIZED_PREFLIGHT_AVAILABLE: PASS
AUTHORIZED_PREFLIGHT_MODEL_PROMPTS: 0
NEW_LIVE_INFERENCE_INVOCATIONS: 0
AUTOMATIC_RETRIES: 0
AUTOMATIC_FALLBACKS: 0
LEGACY_PI_ADAPTER_REGRESSION: PASS
GUARDIAN_PI_SUCCESS_REGRESSION: PASS
FINAL_CLASSIFICATION: PASS
```

The preflight's `oauth_auth_unavailable` result is an operator-visible
bounded readiness observation, not an Executor qualification failure to be
repaired in this task.

## 38. Documentation follow-through

Added this focused proof only. `docs/architecture/00-current-state.md`,
supported-provider posture, release documentation, and all non-allowlisted
surfaces were left unchanged.

## 39. Exact next gate

Do not perform it in this task. Return to Axis for one fresh atomic task:

```text
Requalify the live OpenAI Codex Executor with one newly authorized attempt.
```

That future task must use a new invocation ID and Guardian decision, the same
exact provider/model identity rule, exactly one tools-disabled read-only prompt,
and zero retries or fallbacks. It may use this diagnostic class if it fails.
