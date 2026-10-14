# CE-L2 provider-free lifecycle preparation and readiness

Date: 2026-09-27
Campaign branch: `codex/campaign-engine-closure`
Implementation parent: `50c6b3838683fad68f089414af6f946dc896844c`
Gate: `CE-L2` remains **open**; no live CE-L2 provider invocation occurred.

## Scope and authority

The operator selected a new one-Task disposable Campaign, with locked
Auditor, Executor, and Evaluator RoleBindings before either live call. The
Executor uses `deepseek / deepseek-v4-pro / pi-coding-agent@0.82.1` with
effort `off` and required `write`. The independent read-only Evaluator uses
the same provider/model/harness with effort `medium`. The accepted CE-L1
Campaign and its proof remain immutable and are not reused.

This slice implements and validates the provider-free CE-L2 continuation.
The two future external provider calls require separate direct human
authorizations. No call was made by the implementation, tests, fixture
preparation, or readiness checks recorded here.

## Runtime continuation

`codex_runner/campaign_engine/live_evaluator.py` accepts the same fresh
Campaign's completed Executor checkpoint as immutable input. It validates
the locked bindings, one successful Executor Attempt, one provider-backed
Executor call, required `write`, one changed file, Pi Receipt, Harness
Result, boundary validation, and target state. It constructs a bounded
evidence packet containing the Task objective, acceptance criteria,
source-context reference, Attempt, changed-file list, size-limited diff
and snapshots, validation command/output, and Executor identity evidence.

The Evaluator authorization is read-only and limited to the declared
disposable file. Pi tools are disabled. Its separate Guardian invocation
requests `medium` explicitly and returns only a canonical verdict, short
summary, and bounded criterion judgments. Guardian and Campaign Engine
validate the result. The final artifact tree contains a live Evaluation,
Receipt, CampaignState, immutable Executor Attempt, exact copies of the
validated Executor checkpoint evidence, and bounded Evaluator Pi evidence.
No raw model response or reasoning content is persisted.

Failure is terminal for that call: no retry, fallback, rebinding, repair,
commit, merge, or durable Codexify ingestion. Bounded timeout phase
evidence survives in the failure record. No provider-free test result emits
`CE-L2_EXIT=SINGLE_TASK_SUPERVISED_USABLE`.

## Fresh disposable Campaign

The prepared, unexecuted Campaign is at:

`/var/folders/j7/l5mjdtxn2fj_2sggfbl0407c0000gn/T/ce-l2-fresh-campaign-fivsyy24/campaign_live_test.json`

Its disposable Git target is:

`/var/folders/j7/l5mjdtxn2fj_2sggfbl0407c0000gn/T/ce-l2-fresh-campaign-fivsyy24/ce-l1-test-target`

These fixture-derived names are incidental; the Campaign identity is
`campaign-ce-l2-8eaedca783f8`, the Task identity is
`task-ce-l2-8eaedca783f8`, and the Campaign input hash is
`1cf93d6f0bf42bf95f8ecdec12f52aeade01107a732e9b52ffbde6e49408e10a`.
All three bindings are locked. The live bindings explicitly record the
selected harness and efforts (`off` Executor, `medium` Evaluator). Attempts,
Evaluations, and Receipts are
empty. The disposable baseline Git HEAD is
`ab7d7c22d467efb0db2c31fefa8d5fd608a8a0c5`.

The target contains only the declared `proof_target.txt` source file.
No Executor or Evaluator invocation has been performed on this Campaign.

## Canonical non-inference readiness

`preflight_guardian_authorized_pi` ran once for each role with separate
Guardian envelopes and policy decisions bound to this fresh Campaign and
target. Both reported `ok=true`, deepest stage `auth_available`, actual
identity `deepseek / deepseek-v4-pro / pi-coding-agent@0.82.1`,
authentication available, one preflight call, zero retry, zero fallback,
`session_initialized=false`, and `provider_request_started=false`.
The file bytes and disposable Git HEAD were unchanged before and after.

After implementation commit
`91cd53a72b5346b0cf8751e63eb43c83e951fdb8`, readiness was repeated
against the final Campaign input hash
`1cf93d6f0bf42bf95f8ecdec12f52aeade01107a732e9b52ffbde6e49408e10a`.
Both roles again returned `auth_available`, exact
`deepseek / deepseek-v4-pro / pi-coding-agent@0.82.1` identity, zero
retry/fallback, no session, no provider request, unchanged target bytes,
and unchanged disposable Git HEAD. The locked efforts were `off` and
`medium`, respectively; readiness did not claim either as effective.

Readiness establishes provider/model/harness resolution and authentication
availability only. It creates no Pi session and cannot establish effective
runtime reasoning effort; that must be checked by each authorized live
wrapper before prompting.

An earlier readout-only readiness script raised while serializing its
result, after the canonical preflight had returned. A corrected readout
ran another non-inference readiness check on a separate disposable target.
Neither check started a provider request. The two Campaign-bound readiness
checks above are the evidence used for this preparation.

## Provider-free validation

- `.venv/bin/python -m pytest -q codex_runner/tests/test_campaign_engine_live_executor.py tests/pi/test_pi_live_invocation.py tests/pi/test_pi_evaluator_result.py codex_runner/tests/test_campaign_engine_live_evaluator.py` — focused CE-L1, Guardian/Pi, and CE-L2 suites pass.
- `node --test codex_runner/tests/guardian-evaluator-result.test.mjs` — bounded JS verdict projection tests pass.
- `.venv/bin/ruff check` on the new CE-L2 and Guardian/Pi Python surfaces, `node --check` on changed JS, and `git diff --check` — pass. The existing `live_executor.py` has ten pre-existing Ruff findings; the committed-parent version reports the same ten, so they were not widened into this task.

The CE-L2 tests use fake invokers. They prove schema-valid final records,
all four verdict-to-state transitions, exact checkpoint evidence copying,
zero write authority, no target mutation, credential-safe bounded results,
and fail-closed malformed, retry, identity, reference, and timeout cases.
They do not prove a live Executor or Evaluator call.

## Live-call frontier

After separate direct authorization for the Executor, the operator must
revalidate the Campaign hash and target baseline, create the exact locked
Guardian Executor envelope/decision, run canonical non-inference readiness,
then call `run_live_executor_campaign(...)` once with effort `off`, required
`write`, and a bound of at most 300 seconds. A valid checkpoint is the only
input admitted to `prepare_live_evaluator_campaign(...)`.

After separate direct authorization for the Evaluator, the operator must
create its distinct read-only Guardian envelope/decision using
`LiveEvaluatorPreparation.authorization_metadata()`, call
`preflight_live_evaluator(...)`, then call
`run_live_evaluator_campaign(...)` once with effort `medium` and a bound of
at most 300 seconds. The two calls must remain in the same fresh Campaign.
Only complete positive live evidence may establish
`CE-L2_EXIT=SINGLE_TASK_SUPERVISED_USABLE`.
