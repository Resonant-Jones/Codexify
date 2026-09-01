# 2026-09-01 Pi Authorized Wrapper Subprocess Protocol-Framing Repair and Provider-Free Qualification — PASS

## Result

```
RESULT                              = PASS (provider-free authorized wrapper stdout-framing repair + qualification)
AUTHORIZED_WRAPPER_STDOUT_FRAMING_DEFECT = PROVEN_AND_REPAIRED_PROVIDER_FREE
LIVE_WRAPPER_PROTOCOL_CAUSE              = UNRESOLVED (live raw stdout was not retained; repair is framing, not live causation)
CAUSAL_CLASSIFICATION                     = UNRESOLVED_ASSISTANT_TOOL_CALL_EMISSION_BOUNDARY (unchanged)
CAUSAL_SUB_CLASSIFICATION_RESOLVED        = envelope_campaign_engine_metadata_block_missing_in_driver (from prior slice; UNCHANGED here)
CAUSAL_SUB_CLASSIFICATION_NEW            = adapter_subprocess_wrapper_protocol_failure_after_authorization (still UNRESOLVED as live cause)
CE-L1                                     = OPEN (unchanged)
LIVE_EXECUTOR_PROVEN                      = NOT_EMITTED
SINGLE_TASK_SUPERVISED_USABLE             = NOT_EMITTED
REAL_PROVIDER_CALL_COUNT                  = 0
CAMPAIGN_LIVE_RAIL_CALL_COUNT             = 0
OAUTH_READINESS_COUNT                     = 0
OPERATOR_CREDENTIAL_STORE_ACCESS_COUNT    = 0
```

## Scope

This slice repaired the bounded authorized subprocess stdout framing so that
one terminal JSON protocol frame can coexist with preceding untrusted
dependency diagnostics. The repair is provider-free; it is bounded to the
adapter's response-parsing path and to the bounded failure-class taxonomy.
No provider, model, tool, prompt, persistence, or runtime-authority
semantics change.

The repair is implemented in the canonical wrapper-adapter
`guardian/agents/adapters/pi_codex_runner.py` via the new
`_parse_authorized_stdout_frame(...)` helper. The helper treats the
**final non-empty stdout line** as the authorized JSON result object.
Earlier lines are discarded, never persisted, and carry no authority.

## Repository identity

```
canonical_origin_main        = 77f1acf806a1aa5481defc2dbe298b6701157da6
canonical_origin_main_subject = "proof: migrate private preview database"
implementation_branch         = fix/pi-authorized-wrapper-protocol-framing
implementation_worktree       = /Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify-pi-authorized-wrapper-protocol-framing
pre_task_head_sha            = 77f1acf806a1aa5481defc2dbe298b6701157da6 (clean worktree from origin/main)
```

## Live motivating observation

The prior CE-L1 rail attempt (`7bd62a391` slice) crossed all previously
failing boundaries:

- Campaign preparation
- Guardian envelope validation
- Policy-decision validation
- Cross-object validation
- Campaign authorization-metadata re-derivation (RESOLVED by prior slice)
- Decision-allowed check
- Write-scope agreement
- Real Pi adapter invocation

The rail then received a non-passing adapter result classified:

```
failure_reason       = adapter_execution_failure
diagnostic_class     = wrapper_protocol_failed
diagnostic_stage     = wrapper_protocol
tool_telemetry       = null
provider_backed_invocation_count = 1
source_mutation_count            = 0
```

The canonical adapter currently parses authorized subprocess stdout as:

```python
stdout = (result.stdout or "").strip()
data = json.loads(stdout)
```

This whole-document parser fails closed on any multi-line stdout that
contains one or more dependency-diagnostic lines before the terminal
authorized JSON object. The vulnerability is structural: any subprocess
that writes any diagnostic line to stdout before the terminal JSON frame
corrupts `json.loads(stdout)` and is classified as
`wrapper_protocol_failed` even when the final authorized frame is valid.

## Live evidence boundary (honest)

The live raw wrapper stdout was deliberately not retained, so the exact
live response bytes are unknown. The proof therefore distinguishes:

```
AUTHORIZED_WRAPPER_STDOUT_FRAMING_DEFECT = PROVEN_AND_REPAIRED_PROVIDER_FREE
LIVE_WRAPPER_PROTOCOL_CAUSE              = UNRESOLVED
```

The structural defect is proven provider-free. The live causation is not
claimed — the proof does not label the latest live root cause
`stdout_contamination_proven`.

## Provider-free reproduction (pre-repair)

```python
# Whole-document parser on multi-line stdout:
multiline = "FAKE_PI_SDK_DIAGNOSTIC\n" + json.dumps(authorized_payload)
json.loads(multiline.strip())  # → raises json.JSONDecodeError
```

The provider-free proof fixture uses the canonical test fixture pattern:

```
$ python -m pytest -v tests/pi/test_pi_authorized_failure_diagnostics.py

collected 53 items
tests/pi/test_pi_authorized_failure_diagnostics.py ..................... [ 39%]
................................                                         [100%]
======================== 53 passed, 1 warning in 0.60s =========================
```

Pre-repair the test `test_case_b_leading_noise_then_success_frame` would
have failed with `wrapper_protocol_failed`. Post-repair it passes with a
bounded `AgentRunEnvelope` whose identity, runtime, and bounded failure
state all survive the framing intact.

## Parser helper

