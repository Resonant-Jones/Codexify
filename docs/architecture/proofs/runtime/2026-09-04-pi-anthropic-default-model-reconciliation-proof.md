# 2026-09-04 — Pi Anthropic Default Model Reconciliation Proof

## 1. Result

~~~text
RESULT=PASS
ANTHROPIC_DEFAULT_MODEL_DRIFT=REPAIRED_LOCAL
CANONICAL_ANTHROPIC_CODING_DEFAULT=claude-sonnet-4-6
ANTHROPIC_REPLACEMENT_MODEL_RESOLUTION=PASS_EXACT
ANTHROPIC_REPLACEMENT_SESSION_COMPATIBILITY=PASS_PROVIDER_FREE
GUARDIAN_AUTHORIZED_MODEL_IDENTITY_EXACT=PASS
ANTHROPIC_DEFAULT_COHERENCE=PASS
ANTHROPIC_AUTHORIZED_MODEL_RESOLUTION=PASS_PROVIDER_FREE
OBSOLETE_ANTHROPIC_ID_SILENT_REMAP=false
ACTIVE_CODING_RUNTIME_STALE_ID_COUNT=0
VENDORED_PI_MODEL_REGISTRY_MUTATION_COUNT=0
~~~

This is a local configuration and runtime-boundary repair. It does not close
CE-L1, authorize a new provider-backed control, or widen the Codexify Beta
support claim.

## 2. Scope

This task reconciles the active Codexify coding-worker Anthropic default with
the exact model identifier supplied by the pinned Pi 0.82.1 registry. It
preserves Guardian authorization ownership, exact provider/model identity,
single-attempt behavior, the existing Pi invocation boundary, and the
provider-free evidence posture.

The task authorized zero provider-backed invocations, zero live Executor
invocations, zero OAuth actions, and zero operator credential-store access.
The Pi vendor tree was an authority consumed by the repair, not an edit
surface.

## 3. Captured canonical-main identity

Task-start capture was performed with git fetch origin, followed by
git rev-parse origin/main and git show -s --format='%H %s':

~~~text
AXIS_OBSERVED_AUTHORING_MAIN=a6b2e6cb13f5ac6f2c201d835f99f065871fdea8
CAPTURED_MAIN=a6b2e6cb13f5ac6f2c201d835f99f065871fdea8
CAPTURED_MAIN_SUBJECT=Remove September 4 development log
~~~

The authoring anchor was verified as an ancestor of captured origin/main with
git merge-base --is-ancestor; the command exited successfully.

The source checkout could not create the requested branch because its Git
metadata rejected the ref-lock write with Operation not permitted. A fresh
local clone under the writable Keep root was therefore created from the
captured SHA, and the implementation branch was created there while clean:

~~~text
IMPLEMENTATION_ROOT=/Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify-pi-anthropic-default-reconciliation
BRANCH=fix/pi-anthropic-default-model-registry-drift
PRE_TASK_HEAD=a6b2e6cb13f5ac6f2c201d835f99f065871fdea8
~~~

The original source checkout's pre-existing modification to
tests/pi/fixtures/fake_pi_package/package.json was not changed, staged, or
copied into the implementation branch.

## 4. Main drift classification

The bounded diff from the Axis authoring anchor to captured origin/main over
the CE-L1/provider/model surfaces was empty:

~~~text
DRIFT_CLASS=NO_DRIFT
MATERIAL_CE_L1_FILES_CHANGED_BEFORE_TASK=none
~~~

The task therefore proceeded from the exact captured main tip. No unrelated
frontend, migration, operator-log, or private-preview movement was treated as
provider/runtime drift.

## 5. Governing ADR impact

~~~text
ADR_IMPACT=ALIGNED_WITH_ADR-020_ADR-066_ADR-068
NEW_ADR_REQUIRED=false
~~~

The repair is aligned with:

- ADR-020: Guardian remains the owner of authorization, request identity,
  lineage, and bounded result return; Pi remains the invocation substrate.
- ADR-066: the Campaign Engine does not gain provider fallback, retry,
  rebinding, or provider-selection authority from this configuration repair.
- ADR-068: exact provider/model identity remains the expected RoleBinding
  identity for any future live Executor work; this task performs no such live
  work.

docs/architecture/00-current-state.md was read and intentionally not updated.
Pi 0.82.1 coding-worker changes remain qualification evidence, not live
provider support.

