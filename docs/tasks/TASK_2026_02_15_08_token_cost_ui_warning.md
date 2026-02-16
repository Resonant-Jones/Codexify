
TASK 8 — Token Cost UI Warning (Prompt Cost Transparency + Threshold Guard)

Objective

Expose system prompt assembly metadata to the frontend and warn when prompt cost exceeds configurable thresholds.

This task closes the loop on Task 4 (prompt builder metadata) by:
- exposing prompt segment/token estimates via a backend endpoint
- adding a small UI indicator + warning state
- adding tests to ensure threshold behavior is deterministic

Scope

Full-stack for this task (backend + frontend).
Do not change prompt assembly logic itself (Task 4) except to reuse its existing metadata output.
Do not change retrieval logic.
Do not add new persona/imprint storage behavior.

Correctness / UX Invariants (Must Hold)

1) Read-Only Summary
- The endpoint must be read-only and must not mutate server state.

2) No Sensitive Payload Leakage
- The endpoint must not return full system docs, full imprint text, or raw conversation text.
- It returns sizes/estimates and segment descriptors only.

3) Deterministic Thresholding
- Given the same metadata inputs, threshold status must be stable.

4) Graceful Degradation
- If metadata is unavailable, UI must show an "unknown" state rather than breaking chat.

API Contract

Add a backend endpoint:

GET /api/system_prompt/summary

Response (example shape):

{
  "estimated_tokens_total": 1234,
  "threshold": {
    "warn_tokens": 6000,
    "hard_tokens": 8000,
    "status": "ok" | "warn" | "hard" | "unknown"
  },
  "segments": [
    {
      "name": "base" | "imprint" | "persona" | "system_docs" | "scratchpad",
      "chars": 4000,
      "estimated_tokens": 1000,
      "truncated": false
    }
  ],
  "docs_count": 7,
  "generated_at": "ISO-8601"
}

Rules:
- docs_count is the count of documents included in the system_docs block (if known).
- If docs_count cannot be computed without retrieving full docs, return null and do not fetch.

Threshold Policy

- warn_tokens default: 6000
- hard_tokens default: 8000

Allow overrides via config/env if the repo supports config knobs.
If no config system exists for this, keep constants in backend with a clear TODO comment.

Frontend UI

Add a small indicator component in the chat UI that displays:
- Prompt cost status: OK / WARN / HARD / UNKNOWN
- Total estimated tokens

Behavior:
- OK: subtle indicator.
- WARN: display a warning badge (non-blocking).
- HARD: display a stronger warning and optionally disable "send" with explanatory tooltip (choose the least disruptive behavior consistent with existing UX patterns).
- UNKNOWN: display a neutral state.

The UI should poll or fetch summary in a lightweight way:
- on chat view mount
- after settings/persona changes (if hooks exist)

Do not add aggressive polling.

Files Likely Affected

Backend:
- guardian/routes/* (new route or extend existing)
- guardian/core/prompt_builder.py (read-only metadata reuse)
- guardian/config/* (if threshold config exists)

Frontend:
- frontend/src/features/chat/* (chat UI)
- frontend/src/components/* (indicator component)
- frontend tests for component behavior

Codexify Task Prompt

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:

1) Backend: Implement Summary Endpoint
- Add GET /api/system_prompt/summary.
- Source metadata from the existing prompt builder output.
- Do not return raw segment contents, only counts/estimates.
- Add threshold evaluation (ok/warn/hard/unknown).

2) Backend: Tests
Add tests that fail before and pass after:
- Endpoint returns the expected shape.
- Does not include raw prompt contents.
- Threshold status changes correctly at boundary values.

3) Frontend: Add Indicator Component
- Add a small component that displays status + total estimated tokens.
- Integrate into chat UI in a non-intrusive location.

4) Frontend: Tests
Add tests verifying:
- OK/WARN/HARD/UNKNOWN states render as expected.
- HARD state applies the chosen UX behavior (badge only or disable send).

5) Validation
Run full-stack tests:

Backend:
pytest -v

Frontend (choose repo convention):
- pnpm test
or
- npm test

If linting is part of CI for frontend, run the repo-defined lint command as well.

6) Commit
Stage only modified files.
Commit message:

"Add prompt token cost summary endpoint and UI warning"

Output (Required)

- Summary of backend route + frontend component changes.
- Backend + frontend test results summary.
- Git commit hash.

Constraints

- Do not add new retrieval logic.
- Do not leak sensitive prompt contents.
- Do not implement persona persistence here.

This task makes prompt cost visible and prevents silent token bloat from degrading the user experience.