```python
def _parse_authorized_stdout_frame(stdout: str) -> dict[str, Any] | None:
    """Recover the canonical authorized wrapper result JSON object.

    Authorized protocol framing:

    * The **final non-empty line** of subprocess stdout is the sole
      machine-readable authorized result JSON object.
    * Earlier stdout lines are untrusted dependency diagnostics, are
      never persisted, and carry no authority.
    * Trailing noise after the JSON frame causes protocol failure.
    * The frame must be a JSON object; lists, strings, numbers, booleans,
      and ``null`` are rejected.
    * Empty stdout is rejected.

    This helper performs framing only.  Runtime-identity, tool-telemetry,
    and bounded-failure parsing remain in :meth:`_parse_result`.
    """
    if not stdout:
        return None
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        return None
    final_line = lines[-1]
    try:
        parsed = json.loads(final_line)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed
```

The framing helper is applied only to the **authorized** protocol-parsing
path (`require_runtime_identity=True`). Legacy/non-authorized paths
(`execute(...)`, readiness preflight) preserve the existing
whole-document parse unless current source proves a shared helper makes
this impossible.

## Framing matrix

| Case | Stdout shape | Expected outcome | Result |
|------|--------------|------------------|--------|
| A | single valid JSON line | bounded success | PASS |
| B | leading diagnostic noise + valid JSON | bounded success | PASS |
| C | leading noise + bounded failure JSON | bounded failure preserved | PASS |
| D | valid JSON + trailing noise | `wrapper_protocol_failed` | PASS |
| E | leading diagnostic + malformed final line | `wrapper_protocol_failed` | PASS |
| F | non-object final JSON (`[]`, `"str"`, `123`, `true`, `null`) | `wrapper_protocol_failed` | PASS |
| G | empty stdout | `wrapper_protocol_failed` | PASS |
| H | valid success JSON + nonzero return code | bounded stderr-classified failure | PASS |

Additional strictness preservation:

| Property | Result |
|----------|--------|
| valid final JSON without `actual_runtime_identity` | `actual_identity_missing` |
| valid final JSON with `tool_telemetry=null` | `wrapper_protocol_failed` |
| secret-shaped leading diagnostic | not retained in envelope payload |
| bounded wrapper failure JSON preserved | intact |
| empty stdout | `wrapper_protocol_failed` |
| nonzero subprocess exit | precedence over stdout salvage |

## Real wrapper integration with disposable fake Pi 0.82.1 package

A temporary in-tree fake Pi 0.82.1 package under
`tests/pi/fixtures/fake_pi_package/` exposes:

- `package.json` with `name=@earendil-works/pi-coding-agent`, `version=0.82.1`
- `dist/index.js` exporting `ModelRuntime`, `createAgentSession`,
  `SessionManager`
- `ModelRuntime.getModel(...)` → in-memory `openai-codex / gpt-5.6-sol`
- `ModelRuntime.getProviders()` → `["openai-codex"]`
- `ModelRuntime.checkAuth(provider)` → in-memory descriptor
- `ModelRuntime.getAvailable()` → `[{provider, id}]`
- `createAgentSession({...})` returns `{ session }`
- `session.getActiveToolNames()` → `["read","bash","edit","write"]`
- `session.agent.state.messages` → `[]`
- `session.prompt(prompt)` writes `FAKE_PL_SDK_DIAGNOSTIC
` to stdout,
  then either returns (success) or throws (failure via
  `PI_FAKE_I_BEHAVIOR=failure`)

The fake performs **no network, no DNS, no socket, no real provider SDK,
no real authentication**. The subprocess runs with a disposable HOME and
`PI_CODING_AGENT_PACKAGE_ROOT=<fake package>`.

End-to-end framing repair proof:

```
$ python -m pytest -v tests/pi/test_pi_authorized_failure_diagnostics.py -k real_wrapper

collected 53 items / 51 deselected / 2 selected
tests/pi/test_pi_authorized_failure_diagnostics.py ..                    [100%]
================= 2 passed, 51 deselected, 1 warning in 0.14s ==================
```

Observed subprocess stdout for the success path:

```
FAKE_PI_SDK_DIAGNOSTIC
{...valid terminal JSON...}
```

The framing helper recovers the JSON object; the adapter classifies the
result through the post-framing identity and telemetry validators. The
adapter does NOT collapse the multi-line stdout into
`wrapper_protocol_failed` at the JSON decode step.

## Real wrapper failure integration

The fake `session.prompt(...)` raises a synthetic provider-request error
when `PI_FAKE_I_BEHAVIOR=failure`. The wrapper emits its bounded failure
JSON as the final stdout line, after the leading diagnostic. The framing
repair preserves the bounded `failure_class` / `failure_stage` from the
final frame intact.

```
envelope.status                   = "error"
envelope.failure_classification   = parsed["failure_class"]
envelope.failure_stage            = parsed["failure_stage"]
```

## Non-retention proof

- No new runtime field retains raw subprocess stdout.
- No new runtime field retains raw subprocess stderr.
- No new runtime field retains prompt, provider payload, assistant
  content, reasoning, tool arguments, or tool results.
- The ignored earlier stdout lines are discarded by
  `_parse_authorized_stdout_frame` and never appear in the resulting
  `AgentRunEnvelope`.
- The secret-shaped leading diagnostic line `access_token=secret-not-returned`
  is verified not to appear in `json.dumps(envelope.model_dump())`.

## Zero provider / credential / rail posture

```
REAL_PROVIDER_CALL_COUNT               = 0
CAMPAIGN_LIVE_RAIL_CALL_COUNT          = 0
OAUTH_READINESS_COUNT                  = 0
OPERATOR_CREDENTIAL_STORE_ACCESS_COUNT = 0
fake_network_call_count                = 0 (in-memory resolution)
provider_backed_invocation_count       = 0
```

The fake wrapper subprocess is not a provider-backed invocation. The
fake Pi package resolves provider/model entirely in memory and never
opens a socket.

## Provider / model / tool / telemetry behavior

