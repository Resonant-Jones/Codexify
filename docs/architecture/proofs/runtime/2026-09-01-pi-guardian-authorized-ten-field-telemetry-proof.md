# 2026-09-01 Pi Guardian-authorized ten-field telemetry repair — PASS_QUALIFIED_LOCAL

## Result

```
RESULT                                = PASS
GUARDIAN_AUTHORIZED_TEN_FIELD_TELEMETRY = PASS_QUALIFIED_LOCAL
AUTHORIZED_WRAPPER_STDOUT_FRAMING_DEFECT = PROVEN_AND_REPAIRED_CANONICAL
PI_WRAPPER_PROTOCOL_FIXTURE_REPRODUCIBILITY = PASS_TRACKED_ONLY_CANONICAL
LIVE_WRAPPER_PROTOCOL_CAUSE              = UNRESOLVED
CAUSAL_CLASSIFICATION                     = UNRESOLVED_ASSISTANT_TOOL_CALL_EMISSION_BOUNDARY
CE-L1                                     = OPEN
LIVE_EXECUTOR_PROVEN                      = NOT_EMITTED
SINGLE_TASK_SUPERVISED_USABLE             = NOT_EMITTED
REAL_PROVIDER_CALL_COUNT                  = 0
CAMPAIGN_LIVE_RAIL_CALL_COUNT             = 0
OAUTH_READINESS_COUNT                     = 0
OPERATOR_CREDENTIAL_STORE_ACCESS_COUNT    = 0
TELEMETRY_FIELD_ADDITIONS                 = 0
TELEMETRY_FIELD_REMOVALS                  = 0
PYTHON_DOWNSTREAM_PROPAGATION_CHANGES     = none
```

## Scope

This slice wires the canonical 10-field bounded telemetry surface into
the live `guardian-authorized-task` path.  The accepted architecture
already required 10 fields; the previous canonical wrapper emitted
only 6 because the live producer had not finished wiring the existing
`observeAssistantMessageEvent`, `observeFinalAssistantMessages`, and
`createToolTelemetry` helpers.  The repair aligns implementation with
the already-accepted schema.

No telemetry schema change.  No provider/model/tool/prompt/authority
change.  No persistent-state change.  No Campaign schema change.

## Pre-repair state (provider-free, exact)

The canonical `agent-wrapper.js` `guardian-authorized-task` path
initialized the live accumulator manually with only:

```
{
  effective_tool_names,
  write_tool_available,
  tool_execution_start_count: 0,
  tool_execution_end_count: 0,
  executed_tool_names: [],
  assistant_tool_call_count: 0,
}
```

The four assistant-response fields were omitted:

- `assistant_message_count`
- `assistant_content_block_types`
- `assistant_message_event_types`
- `assistant_tool_call_event_count`

```
AUTHORIZED_WRAPPER_TELEMETRY_FIELD_COUNT_BEFORE = 6
```

## Adapter 10-field requirement (canonical)

`PiCodexRunnerAdapter.execute_authorized(...)` invokes:

```
self._parse_result(
    result,
    require_runtime_identity=True,
    require_tool_telemetry=True,
)
```

The adapter's `_parse_tool_telemetry(...)` defines a 10-position
contract (positions are fixed):

```
1.  effective_tool_names
2.  write_tool_available
3.  tool_execution_start_count
4.  tool_execution_end_count
5.  executed_tool_names
6.  assistant_tool_call_count
7.  assistant_message_count
8.  assistant_content_block_types
9.  assistant_message_event_types
10. assistant_tool_call_event_count
```

`_is_valid_tool_telemetry(...)` rejects missing assistant-response
fields for a successful live-authorized result.  Pre-repair the
real `execute_authorized` path with a 6-field payload returned:

```
failure_classification = wrapper_protocol_failed
failure_stage          = wrapper_protocol
```

```
AUTHORIZED_ADAPTER_REQUIRED_TELEMETRY_FIELD_COUNT = 10
```

## Repair (canonical)

1. Imported `createToolTelemetry` from `./assistant-telemetry.js`.
2. Replaced the manual 6-field accumulator literal with a
   `createToolTelemetry()` call.  The wrapper only sets the
   `effective_tool_names` and `write_tool_available` fields
   post-session-creation; the remaining 8 fields are owned by the
   helper.
3. Wired `observeAssistantMessageEvent(toolTelemetry, event)` inside
   the `session.subscribe` callback, **independently of
   `OPTIONS.verbose`** so evidence collection does not depend on
   logging mode.
