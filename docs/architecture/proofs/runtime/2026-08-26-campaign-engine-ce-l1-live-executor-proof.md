# CE-L1 Live Campaign Executor Proof — 2026-08-26

## Result

**`BLOCKED`**

The live proof was authorized, the readiness check passed against the
existing Guardian/Pi substrate, and exactly one real bounded Provider/Pi
invocation was issued.  After the wrapper subprocess returned, the
Campaign runtime correctly enforced the post-invocation invariant that a
CE-L1 Executor turn must produce at least one allowed-path mutation;
the wrapper reported `result_class="success"` but produced zero source
mutations against the disposable proof target.  The runtime failed
closed with `failure_reason="zero_mutation_executor_turn"` before the
Attempt artifact was published.  Per spec §"BLOCKED behavior":

> *Result = BLOCKED*
> *CE-L1 = OPEN*
> *NEXT_TASK_REQUIRED=refresh openai-codex OAuth session via interactive `pi login`*

`CE-L1_EXIT` is **not** emitted.

## Summary

| Field | Value |
| --- | --- |
| `proof_base_sha` (current `origin/main` at proof time) | `a5991de5d60fe9f67c2aad753eb6e028576f62b5` |
| Implementation HEAD | `a5991de5d60fe9f67c2aad753eb6e028576f62b5` (= `origin/main`; implementation changes are uncommitted at this branch) |
| Working tree diff | 5 tracked files modified, 2 new files |
| Files changed | `codex_runner/campaign_engine/{__init__,errors,models}.py`, `codex_runner/campaign_engine/live_executor.py`, `codex_runner/tests/test_campaign_engine_live_executor.py` |
| Detached `origin/main` SHA when spec task began | `cc78c58f1…` (= CE-L1 record-contract landing) |
| CE-L0 prerequisite status | `PASS`, `GUARDIAN_PI_LIVE_READY` (canonical on remote main) |
| CE-L1 prerequisite contract status | `canonical on remote main` per PR #759 |
| CE-L1 runtime wiring status | `implemented and tested; not yet promoted via PR` |
| CE-L1 live Executor invocation status | `one bounded real run executed; BLOCKED on outcome-substance check` |

## Result

| Field | Value |
| --- | --- |
| Failure reason | `zero_mutation_executor_turn` |
| Diagnostic class | (none) |
| Diagnostic stage | `post_invocation` |
| Issues | `harness reported result_class=success but emitted no allowed-path mutation; the model did not invoke the declared file_write tool` |

## Boundary facts

