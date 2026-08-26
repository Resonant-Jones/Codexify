# CE-L0 Guardian/Pi Live Invocation Proof — 2026-08-26

## Result

`BLOCKED`

The proof executed correctly against current `main` (`966664119`) using the
canonical Guardian-owned `invoke_guardian_authorized_pi` rail, but the
canonical Pi wrapper `codex_runner/src/agent-wrapper.js` raised an
undeclared-variable `ReferenceError` in `runAgent()` after `loadPiSdk()`
succeeded, so no provider-backed invocation ever started. The substrate
is fail-closed at the documented `runtime_load` stage. No retry, no
fallback, no repair attempted.

`NEXT_TASK_REQUIRED=repair codex_runner/src/agent-wrapper.js runAgent() harnessId/harnessVersion destructuring`

The full diagnostic surface is preserved below so a future repair Task
Spec can author the fix without guessing.

This proof does NOT emit `CE-L0_EXIT=GUARDIAN_PI_LIVE_READY`.

---

## Campaign context

| Field | Value |
| --- | --- |
| Campaign ID | `CAMPAIGN-2026-08-26_001_CAMPAIGN_ENGINE_SUPERVISED_USABILITY_CLOSURE` |
| Gate | `CE-L0` |
| Closure doc | `docs/Campaign/campaign-engine-supervised-usability-closure.md` |
| Required exit token on success | `GUARDIAN_PI_LIVE_READY` |
| Operator | `resonant_jones` |
| Date | 2026-08-26 |

## Repository identity (recorded before any live call)

| Field | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `966664119c75d64656132ce8b39c772a0bf7dd2a` |
| `origin/main` | `6b383badb1eb5c5301df0c92c88215e605bf9fff` |
| Merge-base | `6b383badb1eb5c5301df0c92c88215e605bf9fff` |
| Working tree at proof time | `git status --short --branch` → `## main...origin/main [ahead 1]` with untracked items only (`docs/Plans/2026-08-24-guardian-skills-system.md`, `guardian/skills/`, `guardian/tests/skills/`, `mobile/scout-ios/.swiftpm/`). No tracked modifications. |

The single ahead commit is the closure-document commit (`Freeze Campaign
Engine supervised usability closure`) for `docs/Campaign/campaign-engine-supervised-usability-closure.md`.
No runtime source file was modified between `origin/main` and HEAD.
The proof therefore runs against current `main` byte-equivalent to
`origin/main` on every codex_runner/, guardian/pi/, and tests/pi/ path
touched by the rail.

## Proof-target identity (recorded before any live call)

| Field | Value |
| --- | --- |
| Target path | `.hermes/proofs/ce-l0-2026-08-26/fixture/` (outside the Codexify worktree) |
| Target type | disposable, isolated Git repository |
| Symlinks into Codexify | none |
| Credentials | none |
| Git remotes | none |
| Allowed write roots | none (read-only posture) |
| Files | `README.md`, `src/value.py`, `test_value.py` |
| Baseline `HEAD` | `6c59cdf4ebd48d285659d886a9d6b1617f62b04b` |
| Pre-status | `git status --porcelain` → empty |

## Expected identity (resolved through the canonical registry path)

The identity was not hardcoded. It was resolved through the same vendored
Pi SDK that `agent-wrapper.js` loads (`codex_runner/vendor/pi-coding-agent`,
package version `0.72.1`), using the SDK's own `getProviders()` and
`getModel()`:

| Field | Value |
| --- | --- |
| Provider ID | `openai-codex` |
| Model ID | `gpt-5.1` |
| Harness ID | `pi-coding-agent` |
| Harness version | `0.72.1` |

The Pi SDK currently exposes 28 provider IDs (anthropic, deepseek, minimax,
openai, openai-codex, …) and 10 `openai-codex` model IDs (gpt-5.1,
gpt-5.1-codex-max, gpt-5.1-codex-mini, gpt-5.2, gpt-5.2-codex,
gpt-5.3-codex, gpt-5.3-codex-spark, gpt-5.4, gpt-5.4-mini, gpt-5.5).
The chosen `gpt-5.1` is one of those 10 and is the first-listed
registered model for the `openai-codex` lane.

## Deterministic pre-live validation (recorded before any live call)

