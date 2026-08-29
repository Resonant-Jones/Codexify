# Pi 0.82.1 Tool Activation and Bounded Telemetry Repair Proof — 2026-08-29

## Result

```text
TOOL_ACTIVATION_REPAIR=PASS_LOCAL
```

Canonical local PASS for this bounded repair slice.  The wrapper no
longer passes AgentTool objects into Pi 0.82.1's
`createAgentSession({ tools })`.  The maintained session now reports
`["read", "bash", "edit", "write"]` as the active tool set for writable
configurations, and `[]` for disabled configurations.  Bounded tool
telemetry flows from the wrapper through `PiHarnessRuntimeEvidence`,
`PiLiveInvocationOutcome`, `PiInvocationReceipt`,
`PiHarnessResult`, `LiveExecutorRunResult`, and `CampaignLiveExecutorError`
without args/results/content/credentials.  No new Pi failure token was
created; existing `wrapper_protocol_failed` is reused.

This repair does not yet re-run a live CE-L1 attempt and does not emit
`LIVE_EXECUTOR_PROVEN`.  CE-L1 remains OPEN.

## Summary

| Field | Value |
| --- | --- |
| Campaign | `CAMPAIGN-2026-08-26_001_CAMPAIGN_ENGINE_SUPERVISED_USABILITY_CLOSURE` |
| Gate | `CE-L1` |
| Base SHA | `e9ae721cef5112d6e644a1c50657152301aa1666` ("Record CE-L1 gpt-5.6-sol zero-mutation blocker (#775)") |
| Branch | `fix/pi-0821-tool-activation-telemetry` |
| Worktree | `/Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify-pi-0821-tool-activation-telemetry` |
| Canonical Pi coding-agent package/version | `@earendil-works/pi-coding-agent@0.82.1` |
| Canonical Pi AI package/version | `@earendil-works/pi-ai@0.82.1` |
| Selected provider | `openai-codex` |
| Selected model | `gpt-5.6-sol` (resolved locally, `allowModelNetwork: false`) |
| Selected harness | `pi-coding-agent@0.82.1` |
| Operator HOME preserved | true |
| `PI_CODING_AGENT_PACKAGE_ROOT` | NOT SET |
| `PI_CODING_AGENT_NODE_MODULES` | NOT SET |

## Pre-edit wrapper behavior (observed)

`codex_runner/src/agent-wrapper.js` previously computed:

```js
const tools = OPTIONS.disableTools
    ? []
    : createCodingTools(OPTIONS.cwd);
```

then passed `tools` (an array of `AgentTool` objects) into
`createAgentSession({ tools })`.  The vendored Pi 0.82.1 SDK treats the
`tools` option as a collection of tool-NAME strings.  Passing objects
produced an empty effective tool set even though the wrapper believed
coding tools were supplied.

## Pi 0.82.1 expected tool argument shape (observed)

`codex_runner/vendor/pi-coding-agent/dist/core/sdk.js`:

```js
const allowedToolNames = options.tools ?? (options.noTools === "all" ? [] : undefined);
const initialActiveToolNames = (options.tools ? [...options.tools] : options.noTools ? [] : defaultActiveToolNames)
    .filter((name) => !excludedToolNameSet?.has(name));
```

`options.tools` is iterated/spread directly; `setActiveToolsByName` then
keys a `Map<string, tool>` registry by string tool name.  Objects fail
`has(...)` and `registry.get(...)`, producing an empty effective tool
registry.

## `createCodingTools()` return posture

`codex_runner/vendor/pi-coding-agent/dist/core/tools/index.js` returns
4 `AgentTool` objects corresponding to `read`, `bash`, `edit`, `write`.
Each object has keys: `name`, `label`, `description`, `parameters`,
`constrainedSampling`, `prepareArguments`, `executionMode`, `execute`.

## Pre-edit object-tool probe result (non-inference)

