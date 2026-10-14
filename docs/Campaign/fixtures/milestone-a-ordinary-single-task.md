# Milestone A canonical ordinary single-Task specimen

This is the canonical ordinary single-Task specimen for exercising:

```text
Campaign -> live Executor -> boundary validation -> Task validation
         -> live Evaluator -> Receipt -> CampaignState
```

Future operational trials must consume this authored Task Spec directly from
this repository artifact. Use a fresh Campaign and a fresh physical disposable
worktree at the operator-selected clean commit; preserve every failed Campaign
and target. Do not resume a failed run or reconstruct this Task from chat.

Lock Executor and Evaluator to `deepseek / deepseek-v4-pro /
pi-coding-agent@0.82.1`. Executor effort is `off`, with `required_tool_name`
omitted (resolving to `None`); Evaluator effort is `high` and read-only.
Campaign Engine owns the single `make PYTHON=python3 docs` validation attempt
following boundary validation. The Executor performs inspection and the scoped
edit, leaving that command to the host. No automatic retry, repair, fallback,
rebinding, commit, or CE-L3 progression is authorized. Stop on failure, or after
final Evaluation/Receipt/CampaignState on success, and return control to the
operator before committing. Use the physical worktree path and do not create
writable-root symlink aliases or reuse the source checkout's `.venv`.

The fixture records Task semantics, not evidence that any operational Campaign
has completed. Record operational friction separately from Task correctness.

# Task Spec

## Title

Remove the duplicate `canonical-audit-live-proof-receipt` Make target.

## Workflow classification

- **Lane:** Standard
- **Task kind:** Focused build/tooling bug fix
- **Evidence posture:** `proven-code-path` + deterministic local validation
- **Operational posture:** Real-but-disposable Milestone A single-Task Campaign trial
- **Architecture impact:** None
- **Release impact:** None

## Context

GNU Make currently reports a duplicate-target warning for:

`canonical-audit-live-proof-receipt`

Inspection established that `Makefile` contains two definitions of that target.

The older definition is stale relative to the current collector CLI:

- it requires `profile_name`;
- it passes `--profile-name "$(profile_name)"`;
- it conditionally passes obsolete `--env-file "$(env_file)"`;
- it includes the existing `--replace` behavior.

The later definition is the current read-only observer recipe and aligns with:

`scripts/audit/collect_canonical_live_proof_receipt.py`

The current collector CLI establishes:

- `--profile-name` is optional and has a default;
- `--compose-env-file` is the supported Compose environment-file argument;
- there is no current `--env-file` argument;
- the target remains read-only with respect to supported Compose observation;
- optional output and replace behavior remains supported.

The later Make recipe therefore represents the current intended surface.

A prior live operational Campaign already demonstrated the intended edit by removing the older duplicate block, but that Campaign failed at the Campaign boundary before task validation and must not be reused.

Subsequent Campaign Engine repairs resolved:

- task-validation evidence propagation;
- full-snapshot versus actual-changed-path classification.

This task is now intended to be rerun through a **fresh Campaign and fresh disposable worktree**.

## Files

Authorized edit:

1. `Makefile`

Read-only inspection:

2. `scripts/audit/collect_canonical_live_proof_receipt.py`

This change belongs in:

`Makefile`

Do not modify the collector script.

Do not modify any other repository file.

## Goal

Leave exactly one canonical:

`canonical-audit-live-proof-receipt`

Make target by removing the stale older definition and retaining the later recipe that matches the current collector CLI.

The resulting Makefile must stop producing the duplicate-target warning while preserving the current read-only audit command behavior.

## Requirements

1. Inspect both existing `canonical-audit-live-proof-receipt` definitions before editing.

2. Inspect the current argparse surface in:

   `scripts/audit/collect_canonical_live_proof_receipt.py`

3. Remove the **older stale duplicate recipe**.

4. Retain the **later read-only observer recipe**.

5. Do not:
   - rename the target;
   - create an alias;
   - merge the two recipes into a new third form;
   - retain both definitions.

6. Preserve the target name:

   `canonical-audit-live-proof-receipt`

7. Preserve its `.PHONY` declaration.

8. Preserve the later recipe's supported current inputs and behavior.

9. `profile_name` must remain optional/default-compatible.

