Preflight: git status --porcelain -uall must be empty

If preflight is not empty, STOP and run exactly:
- git status --porcelain -uall
- git stash push -u -m "preflight-TASK-2026-02-16-001"
- git status --porcelain -uall

# TASK-2026-02-16-001  SSE outbox cleanup API alignment
- Risk: HIGH
- Findings: FINDING-2026-02-16-011
- Allowed files:
  - guardian/guardian_api.py
  - guardian/core/event_bus.py
  - guardian/tests/test_events_outbox.py
- Dependencies/Prereqs:
  - command -v rg
  - command -v pytest
  - docker compose up -d db
  - docker compose ps db
- Command checklist:
  1. rg -nF "delete_events_up_to" guardian/guardian_api.py
  2. rg -nF "def delete_events_through" guardian/core/event_bus.py
  3. Align caller/callee on one cleanup method/signature.
  4. pytest -q guardian/tests/test_events_outbox.py
- Scope guard:
  - git diff --name-only
  - If any changed file is outside Allowed files, STOP and run exactly:
    - git restore --staged --worktree -- .
    - git clean -fd
    - git status --porcelain -uall
- Expected outputs:
  - No missing-method SSE cleanup call remains.
  - guardian/tests/test_events_outbox.py exits 0.
- Rollback / cleanup commands:
  - git restore --staged --worktree -- guardian/guardian_api.py guardian/core/event_bus.py guardian/tests/test_events_outbox.py
  - git status --porcelain -uall

## Runner Receipt (Start)

- Campaign: CAMPAIGN_2026_02_16_SECURITY_MVP_FOLLOWUP_EXECUTION

- Task ID: TASK-2026-02-16-001

- Head before: e52d117a333b8623a9f90e2c1944534a338dcc36