## 6. Prior Anthropic failure evidence

The local prior proof commit
e840868a3fa95dfc8aa2a976ee8631d335362998 records the one already-spent
Anthropic CE-L1 control. Its exact identity was:

~~~text
anthropic / claude-sonnet-4-20250514 / pi-coding-agent@0.82.1
~~~

The bounded failure was:

~~~text
failure_reason=adapter_execution_failure
diagnostic_class=model_unresolved
diagnostic_stage=model_resolution
provider_transport_reached=false
~~~

The failure occurred before a provider request, so this task does not rerun or
reinterpret that rail.

## 7. Old coding default

Before the repair, the obsolete exact ID appeared in the active coding-worker
default seams:

| Surface | Pre-repair state |
| --- | --- |
| codex_runner/src/agent-wrapper.js | wrapper default, generic Sonnet aliases, partial-match list, help text |
| codex_runner/src/profile.py | default, fast, review, dataclass, and deserialization fallbacks |
| codex_runner/src/runner_cli.py | direct agent, audit, and run fallbacks |
| guardian/agents/pi_readiness.py | readiness default |
| guardian/agents/adapters/pi_codex_runner.py | legacy adapter fallback |
| docker-compose.yml | worker-coding PI_MODEL default |
| operator docs | source-Compose default descriptions |

The active startup-gate test also constructed a blocked readiness report with
the old example value. It was identified before editing and updated under the
task's explicit discovery allowance because it is directly tied to the active
coding-worker readiness surface.

## 8. Replacement-model selection

The task specified claude-sonnet-4-6 as the only permitted replacement. No
alternative model was selected, and no provider policy or fallback behavior
was changed.

## 9. Exact Pi registry resolution

Using the source-vendored Pi 0.82.1 runtime, with
ModelRuntime.create({ allowModelNetwork: false }), the exact lookup returned:

~~~json
{
  "provider": "anthropic",
  "id": "claude-sonnet-4-6",
  "api": "anthropic-messages",
  "reasoning": true,
  "input": ["text", "image"],
  "compat": {
    "forceAdaptiveThinking": true,
    "supportsStrictTools": true
  },
  "thinkingLevelMap": {
    "max": "max"
  }
}
~~~

The lookup used an isolated PI_CODING_AGENT_DIR, PI_OFFLINE=1, and
allowModelNetwork: false. It did not read operator credentials or contact a
provider. The exact registry resolution passed before implementation edits and
was repeated by the focused post-edit regression suite.

## 10. Provider-free session compatibility

The same canonical Pi runtime created a session for the replacement model with
the wrapper's configured posture:

~~~text
tools=["read","bash","edit","write"]
requested_thinking=medium
effective_thinking=medium
api=anthropic-messages
provider_transport_started=false
~~~

The actual session reported the exact four active tool names and included
medium in its available thinking levels. No prompt was issued. The durable
regression is
test_reconciled_anthropic_model_supports_canonical_session_provider_free.

## 11. Active coding-default inventory

The repaired active inventory is:

| Surface | Canonical source of truth | Repaired value |
| --- | --- | --- |
| wrapper | DEFAULT_ANTHROPIC_MODEL | claude-sonnet-4-6 |
| Campaign Runner profiles | DEFAULT_MODEL | claude-sonnet-4-6 |
| Runner CLI | imported DEFAULT_MODEL | claude-sonnet-4-6 |
| Guardian readiness | DEFAULT_PI_PROVIDER / DEFAULT_PI_MODEL | anthropic / claude-sonnet-4-6 |
| legacy adapter | imported DEFAULT_PI_MODEL | claude-sonnet-4-6 |
| worker Compose service | PI_PROVIDER / PI_MODEL | anthropic / claude-sonnet-4-6 |

The active-surface stale-ID command returned no matches. Therefore:

~~~text
ACTIVE_CODING_RUNTIME_STALE_ID_COUNT=0
~~~

## 12. Implementation changes

Changed in the implementation branch:

- codex_runner/src/agent-wrapper.js: introduced one local Anthropic default,
  routed generic Sonnet aliases and non-authorized Sonnet matching through it,
  and updated user-facing model text.
- codex_runner/src/profile.py: introduced DEFAULT_MODEL and applied it to
  active Sonnet/default profiles and dataclass/deserialization fallbacks.