4. Removed the manual `assistant_tool_call_count` scan over
   `session.agent.state.messages`.  Replaced with
   `observeFinalAssistantMessages(toolTelemetry, session)` after
   successful `session.prompt(...)`.  The helper owns
   `assistant_message_count`, `assistant_content_block_types`, and
   `assistant_tool_call_count`.
5. Preserved all existing tool execution counters
   (`tool_execution_start_count`, `tool_execution_end_count`,
   `executed_tool_names`).
6. Preserved `CONFIGURED_WRITABLE_TOOL_NAMES` and the
   `["read","bash","edit","write"]` writable set.
7. Preserved the failure-path emission through
   `emitAuthorizedFailure(...)` and `emitAuthorizedSuccess(...)` —
   the only change is that the emitted `tool_telemetry` object now
   contains all 10 fields (because the helper initializes all 10).
8. Preserved the canonical final-non-empty-line stdout framing
   established in commit `e9125a286`.

```
createToolTelemetry() live wiring result       = PASS
Assistant event observer live wiring result   = PASS
Final assistant observer live wiring result    = PASS
Manual duplicate assistant scan removed       = true
Tool-activation semantics preserved           = PASS
Provider-failure ten-field-shape result        = PASS
Tool-activation-failure ten-field-shape result = PASS
Authorized outer result-schema change          = none
```

## Tracked fake-Pi fixture extension

The disposable fake Pi 0.82.1 package under
`tests/pi/fixtures/fake_pi_package/source/index.js` adds one
provider-free behavior mode:

```
PI_FAKE_I_BEHAVIOR = assistant-tool-call
```

The behavior mode emits the bounded Pi 0.82.1 event sequence the live
wrapper's observers consume:

```
{type: "message_update", assistantMessageEvent: {type: "toolcall_start"}}
{type: "tool_execution_start", toolName: "write"}
{type: "tool_execution_end",   toolName: "write"}
{type: "message_update", assistantMessageEvent: {type: "toolcall_end"}}
```

and sets the final session state to one assistant message with one
`toolCall` content block whose argument is secret-shaped
(`"secret-not-returned"`).  The bounded observer MUST NOT return
this value.

The default (no `PI_FAKE_I_BEHAVIOR`) path remains the prior zero-event
success path so existing framing tests are semantically unchanged.

## Real-wrapper post-repair (provider-free, exact)

Zero-event success path (canonical default):

```
effective_tool_names            = ("read","bash","edit","write")
write_tool_available            = true
tool_execution_start_count      = 0
tool_execution_end_count        = 0
executed_tool_names             = ()
assistant_tool_call_count       = 0
assistant_message_count         = 0
assistant_content_block_types   = ()
assistant_message_event_types   = ()
assistant_tool_call_event_count = 0
```

Sentinel lifecycle (one toolcall_start, one tool_execution_start
`write`, one tool_execution_end `write`, one toolcall_end, one final
`toolCall` block):

```
effective_tool_names            = ("read","bash","edit","write")
write_tool_available            = true
tool_execution_start_count      = 1
tool_execution_end_count        = 1
executed_tool_names             = ("write",)
assistant_tool_call_count       = 1
assistant_message_count         = 1
assistant_content_block_types   = ("toolCall",)
assistant_message_event_types   = ("toolcall_start","toolcall_end")
assistant_tool_call_event_count = 2
```

```
REAL_AUTHORIZED_WRAPPER_TEN_FIELD_PROTOCOL  = PASS
REAL_AUTHORIZED_ASSISTANT_TELEMETRY         = PASS
ASSISTANT_TELEMETRY_CONTENT_REDACTION      = PASS  (secret-not-returned never appears in envelope)
```

## Regression results

- Missing `assistant_message_count` in an otherwise valid authorized
  success frame still returns `wrapper_protocol_failed` /
  `wrapper_protocol` (10-field strictness preserved).
- Real `execute_authorized` zero-event success: 10 fields present,
  `status="ok"`, identity preserved.
- Real `execute_authorized` sentinel success: 10 fields exact-match
  to SENTINEL_EXPECTED.
- Noisy stdout framing regression: `test_real_wrapper_noisy_stdout_success_protocol`
  passes.
- Bounded failure framing regression: `test_real_wrapper_noisy_stdout_failure_protocol`
  passes.
- Runtime identity strictness: `MISSING_RUNTIME_IDENTITY_FAIL_CLOSED`
  passes.
- Nonzero-exit precedence: `NONZERO_RETURN_CODE_PRECEDENCE` passes.

## Network / credential / tool posture

