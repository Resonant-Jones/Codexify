# TASK-2026-02-12-002_flowspec_models_and_schema_export: FlowSpec schema (v0.1) + JSON Schema export

## Metadata
- Task-ID: TASK-2026-02-12-002_flowspec_models_and_schema_export
- Campaign-ID: CAMPAIGN-2026-02-12-001_FLOW_COMPILER_V0
- Branch: feat/flow-compiler-v0
- Repo root: <REPO_ROOT>
- Task artifact: docs/tasks/TASK_2026_02_12_002_flowspec_models_and_schema_export.md
- Owner: resonant_jones
- Risk: MED
- Commit mode: two-phase

## Objective
Define canonical FlowSpec and FlowRun models with strict typing and a reproducible JSON Schema export.

## Scope
### In-scope
- Implement Pydantic models:
  - FlowSpec (v0.1)
  - FlowRun (v0.1)
  - Step types (typed union)
- Provide JSON schema export (script or endpoint)
- Add minimal docs/comments describing fields

### Out-of-scope
- Execution engine behavior (runner) beyond type definitions
- NL parsing
- API endpoints beyond schema export (unless required for export)

## Allowed files (STRICT)
- guardian/flows/spec.py
- guardian/flows/__init__.py
- docs/tasks/TASK_2026_02_12_002_flowspec_models_and_schema_export.md
- docs/Campaign/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md
- <optional one of: scripts/flow_schema_export.py OR guardian/routes/flows.py if export is an endpoint>

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

# implement FlowSpec/FlowRun in guardian/flows/spec.py

# run minimal import check
python -c "from guardian.flows.spec import FlowSpec, FlowRun; print('ok')"

git status --porcelain -uall
```

## Expected results (explicit)
- Import check prints `ok`.
- JSON schema export produces a file or response without errors (exact command depends on chosen export mechanism).

## Rollback / cleanup
```bash
cd <REPO_ROOT>
git checkout -- guardian/flows/spec.py guardian/flows/__init__.py
```

## Commit plan (MANUAL; index.lock workaround)

### Commit A (implementation) — two-phase only
Commit message (EXACT):

`TASK-2026-02-12-002_flowspec_models_and_schema_export: FlowSpec v0.1 models + schema export`

Manual commands (explicit paths only):

```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add guardian/flows/spec.py guardian/flows/__init__.py <EXPORT_PATH_IF_ANY>
git commit --no-verify -m "TASK-2026-02-12-002_flowspec_models_and_schema_export: FlowSpec v0.1 models + schema export"
git log -1 --oneline
git status --porcelain -uall
```
Commit A hash: 1fcf4f05

### Commit B (docs finalize + mapping) — two-phase only
Commit message (EXACT):

`TASK-2026-02-12-002_flowspec_models_and_schema_export: docs finalize + mapping`

Manual commands:

```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add docs/tasks/TASK_2026_02_12_002_flowspec_models_and_schema_export.md docs/Campaign/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md
git commit --no-verify -m "TASK-2026-02-12-002_flowspec_models_and_schema_export: docs finalize + mapping"
git log -1 --oneline
git status --porcelain -uall
```

## Campaign mapping (SOURCE OF TRUTH)
- TASK-2026-02-12-002_flowspec_models_and_schema_export -> [1fcf4f05, <commitB>]

## Completion Summary (fill after completion)
- Status: DONE

- What changed:
  - Implemented FlowSpec v0.1 and FlowRun models in `guardian/flows/spec.py` with strict model-level validation, typed step union, and deterministic defaults.
  - Exported flow model symbols via `guardian/flows/__init__.py`.
  - Added schema export utility `scripts/flow_schema_export.py` for reproducible JSON schema bundle output.

- Commands run:

  ```bash
  git status --porcelain -uall
  .venv/bin/python -c "from guardian.flows.spec import FlowSpec, FlowRun; print('ok')"
  PYTHONPATH=. .venv/bin/python scripts/flow_schema_export.py --out /tmp/flow_schema_v0_1.json
  .venv/bin/python -c "import json; d=json.load(open('/tmp/flow_schema_v0_1.json')); print(sorted(d['schemas'].keys()))"
  git add guardian/flows/spec.py guardian/flows/__init__.py scripts/flow_schema_export.py
  git commit --no-verify -m "TASK-2026-02-12-002_flowspec_models_and_schema_export: FlowSpec v0.1 models + schema export"
  ```

- Tests:

  - `.venv/bin/python -c "from guardian.flows.spec import FlowSpec, FlowRun; print('ok')"` (pass)
  - `PYTHONPATH=. .venv/bin/python scripts/flow_schema_export.py --out /tmp/flow_schema_v0_1.json` (pass)

- Scope check:

  - git status clean before starting: yes
  - Only allowed files modified: yes

- Commit info:

  - Commit mode: two-phase
  - Commit A hash (impl): 1fcf4f05
  - Commit B hash (docs finalize): recorded in campaign mapping as `<commitB>`

- Campaign mapping updated: yes

- Notes / gotchas:

  - Task artifact filename in repo was `docs/tasks/TASK_2026_02_12_002_flowspec_models_json_schema_export.md.md` while campaign/metadata referenced `docs/tasks/TASK_2026_02_12_002_flowspec_models_and_schema_export.md`; the canonical filename was created for commit-path consistency.
  - System `python` lacked `pydantic`; checks were run in `.venv` to satisfy the required validation command.