| Suite | Result |
| --- | --- |
| `pytest -v tests/pi/test_pi_live_invocation.py tests/pi/test_pi_authorized_failure_diagnostics.py` | **56 / 56 PASS** |
| `node --check codex_runner/src/agent-wrapper.js` | **PASS** |

Pre-live regressions are green. The failure that emerges in §Live
invocation is not surfaced by either suite because both stub the
harness_runner at the Python boundary; neither exercises the wrapper
subprocess path under `guardian-authorized-task`.

## Authorized-readiness result

Run through the canonical Python seam
`guardian.pi.invocation.preflight_guardian_authorized_pi`, which in
turn invokes `codex_runner/src/agent-wrapper.js guardian-authorized-readiness`
via `guardian.agents.adapters.pi_codex_runner.PiCodexRunnerAdapter.preflight_authorized`.

| Field | Value |
| --- | --- |
| `ok` | `true` |
| `deepest_stage` | `auth_available` |
| `failure_class` | `null` |
| `failure_stage` | `null` |
| `preflight_call_count` | `1` |
| `retry_count` | `0` |
| `fallback_count` | `0` |
| `runtime_identity_established` | `true` |
| `oauth_available` | `true` |
| `session_initialized` | `false` |
| `provider_request_started` | `false` |
| `actual_identity` | `provider_id=openai-codex, model_id=gpt-5.1, harness_id=pi-coding-agent, harness_version=0.72.1` |
| `expected_identity` | `provider_id=openai-codex, model_id=gpt-5.1, harness_id=pi-coding-agent, harness_version=0.72.1` |
| Identity comparison | match (all four fields equal) |

Readiness is bounded, non-inference, and confirms the Pi SDK loads,
the `openai-codex` lane is registered, the model `gpt-5.1` resolves,
the canonical harness identity resolves, and the stored
`~/.pi/agent/auth.json` `openai-codex` entry is structurally present
(`authStorage.hasAuth` reports true). Readiness does NOT establish
OAuth token validity, provider reachability, or provider entitlement.

## Live invocation result

| Field | Value |
| --- | --- |
| Live entry point | `guardian.pi.invocation.invoke_guardian_authorized_pi` |
| Wrapper mode | `codex_runner/src/agent-wrapper.js guardian-authorized-task` (canonical, unmodified) |
| Guardian authorization result | valid (zero policy-decision failure reasons) |
| Frozen authorization identity | `openai-codex / gpt-5.1 / pi-coding-agent / 0.72.1` |
| Granted permissions | `files.read` on `.` only — no `files.write` granted (read-only posture) |
| Prompt size | bounded, deterministic read-only request against the disposable fixture |
| `runner_call_count` | `1` (exactly one adapter call) |
| `retry_count` | `0` |
| `fallback_count` | `0` |
| `runtime_identity_established` | `false` |
| `session_initialized` | `false` |
| `provider_request_started` | `false` |
| `oauth_available` | `null` (the wrapper never reached the oauth check) |
| `actual_identity` | `null` |
| Identity comparison result | cannot compare — actual identity never reached |
| `return_code` | `null` |
| Outcome `ok` | `false` |
| Outcome `failure_reason` | `adapter_execution_failure` |
| Outcome `diagnostic_class` | `wrapper_unavailable` |
| Outcome `diagnostic_stage` | `runtime_load` |

The wrapper's `runAgent()` entered its catch block after the canonical
`loadPiSdk()` call returned successfully (the same call that succeeds
for `guardian-authorized-readiness` in the same invocation context).
The wrapper's catch reports `wrapper_unavailable` at `runtime_load`
because the caught exception is not a `Cannot find package` /
`Cannot find module` module-resolution error. Inspecting a sibling
diagnostic copy of the wrapper (kept only inside the proof scratch
directory, not committed) surfaces the underlying exception:

```
CE_L0_DEBUG: runAgent caught: ReferenceError: harnessId is not defined
CE_L0_DEBUG: stack=ReferenceError: harnessId is not defined
    at runAgent (agent-wrapper.js line ~330)
```