```
provider/model behavior change  = none (openai-codex / gpt-5.6-sol preserved)
tool activation change          = none (["read","bash","edit","write"] preserved)
telemetry schema change         = none (10-field surface preserved)
prompt change                   = none
PI_PROVIDER / PI_MODEL change   = none
PI_DISABLE_TOOLS change         = none
configured tool names change    = none
thinking level change           = none
```

## Failure-class taxonomy preserved

```
wrapper_protocol_failed = preserved (no new canonical failure class introduced)
NO new failure tokens:
    wrapper_stdout_noise      (NOT introduced)
    wrapper_frame_noise       (NOT introduced)
    wrapper_multiline_result  (NOT introduced)
```

The framing repair only narrows the shape of what
`wrapper_protocol_failed` may be raised from; it does not invent any new
canonical failure class.

## Documentation follow-through

Updates:

- `guardian/agents/adapters/pi_codex_runner.py` — added
  `_parse_authorized_stdout_frame` helper and applied it to the
  authorized protocol-parsing path.
- `tests/pi/test_pi_authorized_failure_diagnostics.py` — added the
  framing matrix (Cases A-H), strictness preservation, secret-shaped
  redaction, helper isolation, and real-wrapper subprocess integration
  with a disposable fake Pi 0.82.1 package.
- `tests/pi/fixtures/fake_pi_package/` — temporary in-tree fake Pi
  0.82.1 package (`package.json` + `dist/index.js`) used only by tests.
- `docs/architecture/pi-invocation-boundary-contract.md` — added the
  bounded "Authorized wrapper subprocess framing" subsection.
- `docs/architecture/proofs/runtime/2026-09-01-pi-authorized-wrapper-protocol-framing-proof.md` —
  this proof.

Not modified:

- `codex_runner/src/agent-wrapper.js` (read-only governing anchor)
- `codex_runner/src/assistant-telemetry.js` (read-only governing anchor)
- `guardian/agents/adapters/base.py` (read-only governing anchor)
- `guardian/pi/invocation.py` (read-only governing anchor)
- `guardian/pi/tokens.py` (read-only governing anchor)
- `tests/pi/test_pi_live_invocation.py` (read-only governing anchor)
- `tests/ops/test_pi_assistant_response_telemetry.py` (read-only governing anchor)
- `docs/architecture/00-current-state.md`
- ADRs
- Campaign freeze / Campaign schema
- Historical CE-L1 ledger
- Release claims

## Node syntax validation

```
$ node --check codex_runner/src/agent-wrapper.js
$ node --check codex_runner/src/assistant-telemetry.js
EXIT=0 / EXIT=0
```

## Focused pytest results

```
$ python -m pytest -v tests/pi/test_pi_authorized_failure_diagnostics.py
collected 53 items
tests/pi/test_pi_authorized_failure_diagnostics.py ..................... [ 39%]
................................                                         [100%]
======================== 53 passed, 1 warning in 0.60s =========================
```

## Regression pytest results

```
$ python -m pytest tests/pi/test_pi_live_invocation.py tests/ops/test_pi_assistant_response_telemetry.py
.......................                                                  [100%]
45 passed, 1 warning
```

## Full CE-L1 deterministic suite

```
$ python -m pytest tests/ops/test_worker_coding_pi_runtime_contract.py tests/ops/test_pi_assistant_response_telemetry.py tests/pi/test_pi_live_invocation.py tests/pi/test_pi_authorized_failure_diagnostics.py codex_runner/tests/test_campaign_engine_live_executor.py
........................................................................ [ 96%]
......                                                                   [100%]
150 passed, 1 warning
```

(132 prior baseline + 18 new framing tests = 150.)

## Docs

```
$ PYTHON=.venv/bin/python make docs
Docs validation passed: required architecture docs, README links, and source headings verified.
Diagram freshness check passed: no runtime source drift detected and matrix decisions are valid.
```

## ADR impact

```
ADR impact   = Aligned with existing ADRs; no new ADR required
Governing:
    ADR-020 Guardian-Mediated Coding Agent Execution Contract
    ADR-066 Campaign Engine Runtime Recovery Contract
    ADR-068 Campaign Engine Live Role Execution Contract
    Pi Invocation Boundary Contract
    Agent Tool Loop Contract
    Runtime Protocol Token Contract

Reason:
    This task changes only the transport framing used to recover one
    already-authorized bounded wrapper result from a subprocess. It does
    not change who authorizes execution, provider/model routing, tool
    authority, mutation authority, retry semantics, persistence,
    Campaign progression, or release claims. The framing decision is
    documented in the Pi Invocation Boundary contract.
```

## Exact tracked changed-file list

```
guardian/agents/adapters/pi_codex_runner.py
tests/pi/test_pi_authorized_failure_diagnostics.py
tests/pi/fixtures/fake_pi_package/package.json
tests/pi/fixtures/fake_pi_package/dist/index.js
docs/architecture/pi-invocation-boundary-contract.md
docs/architecture/proofs/runtime/2026-09-01-pi-authorized-wrapper-protocol-framing-proof.md
```

(Six tracked files. The fake Pi package files are required to
satisfy spec §20-§25; they are not Git-ignored but are scoped to
`tests/pi/fixtures/` and used only by tests.)

## `git diff --check`

```
$ git diff --check
exit=0
```

## Local implementation commit

```
HEAD = <recorded at commit time>
subject = "Repair authorized Pi wrapper protocol framing"
push performed = false
merge performed = false
```

## Invariants

- Guardian remains authorization authority.
- Pi remains execution substrate.
- Adapter framing cannot grant execution authority.
- Final authorized JSON frame remains strictly validated.
- Nonzero process exit remains authoritative over stdout.
- Runtime identity remains mandatory.
- 10-field live telemetry remains mandatory for live authorized success.
- Raw subprocess output is never persisted.
- Earlier stdout diagnostics are non-authoritative.
- No telemetry reconstruction.
- No provider/model substitution.
- No retry/fallback/rebinding.
- No credential inspection.
- No live Campaign execution.
- Historical CE-L1 evidence remains immutable.
- Release claims remain unchanged.

