# 2026-09-07 Pi Guardian Required-Tool Selection Repair Proof

Provider-free architectural-impact repair for Guardian-authorized CE-L1 Pi
execution. Implementation refinement only; no new ADR; no live provider
call; no vendored Pi mutation; no source commit on canonical main
(this proof is a local repair-commit receipt on a non-canonical branch).

## Anchors

- canonical base SHA: `bd5be33ef8762c81f6e0183388040e26a0919fa1`
- branch / worktree: `fix/guardian-required-tool-selection` /
  `/tmp/codexify-ce-l1-anthropic-selection-repair.worktree`
- selection-boundary prerequisite SHA: `f349e0bbd5e833381b5b47d765708bd3c9f355e5d758529defe2e70f3e0047da`
  (1468 B)
- spent v1 control: `/tmp/codexify-ce-l1-anthropic-preparation.SqEtaV` (immutable)
- spent v2 control: `/tmp/codexify-ce-l1-anthropic-control-v2.YpF78t` (immutable)

## Exact changed runtime seam

- `codex_runner/campaign_engine/models.py` — `LiveExecutorPreparation` gains
  the bounded `required_tool_name: str | None = None` field; the canonical
  `as_payload()` includes the field.
- `codex_runner/campaign_engine/live_executor.py` — defines
  `LIVE_EXECUTOR_REQUIRED_TOOL_NAME = "write"`; the prompt builder consumes
  `required_tool_name`; the preparation always sets
  `required_tool_name=LIVE_EXECUTOR_REQUIRED_TOOL_NAME`; the pre-execution
  drift check re-derives the prompt from
  `preparation.required_tool_name`; the invoker protocol passes
  `required_tool_name`; the zero-mutation failure carries bounded
  selection evidence into `to_payload()`; the result envelope carries
  bounded selection evidence.
- `codex_runner/campaign_engine/errors.py` — `CampaignLiveExecutorError`
  gains three optional selection fields; `to_payload()` exposes a
  separate `required_tool_selection` object when evidence exists and
  never places it inside the ten-field `tool_telemetry`.
- `guardian/pi/invocation.py` — `PiAuthorizedHarnessRequest`,
  `PiHarnessRuntimeEvidence`, and `PiLiveInvocationOutcome` each gain
  the three selection fields. `invoke_guardian_authorized_pi` accepts
  `required_tool_name`, normalizes it, rejects non-supported values
  before the runner, blocks when no writable grant is present, and
  copies selection evidence into the receipt and harness-result
  `validation_metadata` under a separate top-level key
  `required_tool_selection`. `preflight_guardian_authorized_pi` is
  selection-free.
- `guardian/agents/adapters/base.py` — `AgentRunEnvelope` gains three
  bounded optional selection fields.
- `guardian/agents/adapters/pi_codex_runner.py` — `execute_authorized`
  accepts `required_tool_name`; pops ambient
  `PI_GUARDIAN_REQUIRED_TOOL`; sets the env var only when the validated
  argument is non-null; rejects non-Anthropic providers before
  subprocess; parses the bounded wrapper selection object; and
  fails closed on missing, malformed, or `count != 1` selection
  evidence. `preflight_authorized` strips ambient selection and never
  propagates required-tool state. `execute` is semantically unchanged.
- `codex_runner/src/agent-wrapper.js` — reads
  `PI_GUARDIAN_REQUIRED_TOOL` ONLY for `guardian-authorized-task`;
  validates the required tool against the actual effective tool
  surface; installs a per-session `Agent.onPayload` hook that chains
  any preexisting hook, applies the projection on the FIRST provider
  request only, and leaves later turns untouched; fails closed with
  `wrapper_protocol_failed` / `tool_selection` when projection cannot
  be applied before the first provider request; emits bounded
  `required_tool_selection` terminal evidence (separate from the
  ten-field `tool_telemetry`).
- `codex_runner/src/guardian-required-tool-selection.js` — NEW pure
  provider-mechanics helper. No I/O, no environment, no network, no
  credentials, no global mutation. Returns a shallow-copied payload
  with `tool_choice` added. Fails closed on unsupported provider,
  unsupported required tool, missing required advertised tool,
  multiple case-insensitive matches, and conflicting preexisting
  choice.
- `tests/pi/fixtures/fake_pi_package/source/index.js` — extended
  provider-free synthetic payload that drives the wrapper's per-
  session `onPayload` once for the first turn and once for the
  continuation (proving the wrapper does not re-apply on the
  continuation), preserves the existing bounded one-write lifecycle,
  honors `PI_FAKE_ADVERTISE_CASING` (lowercase or claude-code), and
  returns the configured provider/model from `getAvailable()` so a
  Guardian-authorized call with `PI_PROVIDER=anthropic` is not
  rejected as `oauth_auth_unavailable`.

## Ownership decision

- declaration owner: **Campaign Engine**
  (`LIVE_EXECUTOR_REQUIRED_TOOL_NAME` constant; never parsed from
  prompt; never inferred by Guardian or Pi).
