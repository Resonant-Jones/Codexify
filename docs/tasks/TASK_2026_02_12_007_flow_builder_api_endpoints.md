# TASK-2026-02-12-007_flow_builder_api_endpoints: API endpoints for Flow Builder (create/list/validate/execute)

## Metadata
- Task-ID: TASK-2026-02-12-007_flow_builder_api_endpoints
- Campaign-ID: CAMPAIGN-2026-02-12-001_FLOW_COMPILER_V0
- Branch: feat/flow-compiler-v0
- Repo root: <REPO_ROOT>
- Task artifact: docs/tasks/TASK_2026_02_12_007_flow_builder_api_endpoints.md
- Owner: resonant_jones
- Risk: HIGH
- Commit mode: two-phase

## Objective
Expose a minimal API surface to create/list/validate/run FlowSpecs and view run traces.

## Scope
### In-scope
- Implement endpoints (names may vary; keep consistent with your routing conventions):
  - POST /api/flows
  - GET /api/flows
  - GET /api/flows/{flow_id}
  - PATCH /api/flows/{flow_id}
  - POST /api/flows/{flow_id}/validate
  - POST /api/flows/{flow_id}/run
  - GET /api/flows/{flow_id}/runs
  - GET /api/flows/runs/{run_id}
- Wire compile_flow + run_flow into handlers (manual runs first)

### Out-of-scope
- UI
- Cron integration beyond already-existing cron endpoints unless trivial wiring

## Allowed files (STRICT)
- guardian/routes/flows.py
- guardian/flows/spec.py (only if API DTOs needed)
- guardian/flows/compiler.py
- guardian/flows/runner.py
- guardian/flows/primitives.py
- docs/tasks/TASK_2026_02_12_007_flow_builder_api_endpoints.md
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

# implement routes in guardian/routes/flows.py

# run minimal import check

python -c "from guardian.routes.flows import router; print('ok')"

git status --porcelain -uall
```

## Expected results (explicit)
- Import check prints `ok`.
- OpenAPI lists the new endpoints after app start (verify via `/openapi.json`).

## Rollback / cleanup
```bash
cd <REPO_ROOT>
git checkout -- guardian/routes/flows.py guardian/flows/spec.py guardian/flows/compiler.py guardian/flows/runner.py guardian/flows/primitives.py
```

## Commit plan (MANUAL; index.lock workaround)

### Commit A (implementation) — two-phase only
`TASK-2026-02-12-007_flow_builder_api_endpoints: flow builder API endpoints`

```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add guardian/routes/flows.py guardian/flows/spec.py guardian/flows/compiler.py guardian/flows/runner.py guardian/flows/primitives.py
git commit --no-verify -m "TASK-2026-02-12-007_flow_builder_api_endpoints: flow builder API endpoints"
git log -1 --oneline
git status --porcelain -uall
```

Commit A hash: <FILL_AFTER_COMMIT_A>

### Commit B (docs finalize + mapping) — two-phase only
`TASK-2026-02-12-007_flow_builder_api_endpoints: docs finalize + mapping`

```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add docs/tasks/TASK_2026_02_12_007_flow_builder_api_endpoints.md docs/Campaign/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md
git commit --no-verify -m "TASK-2026-02-12-007_flow_builder_api_endpoints: docs finalize + mapping"
git log -1 --oneline
git status --porcelain -uall
```

## Campaign mapping (SOURCE OF TRUTH)
- TASK-2026-02-12-007_flow_builder_api_endpoints -> [<commitA>, <commitB>]

## Completion Summary (fill after completion)
- Status: DONE | BLOCKED | DEFERRED
- What changed:
  - <bullets>
- Commands run:
  ```bash
  <commands>
  ```
- Tests:
  - python -c "from guardian.routes.flows import router; print('ok')" (pass/fail)
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