## NEXT_TASK_REQUIRED

```
NEXT_TASK_REQUIRED = land the authorized Pi wrapper protocol-framing
                    repair on remote main; after canonical landing,
                    requalify the CE-L1 disposable driver against that
                    exact landed runtime before authorizing any further
                    live rail attempt
```

## What this slice proves and does not prove

PROVES:

- The structural stdout-framing defect is reproducible provider-free:
  `json.loads(stdout.strip())` raises `json.JSONDecodeError` on any
  multi-line stdout that contains one or more diagnostic lines before
  the terminal JSON object.
- The framing repair recovers the canonical JSON object from multi-line
  stdout by treating the **final non-empty line** as the authorized
  protocol frame.
- All eight spec-defined framing-matrix cases pass.
- All spec-defined strictness preservation properties pass.
- Secret-shaped leading diagnostics do not leak into the bounded
  envelope.
- Real wrapper + fake Pi 0.82.1 package integration proves the framing
  repair works end-to-end without a real provider.
- Real wrapper failure path preserves bounded `failure_class` /
  `failure_stage` through the framing repair.
- 150-test CE-L1 deterministic suite passes (132 prior + 18 new).
- No provider, no credential, no rail call, no target mutation.

DOES NOT PROVE:

- Whether the live root cause was stdout noise (live raw stdout was not
  retained; `LIVE_WRAPPER_PROTOCOL_CAUSE=UNRESOLVED`).
- Whether the wrapper itself needs to be updated to emit the complete
  10-field telemetry surface for live authorized success (the wrapper
  currently emits only the older 6 telemetry fields; the adapter's
  telemetry strictness remains intact).
- Whether a follow-up live rail attempt will succeed (out of scope).


# 2026-09-01 Pi Authorized Wrapper Subprocess Fixture Reproducibility Repair — PASS_TRACKED_ONLY

## Result

```
RESULT                                              = PASS
PI_WRAPPER_PROTOCOL_FIXTURE_REPRODUCIBILITY          = PASS_TRACKED_ONLY
AUTHORIZED_WRAPPER_STDOUT_FRAMING_DEFECT             = PROVEN_AND_REPAIRED_PROVIDER_FREE
LIVE_WRAPPER_PROTOCOL_CAUSE                          = UNRESOLVED
CAUSAL_CLASSIFICATION                                 = UNRESOLVED_ASSISTANT_TOOL_CALL_EMISSION_BOUNDARY (unchanged)
CE-L1                                                 = OPEN
LIVE_EXECUTOR_PROVEN                                  = NOT_EMITTED
REAL_PROVIDER_CALL_COUNT                              = 0
CAMPAIGN_LIVE_RAIL_CALL_COUNT                         = 0
OAUTH_READINESS_COUNT                                 = 0
OPERATOR_CREDENTIAL_STORE_ACCESS_COUNT                = 0
```

## Scope

This slice is a proof-reproducibility repair. The runtime framing repair
itself remains exactly as committed in
`e9125a28693a2681627162bdd090ba51a0a03206` and is byte-identical in
this slice. The only changes are:

1. Migrating the fake Pi 0.82.1 implementation from a hidden ignored
   `dist/index.js` to a tracked
   `tests/pi/fixtures/fake_pi_package/source/index.js`.
2. Adding `_materialize_fake_pi_package(tmp_path)` in
   `tests/pi/test_pi_authorized_failure_diagnostics.py` to materialize
   the tracked source fixture into a fresh disposable package under
   `pytest.tmp_path` at test time.
3. Refactoring both real-wrapper integration tests to point
   `PI_CODING_AGENT_PACKAGE_ROOT` at the materialized tmp package,
   not at the in-repository fixture directory.
4. Updating this proof with the tracked-state evidence.

No production runtime code changes. No `.gitignore` change. No
force-add. The repository-wide `dist/` rule remains intact.

## Proof evolution (explicit)

```
INITIAL_LOCAL_REAL_WRAPPER_FIXTURE         = IGNORED_DIST_PRESENT
INITIAL_CLEAN_CHECKOUT_REPRODUCIBILITY     = NOT_PROVEN
TRACKED_FIXTURE_SOURCE                     = tests/pi/fixtures/fake_pi_package/source/index.js
GENERATED_RUNTIME_LOCATION                = <pytest tmp_path>/fake_pi_package/dist/index.js
LOCAL_IGNORED_FIXTURE_DEPENDENCY          = NONE
REAL_WRAPPER_TRACKED_ONLY_REPRODUCIBILITY  = PASS
```

## Ignored-fixture premise (pre-repair verification)

The local ignored fake Pi file:

```
LOCAL_FAKE_PI_PATH    = tests/pi/fixtures/fake_pi_package/dist/index.js
LOCAL_FAKE_PI_SHA256  = c121257692938d46dbec6f33fb1945545f5ee997bb36049550aec8e32e62e730
LOCAL_FAKE_PI_SIZE    = 2964 bytes
LOCAL_FAKE_PI_TRACKED = false  (git ls-files --error-unmatch FAILED)
LOCAL_FAKE_PI_IGNORED = true   (git check-ignore resolves to .gitignore:76:dist/)
```

The repository-wide `dist/` rule (line 76 of `.gitignore`) is the
effective ignore rule.

## Tracked fixture source migration

The ignored file's bytes were copied byte-for-byte to:

```
TRACKED_FAKE_PI_SOURCE_PATH    = tests/pi/fixtures/fake_pi_package/source/index.js
TRACKED_FAKE_PI_SOURCE_SHA256  = c121257692938d46dbec6f33fb1945545f5ee997bb36049550aec8e32e62e730
TRACKED_FAKE_PI_SOURCE_SIZE    = 2964 bytes
SOURCE_IGNORED_BYTE_EQUIVALENT = true  (sha256 equal to LOCAL_FAKE_PI_SHA256)
```

`git check-ignore tests/pi/fixtures/fake_pi_package/source/index.js`
returns no result, so the tracked source is not ignored.

`git ls-files --error-unmatch tests/pi/fixtures/fake_pi_package/package.json`
PASSES (package metadata already tracked in the prior slice).

The fake package identity is preserved:

```
package.name    = @earendil-works/pi-coding-agent
package.version = 0.82.1
```

## Pre-fix clean-checkout reproduction

A detached worktree was created at exactly
`e9125a28693a2681627162bdd090ba51a0a03206`:

```
CLEAN_BEFORE_PATH                            = /tmp/codexify-pi-framing-before.w1FkVf
CLEAN_BEFORE_DIST_INDEX_JS_EXISTS            = false  (test ! -e ... PASSED)
PRE_FIX_REAL_WRAPPER_TRACKED_ONLY_RESULT     = FAIL
PRE_FIX_FAILURE_ATTRIBUTION                  = runtime_module_unavailable / runtime_load
                                                (wrapper cannot load the missing
                                                tests/pi/fixtures/fake_pi_package/dist/index.js)
PRE_FIX_PROVIDER_CREDENTIAL_NETWORK_INVOLVED = false
```

The pre-fix failure is attributable solely to the missing fake Pi
runtime fixture under `tests/pi/fixtures/fake_pi_package/dist/`. It
is NOT attributable to provider access, credentials, network,
unrelated import failure, or unrelated repository setup.

## Materialization helper

```python
def _materialize_fake_pi_package(tmp_path: Path) -> Path:
    package_root = tmp_path / "fake_pi_package"
    (package_root / "dist").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_FIXTURE_PACKAGE_JSON, package_root / "package.json")
    shutil.copyfile(_FIXTURE_SOURCE_INDEX, package_root / "dist" / "index.js")
    return package_root
```

The materialized package contains both required surfaces:

```
MATERIALIZED_PACKAGE_ROOT  = <tmp_path>/fake_pi_package
MATERIALIZED_DIST_INDEX_JS  = <tmp_path>/fake_pi_package/dist/index.js
```

`PI_CODING_AGENT_PACKAGE_ROOT` is set to the materialized tmp package
in every real-wrapper integration test.  No test points
`PI_CODING_AGENT_PACKAGE_ROOT` at the in-repository fixture directory.

## Local ignored-file independence

The local ignored `tests/pi/fixtures/fake_pi_package/dist/index.js`
was temporarily moved aside:

```
mv tests/pi/fixtures/fake_pi_package/dist/index.js /tmp/...
```

The two real-wrapper integration tests were then re-run with no
local ignored file present. Both PASSED:

```
test_real_wrapper_noisy_stdout_success_protocol  = PASS
test_real_wrapper_noisy_stdout_failure_protocol  = PASS
LOCAL_IGNORED_FIXTURE_DEPENDENCY                 = NONE
```

The ignored file was then restored.

## Staged tracked-only proof

The task-owned files were staged:

```
git add tests/pi/test_pi_authorized_failure_diagnostics.py
git add tests/pi/fixtures/fake_pi_package/source/index.js
```

The staged tracked tree was written into a temporary commit:

```
TREE_SHA        = 4c1cccb964a770b4b4e6179075b3c9a7b54d3e0a
TEMP_COMMIT     = e43d6253611187d3fd33a0c911160457d4049ef7
TEMP_COMMIT_REF = "temporary tracked-only Pi framing fixture validation"
```

A detached disposable worktree was created at the temp commit:

```
STAGED_CLEAN_PATH                       = /tmp/codexify-pi-framing-staged.CRt7kf
STAGED_CLEAN_DIST_INDEX_JS_ABSENT       = true  (test ! -e ... PASSED)
STAGED_CLEAN_TRACKED_SOURCE_PRESENT     = true
```

The two real-wrapper integration tests were then re-run inside the
staged clean worktree (no ignored `dist/index.js` available; no
network; no credentials). Both PASSED:

```
test_real_wrapper_noisy_stdout_success_protocol  = PASS
test_real_wrapper_noisy_stdout_failure_protocol  = PASS
REAL_WRAPPER_TRACKED_ONLY_REPRODUCIBILITY_AFTER   = PASS
```

The disposable worktree was then removed.

## Network / credential / tool posture

```
fake HTTP_CALL_COUNT     = 0  (in-memory provider/model resolution)
fake DNS_CALL_COUNT      = 0
fake SOCKET_CALL_COUNT   = 0
fake PI_PROVIDER         = "openai-codex"
fake PI_MODEL            = "gpt-5.6-sol"
fake PI_HARNESS_ID       = "pi-coding-agent"
fake PI_HARNESS_VERSION  = "0.82.1"
fake getActiveToolNames  = ["read", "bash", "edit", "write"]
PROVIDER_BACKED_INVOCATION_COUNT       = 0
CAMPAIGN_LIVE_RAIL_COUNT               = 0
OAUTH_READINESS_COUNT                  = 0
OPERATOR_CREDENTIAL_STORE_ACCESS_COUNT = 0
disposable HOME                        = <tmp_path>/home  (per-test)
```

## Runtime / wrapper source posture

```
guardian/agents/adapters/pi_codex_runner.py        unchanged  (no edits this slice)
codex_runner/src/agent-wrapper.js                  unchanged  (read-only governing anchor)
codex_runner/src/assistant-telemetry.js            unchanged  (read-only governing anchor)
.gitignore                                          unchanged
```