```text
{
  "object_tool_effective_names": [],
  "name_tool_effective_names": ["read", "bash", "edit", "write"],
  "disabled_tool_effective_names": [],
  "provider_request_count": 0,
  "prompt_count": 0,
  "operator_credential_access_count": 0
}
```

Probe used a disposable HOME, a disposable auth JSON, the canonical
source-vendored Pi 0.82.1 runtime with `allowModelNetwork: false`, and
two consecutive `createAgentSession` calls — one passing
`createCodingTools(cwd)` and one passing `toolNames.map(t => t.name)`.
**No provider request was issued.** **No operator credential was
accessed.**

## Pre-edit name-tool probe result (non-inference)

```text
{
  "object_tool_effective_names": [],
  "name_tool_effective_names": ["read", "bash", "edit", "write"],
  "disabled_tool_effective_names": [],
  "provider_request_count": 0,
  "prompt_count": 0,
  "operator_credential_access_count": 0
}
```

The name-tool path produced exactly the intended four tools.

## Root-cause classification

```text
ROOT_CAUSE=
PI_0821_TOOL_OPTIONS_TYPE_MISMATCH_PROVEN
```

Meaning:

> Codexify supplied AgentTool objects to a Pi 0.82.1 API that interprets
> the `tools` option as tool-name strings, causing the effective built-in
> tool registry to reject the intended names.

## Exact wrapper repair

`codex_runner/src/agent-wrapper.js`:

- Removed the active dependency on `createCodingTools(OPTIONS.cwd)`.
- Added `const CONFIGURED_WRITABLE_TOOL_NAMES = ["read", "bash", "edit", "write"]`.
- Replaced `const tools = OPTIONS.disableTools ? [] : createCodingTools(OPTIONS.cwd);`
  with `const configuredToolNames = OPTIONS.disableTools ? [] : [...CONFIGURED_WRITABLE_TOOL_NAMES];`.
- `createAgentSession({ ... })` now passes `tools: configuredToolNames` (a `string[]`).
- Added `getEffectiveToolNames(session)` helper that prefers
  `session.getActiveToolNames()` and falls back to
  `session.agent.state.tools.map(t => t.name).filter(...)`.
- After session creation, reads `effectiveToolNames` from the session
  itself (NOT from the configured value) and computes
  `writeToolAvailable = effectiveToolNames.includes("write")`.
- For `guardianAuthorizedMode && OPTIONS.disableTools === false`
  where `writeToolAvailable !== true`, emits the existing bounded
  failure `wrapper_protocol_failed` at stage `tool_activation`
  BEFORE calling `session.prompt(...)`, with `session_initialized=true`
  and `provider_request_started=false`.  This is defense-in-depth
  against any future SDK compatibility regression.
- Subscribes to `session.subscribe((event) => ...)` and counts
  `tool_execution_start` (with tool name into `executed_tool_names`)
  and `tool_execution_end` events.
- After completion, walks `session.agent.state.messages` to count
  assistant content blocks whose `type` is exactly `"toolCall"`.
- Emits a bounded `tool_telemetry` field on the Guardian-authorized
  success payload (`status: "ok"`).
- Also includes `tool_telemetry` in `emitAuthorizedFailure` failure
  payloads (defense-in-depth visibility).

`loadPiSdk()` no longer returns `createCodingTools`.  `runAgent` no
longer destructures `createCodingTools`.

## Configured writable tool names

```text
["read", "bash", "edit", "write"]
```

## Post-repair effective tool names

```text
["read", "bash", "edit", "write"]
```

Verified by re-running the post-repair non-inference SDK probe:

```text
{
  "writable_tool_effective_names": ["read", "bash", "edit", "write"],
  "disabled_tool_effective_names": [],
  "provider_request_count": 0,
  "prompt_count": 0,
  "operator_credential_access_count": 0
}
```

## Disabled/read-only effective tool names

```text
[]
```

Verified by the same probe.

## `write_tool_available` result

