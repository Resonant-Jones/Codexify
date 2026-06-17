# Codex Next Task - 2026-06-06

## Goal
Classify local changes before starting a new implementation slice.

## Context
- Current branch: `main` at `2bcd31c00`
- This task exists to turn the Guardian Work Brief into one narrow implementation or verification step.
- Treat `docs/architecture/00-current-state.md` as the release-truth gate.

## Constraints
- Do not widen the supported release promise.
- Do not treat draft marketing or audit artifacts as runtime proof.
- Preserve existing user changes unless explicitly asked to touch them.
- Keep the task bounded to the smallest change that resolves the stated focus.

## Current Risks To Respect
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- Legacy `/tools` behavior still overlaps with the command bus.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains a high-blast-radius area with trust-policy and egress sensitivity.

## Acceptance Criteria
- The work produces one clear `go`, `hold`, or `next-proof-needed` outcome.
- Files changed are limited to the stated implementation or verification slice.
- Validation commands and results are recorded.
- The final response includes what Axis should add to his KB.