The existing helper `_parse_authorized_stdout_frame(...)` and its
final-non-empty-line semantics remain exactly as committed in
`e9125a28693a2681627162bdd090ba51a0a03206`. This task is proof
reproducibility, not a second parser repair.

## Focused pytest result

```
$ python -m pytest -v tests/pi/test_pi_authorized_failure_diagnostics.py
collected 53 items
tests/pi/test_pi_authorized_failure_diagnostics.py ..................... [ 39%]
................................                                         [100%]
======================== 53 passed, 1 warning in 0.68s =========================
```

All 8 framing matrix cases (A-H), strictness preservation, secret-shaped
redaction, helper isolation, and both real-wrapper integration tests
PASS.

## Deterministic CE-L1 suite

```
$ python -m pytest tests/ops/test_worker_coding_pi_runtime_contract.py \
                    tests/ops/test_pi_assistant_response_telemetry.py \
                    tests/pi/test_pi_live_invocation.py \
                    tests/pi/test_pi_authorized_failure_diagnostics.py \
                    codex_runner/tests/test_campaign_engine_live_executor.py
........................................................................ [ 96%]
......                                                                   [100%]
150 passed, 1 warning
```

## Node syntax validation

```
node --check codex_runner/src/agent-wrapper.js        = exit 0
node --check codex_runner/src/assistant-telemetry.js  = exit 0
```

## Docs

```
$ PYTHON=.venv/bin/python make docs
Docs validation passed: required architecture docs, README links, and source headings verified.
Diagram freshness check passed: no runtime source drift detected and matrix decisions are valid.
```

## Tracked file scope

Before commit:

```
git status --short
M  tests/pi/test_pi_authorized_failure_diagnostics.py
A  tests/pi/fixtures/fake_pi_package/source/index.js
```

Only the implementation worktree's tracked changes; the ignored
`tests/pi/fixtures/fake_pi_package/dist/index.js` is NOT staged or
force-added.

```
git check-ignore -v tests/pi/fixtures/fake_pi_package/dist/index.js
.gitignore:76:dist/    tests/pi/fixtures/fake_pi_package/dist/index.js
```

(Generated `dist/` remains untracked.)

## Confirmed invariants

- Tests reproducible from tracked source ✓
- Generated build/runtime fixture output remains disposable ✓
- Global `dist/` ignore remains intact ✓
- No hidden local file required for canonical proof ✓
- Fake provider/package remains provider-free ✓
- No credential access ✓
- Production runtime repair remains byte-identical ✓
- Provider/model/tool semantics remain unchanged ✓
- Historical CE-L1 evidence remains immutable ✓
- No live rail attempt ✓
- Release claims remain unchanged ✓

## What this slice proves and does not prove

PROVES:

- The fake Pi 0.82.1 implementation is preserved by SHA into a tracked
  source fixture.
- The hidden ignored `dist/index.js` dependency is removed: the
  tests materialize the package from the tracked source under
  `tmp_path` at test time.
- The real-wrapper integration tests pass from a clean detached
  worktree at the prior commit, with no ignored file present.
- The staged tracked-only tree (no ignored file) passes both
  real-wrapper integration tests.
- The full CE-L1 deterministic suite (150 tests) still passes.
- `dist/` rule remains intact; no force-add; no `.gitignore` change.
- The runtime framing repair remains byte-identical.

DOES NOT PROVE:

- The framing repair is the exact cause of the prior live failure
  (LIVE_WRAPPER_PROTOCOL_CAUSE=UNRESOLVED, as before).
- A post-repair CE-L1 live observation (out of scope; the proof
  remains provider-free).
- The wrapper itself is updated (no wrapper change; the wrapper
  still emits only the older 6 telemetry fields in
  `guardian-authorized-task` mode).

## What this slice changes about the prior proof

The prior proof section at the top of this file is preserved
unchanged. The proof evolution block above is the only addition.
Future readers can see the exact evolution:

- First local run: relied on ignored `dist/index.js` (NOT
  reproducible from a clean checkout).
- After this slice: reproducible from tracked
  `source/index.js` + `package.json` only.

The fact that the first local run had an ignored fixture available
is recorded explicitly (`INITIAL_LOCAL_REAL_WRAPPER_FIXTURE=
IGNORED_DIST_PRESENT`). The proof does not erase this fact.


# 2026-09-01 canonical landing preflight — PASS

## Result

