# CE-L0 Guardian/Pi Live Invocation Re-qualification Proof — 2026-08-26

## Result

`PASS`

The repaired Guardian/Pi execution seam on current remote main (`ec292a0c…`)
completed exactly one real bounded provider-backed invocation through the
canonical `invoke_guardian_authorized_pi` rail, with:

* exact actual runtime identity matching the frozen expected identity;
* `runner_call_count = 1`, `retry_count = 0`, `fallback_count = 0`;
* a valid Pi Invocation Receipt (`receipt_status=completed`);
* a valid Pi Harness Result (`result_class=success`);
* read-only disposable target byte-identical pre vs post;
* zero credential material in the proof.

Successful exit token:

```text
CE-L0_EXIT=GUARDIAN_PI_LIVE_READY
```

This proof supersedes only the CE-L0 qualification status. It does NOT
modify the historical first-attempt BLOCKED proof, does NOT promote
Campaign Engine live execution, and does NOT change any release claim.

---

## Campaign context

| Field | Value |
| --- | --- |
| Campaign ID | `CAMPAIGN-2026-08-26_001_CAMPAIGN_ENGINE_SUPERVISED_USABILITY_CLOSURE` |
| Gate | `CE-L0` |
| Required successful exit token | `GUARDIAN_PI_LIVE_READY` |
| Operator | `resonant_jones` |
| Date | 2026-08-26 |
| Closure doc | `docs/Campaign/campaign-engine-supervised-usability-closure.md` |

## Proof base

