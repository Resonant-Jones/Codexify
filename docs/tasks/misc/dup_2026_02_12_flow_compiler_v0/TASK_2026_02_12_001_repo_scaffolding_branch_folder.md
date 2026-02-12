# TASK-2026-02-12-001_repo_scaffold: Repo scaffolding (branch + folders)

## Metadata

- Task-ID: TASK-2026-02-12-001_repo_scaffold
- Campaign-ID: CAMPAIGN-2026-02-12-001_FLOW_COMPILER_V0
- Branch: feat/flow-compiler-v0
- Repo root: <REPO_ROOT>
- Task artifact: docs/tasks/TASK_2026_02_12_001_repo_scaffold.md
- Owner: resonant_jones
- Risk: LOW
- Commit mode: two-phase

## Objective

Create the feature branch and module skeleton for the flow compiler system, without altering unrelated code.

## Scope

### In-scope

- Create branch `feat/flow-compiler-v0`
- Add initial module files:
  - guardian/flows/spec.py
  - guardian/flows/primitives.py
  - guardian/flows/compiler.py
  - guardian/flows/runner.py
  - guardian/flows/nl_compiler.py
  - guardian/routes/flows.py
- Add __init__.py as needed

### Out-of-scope

- Any changes to existing routes behavior
- Any database migrations
- Any connector/cron behavioral changes

## Allowed files (STRICT)

- guardian/flows/__init__.py
- guardian/flows/spec.py
- guardian/flows/primitives.py
- guardian/flows/compiler.py
- guardian/flows/runner.py
- guardian/flows/nl_compiler.py
- guardian/routes/flows.py
- docs/tasks/TASK_2026_02_12_001_repo_scaffold.md
- docs/Campaign/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md

## Preconditions (NO GUESSING)

```bash
cd <REPO_ROOT>
git status --porcelain -uall
# EXPECTED: (no output)
```

## Execution plan (copy/paste)

```bash
cd <REPO_ROOT>

# 1) confirm clean scope
git status --porcelain -uall

# 2) create branch
git checkout -b feat/flow-compiler-v0

# 3) create skeleton modules
mkdir -p guardian/flows docs/tasks docs/Campaign
touch guardian/flows/__init__.py \
  guardian/flows/spec.py guardian/flows/primitives.py guardian/flows/compiler.py \
  guardian/flows/runner.py guardian/flows/nl_compiler.py guardian/routes/flows.py

# 4) confirm only allowed files changed
git status --porcelain -uall
```

## Expected results (explicit)

- `git branch --show-current` returns feat/flow-compiler-v0.
- `git status --porcelain -uall` shows only the allowed file paths above.

## Rollback / cleanup

```bash
cd <REPO_ROOT>
git checkout -- guardian/flows guardian/routes/flows.py
git clean -fd -- guardian/flows docs/tasks docs/Campaign
```

## Commit plan (MANUAL; index.lock workaround)

### Commit A (implementation) — two-phase only

**Commit message (EXACT):**  
`TASK-2026-02-12-001_repo_scaffold: scaffold flow compiler modules`

**Manual commands (explicit paths only):**

```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add guardian/flows/__init__.py guardian/flows/spec.py guardian/flows/primitives.py guardian/flows/compiler.py guardian/flows/runner.py guardian/flows/nl_compiler.py guardian/routes/flows.py
git commit --no-verify -m "TASK-2026-02-12-001_repo_scaffold: scaffold flow compiler modules"
git log -1 --oneline
git status --porcelain -uall
```

Commit A hash: <FILL_AFTER_COMMIT_A>

### Commit B (docs finalize + mapping) — two-phase only

**Commit message (EXACT):**  
`TASK-2026-02-12-001_repo_scaffold: docs finalize + mapping`

**Manual commands:**

```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add docs/tasks/TASK_2026_02_12_001_repo_scaffold.md docs/Campaign/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md
git commit --no-verify -m "TASK-2026-02-12-001_repo_scaffold: docs finalize + mapping"
git log -1 --oneline
git status --porcelain -uall
```

## Campaign mapping (SOURCE OF TRUTH)

- TASK-2026-02-12-001_repo_scaffold -> [<commitA>, <commitB>]

## Completion Summary (fill after completion)

- Status: DONE | BLOCKED | DEFERRED
- What changed:
  - 
- Commands run:
  ```bash
  ```
- Tests:
  - 
- Scope check:
  - git status clean before starting: yes/no
  - Only allowed files modified: yes/no
- Commit info:
  - Commit mode: two-phase
  - Commit A hash (impl): <…>
  - Commit B hash (docs finalize): recorded in campaign mapping
- Campaign mapping updated: yes/no
- Notes / gotchas:
  - 
