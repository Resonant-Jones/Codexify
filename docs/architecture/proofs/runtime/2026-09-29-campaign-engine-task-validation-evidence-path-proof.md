# Campaign Engine Task Validation Evidence Path Proof

Date: 2026-09-29

Lane: Architecture-impact, accepted-contract completion

Evidence level: Provider-free deterministic implementation proof

## Outcome

The Milestone A operational-friction blocker is resolved at the implementation boundary. A structured Campaign Task can now carry one optional `validation_command`; Guardian-owned Coding Loop authorization must bind that exact command to the Campaign, Task, Attempt, and disposable repository before the Executor invocation. After a successful bounded mutation and Campaign boundary checks, the Executor runs the approved command once through the shared Coding Loop validation runner and records its bounded `NormalizedTestResult`.

The Attempt’s `validation_command_reference` identifies the content-addressed authorization, and its `validation_result_hash` hashes the canonical bounded task-validation result. Campaign boundary validation has its own `boundary_validation_hash` and retained artifact. The live Evaluator receives the exact task command, authorization reference, normalized result, and result hash in its bounded packet. The packet hash covers those fields. Passing validation remains evidence only; the independent Evaluator still produces the verdict.

## Accepted contract and ownership

This completes the existing [ADR-068 live role execution contract](../../adr/068-campaign-engine-live-role-execution-contract.md). No ADR, release-support claim, or `00-current-state.md` claim changed.

- Guardian/Coding Loop supplies `CodingAgentTaskEnvelope` and `CodingAgentPermissionPolicy` authority, including `allow_shell`, allowed paths, and the runtime limit.
- Campaign Engine verifies the envelope’s Campaign, Task, Attempt, repository, exact command, one-attempt budget, and `commit_after_validation=false` posture before invocation.
- The provider prompt does not receive the validation command as an instruction. Pi tool permissions remain separate from host-side command authority.
- Coding Loop owns shell-free validation execution. The shared runner uses `shlex.split`, direct argv execution with no `shell=True`, an explicit `cwd`, captured output, the existing timeout cap, and the existing `NormalizedTestResult` normalization.
- Validation failure is recorded as a failed Attempt with its true status and hash in a bounded failure artifact. It stops before Evaluation/progression. No retry or automatic repair was added; a later lifecycle decision remains deferred.
- When a Task has no `validation_command`, no Coding Loop validation authorization is required and task-validation Attempt fields and artifacts are omitted. Historical no-task Attempts whose old `validation_result_hash` equals the Campaign boundary hash remain readable.

## Evidence bounds

Durable task-validation output is the normalized result only. Stdout and stderr previews are capped at 2,048 characters; failure signature, error message, and failing-test entries also have explicit limits. Credential-shaped material is rejected. Unbounded process output, environment dumps, transcripts, and unrelated process metadata are not persisted. The Evaluator checkpoint hash set includes the task authorization and result artifacts when present, and preparation fails if those artifacts no longer match their Attempt or Task bindings.

## Deterministic validation

All executor and evaluator seams in the new Campaign tests are fakes. No live Pi session or external model/provider was invoked.

| Check | Result |
| --- | --- |
| `.venv/bin/python -m pytest -v tests/agents/test_validation.py tests/agents/test_coding_worker.py` | Passed, 9 tests |
| `.venv/bin/python -m pytest -v codex_runner/tests/test_campaign_engine_live_executor.py codex_runner/tests/test_campaign_engine_live_evaluator.py` | Passed, 81 tests |
| `.venv/bin/python -m pytest -v guardian/tests/workers/test_coding_worker.py::test_validation_command_with_shell_blocked_records_not_run` | Passed, 1 test |
| `.venv/bin/python -m ruff check` over the touched Python files | Passed |
| `PYTHON=.venv/bin/python make docs` | Passed; Make printed its existing duplicate `canonical-audit-live-proof-receipt` target warning |
| `git diff --check` | Passed |

The deterministic tests cover missing/mismatched authority before invocation, immutable Task-command drift, exact one-shot validation after mutation, truthful failed validation with no retry, separate task/boundary hashes, no-validation compatibility, bounded Evaluator evidence, result-command integrity, and independent Evaluator judgment. Real provider calls and provider prompts for this implementation task: zero.

## Operational boundary

The original Makefile-backed Campaign Task remains unexecuted and unchanged. This proof does not claim a new live Campaign, a new Milestone A qualification, or release readiness. CE-L3 remains unopened.

```text
MILESTONE_A_FRICTION_VALIDATION_EVIDENCE_PATH=RESOLVED
PROVIDER_CALLS=0
LIVE_EXECUTOR_PROVIDER_PROMPTS=0
LIVE_EVALUATOR_PROVIDER_PROMPTS=0
CE_L3=NOT_ENTERED
MAKEFILE_OPERATIONAL_TASK=NOT_EXECUTED
NEXT_OPERATIONAL_TRIAL=RERUN_DUPLICATE_MAKE_TARGET_TASK
```