The wrapper's `runAgent()` declares `createAgentSession`,
`SessionManager`, `AuthStorage`, `ModelRegistry`, `createCodingTools`,
`getModel`, `getProviders` with `let` and then destructures
`harnessId, harnessVersion` from `await loadPiSdk()` into the same
identifiers without first declaring them. Under ES-module strict mode
this raises `ReferenceError: harnessId is not defined` before any
provider request starts. The `guardian-authorized-task` mode therefore
cannot deliver a live invocation in its current canonical form.

The determinism of the failure (same exception on every run, same
`runtime_load` stage classification, no provider request observed,
no fallback or retry attempted) classifies this as a bounded substrate
defect, not an environmental flake.

## Target posture — pre vs post

Pre-invocation snapshot (recorded immediately before the live call):

| Field | Value |
| --- | --- |
| `HEAD` | `6c59cdf4ebd48d285659d886a9d6b1617f62b04b` |
| `git status --porcelain` | empty |
| `test_value.py` SHA-256 | `25a80c09c7ceea64955c10f39b012ef48f4a6526fe7e4e7064527af9548170cb` |
| `README.md` SHA-256 | `6905cfd87fe99bffcbb8147d38aaacbfc332d323ebec09c63f90371b579d3d94` |
| `src/value.py` SHA-256 | `4a21b3eaee15469b642cb35ef536c928f9a0ac67592872a306935ba755be714f` |

Post-invocation snapshot (recorded immediately after the live call):

| Field | Value |
| --- | --- |
| `HEAD` | `6c59cdf4ebd48d285659d886a9d6b1617f62b04b` |
| `git status --porcelain` | empty |
| `test_value.py` SHA-256 | `25a80c09c7ceea64955c10f39b012ef48f4a6526fe7e4e7064527af9548170cb` |
| `README.md` SHA-256 | `6905cfd87fe99bffcbb8147d38aaacbfc332d323ebec09c63f90371b579d3d94` |
| `src/value.py` SHA-256 | `4a21b3eaee15469b642cb35ef536c928f9a0ac67592872a306935ba755be714f` |

Target posture result: **unchanged**. Git HEAD identical, working tree
clean, every file hash identical. No unauthorized filesystem mutation
occurred. No Git commit, push, merge, or PR was performed inside the
proof target. No durable Codexify state was written.

## Receipt validation result

Not produced — the live invocation did not reach the receipt-emission
stage because `runAgent()` raised before any provider request began.
The canonical `validate_receipt_against_envelope` and
`validate_harness_result_against_receipt` validators could not be
exercised against real evidence.

This is expected and bounded: the rail fail-closed before producing
any provider-backed evidence, so there is nothing to validate against
the envelope, and the rail's own `receipt_status` path was not reached.

## Harness-Result validation result

Not produced. Same reason as §Receipt validation result.

## Redaction result

| Check | Result |
| --- | --- |
| Token values | absent from proof |
| Authorization headers | absent from proof |
| Cookies | absent from proof |
| Session contents | absent from proof |
| Refresh / access tokens | absent from proof |
| Raw credential records | absent from proof |
| Raw secret-shaped stderr / stdout | absent from proof |
| Environment dumps | absent from proof (only bounded `PI_*` env keys recorded) |

Only the bounded classification, the non-secret identity metadata
(provider_id, model_id, harness_id, harness_version), the bounded
counters, and the bounded failure class / stage appear in this
artifact. The proof never queried or copied the contents of
`~/.pi/agent/auth.json`.

## First bounded failure

