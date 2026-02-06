# TASK_2026_02_06_008_memory_routes_return_404_on_cross_user_access

## Objective

Align memory route behavior with non-disclosure security semantics.

## Background

Tests expect a 404 when a resource exists but belongs to another user.
Current behavior returns 403, leaking existence.

## Requirements

- Ownership mismatch must return 404
- Auth missing behavior remains unchanged
- Test expectations must pass

## Acceptance Criteria

- Cross-user memory access returns 404
- Tests `test_memory_update_other_user_404` and delete equivalent pass

## Files Likely Touched

- Guardian memory routes
- Authorization logic

## Commit Plan

- Commit A: backend behavior change
- Commit B: docs/task mapping update

# TASK_2026_02_06_008_memory_routes_return_404_on_cross_user_access

## Metadata
- Campaign-ID: CAMPAIGN-2026-02-06-LOOP_INTEGRITY_AUTH_AND_DEFAULTS
- Task-ID: TASK-2026-02-06-008_memory_routes_return_404_on_cross_user_access
- Risk: HIGH
- Branch: campaign/2026-02-06/loop-integrity-auth-and-defaults
- Task artifact: docs/tasks/TASK_2026_02_06_008_memory_routes_return_404_on_cross_user_access.md
- Owner: resonant_jones

## Objective
Ensure cross-user access to memory resources returns **404** (not **403**) to prevent existence disclosure, while keeping “missing auth” behavior unchanged.

## Scope
### In-scope
- Adjust memory route ownership checks so that when an authenticated user attempts to update/delete another user’s memory, the response is **404**.
- Update/validate tests to match the non-disclosure semantic (404 on cross-user).

### Out-of-scope
- Changing the overall auth mechanism (API key / user headers) beyond what is needed to preserve existing “missing auth” behavior.
- Refactoring unrelated routes or test suites.

## Allowed files (STRICT)
> Do not edit files outside this list.

- guardian/routes/memory.py
- tests/routes/test_memory.py
- docs/tasks/TASK_2026_02_06_008_memory_routes_return_404_on_cross_user_access.md
- docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

## Dependencies / prereqs (NO GUESSING)
Run these commands to confirm the relevant files exist and the test runner is available.

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# confirm file paths exist
ls -la guardian/routes/memory.py tests/routes/test_memory.py

# confirm pytest is available (if not, record the exact failure output in Summary)
python -m pytest --version
```

## Command checklist (copy/paste)
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# 0) MUST be clean before starting
git status --porcelain -uall

# 1) locate ownership checks + current 403 behavior
rg -n "memory" guardian/routes/memory.py -S
rg -n "403|404|HTTPException|Forbidden|not found|ownership|user_id" guardian/routes/memory.py tests/routes/test_memory.py -S

# 2) run the focused failing tests (fast loop)
pytest -q tests/routes/test_memory.py -k "ownership|scoping|cannot_access|update_memory_checks_ownership|delete_memory_checks_ownership" -x

# 3) implement change ONLY in allowed files:
#    - when resource exists but user_id mismatches: return 404
#    - when auth is missing: keep current behavior unchanged

# 4) re-run focused tests
pytest -q tests/routes/test_memory.py -k "ownership|scoping|cannot_access|update_memory_checks_ownership|delete_memory_checks_ownership" -x

# 5) full memory test file (still small enough)
pytest -q tests/routes/test_memory.py

# 6) confirm only allowed files changed
git status --porcelain -uall
```

## Expected outputs (explicit success signals)
- The focused pytest run no longer shows `assert 403 == 404` failures.
- `pytest -q tests/routes/test_memory.py` exits **0**.
- Cross-user update/delete endpoints return **404** (verified by tests).
- `git status --porcelain -uall` shows changes only within the **Allowed files (STRICT)** list.

## Rollback / cleanup
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# discard uncommitted changes for this task
git restore -- guardian/routes/memory.py tests/routes/test_memory.py docs/tasks/TASK_2026_02_06_008_memory_routes_return_404_on_cross_user_access.md docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

# verify clean
git status --porcelain -uall
```

## Commit plan (MANUAL; index.lock workaround)
### Commit mode
- two-phase
  - Commit A: implementation + tests
  - Commit B: docs finalize (task summary + campaign mapping)

### Commit A (implementation)
- Commit message (EXACT):
  - `TASK-2026-02-06-008_memory_routes_return_404_on_cross_user_access: return 404 on cross-user access`

- Manual commands:
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

git add guardian/routes/memory.py tests/routes/test_memory.py

git commit --no-verify -m "TASK-2026-02-06-008_memory_routes_return_404_on_cross-user_access: return 404 on cross-user access"

git log -1 --oneline

git status --porcelain -uall
```

### Commit B (docs finalize + mapping)
- Commit message (EXACT):
  - `TASK-2026-02-06-008_memory_routes_return_404_on_cross_user_access: docs finalize + mapping`

- Manual commands:
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

git add docs/tasks/TASK_2026_02_06_008_memory_routes_return_404_on_cross_user_access.md docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

git commit --no-verify -m "TASK-2026-02-06-008_memory_routes_return_404_on_cross_user_access: docs finalize + mapping"

git log -1 --oneline

git status --porcelain -uall
```

## Campaign mapping
Update the campaign file mapping line to the exact format:

- `TASK-2026-02-06-008_memory_routes_return_404_on_cross_user_access -> [<commitA>, <commitB>]`

## Summary (fill after completion)
- What changed:
  - 
- Commands run + key outputs:
  - 
- Tests:
  - 
- Final mapping:
  - `TASK-2026-02-06-008_memory_routes_return_404_on_cross_user_access -> [<commitA>, <commitB>]`