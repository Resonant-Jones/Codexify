# TASK-2026-02-12-009_tests_and_smoke_script: Tests + smoke script

## Metadata
- Task-ID: TASK-2026-02-12-009_tests_and_smoke_script
- Campaign-ID: CAMPAIGN-2026-02-12-001_FLOW_COMPILER_V0
- Branch: feat/flow-compiler-v0
- Repo root: <REPO_ROOT>
- Task artifact: docs/work/tasks/2026/02/TASK_2026_02_12_009_tests_and_smoke_script.md
- Owner: resonant_jones
- Risk: MED
- Commit mode: two-phase

## Objective
Add tests and a smoke script that prove FlowSpec validation, compilation, confidence gating, and a minimal run path.

## Scope
### In-scope
- Unit tests for:
  - FlowSpec validation
  - primitive param validation
  - compiler normalization
  - confidence gating logic
- Smoke script:
  - create flow
  - validate
  - run now
  - fetch run trace

### Out-of-scope
- End-to-end connector tests
- Render deploy wiring

## Allowed files (STRICT)
- <test paths in your repo, e.g. tests/test_flows_*.py>
- <one smoke script path, e.g. scripts/flows_smoke.sh or scripts/flows_smoke.py>
- docs/work/tasks/2026/02/TASK_2026_02_12_009_tests_and_smoke_script.md
- docs/work/campaigns/2026/02/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md

## Preconditions (NO GUESSING)
```bash
cd <REPO_ROOT>
git status --porcelain -uall
# EXPECTED: (no output)
```

## Execution plan (copy/paste)
```bash
cd <REPO_ROOT>
git status --porcelain -uall

# add tests and smoke script under allowed paths

# run tests (choose your test runner)

pytest -q

git status --porcelain -uall
```

## Expected results (explicit)
- `pytest -q` exits 0.
- Smoke script exits 0 and prints a clear success marker (define one string).

## Rollback / cleanup
```bash
cd <REPO_ROOT>
git checkout -- <test_files> <smoke_script>
```

## Commit plan (MANUAL; index.lock workaround)

### Commit A (implementation) — two-phase only

**Commit message (EXACT):** `TASK-2026-02-12-009_tests_and_smoke_script: tests + smoke script`

**Manual commands:**
```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add <test_files> <smoke_script>
git commit --no-verify -m "TASK-2026-02-12-009_tests_and_smoke_script: tests + smoke script"
git log -1 --oneline
git status --porcelain -uall
```

Commit A hash: cc97f3a5

### Commit B (docs finalize + mapping) — two-phase only

**Commit message (EXACT):** `TASK-2026-02-12-009_tests_and_smoke_script: docs finalize + mapping`

**Manual commands:**
```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add docs/work/tasks/2026/02/TASK_2026_02_12_009_tests_and_smoke_script.md docs/work/campaigns/2026/02/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md
git commit --no-verify -m "TASK-2026-02-12-009_tests_and_smoke_script: docs finalize + mapping"
git log -1 --oneline
git status --porcelain -uall
```

## Campaign mapping (SOURCE OF TRUTH)
- TASK-2026-02-12-009_tests_and_smoke_script -> [cc97f3a5, <commitB>]

## Completion Summary (fill after completion)
- Status: DONE
- What changed:
  - Added focused flow test suite at `tests/test_flows_core.py` covering FlowSpec validation, primitive param validation, compiler normalization/warnings, NL confidence gating, and minimal runner path with idempotency cache behavior.
  - Added smoke script `scripts/flows_smoke.py` that performs create -> validate -> run -> list runs -> get run trace and prints `FLOW_SMOKE_OK`.
- Commands run:
  ```bash
  git status --porcelain -uall
  PYTHONPATH=. .venv/bin/pytest -q tests/test_flows_core.py
  PYTHONPATH=. .venv/bin/python scripts/flows_smoke.py
  git add tests/test_flows_core.py scripts/flows_smoke.py
  git commit --no-verify -m "TASK-2026-02-12-009_tests_and_smoke_script: tests + smoke script"
  ```
- Tests:
  - `PYTHONPATH=. .venv/bin/pytest -q tests/test_flows_core.py` (pass)
  - `PYTHONPATH=. .venv/bin/python scripts/flows_smoke.py` (pass; marker: `FLOW_SMOKE_OK`)
- Scope check:
  - git status clean before starting: yes
  - Only allowed files modified: yes
- Commit info:
  - Commit mode: two-phase
  - Commit A hash: cc97f3a5
  - Commit B hash: recorded in campaign mapping
- Campaign mapping updated: yes
- Notes / gotchas:
  - Full-repo `pytest -q` was not executed in this task; targeted flow test module was run to validate newly introduced flow compiler/runtime behavior deterministically.
