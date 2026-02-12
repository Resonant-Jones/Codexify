# TASK-2026-02-12-003_primitive_contracts_and_registry: Primitive contracts + registry

## Metadata
- Task-ID: TASK-2026-02-12-003_primitive_contracts_and_registry
- Campaign-ID: CAMPAIGN-2026-02-12-001_FLOW_COMPILER_V0
- Branch: feat/flow-compiler-v0
- Repo root: <REPO_ROOT>
- Task artifact: docs/tasks/TASK_2026_02_12_003_primitive_contracts_and_registry.md
- Owner: resonant_jones
- Risk: MED
- Commit mode: two-phase

## Objective
Define strict input/output contracts for v0.1 primitives and implement a registry that validates FlowSpec references.

## Scope
### In-scope
- Define v0.1 primitive contract models for:
  - assemble_context, retrieve_memory, summarize, classify, plan, extract_actions
  - create_thread, append_thread, write_codex_entry
  - schedule_cron_job, emit_event
- Implement PrimitiveRegistry mapping primitive_name -> contract + handler stub (callable)
- Add machine-readable primitive catalog export (function)

### Out-of-scope
- Real integration to external systems for commit_to_repo / trigger_webhook (defer to v0.2)
- NL parsing

## Allowed files (STRICT)
- guardian/flows/primitives.py
- guardian/flows/spec.py (only if step union needs updates)
- guardian/flows/__init__.py
- docs/tasks/TASK_2026_02_12_003_primitive_contracts_and_registry.md
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

# implement contracts + registry in guardian/flows/primitives.py

python -c "from guardian.flows.primitives import PrimitiveRegistry; r=PrimitiveRegistry.default(); print(len(r.catalog()))"

git status --porcelain -uall
```

## Expected results (explicit)
- Python command prints a positive integer equal to the number of registered primitives (>= 10).

## Rollback / cleanup
```bash
cd <REPO_ROOT>
git checkout -- guardian/flows/primitives.py guardian/flows/spec.py guardian/flows/__init__.py
```

## Commit plan (MANUAL; index.lock workaround)

### Commit A (implementation) — two-phase only

Commit message (EXACT):

`TASK-2026-02-12-003_primitive_contracts_and_registry: primitive contracts + registry`

Manual commands (explicit paths only):

```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add guardian/flows/primitives.py guardian/flows/spec.py guardian/flows/__init__.py
git commit --no-verify -m "TASK-2026-02-12-003_primitive_contracts_and_registry: primitive contracts + registry"
git log -1 --oneline
git status --porcelain -uall
```

Commit A hash: c77f26de

### Commit B (docs finalize + mapping) — two-phase only

Commit message (EXACT):

`TASK-2026-02-12-003_primitive_contracts_and_registry: docs finalize + mapping`

Manual commands:

```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add docs/tasks/TASK_2026_02_12_003_primitive_contracts_and_registry.md docs/Campaign/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md
git commit --no-verify -m "TASK-2026-02-12-003_primitive_contracts_and_registry: docs finalize + mapping"
git log -1 --oneline
git status --porcelain -uall
```

## Campaign mapping (SOURCE OF TRUTH)
- TASK-2026-02-12-003_primitive_contracts_and_registry -> [c77f26de, <commitB>]

## Completion Summary (fill after completion)
- Status: DONE
- What changed:
  - Implemented strict primitive parameter contracts for 11 v0.1 primitives in `guardian/flows/primitives.py`.
  - Added `PrimitiveRegistry` with contract registration, parameter validation, deterministic handler invocation, and machine-readable catalog output.
  - Exported `PrimitiveRegistry` and `export_primitive_catalog` via `guardian/flows/__init__.py`.
- Commands run:
  ```bash
  git status --porcelain -uall
  .venv/bin/python -c "from guardian.flows.primitives import PrimitiveRegistry; r=PrimitiveRegistry.default(); print(len(r.catalog()))"
  git add guardian/flows/primitives.py guardian/flows/spec.py guardian/flows/__init__.py
  git commit --no-verify -m "TASK-2026-02-12-003_primitive_contracts_and_registry: primitive contracts + registry"
  ```
- Tests:
  - `.venv/bin/python -c "from guardian.flows.primitives import PrimitiveRegistry; r=PrimitiveRegistry.default(); print(len(r.catalog()))"` (pass; output: `11`)
- Scope check:
  - git status clean before starting: yes
  - Only allowed files modified: yes
- Commit info:
  - Commit mode: two-phase
  - Commit A hash (impl): c77f26de
  - Commit B hash (docs finalize): recorded in campaign mapping as `<commitB>`
- Campaign mapping updated: yes
- Notes / gotchas:
  - Runtime checks were executed with `.venv/bin/python` because system `python` in this shell lacks required dependencies.