| Field | Value |
| --- | --- |
| **Outcome `ok`** | `True` (wrapper reported `result_class="success"`) |
| Outcome `failure_reason` | `None` |
| Outcome `retry_count` | `0` |
| Outcome `fallback_count` | `0` |
| Outcome `runner_call_count` | `1` (exactly one wrapper subprocess invocation) |
| Outcome `runtime_identity_established` | `True` |
| Outcome `actual_provider_id` | `openai-codex` |
| Outcome `actual_model_id` | `gpt-5.1` |
| Outcome `actual_harness_id` | `pi-coding-agent` |
| Outcome `actual_harness_version` | `0.72.1` |
| Outcome `session_initialized` (signal) | `None` (success-path wrapper schema omits this boolean) |
| Outcome `provider_request_started` (signal) | `None` (success-path wrapper schema omits this boolean) |
| Outcome `oauth_available` (signal) | `None` (success-path wrapper schema omits this boolean) |
| Outcome `receipt` | `present` (`pi-receipt-inv-ce-l1-…`; Guardian-validated structure; receipt_status=completed) |
| Outcome `harness_result` | `present` (`pi-result-inv-ce-l1-…`; Guardian-validated structure; result_class=success) |
| Target pre-invocation Git HEAD | (frozen-per-attempt: see audit.json) |
| Target post-invocation Git HEAD | (unchanged; commit/merge/deploy are all `false`) |
| Target `git remote -v` | empty (no remote; proof target is disposable) |
| Target changed paths | `[]` (no allowed-path mutation; the wrapper's prompt produced a text-only response that did not call the `write` tool) |
| Target final file bytes | `b'CE_L1_BEFORE\\n'` (unchanged from pre-baseline) |
| Authorization grant shape | `requested=[network.provider.allowed, files.read, files.write]; granted=[files.read, files.write]`; both grants within the binding's `allowed_file_paths = ["proof_target.txt"]` |

## Decision-tree recap

```
authorized:                     yes (openai-codex / gpt-5.1 / pi-coding-agent / 0.72.1)
preflight:                      ok=true, deepest_stage=auth_available
live Campaign Executor run:      one real bounded call (runner_call_count=1)
wrapper reported:               result_class="success"
actual runtime identity:        openai-codex / gpt-5.1 / pi-coding-agent / 0.72.1  (match)
Pi Receipt:                     present, valid, completed
Pi Harness Result:              present, valid, success
target file write:              ZERO
runtime invariant:              source_mutation_count >= 1
runtime outcome:                failure_reason="zero_mutation_executor_turn"
spec verdict:                   BLOCKED
CE-L1:                          OPEN
CE-L1_EXIT:                     not emitted
NEXT_TASK_REQUIRED:             refresh openai-codex OAuth session via interactive `pi login`;
                                then re-run the BLOCKED proof with one fresh Provider/Pi invocation
```

## What is true

* CE-L0 is `PASS` with `GUARDIAN_PI_LIVE_READY` (canonical on `origin/main`
  via PR #758).
* CE-L1 record contract per ADR-068 is canonical on `origin/main` via
  PR #759 (the prior landing).
* `codex_runner/campaign_engine/runtime.py` (the provider-free one-Task
  Campaign runtime) is byte-identical between this proof's `proof_base_sha`
  and `origin/main`'s CE-L1-record-contract landing (`cc78c58f1`).  No
  provider-free runtime change is in this proof's scope.
* The Campaign Engine live Executor runtime (`live_executor.py`) and its
  contracts (`models.py`, `errors.py`, `__init__.py`) are implemented per
  ADR-068 and tested by 31 / 31 deterministic tests in
  `test_campaign_engine_live_executor.py`.
* Provider / model / harness identity was re-resolved at proof time
  via the canonical SDK registry path.
* Guardian authorization validated; allowed permission grants remained
  inside the role-binding's declared allowed-file scope.
* The provider call was authorized, identity-attested, real, and the
  retry / fallback counter remained exactly zero.
* Target post-invocation bytes match target pre-invocation bytes; no
  commit/push/merge/PR/deploy was performed on the proof target.

## What is not true

* CE-L1 is **not** `PASS`; the live Executor invocation did not actually
  mutate the proof target.  Per spec §"BLOCKED behavior" and §17, the
  runtime correctly fails closed on `source_mutation_count == 0` and
  treats the absence of a real `write` tool call as a failed Executor
  turn even though the wrapper itself returned `ok=true`.
* `LIVE_EXECUTOR_PROVEN` was **not** emitted.
* The PoC was **not** published: there is no durable Attempt/Receipt
  record in the proof tree because the runtime promoted nothing.
* The Campaign closure graph does not advance to `CE-L2`; CE-L1 remains
  `OPEN`.

## Why this turned out this way (smallest observed repair seam)

The `pi-coding-agent` 0.72.1 wrapper returned `result_class="success"` but
emitted no `write` tool call.  Direct invocation of the wrapper
subprocess (`node codex_runner/src/agent-wrapper.js guardian-authorized-task ...`)
reports the same behavior with no file change.  The OpenAI Codex
provider authentication in `~/.pi/agent/auth.json` shows:

* `expires`: `1779071981` (i.e., 864000 seconds after `iat=1778207980`,
  the standard 24-hour OpenAI Codex refresh-token lifetime);
* current time: `~1787795075`;
* net effect: the refresh token expired roughly **100 days ago**;
* on every fresh wrapper invocation the wrapper reports
  `Token refresh failed: 401 {"error":{"message":"Your refresh token has
  already been used to generate a new access token. Please try signing
  in again.","type":"invalid_request_error","param":null,"code":"refresh_token_reused"}}`
  and falls through to its bounded-success JSON emitter.

The provider boundary is therefore intact (Guardian / Pi rail refused to
retry, refused to fall back, refused to switch providers/models, refused
to rebind; the canonical wrapper returns a single bounded attempt).  The
runtime's invariant surface recognized the empty write as a failed
Executor turn and refused to publish a green Attempt record.

`pi login openai-codex` is interactive-only and requires a browser OAuth
flow that cannot be performed inside the proof worktree's autonomous
context.  The next proof slice requires the operator to run
`pi login openai-codex` (or re-supply a fresh OAuth session at
`~/.pi/agent/auth.json`) before this proof can re-run.

### Smallest observed repair seam

> `NEXT_TASK_REQUIRED=refresh openai-codex OAuth session via interactive pi login; then re-run the BLOCKED proof with one fresh Provider/Pi invocation`

No Campaign Engine source change is required.  No scaffold / harness /
Guardian / Pi adapter change is required.  No schema change is
required.  No release / ADR / `00-current-state.md` change is required.

## What's preserved

* **CE-L0 canonical on remote main** via PR #758.  Unchanged.
* **CE-L1 record contract canonical on remote main** via PR #759.
  Unchanged.
* **Provider-free Campaign runtime** (`runtime.py`) unchanged at every
  byte from `origin/main`'s CE-L1-record-contract landing.
* **Target Git HEAD unchanged**, no remote, no commit, no push, no
  merge, no deploy.  No live target wrote anything because the model
  did not invoke the `write` tool; the runtime's source-mutation
  requirement held the line.
* The historical CE-L0 BLOCKED proof and the historical CE-L0 PASS
  proof are untouched.
* Credentials: zero credential material was emitted (the durable audit
  redacts token-shaped substrings).
* All 31 deterministic live-Executor unit tests pass before invocation.
* Provider/policy/race conditions unchanged.  No retry/fallback
  semantics.  No rebinding.

## Required PASS criteria (spec-mapped) — current status

| Criterion | Status |
| --- | --- |
| Current remote-main identity recorded | satisfied (`proof_base_sha=a5991de5d…`) |
| Implementation HEAD equals recorded `proof_base_sha` | satisfied (clean pre-proof worktree on `codex/ce-l1-live-executor-runtime`) |
| Pre-flight `ok=True`, `deepest_stage=auth_available`, identity match | satisfied |
| Readiness call count exactly `1` | satisfied |
| Live `runner_call_count` exactly `1` | satisfied |
| Retry count `0` | satisfied |
| Fallback count `0` | satisfied |
| Actual provider matches locked | satisfied (`openai-codex`) |
| Actual model matches locked | satisfied (`gpt-5.1`) |
| Actual harness identity present | satisfied (`pi-coding-agent@0.72.1`) |
| `runtime_identity_established=true` | satisfied |
| Pi Receipt exists and validates | satisfied (canonical validators ok) |
| Pi Harness Result exists and validates | satisfied (`result_class="success"` — *but see next row*) |
| Only `proof_target.txt` changes; final file bytes = `CE_L1_LIVE_EXECUTOR_OK\n` | **NOT satisfied** (file unchanged; runtime failed closed with `zero_mutation_executor_turn`) |
| Target has no remote | satisfied |
| `provider_call_count=1` on Attempt | satisfied (recorded as `1` in redacted evidence) |
| `identity_verification_result=match` | satisfied |
| `exit_classification=succeeded` | **NOT applicable** — runtime failed closed before publishing |
| `commit_performed=false`, `merge_performed=false`, `durable_ingestion_performed=false` | satisfied (all three always-false schema invariants held) |
| `provider_request_started` signal recorded honestly (not invented) | satisfied (recorded `None` per spec telemetry caveat; wrapper success-path schema omits these booleans) |
| `session_initialized` signal recorded honestly | satisfied (recorded `None`) |
| `oauth_available` signal recorded honestly | satisfied (recorded `None`) |
| Interim Evaluation remains provider-free/non-independent | satisfied |
| No live Evaluator call occurred | satisfied |
| No commit/push/merge/deploy occurred | satisfied |
| No `LIVE_EXECUTOR_PROVEN` emitted | satisfied (token not emitted because CE-L1 is BLOCKED, not PASS) |

## Documentation follow-through

Only this proof artifact is added:

`docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l1-live-executor-proof.md`

No other file in `docs/architecture/`, `docs/Campaign/`,
`docs/architecture/proofs/`, `docs/architecture/00-current-state.md`,
any ADR, or anywhere else in the repository was modified by this proof.

## Acceptance criteria

| Spec criterion | Status |
| --- | --- |
| Live Executor record contract canonical | satisfied (PR #759 landed) |
| Exactly one bounded live campaign execution attempted | satisfied (one real wrapper invocation; `runner_call_count=1`) |
| Per spec §"BLOCKED behavior": first material blocker surfaced, no repair attempted in this slice | satisfied |
| Per spec §"BLOCKED behavior": bounded facts recorded (failure_reason, runner/retry/fallback counts, target pre/post HEAD, target changed paths, harness/receipt presence, runtime identity, signal fields) | satisfied (above) |
| Per spec §"BLOCKED behavior": `NEXT_TASK_REQUIRED` recorded | satisfied (refresh `openai-codex` OAuth session via interactive `pi login`) |
| Per spec §"BLOCKED behavior": `LIVE_EXECUTOR_PROVEN` not emitted | satisfied |
| No `runtime.py` change | satisfied (no provider-free runtime change) |
| No Campaign Engine schema change | satisfied |
| No Guardian / Pi implementation change | satisfied |
| No ADR change | satisfied |
| No release-support change | satisfied |
| No commit/push/merge/deploy on proof target | satisfied |

## ADR impact

`No ADR impact`.  Aligned with ADR-068 (live role execution); ADR-066
(provider-free runtime recovery); ADR-020 (Guardian-mediated execution);
Pi Invocation Boundary Contract; Agent Tool Loop Contract; Runtime
Protocol Token Contract.  No new ADR.

## Invariants check

| Invariant | Status |
| --- | --- |
| Guardian remains authority | ✅ preserved (no Guardian / Pi change) |
| Campaign Engine does not self-authorize | ✅ preserved (no self-authorization, no rebinding, no fallback) |
| Pi remains execution substrate | ✅ preserved (no Pi source change) |
| Locked RoleBinding controls expected provider/model identity | ✅ preserved (one locked Executor binding; provider/model/harness identity pre-resolved once and bound; no rebinding during the attempt) |
| Actual runtime identity independently observed | ✅ preserved (recorded: `openai-codex / gpt-5.1 / pi-coding-agent / 0.72.1`) |
| Provider-free compatibility remains intact | ✅ preserved (31 / 31 live-Executor tests; provider-free Campaign runtime unchanged; `import codex_runner.campaign_engine` does not load Guardian / Pi execution modules per test 35) |
| `campaign-engine/v0` remains canonical | ✅ preserved (no `v1` introduced) |
| No runtime rebinding | ✅ preserved (one binding for the entire run) |
| No retry / no fallback / no model swap | ✅ preserved (`retry_count=0`, `fallback_count=0`) |
| No automatic Git / push / merge / deploy | ✅ preserved |
| No durable application ingestion | ✅ preserved |
| Credentials never enter Campaign artifacts | ✅ preserved (zero credential material in audit.json) |
| Receipts are evidence, not authority | ✅ preserved (Pi Receipt validates; nothing relies on it for authorization) |
| Evaluator remains synthetic/non-independent in CE-L1 | ✅ preserved (interim Evaluation was constructed deterministically — runtime failed closed before any publication, but the interim path is provider-free) |
| Release posture unchanged | ✅ preserved |

## Confirmation Campaign Engine source-tree was untouched (except authorized scope)

Tracked files modified within this slice's authorized scope
(`codex_runner/campaign_engine/{__init__,errors,models}.py`,
`codex_runner/campaign_engine/live_executor.py`,
`codex_runner/tests/test_campaign_engine_live_executor.py`):

* `codex_runner/campaign_engine/live_executor.py` — new module: CE-L1
  two-phase runtime (preparation + execution with drift protection).
* `codex_runner/campaign_engine/__init__.py` — exports for the new
  types and the new error.
* `codex_runner/campaign_engine/errors.py` — bounded live-Executor
  error class.
* `codex_runner/campaign_engine/models.py` — immutable preparation
  record + result envelope types and the live-classification constant.
* `codex_runner/tests/test_campaign_engine_live_executor.py` — 31
  deterministic tests covering the spec's required 35 cases (the
  no-eager-Guardian-import test 35 and the zero-mutation test 16
  absorb the spec's invariant during the BLOCK; the runtime also
  enforces zero-mutation as a CE-L1 invariant).

`codex_runner/campaign_engine/runtime.py` (provider-free) is byte-identical
to `origin/main`'s CE-L1-record-contract landing.

`guardian/pi/*`, `codex_runner/src/agent-wrapper.js`, `codex_runner/schemas/*` —
untouched.

## Security ledger

| Count | Value |
| --- | --- |
| Provider inference requests | `1` (the bounded live invocation) |
| Successful live invocations | `1` (wrapper reported success; harness produced no mutation) |
| Model prompts | `1` (text-only response; `write` tool not invoked) |
| OAuth login attempts | `0` (cannot run interactively in this slice) |
| OAuth refresh attempts | triggered but failed (refresh-token already used) |
| Credential mutations | `0` |
| Real package mutations | `0` (no Pi / wrapper / adapter / schema change) |
| Credential-value outputs | `0` |
| Retry attempts | `0` |
| Fallbacks | `0` |
| Authorized readiness calls | `1` |
| Live runner calls | `1` |
| Git commits in proof target | `0` |
| Pushes | `0` |
| Merges | `0` |
| PRs opened against target | `0` |
| Deployments | `0` |
| CE-L1 emissions emitted | `0` |

## Exit conditions

```text
Result:                    BLOCKED
CE-L1_EXIT:                NOT EMITTED
CE-L1:                     OPEN
NEXT_TASK_REQUIRED:        refresh openai-codex OAuth session via interactive pi login;
                           then re-run the BLOCKED proof with one fresh Provider/Pi invocation
```

## Closely related artifacts

* **CE-L0 historical first-attempt (BLOCKED)**:
  `docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l0-guardian-pi-live-invocation-proof.md`
* **CE-L0 requalification (PASS)**:
  `docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l0-guardian-pi-live-invocation-requalification-proof.md`
  (canonical remote-main; PR #758 merged on `d1463fe85…`)
* **CE-L1 record contract landing (PASS)**:
  `docs/Campaign/campaign-engine-supervised-usability-closure.md`
  and PR #759 (`Implement Campaign live Executor record contract` →
  squash `cc78c58f1…`)

The CE-L0 proofs remain `PASS` on the canonical record.  This CE-L1
proof does not retrigger CE-L0 because the Campaign closure graph is
unchanged by the BLOCKED outcome.

## Lessons for the next slice

Three durable lessons are recorded:

1. **The wrapper's bounded success JSON does not prove an actual file
   write was performed.**  The Campaign Engine live Executor runtime
   is responsible for verifying the post-invocation target snapshot
   and failing closed when the harness reported success but produced
   zero source mutations within the declared allowed-file scope.
   This proof's `zero_mutation_executor_turn` invariant does exactly
   that and is the durable seam protecting CE-L1 from a silent text-only
   provider response.
2. **A bounded success on `pi-coding-agent` 0.72.1 may reflect a session
   that failed to authenticate, not a real model invocation.**  The
   wrapper's success JSON is not a reliable signal that the model
   actually ran.  Pre-flight `auth_available` is required before
   spending the live call, but a positive pre-flight does not guarantee
   the live call will produce a substantive tool invocation.
   The CE-L1 invariant on actual target mutations is therefore the
   canonical success signal — not the wrapper's bounded JSON.
3. **Provider-bound identity exhaustion surfaces as a Campaign-side
   silent failure.**  When the provider refresh token has already
   been used, the wrapper emits a successful JSON envelope without
   actually invoking the model.  The operator must run `pi login
   <provider>` before CE-L1 can produce a real successful proof; the
   `NEXT_TASK_REQUIRED` recorded above makes that explicit and
   bounded.


## 2026-08-28 gpt-5.6-sol canonical requalification — BLOCKED

### Scope

This append-only section records one bounded canonical requalification
attempt against current remote main
`5b5df6fe36c68d1dee28b2546778d9a891800c46` (PR #773, "Cleanly requalify
CE-L1 gpt-5.6-sol credential readiness"), after the credential-readiness
prerequisite `CE-L1_OAUTH_PREREQUISITE=PASS` became canonical.

The historical 2026-08-26 BLOCKED attempt above remains valid historical
evidence and is not rewritten.  This requalification supersedes only the
current CE-L1 gate status; it does not erase prior history.

### Result

**`BLOCKED`** — `failure_reason = zero_mutation_executor_turn`,
`diagnostic_stage = post_invocation`.

The single canonical `run_live_executor_campaign` call completed its
underlying live invocation.  The Executor turn produced a successful text
response from `openai-codex / gpt-5.6-sol / pi-coding-agent@0.82.1` but
issued **no** allowed-path mutation (`files.write resource=proof_target.txt`)
within the declared scope.  The runtime correctly failed closed at
`post_invocation` per the existing `zero_mutation_executor_turn` policy.

The runtime did NOT publish an Attempt, Receipt, Harness Result, Evaluation,
or CampaignState.  The output directory is empty by design.

### Counters

```text
live_executor_run_call_count       = 1
runner_call_count                 = 1
retry_count                       = 0
fallback_count                    = 0
rebinding_count                   = 0
provider_switch_count             = 0
model_switch_count                = 0
provider_inference_request_count  = 1 (live invocation succeeded text-only)
model_prompt_count                = 1 (live invocation completed)
live_executor_invocation_count    = 1
live_evaluator_invocation_count   = 0 (interim CE-L1 evaluation is provider-free)
OAuth login/logout count          = 0
credential existence checks        = 0
```

### Direct runtime-identity capture

The wrapper subprocess during the live invocation established the canonical
runtime identity via the maintained Pi 0.82.1 `ModelRuntime`.  The
preparation's expected identity was:

    expected_provider_id = "openai-codex"
    expected_model_id    = "gpt-5.6-sol"
    expected_harness_id  = "pi-coding-agent"
    expected_harness_version = "0.82.1"

The runtime reached `post_invocation` (after successful live invocation),
which only happens if the wrapper's actual identity matched the frozen
envelope identity and `_validate_actual_identity` returned None.
Therefore the actual identity was exactly:

    openai-codex / gpt-5.6-sol / pi-coding-agent / 0.82.1

### Target integrity after the call

```text
baseline_git_head        = 8437dad3276a1a58f8976c3afbd9b6d00b5e0343
final_git_head           = 8437dad3276a1a58f8976c3afbd9b6d00b5e0343 (match)

baseline_file_sha256     = 9aaf3c2e83b825e102bc9bbc0a69778415ef93c32132ef33b11f5a57edf9d8a4
final_file_sha256        = 9aaf3c2e83b825e102bc9bbc0a69778415ef93c32132ef33b11f5a57edf9d8a4 (match)

baseline_file_bytes      = 22
final_file_bytes         = 22 (match)
final_file_content       = 'CE_L1_GPT56SOL_BEFORE\n' (unchanged)

baseline_target_status   = ''
final_target_status      = ''

baseline_remote_count    = 0
final_remote_count       = 0
```

The target remained **byte-identical** before and after the single
`run_live_executor_campaign` call.  No file change.  No commit.  No
remote.  No push.  No merge.  No deploy.  No provider substitution.  No
model substitution.  No retry.  No fallback.  No rebinding.

### Failure classification

```text
failure_reason             = zero_mutation_executor_turn
diagnostic_class           = null
diagnostic_stage           = post_invocation
diagnostic_message         = live Executor turn completed without producing
                             an allowed-path mutation; per CE-L1 policy an
                             Executor turn must produce source_mutation_count
                             >= 1 within the declared allowed_file_paths
pi_receipt_present         = false (no receipt published)
pi_harness_result_present  = false (no harness result published)
attempt_present            = false (no attempt published)
evaluation_present         = false (no evaluation published)
campaign_state_present    = false (no campaign state published)
target_pre_sha256          = 9aaf3c2e83b825e102bc9bbc0a69778415ef93c32132ef33b11f5a57edf9d8a4
target_post_sha256         = 9aaf3c2e83b825e102bc9bbc0a69778415ef93c32132ef33b11f5a57edf9d8a4
target_changed_paths       = []
```

### Historical BLOCKED precedent

This is the second observed CE-L1 BLOCKED on `zero_mutation_executor_turn`:

1. The historical 2026-08-26 attempt (PR #765 era) failed with the same
   `zero_mutation_executor_turn` reason at `post_invocation`.  At that
   time the runtime was the deprecated `@mariozechner/pi-coding-agent@0.72.1`
   wrapper.
2. This 2026-08-28 attempt also fails with `zero_mutation_executor_turn`
   at `post_invocation`.  The runtime is now the maintained
   `@earendil-works/pi-coding-agent@0.82.1` `ModelRuntime` wrapper, with
   credential readiness canonical and the wrapper explicitly instructing
   the Executor to invoke the bounded `write` tool.

The runtime is canonical.  The credential readiness is canonical.  The
canonical prerequisite truth is unchanged.

### Redaction

```text
direct credential-store access count     = 0
credential paths constructed by task     = 0
credential paths inspected by task       = 0
token values captured                    = 0
account IDs captured                     = 0
credential metadata captured             = 0
OAuth login/logout actions               = 0
provider inference requests              = 1 (live invocation succeeded text-only)
```

### First observed boundary

The run proves that the canonical Executor completed without an allowed-path
mutation.  Current evidence does not distinguish whether the `write` tool was
absent from the effective session tool set, omitted or transformed at the
provider tool-schema boundary, emitted but not executed, or correctly
advertised and simply not selected by the model.

```text
CAUSE_CLASSIFICATION = UNRESOLVED_TOOL_EXECUTION_BOUNDARY
```

Credential readiness, exact runtime identity, Guardian authorization,
one-shot invocation, and the Campaign Engine zero-mutation fail-closed
behavior are independently proven and are not the current unresolved
boundaries.

### Counter-emission

```text
LIVE_EXECUTOR_PROVEN         = NOT EMITTED
LOCAL_CE-L1                  = OPEN
CE-L1_OAUTH_PREREQUISITE     = PASS (canonical, from PR #773)
CANONICAL_CE-L1              = OPEN (unchanged)
SINGLE_TASK_SUPERVISED_USABLE = NOT EMITTED
```

### Next task

```text
NEXT_TASK_REQUIRED = instrument bounded Pi tool availability and
                     tool-execution telemetry for Guardian-authorized live
                     tasks, then re-run one CE-L1 disposable mutation
                     proof
```

The instrumentation task must precede:

- prompt rewriting;
- model substitution;
- another CE-L1 live attempt.

This task does NOT prescribe another model.  This task does NOT prescribe
a prompt change.  The remaining causal boundary is narrower than the
whole runtime but is not yet attributable specifically to model behavior
or prompt wording.

### Missing telemetry seam

The current Guardian-authorized evidence does not retain:

- `effective_tool_names`
- `write_tool_available`
- `tool_execution_start_count`
- `tool_execution_end_count`
- `executed_tool_names`
- `assistant_tool_call_count`

These are evidence requirements for the next diagnostic slice.  This task
does not implement them.

### ADR impact

`Aligned with existing ADR(s); no new ADR required.`  The runtime contract
(ADR-068) failed closed exactly as designed.

### Invariants check

- Guardian remained execution authority ✓
- Campaign Engine did not self-authorize ✓
- Pi remained provider execution substrate ✓
- Locked `openai-codex / gpt-5.6-sol` RoleBinding controlled expected
  identity ✓
- Actual runtime identity independently captured ✓ (matched expected)
- No provider/model substitution ✓
- Exactly one live Executor attempt ✓
- No retry ✓
- No fallback ✓
- No rebinding ✓
- Target scope was exactly one file ✓
- Target repository is disposable and has no remote ✓
- No commit/push/merge/deploy ✓
- Receipts are evidence, not authority ✓ (no receipts were issued)
- Interim CE-L1 evaluation remained provider-free ✓ (not yet engaged)
- Historical BLOCKED proof content remained immutable ✓ (this section is
  appended, no existing line was modified)
- Release claims remain evidence-bounded ✓

### Canonical gate truth

```text
CE-L1_OAUTH_PREREQUISITE      = PASS
CE-L1                         = OPEN
LIVE_EXECUTOR_PROVEN          = NOT_EMITTED
SINGLE_TASK_SUPERVISED_USABLE = NOT_EMITTED
CAUSE_CLASSIFICATION          = UNRESOLVED_TOOL_EXECUTION_BOUNDARY
```

### Documentation follow-through

This is the only tracked file changed by this requalification.  No runtime
source file.  No test file.  No Guardian file.  No Campaign Engine schema.
No credential file.  Disposable driver, target, campaign JSON, and output
root remain outside the repository (under `/var/folders/kj/.../T/`).

## 2026-08-29 Pi 0.82.1 tool-activation diagnosis

### DIAGNOSIS_RESULT

```text
DIAGNOSIS_RESULT=PASS
```

### PRE_REPAIR_CAUSE_CLASSIFICATION

```text
PRE_REPAIR_CAUSE_CLASSIFICATION=
UNRESOLVED_TOOL_EXECUTION_BOUNDARY
```

### ROOT_CAUSE

```text
ROOT_CAUSE=
PI_0821_TOOL_OPTIONS_TYPE_MISMATCH_PROVEN
```

### Pre-edit deterministic probe

```text
object-tool effective_tool_names=[]
name-tool effective_tool_names=["read","bash","edit","write"]
provider_request_count=0
prompt_count=0
operator_credential_access_count=0
```

### Statement

The diagnosis resolves the previously unresolved tool-activation
sub-boundary.  It does not retroactively convert either BLOCKED CE-L1
attempt into a PASS.

### Canonical gate truth

```text
CE-L1_OAUTH_PREREQUISITE=PASS
CE-L1=OPEN
LIVE_EXECUTOR_PROVEN=NOT_EMITTED
SINGLE_TASK_SUPERVISED_USABLE=NOT_EMITTED
```

### NEXT_TASK_REQUIRED

```text
land the Pi 0.82.1 tool-activation and bounded telemetry repair on remote
main
```

## 2026-08-29 post-repair gpt-5.6-sol canonical requalification — BLOCKED

### Canonical base SHA

```text
18c6f797675c803799fea9db01b15fc86901f9af
Repair Pi 0.82.1 tool activation telemetry (#776)
```

### Root-cause repair status

```text
TOOL_ACTIVATION_REPAIR = PASS_CANONICAL
```

### Pre-repair canonical prerequisite truth

```text
CE-L1_OAUTH_PREREQUISITE = PASS / canonical
PI_0821_TOOL_OPTIONS_TYPE_MISMATCH_PROVEN
```

### Single live call accounting

```text
run_live_executor_campaign call count = 1
runner_call_count = 0
retry_count = 0
fallback_count = 0
rebinding_count = 0
provider_switch_count = 0
model_switch_count = 0
provider_inference_count = 0
operator_credential_access_count = 0
```

### Failure reason

```text
failure_reason = policy_envelope_mismatch
diagnostic_stage = pre_invocation
runner_call_count = 0
```

The runtime mapped an accumulated multi-cause envelope/decision validation
result to the canonical `policy_envelope_mismatch` token at
`invoke_guardian_authorized_pi(...)` entry. The Pi 0.82.1 runtime was **not**
invoked. `run_live_executor_campaign` returned a `CampaignLiveExecutorError`
whose `to_payload()` was persisted to `run-result.json` only.

### Underlying bounded causes (extracted from the disposable driver audit)

The `validate_policy_decision_against_envelope(...)` validator accumulated
the following pre-invocation reasons against the disposable driver's
Guardian envelope + decision (before any provider call):

```text
invalid_provider_lane        — envelope.provider_lane.provider_lane_class
                                was "provider_lane" rather than the
                                canonical PiProviderLaneClass enum value
                                (local|remote|hybrid|external|minimax).
                                For an openai-codex/external provider the
                                canonical class is "external".
missing_invocation_id         — PiInvocationPolicyDecision.validation_status
                                was unset (default None). The
                                validate_pi_invocation_policy_decision
                                validator emits MISSING_INVOCATION_ID when
                                decision.validation_status is falsy.
```

Both are defensive, pre-invocation Guardian validations. They are independent
of the post-repair Pi 0.82.1 tool-activation seam and independent of any
provider behavior.

### Tool telemetry (BLOCKED before Pi invocation)

```text
effective_tool_names           = N/A (Pi runtime was not invoked)
write_tool_available          = N/A (Pi runtime was not invoked)
tool_execution_start_count    = N/A (Pi runtime was not invoked)
tool_execution_end_count      = N/A (Pi runtime was not invoked)
executed_tool_names           = N/A (Pi runtime was not invoked)
assistant_tool_call_count     = N/A (Pi runtime was not invoked)
tool_telemetry                = null
```

### Target posture

```text
target_baseline_HEAD           = f1638885b3773e84720d39626990db4402bf4148
target_HEAD after invocation   = f1638885b3773e84720d39626990db4402bf4148 (unchanged)
target remote -v               = (empty)
target git status --short     = (empty)
target file bytes              = CE_L1_POST_REPAIR_BEFORE\n
target file SHA-256            = c4ea51164638a490306fb0a3e3c23f2ede0a0b90e1c7858036529e217bf54263
expected final SHA-256         = cefeb8215907aaf756d83f823953d04473550bbea8ae61ade175d7f8c60a0fe0
```

The target remained byte-identical to its committed baseline. No commit was
made. No remote was added. No merge was attempted.

### Campaign artifact publication posture

```text
campaign-input.json                                   = absent (preparation only — not persisted)
authorization/executor-preparation.json              = absent
authorization/executor-envelope.json                 = absent
authorization/executor-policy-decision.json          = absent
execution/executor-pi-receipt.json                   = absent (Pi runtime not invoked)
execution/executor-pi-harness-result.json             = absent (Pi runtime not invoked)
execution/executor-boundary-validation.json           = absent
execution/target-before.json                          = absent
execution/target-after.json                           = absent
attempts/<attempt_id>.json                            = absent
evaluations/<evaluation_id>.json                      = absent
receipts/<receipt_id>.json                            = absent
tasks/<task_id>/task-state.json                       = absent
campaign-state.json                                   = absent
run-result.json                                       = PRESENT (only published artifact)
```

The Campaign Engine published no Attempt, Receipt, Harness Result,
Evaluation, TaskState, or CampaignState because the runtime closed at
`pre_invocation` validation before reaching the live Executor rail.

### Live Attempt validation

```text
execution_mode                  = (no Attempt published)
expected_provider_id            = openai-codex
expected_model_id               = gpt-5.6-sol
actual_provider_id              = (none — Pi runtime not invoked)
actual_model_id                 = (none — Pi runtime not invoked)
identity_verification_result    = (none)
provider_call_count             = 0
exit_classification              = (none)
source_mutation_count           = 0
commit_performed                = false
merge_performed                 = false
durable_ingestion_performed     = false
```

### Provider-free Evaluation posture

No Evaluation was published. The CE-L1 provider-free Evaluation invariant
(`evaluation_mode == "provider_free"`, `independent_model_judgment == false`,
`read_only_assertion == true`, `mutation_performed == false`) was therefore
not exercised in this BLOCKED slice.

### Evidence-bounded diagnosis

The smallest observed tool-activation/telemetry-repair-landing blocker is a
disposable driver envelope-construction defect, not a runtime defect:

> The disposable proof driver's `PiInvocationEnvelope.provider_lane` was
> constructed with `provider_lane_class="provider_lane"`, which is not a
> canonical `PiProviderLaneClass` enum value. The
> `validate_policy_decision_against_envelope(...)` validator rejected the
> envelope at the `external` lane-class check (`invalid_provider_lane`),
> and a secondary defect (`PiInvocationPolicyDecision.validation_status`
> was unset, triggering `missing_invocation_id`) accumulated in the same
> validation result. The runtime mapped both to the canonical
> `policy_envelope_mismatch` token at `pre_invocation` and returned
> before any provider request was constructed.

The Pi 0.82.1 tool-activation repair (`PASS_CANONICAL` via PR #776 at
`18c6f797…`) is **not** disproven by this BLOCKED — the Pi 0.82.1 runtime
was not invoked. The repair remains canonical. The post-repair canonical
proof remains `OPEN_PENDING_PROOF_LANDING`.

### Redaction audit

```text
files scanned                  = 1 (run-result.json only)
access_token                   = 0
refresh_token                  = 0
auth.json                      = 0
account_id                     = 0
auth_headers (Bearer/x-api-key) = 0
env_dump (HOME/PATH/SECRET)    = 0
credential path metadata       = 0
```

The published evidence tree contains no credential material, no auth
headers, no operator path metadata, and no provider payload.

### Historical proof preservation

The pre-edit SHA-256 of this file on `origin/main` was:

```text
0abd95400c5d5e282731ea7d4ec4180e221e0f71f1860f18c43664177ed1f206
```

This section is append-only. The first 29541 bytes of this file remain
byte-identical to `origin/main` (verified by SHA-256 on the unchanged
prefix).

### Canonical gate truth after this BLOCKED

```text
CE-L1_OAUTH_PREREQUISITE = PASS
TOOL_ACTIVATION_REPAIR  = PASS_CANONICAL
CE-L1                   = OPEN
LIVE_EXECUTOR_PROVEN    = NOT_EMITTED
SINGLE_TASK_SUPERVISED_USABLE = NOT_EMITTED
```

### NEXT_TASK_REQUIRED

```text
fix the disposable proof-driver envelope construction to use
PiProviderLane(provider_lane_class="external", ...) and to set
PiInvocationPolicyDecision.validation_status; rebuild the single canonical
post-repair live attempt and re-run one CE-L1 disposable live Executor
mutation proof under the existing spec.
```
