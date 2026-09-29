# Campaign Engine boundary changed-path classification repair

Date: 2026-09-29

Lane: architecture-impact runtime correctness

Governing contract: accepted ADR-068
Evidence level: provider-free deterministic regression proof

## Operational trigger

One fresh Milestone A duplicate-Make-target Campaign reached one authorized live DeepSeek Executor call. The Executor removed the older duplicate `canonical-audit-live-proof-receipt` recipe in its disposable worktree. Read-only inspection found only `Makefile` changed, one target definition remaining, the later recipe's optional `profile_name` and `compose_env_file -> --compose-env-file` behavior preserved, and `git diff --check` passing. Campaign Engine then raised `boundary_validation_failed` before the authorized `make PYTHON=python3 docs` Task validation. No Evaluator call or final Receipt/CampaignState occurred. The failed Campaign and its partially mutated disposable target remain historical evidence; this repair did not resume, validate, repair, or commit them.

The full post-invocation snapshot contained approximately 25,195 repository files. The independent post-invocation mutation check correctly compared each file's pre/post hashes, but the boundary artifact treated every snapshot key as a changed path. Unchanged files outside the Task's `Makefile` allowlist therefore failed its scope check.

## Repair and invariant

`_actual_changed_entries` selects entries from the full snapshot only when `pre_hash != post_hash`. Both changed-file/source-mutation evidence and the independently recorded boundary allowlist check use that one pure classification rule. The full pre/post snapshot remains available, including pre-only deletions and post-only creations. The existing out-of-scope rejection, zero-mutation failure, Git HEAD protection, Guardian authorization, Task validation order, and no-retry posture remain unchanged.

| Snapshot entry | Classification |
| --- | --- |
| Same pre/post hash | Unchanged; inert even outside the allowlist |
| Different nonempty hashes | Modification |
| Empty pre, nonempty post | Creation |
| Nonempty pre, empty post | Deletion |

The boundary artifact still checks `changed_paths_within_allowed_scope` and identifies genuine unauthorized changes. It does not infer mutation from repository membership.

## Deterministic proof

No live provider or Evaluator was invoked for this repair. The focused tests use the test-only fake Executor seam.

| Check | Result |
| --- | --- |
| New focused selector for changed-path and runtime out-of-scope regressions | 9 passed |
| Full `codex_runner/tests/test_campaign_engine_live_executor.py` | 66 passed |
| Ruff on the touched Python files | Passed; existing `pyproject.toml` top-level-setting deprecation warning |
| `PYTHON=.venv/bin/python make docs` | Passed; existing duplicate Make target warning remains because the source checkout's `Makefile` is out of scope |
| `git diff --check` | Passed |
| Provider calls during this repair | 0 |

The new regressions prove one allowed change among 258 unchanged outside paths, a persisted successful boundary artifact with one changed file and `source_mutation_count=1`, and fail-closed boundary classification for unauthorized modification, creation, and deletion. Separate runtime tests prove that the independent post-invocation check rejects each of those three unauthorized mutations. The no-mutation test confirms the classification helper returns no changes; the existing live Executor regression continues to require `zero_mutation_executor_turn`. Existing tests also cover unchanged Git HEAD and validation sequencing after the boundary.

## Remaining operational boundary

This is code and test proof, not a completed duplicate-Make-target Campaign. Its Task validation, independent live Evaluator verdict, final Receipt, and final CampaignState remain unproven. A later operational trial requires separate authorization, a fresh Campaign, and a fresh disposable worktree from the intended clean source commit. No ADR, Campaign schema, RoleBinding, Guardian/Pi, release/current-state, or CE-L3 change is made here.

```text
MILESTONE_A_FRICTION_BOUNDARY_CHANGED_PATH_CLASSIFICATION=RESOLVED
PROVIDER_CALLS=0
CE_L3=NOT_ENTERED
NEXT_OPERATIONAL_TRIAL=FRESH_RERUN_DUPLICATE_MAKE_TARGET_TASK
```
