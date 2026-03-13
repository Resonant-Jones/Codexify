# TASK-2026-02-12-001_repo_scaffold: Repo scaffolding (branch + folders)

## Metadata

- Task-ID: TASK-2026-02-12-001_repo_scaffold
- Campaign-ID: CAMPAIGN-2026-02-12-001_FLOW_COMPILER_V0
- Branch: feat/flow-compiler-v0
- Repo root: <REPO_ROOT>
- Task artifact: docs/work/tasks/2026/02/TASK_2026_02_12_001_repo_scaffold.md
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
- docs/work/tasks/2026/02/TASK_2026_02_12_001_repo_scaffold.md
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

# 1) confirm clean scope
git status --porcelain -uall

# 2) create branch
git checkout -b feat/flow-compiler-v0

# 3) create skeleton modules
mkdir -p guardian/flows docs/work/tasks docs/work/campaigns
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
git clean -fd -- guardian/flows docs/work/tasks docs/work/campaigns
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

Commit A hash: f532d9b7

### Commit B (docs finalize + mapping) — two-phase only

**Commit message (EXACT):**  
`TASK-2026-02-12-001_repo_scaffold: docs finalize + mapping`

**Manual commands:**

```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add docs/work/tasks/2026/02/TASK_2026_02_12_001_repo_scaffold.md docs/work/campaigns/2026/02/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md
git commit --no-verify -m "TASK-2026-02-12-001_repo_scaffold: docs finalize + mapping"
git log -1 --oneline
git status --porcelain -uall
```

## Campaign mapping (SOURCE OF TRUTH)

- TASK-2026-02-12-001_repo_scaffold -> [f532d9b7, <commitB>]

## Completion Summary (fill after completion)

- Status: DONE
- What changed:
  - Created scaffold files under `guardian/flows/` and `guardian/routes/flows.py`.
  - Added canonical task artifact file `docs/work/tasks/2026/02/TASK_2026_02_12_001_repo_scaffold.md` from the existing task artifact content, then finalized this summary.
  - Updated campaign final mapping row for this task.
- Commands run:
  ```bash
  git status --porcelain -uall
  git branch --show-current
  mkdir -p guardian/flows docs/work/tasks docs/work/campaigns
  touch guardian/flows/__init__.py guardian/flows/spec.py guardian/flows/primitives.py guardian/flows/compiler.py guardian/flows/runner.py guardian/flows/nl_compiler.py guardian/routes/flows.py
  git add guardian/flows/__init__.py guardian/flows/spec.py guardian/flows/primitives.py guardian/flows/compiler.py guardian/flows/runner.py guardian/flows/nl_compiler.py guardian/routes/flows.py
  git commit --no-verify -m "TASK-2026-02-12-001_repo_scaffold: scaffold flow compiler modules"
  cp docs/work/tasks/2026/02/TASK_2026_02_12_001_repo_scaffolding_branch_folder.md docs/work/tasks/2026/02/TASK_2026_02_12_001_repo_scaffold.md
  ```
- Tests:
  - None (scaffolding-only task). Verified clean preconditions and allowed-file scope via `git status --porcelain -uall`.
- Scope check:
  - git status clean before starting: yes
  - Only allowed files modified: yes
- Commit info:
  - Commit mode: two-phase
  - Commit A hash (impl): f532d9b7
  - Commit B hash (docs finalize): recorded in campaign mapping as `<commitB>`
- Campaign mapping updated: yes
- Notes / gotchas:
  - The repository artifact filename was `docs/work/tasks/2026/02/TASK_2026_02_12_001_repo_scaffolding_branch_folder.md` while campaign/metadata referenced `docs/work/tasks/2026/02/TASK_2026_02_12_001_repo_scaffold.md`; the canonical filename was created to keep commit paths aligned with campaign instructions.