```text
true
```

For writable configuration: `["read","bash","edit","write"]`
includes `"write"`.  For disabled configuration: `[]` excludes
`"write"` — the wrapper still sets `configuredToolNames = []` and never
calls `session.prompt(...)` (the live authorized-task path skips the
session entirely when `disableTools=true` would have set
`configuredToolNames=[]`; however the live authorized-task path
currently does not pass `PI_DISABLE_TOOLS=1` from Campaign Engine
side — the existing `PI_DISABLE_TOOLS` env-var contract is preserved
as-is).

## Writable missing-write fail-closed result

```text
failure_class=wrapper_protocol_failed
failure_stage=tool_activation
session_initialized=true
provider_request_started=false
tool_telemetry={
  effective_tool_names=[...],
  write_tool_available=false,
  ...
}
```

No new Pi failure token was created.

## Telemetry fields implemented

Six bounded fields flow through every layer:

- `effective_tool_names`: `string[]`
- `write_tool_available`: `bool`
- `tool_execution_start_count`: `int >= 0`
- `tool_execution_end_count`: `int >= 0`
- `executed_tool_names`: `string[]`
- `assistant_tool_call_count`: `int >= 0`

Propagation path:

```text
wrapper emitAuthorizedFailure / success payload
  -> PiCodexRunnerAdapter._parse_result  (require_tool_telemetry=True for live)
  -> PiHarnessRuntimeEvidence (added 6 fields)
  -> _run_with_pi_adapter (copies directly)
  -> invoke_guardian_authorized_pi success branch:
       PiLiveInvocationOutcome  (added 6 fields)
       PiInvocationReceipt.validation_metadata.tool_telemetry
       PiHarnessResult.validation_metadata.tool_telemetry
  -> run_live_executor_campaign success branch:
       LiveExecutorRunResult (added 6 fields)
       LiveExecutorRunResult.to_dict() exposes tool_telemetry
  -> run_live_executor_campaign failure branch (zero_mutation_executor_turn):
       CampaignLiveExecutorError (added 6 fields)
       CampaignLiveExecutorError.to_payload() exposes tool_telemetry
```

## Telemetry redaction result

The telemetry payload contains **only**:

- `string[]` tool names
- `bool`
- `int >= 0` counts

It does NOT contain:

- prompt text
- assistant text
- thinking content
- tool arguments
- tool-call IDs
- tool results
- partial results
- file contents
- provider payloads
- headers
- tokens
- account IDs
- credential metadata
- environment dumps

## Adapter telemetry parse result

`PiCodexRunnerAdapter._parse_result` accepts a new
`require_tool_telemetry: bool` parameter (default `False`).
`execute_authorized` calls it with `True`; `preflight_authorized`
keeps `False`.  `_parse_tool_telemetry` extracts and normalizes all
six fields.  `_is_valid_tool_telemetry` requires live-authorized-task
payloads to carry a complete, well-formed telemetry set; missing or
malformed fields cause `wrapper_protocol_failed` at stage
`wrapper_protocol`.

## Readiness-without-live-telemetry regression result

Existing readiness regressions in
`tests/pi/test_pi_authorized_failure_diagnostics.py` and `tests/pi/test_pi_live_invocation.py`
continue to pass without requiring tool telemetry.

## Guardian telemetry propagation result

`PiHarnessRuntimeEvidence` and `PiLiveInvocationOutcome` carry the six
fields directly via `_run_with_pi_adapter` (evidence source =
AgentRunEnvelope; Guardian does not recompute).  New regression
`test_tool_telemetry_propagates_into_pi_live_invocation_outcome` and
`test_tool_telemetry_into_receipt_validation_metadata` pass.

## Receipt telemetry result

`PiInvocationReceipt.validation_metadata["tool_telemetry"]` carries the
six fields on the successful Guardian-authorized live execution path.

## Harness Result telemetry result

