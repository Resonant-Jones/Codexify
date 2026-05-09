# Codexify Solo Operator Coding Worker Runbook

Purpose: give a solo operator the current truth surface for Guardian-mediated
coding-worker work without implying autonomous retry loops or test-gated
convergence that do not exist yet.

Last updated: 2026-05-09

Source anchors:
- `docs/architecture/00-current-state.md`
- `docs/architecture/runtime-protocol-token-contract.md`
- `docs/architecture/delegation-operator-manual.md`
- `guardian/agents/coding_agent_contracts.py`
- `guardian/agents/test_results.py`
- `guardian/agents/store.py`
- `guardian/workers/`
- `guardian/tests/agents/test_test_results.py`

## Runtime Truths

1. A normalized test-result contract now exists in `guardian/agents/test_results.py`.
2. The contract is a preparatory seam for future autonomous convergence logic.
3. It does not by itself cause the coding worker to execute tests automatically.
4. It does not enable retry-until-tests-pass behavior.
5. Future loop work must consume the normalized test-result contract rather than
   raw stdout/stderr blobs.

## Bounded Validation Retry

- The worker now supports bounded supervised validation retries.
- Default maximum validation attempts: `3`.
- Environment override: `CODING_WORKER_MAX_VALIDATION_ATTEMPTS`.
- Valid values clamp to the range `1..10`.
- `1` preserves the old single-attempt behavior.
- Retries happen only after a success-like adapter result and a failing
  validation command.
- Retries do not happen when the adapter fails, when no validation command is
  present, or when shell execution is blocked by policy.
- The retry prompt includes bounded validation feedback: command, status, exit
  code, fail signature, and truncated stdout/stderr previews.
- Final validation failure is still a terminal failure.
- The worker stops when attempts are exhausted; this is still not autonomous
  commit/merge behavior.

## Operator Interpretation

- `passed` means the test subprocess exited cleanly and may carry summary counts.
- `failed` means the subprocess returned a nonzero exit code and produced a
  deterministic fail signature.
- `error` means the command could not be treated as a valid test result.
- `not_run` means the run was intentionally skipped by policy and must not be
  mistaken for success.

## What This Does Not Mean

- It does not mean Guardian has an autonomous remediation loop.
- It does not mean coding-worker execution now re-runs until green.
- It does not mean adapter success is equivalent to repository test success.
- It does not mean retry policy should read raw terminal output directly once
  this seam is wired into the worker path.
- MiniMax may run behind the `codex` adapter, but Guardian still owns the loop
  boundary and stops after the bounded attempts are exhausted.

## Follow-Through Rule

When the worker-side loop is implemented later, it must:

1. normalize subprocess output through this contract,
2. persist or forward the normalized result,
3. keep retry policy separate from normalization, and
4. keep operator-visible truth deterministic across repeated attempts.