```
fake HTTP_CALL_COUNT                  = 0
fake DNS_CALL_COUNT                   = 0
fake SOCKET_CALL_COUNT                = 0
fake PI_PROVIDER                      = "openai-codex"
fake PI_MODEL                         = "gpt-5.6-sol"
fake PI_HARNESS_ID                    = "pi-coding-agent"
fake PI_HARNESS_VERSION               = "0.82.1"
fake getActiveToolNames               = ("read","bash","edit","write")
PROVIDER_BACKED_INVOCATION_COUNT      = 0
CAMPAIGN_LIVE_RAIL_COUNT              = 0
OAUTH_READINESS_COUNT                 = 0
OPERATOR_CREDENTIAL_STORE_ACCESS_COUNT = 0
disposable HOME                       = <tmp_path>/home  (per-test)
PI_CODING_AGENT_PACKAGE_ROOT          = <materialized tmp_path>/fake_pi_package  (per-test)
```

## Validation

```
$ python -m pytest -v tests/pi/test_pi_authorized_failure_diagnostics.py
collected 56 items
...................................                                  [100%]
======================== 56 passed, 1 warning in 0.58s =========================

$ python -m pytest -v tests/ops/test_pi_assistant_response_telemetry.py
collected 7 items
.......                                                                 [100%]
======================== 7 passed, 1 warning in 0.05s =========================

$ python -m pytest tests/ops/test_worker_coding_pi_runtime_contract.py \
                    tests/ops/test_pi_assistant_response_telemetry.py \
                    tests/pi/test_pi_live_invocation.py \
                    tests/pi/test_pi_authorized_failure_diagnostics.py \
                    codex_runner/tests/test_campaign_engine_live_executor.py
........................................................................ [ 90%]
................                                                         [100%]
======================== 160 passed, 1 warning in 7.24s =========================
```

Pre-task baseline after PR #778: `150 passed`.  Fresh count after
repair: `160 passed` (7 new assistant-telemetry wrapper source
regressions + 3 new ten-field framing tests).

## Node syntax validation

```
$ node --check codex_runner/src/agent-wrapper.js        = exit 0
$ node --check codex_runner/src/assistant-telemetry.js  = exit 0
```

## Docs

```
$ python scripts/validate_docs.py
Docs validation passed: required architecture docs, README links, and source headings verified.

$ python scripts/check_diagram_freshness.py
Diagram freshness check passed: no runtime source drift detected and matrix decisions are valid.
```

## Tracked file scope (canonical)

```
codex_runner/src/agent-wrapper.js                          (M)
tests/ops/test_pi_assistant_response_telemetry.py         (M; +7 pytest regressions)
tests/pi/test_pi_authorized_failure_diagnostics.py         (M; +3 ten-field tests + docstring update)
tests/pi/fixtures/fake_pi_package/source/index.js          (M; +assistant-tool-call behavior)
docs/architecture/proofs/runtime/2026-09-01-pi-guardian-authorized-ten-field-telemetry-proof.md (A; this proof)
```

No other tracked file changed.  No runtime source edit to
`codex_runner/src/assistant-telemetry.js` (the helper is unchanged).
No edit to `guardian/agents/adapters/pi_codex_runner.py`
(adapter 10-field parsing unchanged).  No edit to `guardian/pi/invocation.py`
or any Campaign Engine surface.  No edit to the historical CE-L1
proof ledger.  No edit to the disposable CE-L1 driver.

## What this slice proves and does not prove

PROVES:

- The canonical 10-field telemetry shape is now produced by the
  live `guardian-authorized-task` path.
- The real `execute_authorized` provider-free end-to-end path
  accepts the wrapper's success frame (no longer rejected at
  `wrapper_protocol_failed`).
- The 4 missing assistant-response fields are populated by the
  existing canonical helpers (`createToolTelemetry`,
  `observeAssistantMessageEvent`,
  `observeFinalAssistantMessages`).
- Secret-shaped tool arguments are not retained anywhere in the
  bounded envelope.
- The 10-field strictness contract is preserved (missing field
  still fails closed).
- The canonical framing repair and the tracked-only fixture
  reproducibility are both preserved.

DOES NOT PROVE:

- That the wiring makes a real provider call succeed (no live rail
  in this slice; LIVE_WRAPPER_PROTOCOL_CAUSE=UNRESOLVED).
- CE-L1 closure (CE-L1=OPEN; LIVE_EXECUTOR_PROVEN=NOT_EMITTED).
- The readiness-helper `await` question (parked; not admitted).
- A schema-version change.  The 10-field shape is unchanged.


