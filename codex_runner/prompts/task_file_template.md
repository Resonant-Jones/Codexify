# <TASK-ID>: <Title>

## Metadata
- task_id: <TASK-ID>
- campaign_id: <CAMPAIGN-ID>
- run_id: <RUN-ID>
- risk: HIGH | MED | LOW

## Objective
One sentence measurable outcome.

## Scope
### In scope
- Explicit behavior/files to change.

### Out of scope
- Explicit exclusions.

## Allowed Files (STRICT)
- <repo-relative path or tight glob>

## Preconditions
- `git status --porcelain -uall` must be empty.

## Execution Checklist
- Deterministic command list.
- Validation commands.

## Expected Results
- Concrete success signals.

## Rollback / Cleanup
- Exact commands.

## Runner Receipt Contract
- Runner owns commits and artifact paths.
- Runner appends:
  - `## Implementation Receipt (Runner)`
  - `## Completion Summary (Runner)`
- Campaign mapping is updated by runner only inside:
  - `<!-- RUNNER_TASK_MAP -->`
  - `<!-- /RUNNER_TASK_MAP -->`