```
LANDING_BASE_CHECK                       = PASS  (origin/main == 77f1acf8061aa5481defc2dbe298b6701157da6)
MAIN_MOVEMENT_BEFORE_PUSH                = NONE
RUNTIME_SEAM_DRIFT_RESULT                = ORTHOGONAL
IMPLEMENTATION_LINEAGE                   = PASS
AUTHORIZED_WRAPPER_FRAME_PARSER          = PASS
AUTHORIZED_LEGACY_PROTOCOL_SEPARATION    = PASS
NONZERO_RETURN_CODE_PRECEDENCE           = PASS
MISSING_RUNTIME_IDENTITY_FAIL_CLOSED     = PASS
AUTHORIZED_TOOL_TELEMETRY_STRICTNESS     = PASS
Bounded failure token preservation       = wrapper_protocol_failed at wrapper_protocol (no new token introduced)
TRACKED_FAKE_SOURCE_PATH                 = tests/pi/fixtures/fake_pi_package/source/index.js
TRACKED_FAKE_SOURCE_SHA256               = c121257692938d46dbec6f33fb1945545f5ee997bb36049550aec8e32e62e730
TRACKED_FAKE_SOURCE_SIZE                 = 2964 bytes
REPOSITORY_IGNORED_DIST_TRACKED          = false
GLOBAL_DIST_IGNORE_RULE_PRESERVED        = .gitignore:76:dist/
CLEAN_CANDIDATE_DIST_INDEX_JS_ABSENT      = true
CLEAN_CANDIDATE_NOISY_SUCCESS            = PASS
CLEAN_CANDIDATE_NOISY_FAILURE            = PASS
TMP_PATH_MATERIALIZATION_VERIFIED        = true
FOCUSED_FRAMING_PYTEST_COUNT              = 53 passed
DETERMINISTIC_CE_L1_PYTEST_COUNT         = 150 passed
NODE_CHECKS                              = PASS
DOCS_PRE_PUSH                            = PASS
PROVIDER_BACKED_INVOCATION_COUNT         = 0
CAMPAIGN_LIVE_RAIL_COUNT                 = 0
OAUTH_READINESS_COUNT                    = 0
OPERATOR_CREDENTIAL_STORE_ACCESS_COUNT   = 0
LIVE_WRAPPER_PROTOCOL_CAUSE              = UNRESOLVED
CAUSAL_CLASSIFICATION                     = UNRESOLVED_ASSISTANT_TOOL_CALL_EMISSION_BOUNDARY
CE-L1                                     = OPEN
LIVE_EXECUTOR_PROVEN                      = NOT_EMITTED
CANONICAL_LANDING_CANDIDATE               = PASS
```

## Scope

This is a pre-push landing-preflight receipt only.  No new runtime
implementation edit is authorized.  The two implementation commits
are:

```
e9125a28693a2681627162bdd090ba51a0a03206  Repair authorized Pi wrapper protocol framing
5a6aef512f5b38aa61283e3e4e6eaa3483c03d5e  Make Pi wrapper protocol fixture reproducible
```

with parent/ancestry:

```
77f1acf806a1aa5481defc2dbe298b6701157da6
  -> e9125a28693a2681627162bdd090ba51a0a03206
  -> 5a6aef512f5b38aa61283e3e4e6eaa3483c03d5e
```

Verified via:

```
git rev-parse 5a6aef512^  =  e9125a28693a2681627162bdd090ba51a0a03206
git merge-base e9125a286 77f1acf8061aa  =  77f1acf806a1aa5481defc2dbe298b6701157da6
```

## Candidate changed-file list (canonical landing surface)

```
git diff 77f1acf8061aa5481defc2dbe298b6701157da6..5a6aef512f5b38aa61283e3e4e6eaa3483c03d5e
--name-status

M  docs/architecture/pi-invocation-boundary-contract.md
A  docs/architecture/proofs/runtime/2026-09-01-pi-authorized-wrapper-protocol-framing-proof.md
M  guardian/agents/adapters/pi_codex_runner.py
A  tests/pi/fixtures/fake_pi_package/package.json
A  tests/pi/fixtures/fake_pi_package/source/index.js
M  tests/pi/test_pi_authorized_failure_diagnostics.py
```

Exactly the intended framing/fixture/boundary/proof surface.  No
unrelated dirty content.  No ignored file appears in the PR diff.

## Runtime parser semantic readback (canonical)

`_parse_authorized_stdout_frame(stdout)` (in
`guardian/agents/adapters/pi_codex_runner.py`) implements the canonical
seven semantics:

1. split stdout into lines;
2. discard empty lines;
3. inspect only the final non-empty line as the authorized protocol
   frame;
4. parse the final line as JSON;
5. require the parsed value to be a mapping/object;
6. never return or persist earlier stdout lines;
7. fail closed (`None`) when no valid terminal object exists.

The framing helper is applied only on the authorized
(`require_runtime_identity=True`) parsing path.  Legacy/non-authorized
paths (the unbounded `execute(...)` legacy path and the readiness
preflight) preserve their existing whole-document parse
unmodified.

## Legacy / authorized separation (canonical)

The framing repair does not silently redefine unrelated legacy
`audit`, `compile`, or `task` stdout semantics.  The `execute(...)`
method and the readiness preflight both continue to use the
whole-document `json.loads(stdout.strip())` parse.  The framing
helper is gated on `require_runtime_identity=True`.

## Nonzero-return-code precedence (canonical)

A nonzero subprocess exit cannot be salvaged by a valid stdout success
frame.  The `_parse_result(...)` method's nonzero branch (returns
the bounded stderr-classified failure) executes before any
`json.loads` is attempted, regardless of the framing helper.

## Runtime-identity strictness (canonical)

A valid final JSON object without `actual_runtime_identity` under
`require_runtime_identity=True` still fails closed as
`actual_identity_missing` (the `MISSING_RUNTIME_IDENTITY_FAIL_CLOSED`
test in the focused module passes).  Framing parsing does not weaken
identity attestation.

## Telemetry strictness (canonical)

A valid final JSON object with `tool_telemetry=null` or
missing/malformed telemetry still returns
`failure_classification="wrapper_protocol_failed"`,
`failure_stage="wrapper_protocol"`.  The 10-field live authorized
telemetry contract is preserved.

## Canonical failure token preservation

The bounded `wrapper_protocol_failed` failure token at
`wrapper_protocol` stage continues to be used for actual terminal
frame violations.  No new canonical failure class has been
introduced.  Specifically the recipe does NOT introduce:

- `wrapper_stdout_noise`
- `wrapper_frame_noise`
- `wrapper_multiline_result`

## Tracked fixture source (canonical)

```
TRACKED_FAKE_SOURCE_PATH     = tests/pi/fixtures/fake_pi_package/source/index.js
TRACKED_FAKE_SOURCE_SHA256   = c121257692938d46dbec6f33fb1945545f5ee997bb36049550aec8e32e62e730
TRACKED_FAKE_SOURCE_SIZE     = 2964 bytes
TRACKED_FAKE_SOURCE_LS_FILES = PASS
TRACKED_FAKE_SOURCE_GITIGNORE = (not ignored)
```