# 2026-09-01 canonical landing preflight — PASS

## Result

```
RESULT                                = PASS
GUARDIAN_AUTHORIZED_TEN_FIELD_TELEMETRY = PASS_QUALIFIED_LOCAL
AUTHORIZED_WRAPPER_STDOUT_FRAMING_DEFECT = PROVEN_AND_REPAIRED_CANONICAL
PI_WRAPPER_PROTOCOL_FIXTURE_REPRODUCIBILITY = PASS_TRACKED_ONLY_CANONICAL
LIVE_WRAPPER_PROTOCOL_CAUSE              = UNRESOLVED
CAUSAL_CLASSIFICATION                     = UNRESOLVED_ASSISTANT_TOOL_CALL_EMISSION_BOUNDARY
CE-L1                                     = OPEN
LIVE_EXECUTOR_PROVEN                      = NOT_EMITTED
CANONICAL_LANDING_CANDIDATE               = PASS
```

## Scope

This is a landing-preflight receipt only.  No new implementation edit
is authorized.  The locally-qualified Guardian-authorized ten-field
telemetry repair is committed as:

```
c32f84f12395a157d59b6e68b635677bd5a8bec3  Complete Pi authorized ten-field telemetry
```

with parent:

```
96a9cc3de79cbefbe14b78c64fabedb1f3b4d9ef
```

## Pre-push identity

```
LANDING_BASE_CHECK                       = PASS  (origin/main == 96a9cc3de79cbefbe14b78c64fabedb1f3b4d9ef)
MAIN_MOVEMENT_BEFORE_PUSH                = NONE
RUNTIME_SEAM_DRIFT_RESULT                = ORTHOGONAL
AUTHORITATIVE_IMPLEMENTATION_SHA         = c32f84f12395a157d59b6e68b635677bd5a8bec3
IMPLEMENTATION_BASE                      = PASS  (merge-base == 96a9cc3de79cbefbe14b78c64fabedb1f3b4d9ef)
IMPLEMENTATION_SUBJECT                    = "Complete Pi authorized ten-field telemetry"
TRACKED_WORKTREE_STATUS                  = clean  (LFS package.json ghost "M" only)
```

## Candidate changed-file list (canonical landing surface)

```
git diff 96a9cc3de79cbefbe14b78c64fabedb1f3b4d9ef..c32f84f12395a157d59b6e68b635677bd5a8bec3
--name-status

M  codex_runner/src/agent-wrapper.js
A  docs/architecture/proofs/runtime/2026-09-01-pi-guardian-authorized-ten-field-telemetry-proof.md
M  tests/ops/test_pi_assistant_response_telemetry.py
M  tests/pi/fixtures/fake_pi_package/source/index.js
M  tests/pi/test_pi_authorized_failure_diagnostics.py
```

Exactly the intended five-file surface.  No unrelated dirty content.
No ignored `dist/index.js` appears in the PR diff.

## Telemetry field count

```
TELEMETRY_FIELD_COUNT = 10
```

## Exact telemetry names

```
effective_tool_names
write_tool_available
tool_execution_start_count
tool_execution_end_count
executed_tool_names
assistant_tool_call_count
assistant_message_count
assistant_content_block_types
assistant_message_event_types
assistant_tool_call_event_count
```

## Telemetry source code readback (canonical-candidate)

- `_parse_authorized_stdout_frame` import and `createToolTelemetry()`
  call present in `codex_runner/src/agent-wrapper.js`.
- `createToolTelemetry()` live wiring result = PASS.
- Assistant event observer wired in `session.subscribe`:
  `observeAssistantMessageEvent(toolTelemetry, event)`.
- Final assistant observer wired after successful prompt:
  `observeFinalAssistantMessages(toolTelemetry, session)`.
- Manual independent final assistant scan removed: the previous
  for-of-finalMessages loop that bumped assistant_tool_call_count
  outside the helper is no longer present.
- Existing tool-execution observations preserved (start, end, executed
  names).

## Failure-path ten-field result

Both bounded failure paths emit a complete ten-field object:

- Tool-activation failure: `wrapper_protocol_failed / tool_activation`
  carries a complete ten-field accumulator.
- Provider/request failure: `provider_request_failed / provider_request`
  carries a complete ten-field accumulator (partial/zero values are
  permitted; missing fields are not).

## Outer result schema

The authorized outer schema is unchanged.  Only the contents of
`tool_telemetry` are now complete:

```
status
summary
actual_runtime_identity
execution_result
session_initialized
provider_request_started
tool_telemetry
```

## Stdout framing regression

