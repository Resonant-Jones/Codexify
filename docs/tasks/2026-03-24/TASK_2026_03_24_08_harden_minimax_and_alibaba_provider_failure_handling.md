
Task 8: Harden Minimax and Alibaba provider failure handling

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Improve reliability and failure reporting for Minimax and Alibaba provider access so intermittent failures do not leave the chat loop or provider state ambiguous.

Perform the described edit only in the specified files.

This change belongs in:
 • backend provider adapters for Minimax and Alibaba
 • provider routing / timeout / retry policy files
 • tests covering provider error handling and catalog/request stability

Required behavior
 1. Audit current request path for both providers.
 2. Ensure timeouts and error handling are explicit and bounded.
 3. Differentiate:
 • auth/config failure
 • transport/network failure
 • provider timeout
 • provider returned error response
 • empty catalog / empty model result
 4. Ensure provider failures do not strand thread lock state upstream.
 5. Return diagnostics that the frontend can surface cleanly.
 6. Do not add broad speculative retries that amplify latency.

Files to modify

List all files before changes. Likely candidates include:
 • provider adapter files
 • routing/transport helpers
 • provider tests

Tests

Run:

pytest -v

If frontend provider error UI is changed too:

pnpm test

Add or update tests for:
 • timeout path
 • auth/config error path
 • transport failure path
 • provider error payload handling
 • deterministic surfaced diagnostics

Git commands

If checks pass:

git add <modified files>
git commit -m "Harden Minimax and Alibaba provider failures"

Output must include
 • Summary of changes
 • files modified
 • adapters/helpers touched
 • Test results
 • Git commit hash

⸻

# TASK_2026_03_24_08_harden_minimax_and_alibaba_provider_failure_handling

## Context

You’re operating on the local Codexify repo.  
Each task must be self-contained, testable, and committed individually.

## Instructions

Perform the described edit only in the specified files.

Improve reliability and failure reporting for Minimax and Alibaba provider access so intermittent failures do not leave the chat loop or provider state ambiguous.

This change belongs in:

- backend provider adapters for Minimax and Alibaba
- provider routing / timeout / retry policy files
- tests covering provider error handling and catalog/request stability

## Goal

Provider failures must be explicitly classified, bounded, and surfaced in a way that does not destabilize the chat loop or strand upstream state.

## Required Behavior

1. Audit current request path for both providers.

2. Ensure timeouts and error handling are explicit and bounded:
   - no unbounded waits
   - no silent failure paths

3. Differentiate failure types clearly:
   - auth/config failure
   - transport/network failure
   - provider timeout
   - provider returned error response
   - empty catalog / empty model result

4. Ensure provider failures do not strand thread lock state upstream:
   - failures must resolve the request lifecycle cleanly
   - upstream consumers must receive terminal signals

5. Return diagnostics that the frontend can surface cleanly:
   - structured error payloads
   - deterministic error categories

6. Do not add broad speculative retries that amplify latency:
   - retries must be explicit, minimal, and justified

## Files to Modify

List all files before changes. Likely candidates include:

- provider adapter files
- routing/transport helpers
- provider tests

## Run Tests

Run based on scope:

### Backend

```bash
pytest -v
```

### If frontend provider error UI is also modified

```bash
pnpm test
```

Add or update tests for:

- timeout path
- auth/config error path
- transport failure path
- provider error payload handling
- deterministic surfaced diagnostics

## Git Commands

If checks pass:

```bash
git add <modified files>
git commit -m "Harden Minimax and Alibaba provider failures"
```

## Output Must Include

- Summary of changes
- Files modified
- Adapters/helpers touched
- Test results
- Git commit hash