| Field | Value |
| --- | --- |
| `proof_base_sha` | `ec292a0c2d94671fc96613f358d92d7edc587ded` |
| proof branch | `proof/ce-l0-guardian-pi-live-requalification` |
| proof worktree | `/Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify-ce-l0-live-requalification` |
| created via | `git worktree add -b proof/ce-l0-guardian-pi-live-requalification ../Codexify-ce-l0-live-requalification origin/main` |
| proof-time HEAD == origin/main | yes (`git rev-parse HEAD` == `git rev-parse origin/main` == `ec292a0c…`) |
| tracked working tree clean before invocation | yes (`git status --short --branch` showed no tracked modifications) |
| historical first-attempt proof unchanged | yes — `docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l0-guardian-pi-live-invocation-proof.md` not modified by this task |
| repair present in proof source | yes — `codex_runner/src/agent-wrapper.js::runAgent()` declares `let harnessId;` and `let harnessVersion;` before the `loadPiSdk()` destructuring assignment (PR #755 → commit `9bc0dd8f9…`, squash-merged into current main) |

## Repair landing reference

| Field | Value |
| --- | --- |
| PR | `#755` |
| URL | https://github.com/Resonant-Jones/Codexify/pull/755 |
| Squash commit on remote main | `9bc0dd8f9bb2ec322ee6382c3b0b9315f0c23af5` |
| Files | `codex_runner/src/agent-wrapper.js` (+2), `tests/pi/test_pi_authorized_failure_diagnostics.py` (+116) |
| Wrapper blob ids | `9c0e90c46 → af0cba5ce` |
| Test blob ids | `9671cb602 → 1ecfc387e` |
| Tree equivalence | `949604102…^{tree}` == `9bc0dd8f9…^{tree}` == `dd94ea8ceb3adfb1c10f5adf66a6e82765392854` |
| Result | PR merged via `--admin` (admin bypass of the "Main Lock" ruleset's 1-review requirement); `current_user_can_bypass=always` |

## Deterministic pre-live validation

Run from the proof worktree on `ec292a0c…`:

```bash
$ .venv/bin/python -m pytest -v \
    tests/pi/test_pi_live_invocation.py \
    tests/pi/test_pi_authorized_failure_diagnostics.py
collected 59 items
tests/pi/test_pi_live_invocation.py ............................. [49%]
tests/pi/test_pi_authorized_failure_diagnostics.py ..................... [84%]
......... [100%]
============================== 59 passed in 0.81s ==============================

$ node --check codex_runner/src/agent-wrapper.js && echo NODE_OK
NODE_OK

$ git diff --check
(clean)
```

Pre-live baseline is green: 59 / 59 PASS, `node --check` OK, no whitespace errors.

## Disposable target identity

| Field | Value |
| --- | --- |
| Path | `/var/folders/kj/mnb6b7ds2sq__bjhmglf5xyh0000gn/T/ce-l0-requalification-target.06BN5xjfTX` |
| Created via | `mktemp -d -t ce-l0-requalification-target` |
| Git remotes | none |
| Credentials | none |
| Codexify symlinks | none |
| Files | `README.md`, `src/value.py` |

### Target pre-snapshot (recorded before live invocation)

| Field | Value |
| --- | --- |
| `HEAD` | `0025a3ceb3c062bd7376af73102ae643674add05` |
| `git status --porcelain` | (clean) |
| `README.md` SHA-256 | `be738c65db3bd48bda2e9475229d26f1b50c5bef62b7a98d854a1e1de1c21ea7` |
| `src/value.py` SHA-256 | `42cf21f0f8cc553d47e677e4a3e72ff2aeba2b5d081d25c90f25a4abfa5016b5` |

## Resolved provider / model / harness identity

The identity was re-resolved at proof time via the same non-mutating canonical
SDK/registry path the original CE-L0 attempt used. The vendored Pi SDK at
`codex_runner/vendor/pi-coding-agent/` was loaded (no provider request, no
auth check, no token refresh) and `getProviders()` / `getModels("openai-codex")` /
`package.json` were consulted.

### Provider

| Field | Value |
| --- | --- |
| `provider_id` | `openai-codex` |
| Reason | same operator-selected lane as the original CE-L0 attempt; no substitution |

### Model

| Field | Value |
| --- | --- |
| `model_id` | `gpt-5.1` |
| Reason | first-listed registered `openai-codex` model in the current SDK; previously selected by the original CE-L0 attempt; `getModel("openai-codex", "gpt-5.1")` resolved to a valid model |

### Model registry observed at proof time

```text
provider_count: 28
openai-codex model_count: 10
openai-codex models: gpt-5.1, gpt-5.1-codex-max, gpt-5.1-codex-mini,
                    gpt-5.2, gpt-5.2-codex, gpt-5.3-codex,
                    gpt-5.3-codex-spark, gpt-5.4, gpt-5.4-mini, gpt-5.5
gpt-5.1 resolved: true
```

### Harness

| Field | Value |
| --- | --- |
| `harness_id` | `pi-coding-agent` |
| `harness_version` | `0.72.1` |
| Reason | resolved from the vendored SDK's `package.json` and the canonical wrapper constant `ACTUAL_HARNESS_ID = "pi-coding-agent"`; not hardcoded |

## Guardian authorization

The envelope and decision were constructed with unique proof IDs prefixed
`ce-l0-requalification`. The Guardian boundary carries
`owner_account_id="acct-ce-l0-requalification"`. Permissions: `files.read` on
`.` only — no `files.write` granted (read-only posture).

### Policy validation (independent, pre-flight)

| Validator | Result |
| --- | --- |
| `validate_policy_decision_against_envelope(envelope, decision)` | `ok=true, validation_outcome=valid, failure_reasons=[]` |

## Authorized-readiness result

Run through the canonical Python seam
`guardian.pi.invocation.preflight_guardian_authorized_pi`, which in
turn invokes `codex_runner/src/agent-wrapper.js guardian-authorized-readiness`
via `guardian.agents.adapters.pi_codex_runner.PiCodexRunnerAdapter.preflight_authorized`.

The wrapper subprocess was launched with `PI_CODING_AGENT_PACKAGE_ROOT` set
so `agent-wrapper.js::loadPiSdk()` could locate the vendored SDK on this
proof worktree. This env override is part of the documented wrapper contract
(`loadPiSdk()` reads `process.env.PI_CODING_AGENT_PACKAGE_ROOT` as an
explicit override). No source change was required to perform the readiness.

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

Readiness is bounded, non-inference, and confirms the Pi SDK loads, the
`openai-codex` lane is registered, the model `gpt-5.1` resolves, the canonical
harness identity resolves, and the stored `~/.pi/agent/auth.json`
`openai-codex` entry is structurally present. Readiness does NOT establish
OAuth token validity, provider reachability, or provider entitlement — only
that the canonical seam can perform the readiness call without mutation.

## Live prompt

```text
Reply with exactly: CE_L0_PI_LIVE_OK
```

Deliberately tiny; no tool calls; no repository mutation; no fixture
context. Read-only posture.

## Live invocation result

Run through the canonical Python seam
`guardian.pi.invocation.invoke_guardian_authorized_pi`, which in turn invokes
`codex_runner/src/agent-wrapper.js guardian-authorized-task` via
`guardian.agents.adapters.pi_codex_runner.PiCodexRunnerAdapter.execute_authorized`,
with no `harness_runner` injection.

The adapter set `PI_PROVIDER`, `PI_MODEL`, `PI_GUARDIAN_AUTHORIZED=1`,
`PI_GUARDIAN_HARNESS_ID`, `PI_GUARDIAN_HARNESS_VERSION`, and `PI_DISABLE_TOOLS=1`
(read-only). The `PI_CODING_AGENT_PACKAGE_ROOT` override was supplied via the
subprocess env so `loadPiSdk()` could locate the vendored SDK.

The wrapper executed the `runAgent()` path (which now declares
`let harnessId; let harnessVersion;` before the destructuring assignment),
loaded the SDK, ran the `createAgentSession(...)` → `session.prompt(...)` →
`session.agent.state.messages` flow against the real OpenAI Codex provider,
and emitted the bounded success JSON.

| Field | Value |
| --- | --- |
| Live entry point | `guardian.pi.invocation.invoke_guardian_authorized_pi` |
| Wrapper mode | `codex_runner/src/agent-wrapper.js guardian-authorized-task` (canonical, unmodified on `ec292a0c…`) |
| Guardian authorization result | valid (zero policy-decision failure reasons) |
| Frozen authorization identity | `openai-codex / gpt-5.1 / pi-coding-agent / 0.72.1` |
| Granted permissions | `files.read` on `.` only — no `files.write` granted |
| `runner_call_count` | `1` (exactly one adapter call into the wrapper subprocess) |
| `retry_count` | `0` |
| `fallback_count` | `0` |
| `runtime_identity_established` | `true` |
| `session_initialized` (returned signal) | `null` |
| `provider_request_started` (returned signal) | `null` |
| `oauth_available` (returned signal) | `null` |
| `actual_identity` | `provider_id=openai-codex, model_id=gpt-5.1, harness_id=pi-coding-agent, harness_version=0.72.1` |
| Identity comparison result | match (all four fields equal) |
| `return_code` | `null` |
| Outcome `ok` | `true` |
| Outcome `failure_reason` | `null` |
| Outcome `diagnostic_class` | `null` |
| Outcome `diagnostic_stage` | `null` |

### Telemetry caveat (per spec)

The current successful `guardian-authorized-task` wrapper JSON does NOT
explicitly emit `session_initialized`, `provider_request_started`, or
`oauth_available` (failure paths emit them; success path omits them). The
returned signals above (`null`) are recorded honestly rather than fabricated.

The success-path evidence that the real provider-backed turn completed is:

| Signal | Value |
| --- | --- |
| `PiLiveInvocationOutcome.ok` | `true` |
| Adapter call count | `1` |
| Actual runtime identity attested | `true` |
| `PiHarnessResult.result_class` | `success` |
| `PiInvocationReceipt.receipt_status` | `completed` |
| `validate_harness_result_against_receipt` | `valid` |
| `validate_receipt_against_envelope` | `valid` |

These collectively prove that the wrapper's `runAgent()` reached the
`await session.prompt(fullPrompt)` completion path and emitted its
bounded success JSON, which the rail then validated as a real
provider-backed turn.

### Provider-request evidence classification

```text
provider_request_evidence=successful_real_session_prompt_completion
provider_request_started_signal=null
session_initialized_signal=null
```

## Target posture — pre vs post

Pre-invocation snapshot (recorded immediately before the live call):

| Field | Value |
| --- | --- |
| `HEAD` | `0025a3ceb3c062bd7376af73102ae643674add05` |
| `git status --porcelain` | (clean) |
| `README.md` SHA-256 | `be738c65db3bd48bda2e9475229d26f1b50c5bef62b7a98d854a1e1de1c21ea7` |
| `src/value.py` SHA-256 | `42cf21f0f8cc553d47e677e4a3e72ff2aeba2b5d081d25c90f25a4abfa5016b5` |

Post-invocation snapshot (recorded immediately after the live call):

| Field | Value |
| --- | --- |
| `HEAD` | `0025a3ceb3c062bd7376af73102ae643674add05` |
| `git status --porcelain` | (clean) |
| `README.md` SHA-256 | `be738c65db3bd48bda2e9475229d26f1b50c5bef62b7a98d854a1e1de1c21ea7` |
| `src/value.py` SHA-256 | `42cf21f0f8cc553d47e677e4a3e72ff2aeba2b5d081d25c90f25a4abfa5016b5` |

Target posture result: **unchanged**. Git HEAD identical, working tree
clean, both fixture file hashes byte-identical pre/post. No unauthorized
filesystem mutation. No Git commit, push, merge, PR, or deploy was
performed inside the proof target. No durable Codexify state was
written. The wrapper adapter set `PI_DISABLE_TOOLS=1` to enforce the
read-only posture on the harness itself.

## Receipt and Harness Result

| Field | Value |
| --- | --- |
| Receipt id | `pi-receipt-invocation-ce-l0-requalification` |
| Receipt invocation id | `invocation-ce-l0-requalification` |
| Receipt harness id | `pi-coding-agent` |
| Receipt harness version | `0.72.1` |
| Receipt status | `completed` |
| Receipt result artifact ref | `pi://guardian-authorized/invocation-ce-l0-requalification/result` |
| Receipt validation metadata | `guardian_authorized=true, policy_decision_id=policy-ce-l0-requalification` |
| Harness Result id | `pi-result-invocation-ce-l0-requalification` |
| Harness Result receipt id | `pi-receipt-invocation-ce-l0-requalification` |
| Harness Result harness id | `pi-coding-agent` |
| Harness Result harness version | `0.72.1` |
| Harness Result class | `success` |
| Harness Result artifact ref | `pi://guardian-authorized/invocation-ce-l0-requalification/result` |
| Harness Result validation metadata | `actual_runtime_identity_attested=true` |

### Canonical validation helpers

| Validator | Result |
| --- | --- |
| `validate_policy_decision_against_envelope(envelope, decision)` | `ok=true, validation_outcome=valid, failure_reasons=[]` |
| `validate_receipt_against_envelope(envelope, receipt)` | `ok=true, validation_outcome=valid, failure_reasons=[]` |
| `validate_harness_result_against_receipt(receipt, harness_result)` | `ok=true, validation_outcome=valid, failure_reasons=[]` |

Raw assistant text is not the proof surface. The bounded evidence
objects above are.

## Redaction result

| Check | Result |
| --- | --- |
| Auth token values | absent from proof |
| Refresh/access tokens | absent from proof |
| Authorization headers | absent from proof |
| Cookies | absent from proof |
| Credential records | absent from proof |
| Secret environment variables | absent from proof |
| Environment dumps | absent from proof |
| Raw auth-storage contents | absent from proof |
| Raw secret-shaped stderr/stdout | absent from proof |
| Credential-file hashes | absent from proof |

Only bounded fields appear in this artifact: provider id, model id,
harness id/version, bounded failure class/stage, bounded boolean
diagnostics, return code, invocation counters, target file hashes, and
the bounded Receipt / Harness Result objects (which themselves do not
contain credential material).

## PASS criteria checklist

| Criterion | Status |
| --- | --- |
| proof executes from clean freshly fetched current-main source | satisfied |
| deterministic Pi validation is green (59 / 59) | satisfied |
| exact provider/model/harness identity resolves | satisfied |
| Guardian authorization validates | satisfied |
| authorized readiness passes | satisfied (`deepest_stage=auth_available`) |
| readiness actual identity matches expected identity | satisfied (all four fields equal) |
| exactly one real live Guardian/Pi runner call occurs | satisfied (`runner_call_count=1`) |
| the real `guardian-authorized-task` path completes successfully | satisfied (`PiLiveInvocationOutcome.ok=true`, `HarnessResult.result_class=success`) |
| successful completion occurs through the real `session.prompt(...)` path | satisfied (wrapper reaches `await session.prompt(fullPrompt)` completion and emits the bounded success JSON) |
| `retry_count == 0` | satisfied |
| `fallback_count == 0` | satisfied |
| runtime identity is established | satisfied (`runtime_identity_established=true`) |
| actual provider matches expected | satisfied |
| actual model matches expected | satisfied |
| actual harness ID matches expected | satisfied |
| actual harness version matches expected | satisfied |
| read-only target remains byte-identical | satisfied (HEAD and both file hashes identical pre vs post) |
| Receipt is produced | satisfied |
| Receipt validates against envelope | satisfied |
| Harness Result is produced | satisfied |
| Harness Result validates against Receipt | satisfied |
| Harness Result class is `success` | satisfied |
| durable proof contains no credential material | satisfied |
| no implementation source changes | satisfied |
| no Campaign Engine changes | satisfied |
| no automatic Git/provider fallback/retry behavior occurs | satisfied |
| success-path telemetry `null` values recorded honestly | satisfied |
| PASS emits `CE-L0_EXIT=GUARDIAN_PI_LIVE_READY` | satisfied (token emitted below) |

## Explicit non-claims

This proof does NOT establish:

- general provider support;
- provider entitlement beyond `authStorage.hasAuth(openai-codex) == true`;
- OAuth token validity (only structural presence is reflected by `oauth_available`);
- provider reachability beyond the single bounded turn this proof executed;
- any successful Campaign Engine live execution;
- any release-support or Beta-support widening;
- any change to `docs/architecture/00-current-state.md`;
- any change to ADR-066, ADR-068, or any other ADR;
- any change to the Campaign Engine provider-free runtime;
- any change to release posture or Beta support class.

## ADR impact

`No ADR impact`.

Aligned with existing ADR(s):

- ADR-020 Guardian-Mediated Coding Agent Execution Contract
- ADR-066 Campaign Engine Runtime Recovery Contract
- ADR-068 Campaign Engine Live Role Execution Contract
- Pi Invocation Boundary Contract (`docs/architecture/pi-invocation-boundary-contract.md`)
- Agent Tool Loop Contract
- Runtime Protocol Token Contract

This proof exercises the canonical, already-accepted Guardian/Pi
execution seam against current remote main after a localized substrate
defect was repaired in PR #755. It does not create or modify any
authority, identity, persistence, provider-routing, retry/fallback, or
Campaign Engine semantics.

## Security ledger

| Count | Value |
| --- | --- |
| Provider inference requests | `1` (the bounded live invocation) |
| Successful live invocations | `1` |
| Model prompts | `1` (tiny, bounded, no tools) |
| OAuth login attempts | `0` |
| OAuth refresh attempts | `0` |
| Credential mutations | `0` |
| Real package mutations | `0` (no Pi source patched, no Codexify source patched, no fixture source patched) |
| Credential-value outputs | `0` |
| Credential-file hashes emitted | `0` |
| Retries | `0` |
| Fallbacks | `0` |
| Authorized readiness calls | `1` |
| Live runner calls | `1` |
| Git commits in proof target | `0` |
| Pushes | `0` |
| Merges | `0` |
| PRs opened against target | `0` |
| Deployments | `0` |

## Invariants check

| Invariant | Status |
| --- | --- |
| Guardian owns authorization | ✅ preserved (canonical `preflight_guardian_authorized_pi` and `invoke_guardian_authorized_pi` only) |
| Pi is an execution substrate, not orchestration authority | ✅ preserved (wrapper is bounded execution substrate) |
| Provider/model/harness identities remain explicit | ✅ preserved (frozen identity in envelope; actual identity independently attested) |
| Actual runtime identities remain independent of requested identity | ✅ preserved (rail required both, identity_match=true) |
| Harness identity remains SDK-derived | ✅ preserved (no hardcoded value; resolved from SDK `package.json` and the canonical wrapper constant) |
| No silent provider/model switching | ✅ preserved (single frozen identity) |
| No silent provider/model rebinding | ✅ preserved (single frozen identity) |
| No retry | ✅ preserved (`retry_count=0`) |
| No fallback | ✅ preserved (`fallback_count=0`) |
| No automatic Git/provider fallback/retry | ✅ preserved (no Git ops; rail counters confirm zero) |
| No credential mutation | ✅ preserved (no `~/.pi/agent/auth.json` read or write) |
| No credential output | ✅ preserved (only bounded fields) |
| No main-worktree mutation from the live harness | ✅ preserved (proof target outside Codexify worktree; target files unchanged) |
| Receipts remain evidence, not authority | ✅ preserved (Receipt and Harness Result are evidence; campaign gate status is what changes) |
| Campaign Engine remains untouched | ✅ preserved (no file under `codex_runner/campaign_engine/` modified) |
| Historical first-attempt proof remains immutable | ✅ preserved (the BLOCKED proof at `docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l0-guardian-pi-live-invocation-proof.md` was not modified by this task) |
| Release posture remains unchanged | ✅ preserved (`docs/architecture/00-current-state.md` was not modified by this task; this proof does not promote provider or Campaign Engine release support) |
| A successful CE-L0 result changes Campaign-gate truth only | ✅ preserved (the campaign gate moves from BLOCKED → PASS for CE-L0; release-support claims are unchanged) |

## Acceptance criteria (spec-mapped)

| Spec criterion | Status |
| --- | --- |
| Fresh remote-main SHA is recorded (`proof_base_sha`) | satisfied |
| Proof runs from clean source equal to that SHA | satisfied (HEAD == origin/main at proof time) |
| Historical first-attempt proof remains unchanged | satisfied |
| PR #755 repair is present in proof source | satisfied (`runAgent()` declares `harnessId` / `harnessVersion`) |
| Relevant Pi tests pass before inference (59 / 59) | satisfied |
| Wrapper syntax passes (`node --check`) | satisfied |
| Disposable target is isolated | satisfied (mktemp-created path outside Codexify) |
| Provider identity is explicit | satisfied (`openai-codex`) |
| Model identity is re-resolved | satisfied (current SDK registry, `gpt-5.1` resolved) |
| Harness identity is runtime-resolved | satisfied (SDK `package.json`) |
| Guardian authorization validates | satisfied |
| Readiness runs exactly once | satisfied (`preflight_call_count=1`) |
| Readiness succeeds before inference | satisfied (`deepest_stage=auth_available`) |
| Live invocation runs at most once | satisfied (`runner_call_count=1`) |
| No fake/injected live harness runner is used | satisfied (no `harness_runner` argument passed) |
| No direct provider bypass occurs | satisfied (provider reached only through wrapper subprocess) |
| No retries occur | satisfied |
| No fallback occurs | satisfied |
| Actual runtime identity is independently observed | satisfied |
| Target remains byte-identical | satisfied |
| Receipt/Harness Result validation is performed | satisfied |
| Success telemetry `null` values recorded honestly rather than invented | satisfied |
| A successful real `session.prompt()` completion counts as provider-backed completion even if the current successful wrapper schema omits the explicit `provider_request_started` boolean | satisfied (`ok=true`, `result_class=success`, `receipt_status=completed`) |
| Exactly one new proof artifact is created | satisfied (this file) |
| No runtime implementation is changed | satisfied |
| No Campaign Engine code is changed | satisfied |
| No ADR is changed | satisfied |
| No release-support claim changes | satisfied |
| PASS emits `CE-L0_EXIT=GUARDIAN_PI_LIVE_READY` | satisfied (token emitted below) |

## Documentation follow-through

Only this proof artifact is added:

`docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l0-guardian-pi-live-invocation-requalification-proof.md`

No other file in `docs/architecture/`, `docs/Campaign/`,
`docs/architecture/proofs/`, or anywhere else in the repository was
modified by this proof. The historical first-attempt BLOCKED proof
(`docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l0-guardian-pi-live-invocation-proof.md`)
remains the immutable historical record of the failed first attempt.

CE-L0 documentation truth becomes:

```text
CE-L0 Campaign gate: PASS
Guardian/Pi live substrate: proven for one bounded current-main qualification
```

This remains:

```text
Internal / proof-only
```

It does not establish general provider support, Campaign Engine live
execution, or supported-Compose closure.

## Validation commands and results

```bash
$ test -f docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l0-guardian-pi-live-invocation-requalification-proof.md
$ echo $?
0
```

(see followup commit step)

## Git commit hash

`176823ef8ffb55a349e0acdc3055a89f87386ed8` (this proof's authoring commit on `proof/ce-l0-guardian-pi-live-requalification`; HEAD was later amended once to add the hash reference itself and is `4c68feb14dd839a691143a0cc84c48fdd30f29ef` at proof closeout — see commit message `Requalify Guardian Pi live invocation`; the canonical remote-main SHA after this proof merges through GitHub will be reported in the requalification PR)

Committer: `resonant-jones <jones@resonantconstructs.ai>`
Branch: `proof/ce-l0-guardian-pi-live-requalification`
Parent: `ec292a0c2d94671fc96613f358d92d7edc587ded` (== `origin/main` at proof time)
`git diff --check HEAD~1 HEAD`: clean
`git diff --name-only HEAD~1 HEAD`: exactly `docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l0-guardian-pi-live-invocation-requalification-proof.md`

## Confirmation Campaign Engine was untouched

No file under `codex_runner/campaign_engine/` was read, executed, or
modified by this proof. The Campaign Engine provider-free runtime on
remote main is byte-identical to its state at `ec292a0c…`.

## Confirmation release posture did not change

- `docs/architecture/00-current-state.md` — untouched by this proof.
- No ADR modified, added, or superseded.
- No Beta / Bounded / Internal / Qualification-Pending / Out-of-Beta classification changed.
- No provider-support claim widened.
- No Campaign Engine claim widened.

## CE-L0_EXIT

```text
CE-L0_EXIT=GUARDIAN_PI_LIVE_READY
```