- codex_runner/src/runner_cli.py: imported and reused DEFAULT_MODEL for the
  direct agent, audit, and run fallbacks; the explicit Opus compile fallback is
  unchanged.
- guardian/agents/pi_readiness.py: changed only the default model value.
- guardian/agents/adapters/pi_codex_runner.py: imported the readiness default;
  authorized identity injection is unchanged.
- docker-compose.yml: changed only the coding-worker PI_MODEL default.
- docs/architecture/config-and-ops.md and
  docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md: aligned source-Compose
  default documentation and stated the pinned-registry resolution boundary.

No file beneath codex_runner/vendor/pi-coding-agent/ changed:

~~~text
VENDORED_PI_MODEL_REGISTRY_MUTATION_COUNT=0
~~~

## 13. Guardian-authorized exact-identity invariant

requireGuardianAuthorizedIdentity() remains the required source of the
authorized provider, model, harness, and harness version. The authorized path
continues to call getModel(identity.providerId, identity.modelId) with the
exact supplied values. It does not pass authorized model IDs through generic
aliases or the non-authorized partial-match list.

The replacement authorized-readiness regression established:

~~~text
actual_provider_id=anthropic
actual_model_id=claude-sonnet-4-6
actual_harness_id=pi-coding-agent
actual_harness_version=0.82.1
runtime_identity_established=true
session_initialized=false
provider_request_started=false
~~~

~~~text
GUARDIAN_AUTHORIZED_MODEL_IDENTITY_EXACT=PASS
~~~

## 14. Default-coherence regression

tests/ops/test_worker_coding_pi_runtime_contract.py now imports the Python
readiness and adapter defaults, loads the source Campaign Runner profile and
CLI modules, checks default/fast/review/profile fallbacks, verifies the
wrapper's local constant and aliases, and checks the Compose provider/model
pair. It also behaviorally covers the run_pi_agent, cmd_audit, and cmd_run
fallback paths.

~~~text
ANTHROPIC_DEFAULT_COHERENCE=PASS
~~~

## 15. Authorized replacement-resolution regression

The exact authorized-readiness regression invokes the real source-relative
wrapper with a disposable empty HOME, isolated PI_CODING_AGENT_DIR, PI_OFFLINE=1,
and no inherited environment or credentials. With
anthropic / claude-sonnet-4-6 / pi-coding-agent@0.82.1, it established exact
runtime identity before terminating at the expected no-credential boundary:

~~~text
failure_class=oauth_auth_unavailable
failure_stage=oauth_readiness
session_initialized=false
provider_request_started=false
~~~

~~~text
ANTHROPIC_AUTHORIZED_MODEL_RESOLUTION=PASS_PROVIDER_FREE
~~~

## 16. Obsolete-ID fail-closed regression

The same isolated authorized-readiness path was run with the exact obsolete
model ID as input. Pi did not expose that ID in the current Anthropic catalog,
and the wrapper returned before auth/session/provider activity:

~~~text
failure_class=model_unresolved
failure_stage=model_resolution
runtime_identity_established=false
actual_runtime_identity=null
session_initialized=false
provider_request_started=false
~~~

The obsolete ID is intentionally retained as a test input so a future registry
change cannot silently turn exact identity into a replacement alias. Its one
working-tree occurrence is a fixture_or_example for this fail-closed
regression, not an active coding default.

~~~text
OBSOLETE_ANTHROPIC_ID_SILENT_REMAP=false
~~~

## 17. Remaining stale-ID occurrence classification

The old string was not mass-replaced. Remaining repository occurrences are
classified as follows:

| Classification | Remaining surfaces |
| --- | --- |
| fixture_or_example | intentional obsolete-ID input in tests/ops/test_worker_coding_pi_runtime_contract.py |
| historical | docs/tasks/TASK-2026-05-01-001_pi_adapter.md, docs/tasks/TASK-2026-05-01-002_pi_tool_wrapper.md, and prior proof/examples outside the active default surface |
| unrelated_product_surface | Persona Studio store/tests and persona-profile runtime tests |
| migration | the persona-profile database migration default |
| vendored_reference | Pi vendor documentation, changelog, SDK examples, and provider SDK type/reference material |

None of these occurrences is an active coding-worker/config/operator default.

## 18. Provider/network/credential isolation