## Fake package metadata

`tests/pi/fixtures/fake_pi_package/package.json` reports:

```
name    = @earendil-works/pi-coding-agent
version = 0.82.1
```

NOTE: Spec §13 writes the package name as
`"@file:`earendil-works/pi-coding-agent"`"`.  This is interpreted as a
documentation typo for the canonical npm scope
`@earendil-works/pi-coding-agent`.  The actual tracked package
metadata has used `@earendil-works/pi-coding-agent` since the first
slice; this preflight does not modify the name.  The actual
wrapper-side identity verification reads
`packageMetadata.name === "@earendil-works/pi-coding-agent"` (see
`codex_runner/src/agent-wrapper.js:211`); using any other name would
fail-closed at `runtime_load`.  Preserving the npm-scope name
therefore preserves the live runtime contract.

## Ignored dist remains untracked (canonical)

```
git ls-files tests/pi/fixtures/fake_pi_package/dist/index.js = (empty)
git check-ignore -v .../dist/index.js = .gitignore:76:dist/
```

The global `dist/` rule remains intact and the generated
`dist/index.js` is not tracked.  No `.gitignore` edit was made in any
implementation commit.

## Tmp-path materialization (canonical)

The `_materialize_fake_pi_package(tmp_path)` helper materializes:

```
<tmp_path>/fake_pi_package/package.json
<tmp_path>/fake_pi_package/dist/index.js
```

from the tracked fixture source.  `PI_CODING_AGENT_PACKAGE_ROOT` is
set to the materialized tmp package root in every real-wrapper
integration test.  No test depends on the in-repository fixture's
ignored `dist/`.

## Clean tracked-only candidate-worktree proof

A detached disposable worktree was created at exactly
`5a6aef512f5b38aa61283e3e4e6eaa3483c03d5e`:

```
CLEAN_ROOT_PATH                            = /tmp/codexify-pi-framing-landing.XXXXXX
CLEAN_ROOT_DIST_INDEX_JS_ABSENT            = true
CLEAN_ROOT_NOISY_SUCCESS                   = PASS
CLEAN_ROOT_NOISY_FAILURE                   = PASS
```

The detached worktree was removed after validation.

## Provider / rail / credential posture

Across this entire landing-preflight slice:

```
provider-backed invocation count       = 0
Campaign live rail call count           = 0
OAuth readiness count                  = 0
operator credential-store access count = 0
```

The fake Pi subprocess is provider-free (in-memory resolution; zero
HTTP / DNS / socket).

## Focused framing suite (fresh)

```
$ python -m pytest -v tests/pi/test_pi_authorized_failure_diagnostics.py
collected 53 items
................................                                         [100%]
======================== 53 passed, 1 warning in 0.71s =========================
```

## Deterministic CE-L1 suite (fresh)

```
$ python -m pytest tests/ops/test_worker_coding_pi_runtime_contract.py \
                    tests/ops/test_pi_assistant_response_telemetry.py \
                    tests/pi/test_pi_live_invocation.py \
                    tests/pi/test_pi_authorized_failure_diagnostics.py \
                    codex_runner/tests/test_campaign_engine_live_executor.py
........................................................................ [ 96%]
......                                                                   [100%]
150 passed, 1 warning
```

## Node checks

```
node --check codex_runner/src/agent-wrapper.js        = exit 0
node --check codex_runner/src/assistant-telemetry.js  = exit 0
```

## Docs (pre-push)

```
$ python scripts/validate_docs.py
Docs validation passed: required architecture docs, README links, and source headings verified.

$ python scripts/check_diagram_freshness.py
Diagram freshness check passed: no runtime source drift detected and matrix decisions are valid.

$ git diff --check
exit 0
```

## Specified discoveries (parked, not in scope)

The prior proof closeout noted two unrelated observations that are
classified as separate discoveries:

1. The wrapper emits only the older 6 telemetry fields in
   `guardian-authorized-task` mode (the 4 assistant-response fields
   are emitted only in `assistant-telemetry-test` mode).  A wrapper
   output-schema expansion is a separate slice.
2. The wrapper's readiness code path calls `getModel(...)` /
   `getProviders(...)` / `checkAuth(...)` / `getAvailable(...)`
   without `await`, while the maintained Pi 0.82.1 runtime may
   return Promises.  A readiness-`await` repair is a separate slice.

Neither enters this landing task.  Park them unless a subsequent
canonical driver requalification proves one is the next CE-L1
blocker.

## What this slice proves and does not prove

PROVES:

- The exact two-commit implementation lineage is locally complete,
  reproducible from tracked state, and free of hidden fixture
  dependencies.
- The runtime framing helper implements the canonical final-non-
  empty-line protocol-frame rule with all seven required semantics.
- Authorized/legacy separation is preserved; legacy `audit`,
  `compile`, and `task` paths are not redefined.
- All eight framing-matrix cases (A-H), strictness preservation,
  secret-shaped redaction, helper isolation, and both real-wrapper
  integration tests pass.
- The complete CE-L1 deterministic suite (150 tests) passes.
- The canonical candidate surface is exactly the six intended
  files; no scope expansion; ignored `dist/` not in the PR.
- The landing is eligible for canonical promotion; this is the
  pre-push receipt that the Task Spec required.

DOES NOT PROVE:

- That the framing repair is the exact live cause of the prior
  `wrapper_protocol_failed` (LIVE_WRAPPER_PROTOCOL_CAUSE=UNRESOLVED).
- A post-repair live Executor observation (no live rail in this
  slice).
- CE-L1 closure (CE-L1=OPEN; LIVE_EXECUTOR_PROVEN=NOT_EMITTED).