`PiHarnessResult.validation_metadata["tool_telemetry"]` carries the
six fields on the successful Guardian-authorized live execution path.

## Campaign error telemetry result

`CampaignLiveExecutorError` constructor accepts the six fields and
`to_payload()` exposes them under `tool_telemetry`.  In particular,
`zero_mutation_executor_turn` carries all six fields so the operator
can distinguish absence-of-write-tool from
absence-of-tool-execution from absence-of-assistant-tool-call.

## Successful Campaign result telemetry result

`LiveExecutorRunResult` carries all six fields populated directly from
`PiLiveInvocationOutcome`.  `to_dict()` retains them.

## Zero-mutation causal-text correction result

The runtime error message for `zero_mutation_executor_turn` no longer
contains the inference `the model did not invoke the declared
file_write tool`.  The new message is:

> Harness success produced zero allowed-path mutation; inspect bounded
> tool availability and execution telemetry to classify the
> tool-execution boundary.

The associated issue text also no longer blames the model.

## Confirmation no new failure token

- No new canonical Pi failure class was introduced.
- Existing `wrapper_protocol_failed`, `tool_activation` stage (already
  defined in `_failure_stage_for_class`), and the existing
  `CampaignLiveExecutorError.failure_reason = "zero_mutation_executor_turn"`
  were reused.

## Confirmation no Campaign schema change

`codex_runner/schemas/campaign_engine/*.json` are unchanged.  The
runtime result carries telemetry via the `tool_telemetry` nested key
in `LiveExecutorRunResult.to_dict()` and `CampaignLiveExecutorError.to_payload()`.

## Confirmation no Pi vendor change

`codex_runner/vendor/pi-coding-agent/**` is unchanged.  No vendor
regeneration.

## Confirmation no provider/model routing change

Provider/model/routing logic is unchanged.

## Confirmation no live provider call

This task issued no live provider-backed prompt.  All probes are
non-inference; SDK probes use `allowModelNetwork: false`.

## Confirmation no credential readiness call

This task did not re-run `preflight_guardian_authorized_pi` against
operator credentials.  Canonical `CE-L1_OAUTH_PREREQUISITE=PASS`
remains the unchanged canonical prerequisite.

## Confirmation no operator credential access

This task never opened, listed, stat-ed, hashed, or inspected the
operator's credential file or path.

## Permanent source-vendor regression result

`tests/ops/test_worker_coding_pi_runtime_contract.py` adds:

- `test_maintained_pi_0821_treats_tools_as_name_strings`: probes the
  vendored 0.82.1 SDK with disposable HOME and synthetic OAuth
  fixture, asserts that writable sessions report `["read", "bash",
  "edit", "write"]` and disabled sessions report `[]`. **No prompt,
  no network, no operator credentials.**
- `test_active_runtime_passes_tool_name_strings_not_agenttool_objects`:
  source-grep ensures the wrapper no longer calls
  `createCodingTools(OPTIONS.cwd)` outside a comment, requires the
  exact writable tool-name string set in the source, and requires
  `getActiveToolNames` to be used for effective tool readback.

## Full deterministic test results

```text
tests/ops/test_worker_coding_pi_runtime_contract.py    15 passed
tests/pi/test_pi_live_invocation.py                    32 passed (includes 3 new telemetry regressions)
codex_runner/tests/test_campaign_engine_live_executor.py    33 passed (includes 2 new telemetry regressions)
```

## Post-repair no-inference SDK probe result

```text
writable_tool_effective_names=["read","bash","edit","write"]
disabled_tool_effective_names=[]
provider_request_count=0
prompt_count=0
operator_credential_access_count=0
```

## CE-L1 proof-ledger append-only result

The 2026-08-26 CE-L1 live Executor proof ledger
(`docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l1-live-executor-proof.md`)
received an append-only `## 2026-08-29 Pi 0.82.1 tool-activation diagnosis`
section.  The pre-edit SHA-256 (`1d7567ed82995dcc77cb86bdefb7cef1e6313718308378927233467886a8d389`)
matched the first 29541 bytes of the new proof after appending.
The historical 2026-08-26 BLOCKED sections were not modified.