`AUTHORIZED_STDOUT_FRAMING_REGRESSION = PASS`

The canonical final-non-empty-line framing from PR #778 is preserved.
`_parse_authorized_stdout_frame` is unchanged; the adapter 10-field
parsing is unchanged.

## Runtime identity strictness

`MISSING_RUNTIME_IDENTITY_FAIL_CLOSED = PASS`

A valid final JSON object without `actual_runtime_identity` under
`require_runtime_identity=True` still returns `actual_identity_missing`.

## Missing-field fail-closed

`REMOVE_ASSISTANT_FIELD_FAIL_CLOSED = PASS`

Removing `assistant_message_count` from an otherwise valid
authorized success frame returns
`failure_classification="wrapper_protocol_failed"`,
`failure_stage="wrapper_protocol"`.

## Provider / model / tool posture

```
provider            = openai-codex
model               = gpt-5.6-sol
harness_id          = pi-coding-agent
harness_version     = 0.82.1
configured_tools    = ["read","bash","edit","write"]
fake_pi_provider    = "openai-codex"
fake_pi_model       = "gpt-5.6-sol"
fake_pi_harness_id  = "pi-coding-agent"
fake_pi_harness_v   = "0.82.1"
```

No fallback or substitution.

## Tracked fake fixture

- Tracked fake Pi source path:
  `tests/pi/fixtures/fake_pi_package/source/index.js`
- Materialized fake package root:
  `<pytest tmp_path>/fake_pi_package`
- `PI_CODING_AGENT_PACKAGE_ROOT` always points at the materialized
  package, never at the in-repository fixture directory.
- Repository ignored `dist/index.js` remains untracked and is never
  required.

## Clean tracked-only integration

A fresh detached worktree was created at exactly
`c32f84f12395a157d59b6e68b635677bd5a8bec3`:

```
clean_worktree_repository_dist_absent = true
clean_worktree_noisy_success          = PASS
clean_worktree_noisy_failure          = PASS
clean_worktree_zero_event_success     = PASS
clean_worktree_sentinel_lifecycle      = PASS
clean_worktree_missing_field_closed   = PASS
TRACKED_ONLY_TEN_FIELD_AUTHORIZED_PROTOCOL = PASS
```

## Provider-free posture

```
PROVIDER_BACKED_INVOCATION_COUNT      = 0
CAMPAIGN_LIVE_RAIL_COUNT              = 0
OAUTH_READINESS_COUNT                 = 0
OPERATOR_CREDENTIAL_STORE_ACCESS_COUNT = 0
```

## Validation (pre-push)

```
node --check codex_runner/src/agent-wrapper.js        = exit 0
node --check codex_runner/src/assistant-telemetry.js  = exit 0
pytest -v tests/ops/test_pi_assistant_response_telemetry.py
    collected 7 items
    7 passed, 1 warning
pytest -v tests/pi/test_pi_authorized_failure_diagnostics.py
    collected 56 items
    56 passed, 1 warning
pytest -v tests/pi/test_pi_live_invocation.py
    collected 3 items
    3 passed, 1 warning
pytest -v <complete CE-L1 deterministic suite>
    160 passed, 1 warning
PYTHON=.venv/bin/python make docs
    Docs validation passed
    Diagram freshness check passed
git diff --check
    exit 0
```

## What this slice proves and does not prove

PROVES:

- The exact two-commit implementation lineage (this receipt is a
  child of the implementation commit) is locally complete,
  reproducible from tracked state, and free of hidden fixture
  dependencies.
- The runtime framing helper implements the canonical
  final-non-empty-line protocol-frame rule with all seven required
  semantics (unchanged from PR #778).
- The live wrapper now produces the complete ten-field telemetry
  surface.
- The real `execute_authorized` provider-free end-to-end path
  accepts the wrapper's success frame (no longer rejected at
  `wrapper_protocol_failed` due to missing telemetry).
- The 4 missing assistant-response fields are populated by the
  existing canonical helpers.
- Secret-shaped tool arguments are not retained anywhere in the
  bounded envelope.
- The 10-field strictness contract is preserved (missing field
  still fails closed).

DOES NOT PROVE:

- That the wiring makes a real provider call succeed (no live rail
  in this slice; LIVE_WRAPPER_PROTOCOL_CAUSE=UNRESOLVED).
- CE-L1 closure (CE-L1=OPEN; LIVE_EXECUTOR_PROVEN=NOT_EMITTED).
- A schema-version change.  The 10-field shape is unchanged.
- The readiness-helper `await` question (parked; not admitted).
