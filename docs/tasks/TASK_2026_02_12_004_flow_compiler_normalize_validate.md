# TASK-2026-02-12-004_flow_compiler_normalize_validate: Flow Compiler (stack primitives into executable jobs)

## Metadata
- Task-ID: TASK-2026-02-12-004_flow_compiler_normalize_validate
- Campaign-ID: CAMPAIGN-2026-02-12-001_FLOW_COMPILER_V0
- Branch: feat/flow-compiler-v0
- Repo root: <REPO_ROOT>
- Task artifact: docs/tasks/TASK_2026_02_12_004_flow_compiler_normalize_validate.md
- Owner: resonant_jones
- Risk: MED
- Commit mode: two-phase

## Objective
Implement compile_flow() to normalize and validate FlowSpecs into an executable compiled plan.

## Scope
### In-scope
- Implement compile_flow(flow_spec) -> CompiledFlow
- Normalization: defaults, templates, sugar expansion
- Validation: primitive exists, params schema-valid, budgets sane, triggers valid
- Stable JSON-serializable compiled output

### Out-of-scope
- Running/executing steps (runner is next task)
- NL parsing

## Allowed files (STRICT)
- guardian/flows/compiler.py
- guardian/flows/spec.py (only if compiled models needed)
- guardian/flows/primitives.py (only if registry hooks needed)
- guardian/flows/__init__.py
- docs/tasks/TASK_2026_02_12_004_flow_compiler_normalize_validate.md
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
git status --porcelain -uall

# implement compile_flow in guardian/flows/compiler.py

python -c "from guardian.flows.compiler import compile_flow; from guardian.flows.spec import FlowSpec; print('ok')"

git status --porcelain -uall
```

## Expected results (explicit)
- Import check prints `ok`.
- Compiler raises explicit validation errors on invalid input (document at least one example in code comments or tests later).

## Rollback / cleanup
```bash
cd <REPO_ROOT>
git checkout -- guardian/flows/compiler.py guardian/flows/spec.py guardian/flows/primitives.py guardian/flows/__init__.py
```

## Commit plan (MANUAL; index.lock workaround)

### Commit A (implementation) — two-phase only
Commit message: `TASK-2026-02-12-004_flow_compiler_normalize_validate: flow compiler normalize+validate`

```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add guardian/flows/compiler.py guardian/flows/spec.py guardian/flows/primitives.py guardian/flows/__init__.py
git commit --no-verify -m "TASK-2026-02-12-004_flow_compiler_normalize_validate: flow compiler normalize+validate"
git log -1 --oneline
git status --porcelain -uall
```

Commit A hash: <FILL_AFTER_COMMIT_A>

### Commit B (docs finalize + mapping) — two-phase only
Commit message: `TASK-2026-02-12-004_flow_compiler_normalize_validate: docs finalize + mapping`

```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add docs/tasks/TASK_2026_02_12_004_flow_compiler_normalize_validate.md docs/Campaign/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md
git commit --no-verify -m "TASK-2026-02-12-004_flow_compiler_normalize_validate: docs finalize + mapping"
git log -1 --oneline
git status --porcelain -uall
```

## Campaign mapping (SOURCE OF TRUTH)
- TASK-2026-02-12-004_flow_compiler_normalize_validate -> [<commitA>, <commitB>]

## Completion Summary (fill after completion)
- Status: DONE | BLOCKED | DEFERRED
- What changed:
  - <bullets>
- Commands run:
  ``` 
  <commands>
  ```
- Tests:
  - <none in this task; added later> OR <import check pass/fail>
- Scope check:
  - git status clean before starting: yes/no
  - Only allowed files modified: yes/no
- Commit info:
  - Commit mode: two-phase
  - Commit A hash (impl): <…>
  - Commit B hash (docs finalize): recorded in campaign mapping
- Campaign mapping updated: yes/no
- Notes / gotchas:
  - <anything important>
