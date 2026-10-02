# CE-L2 Evaluator effort binding repair: provider-free proof

Date: 2026-09-28
Campaign branch: `codex/campaign-engine-closure`
Implementation parent: `67f10df11a368746016429a3f1700f6f6f73fd46`
Governing decision: accepted ADR-068; no new ADR or release claim.

`CE-L2=OPEN`
`LIVE_EVALUATOR_HIGH_EFFECTIVE_EFFORT=NOT_YET_PROVEN`
`PROVIDER_CALL_COUNT=0`

## Authority and repair

The accepted live RoleBinding schema already carries
`live_role_binding.reasoning_effort`. The historical fresh Campaign locked its
Evaluator to `medium`; its input hash remains
`1cf93d6f0bf42bf95f8ecdec12f52aeade01107a732e9b52ffbde6e49408e10a`.
That Campaign, its successful live Executor checkpoint, and the failed
Evaluator invocation were not edited or rebound. The failed invocation remains
the terminal evidence for its `medium` selection.

`live_evaluator.py` now derives the selected effort from the locked Evaluator
RoleBinding. Preparation resolves current local Pi model metadata with model
network refresh disabled, an empty auth path, and no Pi session. Unsupported
or unresolved effort fails before inference. A positive effort whose Pi
capability map changes it to a different level also fails closed. Execution
re-prepares from the same source Campaign and checkpoint, checks the selected
request effort against
the prepared locked effort, and binds that effort in Guardian authorization
metadata. Requested and effective effort must match the lock in the live
outcome. No default, clamp, fallback, or `medium` to `high` translation is
introduced.

The installed `pi-coding-agent@0.82.1` registry resolves
`deepseek / deepseek-v4-pro` with `reasoning=true` and a thinking-level map in
which `medium` is `null` and `high` maps to `high`. Focused provider-free tests
prove locked `medium` rejects with `evaluator_effort_unsupported` before the
Evaluator invocation seam, while locked `high` prepares and passes the fake
single-Task lifecycle. The tests also cover Campaign, Guardian metadata,
execution-request, and terminal-effective-effort drift. Pi capability support
does not establish effective effort in a future live session.

## Fresh high-locked proof Campaign

A separate disposable provider-free fixture was created at
`/private/tmp/ce-l2-high-binding-provider-free-fx732194`. Its Campaign ID is
`campaign-ce-l2-high-effort-proof-001`; its canonical input hash is
`c0fd580630ad4586378d76b74928780c86d3860e833657e50db38ba6ab61ecb8`.
The Auditor remains provider-free. The Executor binding locks
`deepseek / deepseek-v4-pro / pi-coding-agent@0.82.1` at `off`; the Evaluator
binding locks the same identity at `high`, read-only. All three RoleBindings
were locked before the provider-free fake Executor fixture ran. The new input
hash differs from the historical `medium` Campaign hash.

The fixture's fake Executor writes its isolated test target once to construct
a synthetic checkpoint. This is fixture setup, not a provider-backed Executor
Attempt or a reusable live checkpoint. Repeated Evaluator preparation left
that fixture target fingerprint unchanged. The historical live target and
checkpoint remained unchanged. The fresh Evaluator preparation succeeded with
only `files.read` granted, no mutation permission, and evidence-packet hash
`9dea5958321255f8080ab19e210e64acb4eb9657721649d8df87c9bccb0d5988`.
The bounded packet and prompt hashes are recorded in
`/private/tmp/ce-l2-high-binding-provider-free-fx732194/provider-free-proof.json`.

## Preservation and validation

- Historical Campaign SHA-256 remained
  `41bd41cdf457d91a15e45b6b93ed97a40c9d9f490e070e02af3`.
- Historical failed Evaluator result SHA-256 remained
  `209155aa57219de5747b66aa64f538859b23627e20d7cd0d38ae880e515a9f67`.
- Every hash in the frozen successful live Executor checkpoint manifest
  remained unchanged.
- Focused CE-L2 tests use fake invokers only. No external provider request,
  retry, fallback, OAuth operation, credential readout, or live target mutation
  occurred in this repair.
- The prior `medium` invocation is not relabeled. A changed effort requires a
  new Campaign input identity and, later, distinct Guardian authorization and
  invocation identities.

The untouched historical Campaign was also passed directly to the repaired
provider-free preparation. It rejected with `evaluator_effort_unsupported` and
`runner_call_count=0`; its Campaign, failed-invocation, and target hashes
remained unchanged.

## Validation commands

- `.venv/bin/python -m pytest -v codex_runner/tests/test_campaign_engine_live_evaluator.py`
  — 22 passed, fake invocation seams only.
- `.venv/bin/python -m ruff check codex_runner/campaign_engine/live_evaluator.py codex_runner/tests/test_campaign_engine_live_evaluator.py`
  — passed.
- `PYTHON=.venv/bin/python make docs` — docs validation and diagram freshness
  passed.
- `git diff --check` — passed.
- Scope review — only the authorized runtime file, focused tests, and this
  proof record changed. The Pi Invocation Boundary Contract needed no edit.

The existing Pi Invocation Boundary Contract already says live RoleBindings
record explicit selected effort and does not make `medium` normative. It was
therefore left unchanged. ADR-068 and `00-current-state.md` were also left
unchanged.

This proof fixture cannot close CE-L2. A future live lifecycle requires a
separately authorized live Executor in a fresh `high`-locked Campaign and a
separately authorized read-only live Evaluator. Effective live `high`, terminal
actual identity, Pi Receipt and Harness Result, final Evaluation, combined
Receipt, and final CampaignState remain unproven.