| Field | Value |
| --- | --- |
| Deepest successfully reached stage | `runtime_load` (the wrapper's `loadPiSdk()` succeeded; `runAgent()` failed before any provider request) |
| Canonical bounded failure class | `wrapper_unavailable` |
| Canonical bounded failure stage | `runtime_load` |
| Runtime identity established | `false` |
| Session initialization occurred | `false` |
| Provider request started | `false` |
| Return code | `null` (wrapper emitted JSON envelope only) |
| Runner call count | `1` |
| Retry count | `0` |
| Fallback count | `0` |
| Underlying exception (sibling debug copy only) | `ReferenceError: harnessId is not defined` in `runAgent()`, raised when destructuring `await loadPiSdk()` without prior `let harnessId; let harnessVersion;` declarations |

`NEXT_TASK_REQUIRED=repair codex_runner/src/agent-wrapper.js runAgent() harnessId/harnessVersion destructuring`

## Explicit non-claims

This proof does NOT establish:

- current OAuth token validity (only structural presence is reflected by
  `authStorage.hasAuth`);
- provider reachability;
- provider entitlement;
- any successful Pi-backed provider turn;
- `GUARDIAN_PI_LIVE_READY`;
- any change to `docs/architecture/00-current-state.md`;
- any change to ADR-066, ADR-068, or any other ADR;
- any change to the Campaign Engine provider-free runtime;
- any change to release posture or Beta support class;
- any successful mutation by the harness (none was attempted because
  read-only posture was enforced).

## ADR impact

`No ADR impact`

Aligned with existing ADR(s):

- ADR-020 Guardian-Mediated Coding Agent Execution Contract
- ADR-066 Campaign Engine Runtime Recovery Contract
- ADR-068 Campaign Engine Live Role Execution Contract
- Pi Invocation Boundary Contract (`docs/architecture/pi-invocation-boundary-contract.md`)
- Agent Tool Loop Contract
- Runtime Protocol Token Contract
- Guardian delegation contracts

This proof exercises the canonical, already-accepted Guardian/Pi
execution seam and surfaces a bounded substrate defect in the live
wrapper's `runAgent()` path. It does not create or modify any
authority, identity, persistence, provider-routing, retry, fallback, or
Campaign Engine semantics. No ADR was created or modified.

## Security ledger

| Count | Value |
| --- | --- |
| Provider inference requests | `0` (the `provider_request_started` flag is `false`; no provider request ever began) |
| Model prompts | `0` |
| OAuth login attempts | `0` |
| OAuth refresh attempts | `0` |
| Credential mutations | `0` |
| Real package mutations | `0` (no Pi source patched, no Codexify source patched, no fixture source patched) |
| Credential-value outputs | `0` |
| Credential-file hashes emitted | `0` |
| Retries | `0` |
| Fallbacks | `0` |
| Successful live invocations | `0` |
| Bounded BLOCKED results | `1` |

## Acceptance criteria (spec-mapped)

| Spec criterion | Status |
| --- | --- |
| CE-L0 evaluated against current source truth | satisfied (HEAD `966664119`, merge-base == `origin/main`) |
| Exactly one proof artifact added | satisfied (this file) |
| No implementation code changed | satisfied (no tracked file modified) |
| No Campaign Engine code changed | satisfied |
| Existing Pi regression tests green before live qualification | satisfied (56 / 56) |
| Authorized readiness ran before inference | satisfied (`deepest_stage=auth_available`) |
| Provider / model / harness identity explicit and frozen | satisfied |
| Live path uses `invoke_guardian_authorized_pi` | satisfied |
| Guardian remains the authority boundary | satisfied |
| No direct provider bypass | satisfied |
| At most one live provider-backed invocation occurred | satisfied (zero provider invocations; the rail fail-closed at `runtime_load`) |
| No retries | satisfied |
| No fallback | satisfied |
| Actual runtime identity inspected rather than assumed | satisfied (rail confirmed identity never reached, `actual_identity=null`) |
| Target posture checked before and after | satisfied (HEAD and hashes identical pre/post) |
| Pi Receipt and Harness Result provenance validated | not produced — wrapper failed before evidence emission; bounded blocker recorded |
| Credential material absent from durable proof | satisfied |
| PASS emits `GUARDIAN_PI_LIVE_READY` | not applicable — result is BLOCKED |
| BLOCKED does NOT emit that token | satisfied (token omitted) |
| BLOCKED does NOT expand into repair work | satisfied (no source file modified; only proof + this artifact) |
| No release-support claim changed | satisfied |
| Campaign Engine untouched | satisfied |

## Documentation follow-through

Only this proof artifact is committed:

`docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l0-guardian-pi-live-invocation-proof.md`

No other file in `docs/architecture/`, `docs/Campaign/`,
`docs/architecture/proofs/`, or anywhere else in the repository was
modified by this proof. The proof scratch directory under
`.hermes/proofs/ce-l0-2026-08-26/` is intentionally outside the
authorized write path and is not part of the commit; it is preserved
for forensic re-runs only.

A future CE-L1 Task Spec may cite this proof after the substrate repair
upgrades CE-L0 from BLOCKED to PASS.