10. `compose_env_file` must continue mapping to:

    `--compose-env-file`

11. Do not reintroduce obsolete:

    `--env-file`

12. Preserve the current collector's optional output/replace behavior where already exposed by the retained recipe.

13. Preserve the later recipe's read-only operational intent.

14. Do not change:
    - canonical audit authority;
    - runtime identity semantics;
    - evidence semantics;
    - Docker/Compose behavior;
    - collector implementation;
    - release claims;
    - architecture contracts.

15. Do not perform unrelated Makefile cleanup.

16. In particular, ignore unrelated duplicate comments, formatting inconsistencies, or neighboring cleanup opportunities.

17. Only `Makefile` may be mutated by the Task.

## Acceptance Criteria

Complete only when:

1. `Makefile` contains exactly one definition matching:

   `^canonical-audit-live-proof-receipt:`

2. The retained definition is the later read-only recipe aligned with the current collector CLI.

3. The stale recipe using obsolete `--env-file` is removed.

4. `profile_name` remains optional.

5. `compose_env_file` maps to:

   `--compose-env-file`

6. The target remains listed in `.PHONY`.

7. The retained recipe does not introduce unsupported collector arguments.

8. Docs validation passes:

   `make PYTHON=python3 docs`

9. The previous GNU Make duplicate-target warning for:

   `canonical-audit-live-proof-receipt`

   is absent from that validation run.

10. `git diff --check` passes.

11. Only `Makefile` is changed.

12. No live deployment, provider configuration, supported-Compose mutation, or production audit action occurs during validation.

## Non-Goals

Do not:

- modify `scripts/audit/collect_canonical_live_proof_receipt.py`;
- redesign the canonical audit interface;
- rename Make targets;
- clean unrelated Makefile comments;
- refactor neighboring audit recipes;
- change Docker Compose behavior;
- change release or runtime semantics;
- modify documentation;
- modify tests unrelated to this target;
- perform a provider integration change;
- enter CE-L3;
- add retry, repair, fallback, or rebinding behavior.

## Validation

The Executor must inspect both definitions and the current argparse surface.
The host runs the Task validation command exactly once after the boundary
check:

```bash
make PYTHON=python3 docs
```

Read-only acceptance checks:

```bash
test "$(rg -c '^canonical-audit-live-proof-receipt:' Makefile)" -eq 1
rg -n -A35 '^canonical-audit-live-proof-receipt:' Makefile
python3 scripts/audit/collect_canonical_live_proof_receipt.py --help
git diff --check
git status --short
git diff -- Makefile
```

The validation output must not contain the duplicate-target warning for
`canonical-audit-live-proof-receipt`. The expected changed-file set is exactly
`Makefile`. No deployment, provider configuration change, supported-Compose
mutation, or production audit action is part of validation.

## Campaign execution

Use a fresh Campaign and disposable worktree. Validation attempts = 1.
No automatic retry, repair, fallback, rebinding, commit, or CE-L3 progression.
The full authored Task Spec above is canonical Task input. Independent
Evaluator judgment must use verified bounded mutation evidence and the Task
validation result. File-scope or docs checks alone are not final Evaluation.

## Git — post-Evaluation operator closeout only

After a successful Campaign and after control returns to the operator, the
operator may separately authorize:

```bash
git add Makefile
git commit -m "Remove duplicate canonical audit make target"
```

Do not use `git add .`. Do not stage or commit inside the Campaign Executor.

## Closeout

Report:

- final Campaign result and independent Evaluator verdict;
- changed file, stale recipe removed, and current recipe retained;
- retained recipe alignment with the current collector CLI;
- target-definition count before and after;
- optional/default-compatible `profile_name`;
- preserved `compose_env_file -> --compose-env-file` mapping;
- absence of obsolete `--env-file` from the retained target;
- preserved `.PHONY`, optional output, replace, and read-only intent;
- the one `make PYTHON=python3 docs` result and absence of the duplicate warning;
- `git diff --check` result and final changed-file set;
- Executor/Evaluator provider-call counts and retry/fallback/rebinding counts;
- operational friction separately from Task correctness;
- no Campaign commit, no CE-L3, and preserved failure evidence when applicable.

Stop after this one Task. Do not automatically start another Task.