- permission authority owner: **Guardian** (existing `files.write`
  grant; required tool cannot broaden permissions; read-only
  invocations are blocked before the runner).
- provider-projection owner: **Pi-authorized wrapper** (per-session
  `Agent.onPayload`; first-turn only; never global).

## One-shot first-turn-only invariant

- `HARD_TOOL_SELECTION_SCOPE=FIRST_PROVIDER_TURN_ONLY`
- `HARD_TOOL_SELECTION_APPLICATION_COUNT=1` (success path)
- `POST_TOOL_CONTINUATION_HARD_SELECTION=false` (the wrapper's hook
  becomes a no-op after the first turn)
- `REQUIRED_TOOL_DOES_NOT_GRANT_PERMISSION=true`

## API-key-style mapping result

Pure helper:

```
$ node -e "import {applyGuardianRequiredToolSelection} from './codex_runner/src/guardian-required-tool-selection.js'; const out = applyGuardianRequiredToolSelection({providerId:'anthropic', requiredToolName:'write', payload:{model:'claude-sonnet-4-6', tools:[{name:'read'},{name:'bash'},{name:'edit'},{name:'write'}]}}); process.stdout.write(JSON.stringify(out.tool_choice));"
{"type":"tool","name":"write"}
```

Real vendored Anthropic request-builder (API-key branch,
`allowModelNetwork=false`, local sentinel, no network):

```
REQUEST_MODEL=claude-sonnet-4-6
REQUEST_TOOL_COUNT=4
REQUEST_TOOL_NAMES=["read","bash","edit","write"]
tool_choice={"type":"tool","name":"write"}
thinking.type=adaptive
output_config.effort=medium
provider_request_count=0
```

## OAuth-style mapping result

Real vendored Anthropic request-builder (OAuth branch):

```
REQUEST_TOOL_COUNT=4
REQUEST_TOOL_NAMES=["Read","Bash","Edit","Write"]
tool_choice={"type":"tool","name":"Write"}
thinking.type=adaptive
output_config.effort=medium
provider_request_count=0
```

The exact advertised casing is preserved in `tool_choice`; the
wrapper's bounded evidence records the canonical
`required_tool_name="write"`, not the outbound casing.

## Adaptive-thinking preservation

The pure helper does not modify `thinking` or `output_config`. The
real wrapper + fake Pi integration shows the wrapper's per-session
`onPayload` hook chains the previous hook and only adds or verifies
`tool_choice`. The synthetic Agent probe and the real wrapper run
both preserve `thinking.type=adaptive` and
`output_config.effort=medium` byte/structurally.

## Real wrapper + tracked fake Pi result

The real `codex_runner/src/agent-wrapper.js` was run end-to-end
against the materialized fake Pi 0.82.1 package with both
`PI_FAKE_ADVERTISE_CASING=lowercase` and `=claude-code`. The terminal
JSON carries the bounded `required_tool_selection` object and the
canonical ten-field `tool_telemetry`:

```json
{
  "status": "ok",
  "required_tool_selection": {
    "required_tool_name": "write",
    "hard_tool_selection_applied": true,
    "hard_tool_selection_application_count": 1
  },
  "tool_telemetry": {
    "effective_tool_names": ["read","bash","edit","write"],
    "write_tool_available": true,
    "tool_execution_start_count": 1,
    "tool_execution_end_count": 1,
    "executed_tool_names": ["write"],
    "assistant_tool_call_count": 1,
    "assistant_message_count": 1,
    "assistant_content_block_types": ["toolCall"],
    "assistant_message_event_types": ["toolcall_start","toolcall_end"],
    "assistant_tool_call_event_count": 2
  }
}
```

`provider_request_count=0` (the canonical `Agent.onPayload` is the
only path; no real network, no DNS, no socket).

## Guardian permission-bound result

`tests/pi/test_pi_live_invocation.py` proves:

- default invocation: `required_tool_name=None` reaches the runner
  exactly once.
- required `write` + granted `files.write`: exactly one runner call;
  `request.required_tool_name == "write"`.
- required `write` + read-only: blocked before runner;
  `runner_call_count == 0`; `failure_reason` in
  `{MUTATION_SCOPE_VIOLATION, READ_ONLY_VIOLATION}`.
- unsupported required tool: blocked before runner;
  `runner_call_count == 0`.
- required-tool constraint never changes the granted permission set.
- selection evidence copies into `PiLiveInvocationOutcome`,
  `receipt.validation_metadata`, and
  `harness_result.validation_metadata` under a separate top-level
  key (never inside the ten-field `tool_telemetry`).

## Selection evidence propagation summary

