```markdown

# TASK-2026-02-06-002_fix_make_test_target_and_pytest_install_path.md
## Metadata

- Task-ID: TASK-2026-02-06-002_fix_make_test_target_and_pytest_install_path
- Campaign-ID: CAMPAIGN-2026-02-06-LOOP_INTEGRITY_PLAN_ENV_AND_VALIDATION
- Task artifact: docs/tasks/TASK_2026_02_06_002_fix_make_test_target_and_pytest_install_path.md
- Owner: resonant_jones
- Risk: MED

## Objective

Make `make test` (or the repo’s canonical test command) deterministically runnable on a fresh local machine by ensuring pytest is discoverable and the test entrypoint matches reality.

## Scope

### In-scope

- Fix Makefile test target to run pytest (or existing canonical runner).
- Document the exact python invocation that matches your venv layout.
- Ensure it fails with a helpful message if pytest is missing.

### Out-of-scope

- Rewriting tests.
- Adding CI.

## Allowed files (STRICT)

- Makefile
- README.md
- docs/tasks/TASK_2026_02_06_002_fix_make_test_target_and_pytest_install_path.md
- docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_PLAN_ENV_AND_VALIDATION.md

## Preconditions (NO GUESSING)

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall
```

Expected: no output.

Execution plan

cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# See current behavior
make test || true

# Confirm pytest presence
python -m pytest --version || true

# Canonical test command (must be what Makefile will run)
python -m pytest -q || true

Expected results
 • make test invokes the canonical pytest command (or documented equivalent).
 • If pytest is missing, output instructs exactly how to install it (e.g., python -m pip install -r requirements.txt or python -m pip install pytest depending on repo policy).

Rollback / cleanup

git checkout -- Makefile README.md

Commit plan (MANUAL; index.lock workaround)

Commit A (implementation)
 • Commit message (EXACT):
 • TASK-2026-02-06-002_fix_make_test_target_and_pytest_install_path: make test deterministic
 • Manual commands:

git add Makefile README.md
git commit --no-verify -m "TASK-2026-02-06-002_fix_make_test_target_and_pytest_install_path: make test deterministic"
git log -1 --oneline
git status --porcelain -uall

Commit B (docs finalize + mapping)
 • Commit message (EXACT):
 • TASK-2026-02-06-002_fix_make_test_target_and_pytest_install_path: docs finalize + mapping
 • Manual commands:

git add docs/tasks/TASK_2026_02_06_002_fix_make_test_target_and_pytest_install_path.md docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_PLAN_ENV_AND_VALIDATION.md
git commit --no-verify -m "TASK-2026-02-06-002_fix_make_test_target_and_pytest_install_path: docs finalize + mapping"
git log -1 --oneline
git status --porcelain -uall

Mapping
 • TASK-2026-02-06-002_fix_make_test_target_and_pytest_install_path -> [, ]

## Summary
- Status: DONE.
- Changes:
  - Updated `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/Makefile` to use `python`/`pip` defaults and to fail fast with pytest install guidance.
  - Updated `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/README.md` to reflect the fixed `make test` behavior.
- Commands run:
  - `make test` (failed with guided pytest install message)
  - `python -m pytest --version` → `No module named pytest`
  - `python -m pytest -q` → `No module named pytest`
- Commit mode: two-phase.
- Implementation commit: `de6379d3`.