~~~text
PROVIDER_BACKED_INVOCATION_COUNT=0
LIVE_EXECUTOR_CALL_COUNT=0
OAUTH_LOGIN_LOGOUT_COUNT=0
OPERATOR_CREDENTIAL_STORE_ACCESS_COUNT=0
~~~

The provider-free probes used empty disposable homes, a disposable Pi agent
directory, PI_OFFLINE=1, and allowModelNetwork: false. They did not inspect the
operator auth store, use an API key, run /login, prompt a model, perform
DNS/socket/HTTP model transport, or invoke the Campaign Engine live Executor.

## 19. Validation

Node syntax:

~~~text
node --check codex_runner/src/agent-wrapper.js                         PASS
node --check codex_runner/src/assistant-telemetry.js                    PASS
~~~

Focused readiness/default suite:

~~~text
pytest -v guardian/tests/agents/test_pi_readiness.py tests/ops/test_worker_coding_pi_runtime_contract.py
37 passed, 8 warnings
~~~

Authorized Pi / CE-L1 regression suite:

~~~text
pytest -v tests/ops/test_pi_assistant_response_telemetry.py tests/pi/test_pi_live_invocation.py tests/pi/test_pi_authorized_failure_diagnostics.py codex_runner/tests/test_campaign_engine_live_executor.py
140 passed
~~~

Combined deterministic seam:

~~~text
pytest -v guardian/tests/agents/test_pi_readiness.py tests/ops/test_worker_coding_pi_runtime_contract.py tests/ops/test_pi_assistant_response_telemetry.py tests/pi/test_pi_live_invocation.py tests/pi/test_pi_authorized_failure_diagnostics.py codex_runner/tests/test_campaign_engine_live_executor.py
177 passed, 8 warnings
~~~

Additional repository checks:

~~~text
active stale-ID grep                                             PASS (no matches)
replacement-ID inventory                                         PASS
git diff --check                                                  PASS
vendor diff from captured main                                   PASS (empty)
~~~

The focused and combined pytest commands used the qualified local Python
runtime /opt/homebrew/Caskroom/miniconda/base/bin/python. The default system
Python could not collect Guardian tests because bcrypt was not installed; no
repository or environment mutation was used to bypass that condition.

## 20. What is proven

- Captured origin/main is the task base and the authoring anchor is an
  ancestor.
- The bounded CE-L1 seam had no material pre-task drift.
- claude-sonnet-4-6 resolves exactly from the pinned Pi 0.82.1 catalog as
  anthropic-messages.
- The replacement supports the canonical coding tool names and medium thinking
  without provider transport.
- Wrapper, profiles, CLI fallback, readiness, legacy fallback, Compose, and
  operator/config documentation agree on the active default.
- Guardian-authorized exact identity remains exact, and the obsolete exact ID
  fails closed instead of remapping.
- Focused and combined deterministic tests pass, with no vendor mutation and
  no provider/credential activity.

## 21. What remains unresolved

- No Anthropic inference, tool request, provider response, or live Executor
  result was observed in this task.
- Credential presence/validity and provider reachability remain unproven.
- CE-L1 still lacks the canonical live Executor result, durable terminal
  result, and source-thread readback required for closure.
- No canonical landing, push, merge, release, or Beta-support claim was made.

## 22. CE-L1 decision

~~~text
CE-L1=OPEN
LIVE_EXECUTOR_PROVEN_CANONICAL=NOT_EMITTED
SINGLE_TASK_SUPERVISED_USABLE=NOT_EMITTED
ANTHROPIC_PI_TOOLCALL_REQUEST_OBSERVED=NOT_RETAINED
~~~

This task repairs the prerequisite identity seam only. It does not authorize
or perform the next live control.

## 23. Next dependency

~~~text
SOL_ATTEMPT_BUDGET=SPENT
LUNA_COMPARISON_BUDGET=SPENT
SPARK_COMPARISON_BUDGET=SPENT
ANTHROPIC_CONTROL_BUDGET=SPENT
NEXT_TASK_REQUIRED=land this Anthropic default-model reconciliation onto then-current canonical main with a bounded CE-L1 drift check; do not authorize a live control yet
~~~

The local implementation commit, exact changed-file list, and post-capture
remote movement are reported in the task closeout. Canonical landing remains a
separate follow-up.