```
Campaign Engine ──► required_tool_name="write" (preparation)
  ▼
Live Executor ──► invoker(required_tool_name)
  ▼
Guardian ──► PiAuthorizedHarnessRequest(required_tool_name)
            receipt.validation_metadata["required_tool_selection"]
            harness_result.validation_metadata["required_tool_selection"]
            PiLiveInvocationOutcome(required_tool_name, applied, count)
  ▼
Pi adapter ──► subprocess env PI_GUARDIAN_REQUIRED_TOOL=write
  ▼
Pi wrapper ──► per-session Agent.onPayload
              applies on FIRST turn only
              bounded required_tool_selection terminal object
  ▼
Campaign Engine ──► LiveExecutorRunResult(required_tool_name, applied, count)
                   CampaignLiveExecutorError (zero-mutation) carries
                   required_tool_selection when evidence exists
```

## Ten-field telemetry non-regression

The canonical ten-field `tool_telemetry` object remains exactly ten
fields. Selection evidence is exposed as a separate
`required_tool_selection` object at every layer where it appears.
The fake Pi package still emits the bounded one-write lifecycle:
`toolcall_start`, `tool_execution_start(write)`,
`tool_execution_end(write)`, `toolcall_end`, plus one final assistant
`toolCall` content block.

## Vendored Pi invariant

`VENDORED_PI_MUTATION_COUNT=0`. The repair uses Pi's existing public
per-session `Agent.onPayload` surface. No vendored file under
`codex_runner/vendor/pi-coding-agent/` is modified.

## Counters

```
PROVIDER_BACKED_INVOCATION_COUNT=0
PROVIDER_REQUEST_COUNT=0
LIVE_EXECUTOR_RUN_CALL_COUNT=0
REAL_PROVIDER_SESSION_PROMPT_COUNT=0
PI_READINESS_PROBE_COUNT=0
OAUTH_LOGIN_COUNT=0
OAUTH_LOGOUT_COUNT=0
MANUAL_TOKEN_REFRESH_COUNT=0
DIRECT_OPERATOR_CREDENTIAL_INSPECTION_COUNT=0
OPERATOR_AUTH_FILE_READ_COUNT=0
OPERATOR_ENV_SECRET_READ_COUNT=0
RETRY_COUNT=0
FALLBACK_COUNT=0
PROVIDER_REBIND_COUNT=0
PROVIDER_SWITCH_COUNT=0
MODEL_SWITCH_COUNT=0
VENDORED_PI_MUTATION_COUNT=0
```

The wrapper subprocess runs the tracked fake Pi 0.82.1 package under
`HOME=<disposable tmp_path>` and
`PI_CODING_AGENT_PACKAGE_ROOT=<materialized tmp package>` so no
ambient credentials are inspected.

## Tests and validation

- `node --check codex_runner/src/agent-wrapper.js` PASS
- `node --check codex_runner/src/guardian-required-tool-selection.js` PASS
- `pytest -q tests/pi/test_pi_required_tool_selection.py` PASS (13 tests)
- `pytest -q tests/pi/test_pi_live_invocation.py` PASS (one pre-existing
  test_git_head_mutation_fails_closed failure is unrelated to this
  repair — it fails because the test environment's git config has no
  user.email/user.name configured; the same failure exists on
  canonical main)
- `pytest -q tests/pi/test_pi_authorized_failure_diagnostics.py` PASS
  (43 tests)
- `pytest -q codex_runner/tests/test_campaign_engine_live_executor.py`
  PASS (39 tests)
- `pytest -q tests/ops/test_worker_coding_pi_runtime_contract.py` PASS
  (legacy Pi execution unchanged)
- `pytest -q tests/ops/test_pi_assistant_response_telemetry.py` PASS
  (ten-field telemetry contract unchanged)
- `pytest -q tests/architecture` PASS (architecture contracts)
- `git diff --check` PASS
- `git diff --exit-code -- docs/architecture/completion_pipeline.md` PASS
  (no changes)

## Repair commit (local non-canonical)

- `REPAIR_COMMIT_SHA=7acca007b5523f3af3bf33a086a784f6758be74a`
- parent: `bd5be33ef8762c81f6e0183388040e26a0919fa1`
- one clean commit, no push, no merge.

## State preserved

```
SOL_ATTEMPT_BUDGET=SPENT
LUNA_COMPARISON_BUDGET=SPENT
SPARK_COMPARISON_BUDGET=SPENT
ANTHROPIC_CONTROL_BUDGET=SPENT
NEW_ANTHROPIC_CONTROL_BUDGET=SPENT
NEW_ANTHROPIC_REATTEMPT_BUDGET=SPENT
ORIGINAL_CONTROL_REUSABLE=false
ANTHROPIC_OPERATOR_AUTH_READINESS=PASS_PROVIDER_FREE
CE_L1_REQUIRED_MUTATION_SELECTION_GAP=REPAIRED_PROVIDER_FREE_LOCAL
CE-L1=OPEN
LIVE_EXECUTOR_PROVEN_CANONICAL=NOT_EMITTED
SINGLE_TASK_SUPERVISED_USABLE=NOT_EMITTED
SOURCE_THREAD_READBACK=NOT_PROVEN
NEW_SELECTION_REPAIR_LIVE_BUDGET=NOT_AUTHORIZED
```
