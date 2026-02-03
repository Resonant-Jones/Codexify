# Task 001: Standardize Activation Prompt Validation

## Objective
Ensure activation prompts are consistently structured and validated before task execution.

## Background
Audit review found activation prompts vary in structure, making auditability and reproducibility inconsistent.

## Scope
- Define a minimal activation prompt schema.
- Add validation to reject missing or malformed prompts.
- Record validation failures in audit logs.

## Acceptance Criteria
- Activation prompt schema is documented and enforced.
- Missing required fields fails fast with a clear error.
- Validation results are logged with task id and timestamp.

## Implementation Notes
- Prefer a centralized validation helper used by all task runners.
- Keep schema small: objective, scope, constraints, success criteria.

## Files
- codex_runner/
- codex_tasks/
- docs/

## Tests
- pytest -q