## Detailed proof path

This file:
`docs/architecture/proofs/runtime/2026-08-29-pi-0821-tool-activation-telemetry-repair-proof.md`

## Docs result

```text
make docs → PASS
```

## `git diff --check` result

```text
clean
```

## Files changed

```text
M codex_runner/src/agent-wrapper.js
M guardian/agents/adapters/base.py
M guardian/agents/adapters/pi_codex_runner.py
M guardian/pi/invocation.py
M codex_runner/campaign_engine/errors.py
M codex_runner/campaign_engine/models.py
M codex_runner/campaign_engine/live_executor.py
M tests/ops/test_worker_coding_pi_runtime_contract.py
M tests/pi/test_pi_live_invocation.py
M codex_runner/tests/test_campaign_engine_live_executor.py
M docs/architecture/pi-invocation-boundary-contract.md
M docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l1-live-executor-proof.md
A docs/architecture/proofs/runtime/2026-08-29-pi-0821-tool-activation-telemetry-repair-proof.md
```

## ADR impact

```text
Aligned with existing ADR(s); no new ADR required
```

Governing contracts preserved: ADR-020, ADR-066, ADR-068, Pi Invocation
Boundary Contract, Agent Tool Loop Contract, Runtime Protocol Token
Contract.

## Invariants check

- Evidence did not outrun observation: the wrapper reads effective
  tool names from the actual session, not from the configured value.
- Historical proof truth remains immutable: 29541 bytes preserved
  byte-identically.
- Guardian remains execution authority.
- Pi remains execution substrate.
- Campaign Engine never self-authorizes.
- Tool exposure did not exceed the pre-existing intended coding set
  (`read`, `bash`, `edit`, `write` — not `grep`/`find`/`ls`).
- Read-only execution remains tool-disabled under the existing
  `PI_DISABLE_TOOLS` env-var contract.
- Tool telemetry grants no authority.
- Tool telemetry contains no prompt/content/arguments/results/secrets.
- Actual target readback remains authoritative for mutation.
- Exact runtime identity remains independent of tool telemetry.
- No provider/model substitution.
- No retry.
- No fallback.
- No rebinding.
- No live proof was spent before the deterministic repair is
  canonical.
- Release claims remain evidence-bounded.

## Proof results

22 of 22 spec §22 proof items satisfied.

## Documentation follow-through

- Updated only `docs/architecture/pi-invocation-boundary-contract.md`
  (added a single narrowly-bounded "Bounded Pi 0.82.1 tool
  observability" subsection under "Observability and Proof Surface").
- Appended only to
  `docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l1-live-executor-proof.md`
  (added a `## 2026-08-29 Pi 0.82.1 tool-activation diagnosis` section).
- Created only this proof:
  `docs/architecture/proofs/runtime/2026-08-29-pi-0821-tool-activation-telemetry-repair-proof.md`.
- Did not modify `docs/architecture/00-current-state.md`.
- Did not modify ADRs.
- Did not modify release claims.

## Local proof truth

```text
ROOT_CAUSE=
PI_0821_TOOL_OPTIONS_TYPE_MISMATCH_PROVEN

CE-L1_OAUTH_PREREQUISITE=PASS
CE-L1=OPEN
LIVE_EXECUTOR_PROVEN=NOT_EMITTED
SINGLE_TASK_SUPERVISED_USABLE=NOT_EMITTED
TOOL_ACTIVATION_REPAIR=PASS_LOCAL
```

## Next task

```text
land the Pi 0.82.1 tool-activation and bounded telemetry repair on remote main
```

Only after canonical landing may Axis authorize:

```text
re-run one CE-L1 gpt-5.6-sol disposable live Executor mutation proof
```
