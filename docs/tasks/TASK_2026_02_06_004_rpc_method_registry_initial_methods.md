
## TASK-2026-02-06-004 — RPC Method Registry + Initial Methods

**Goal:** Minimal useful RPC surface.

**Deliverables:**

* `guardian/ws/methods.py`

  * `@rpc_method` decorator + registry
  * initial methods:

    * `ping`
    * `subscribe` / `unsubscribe`
    * `health.status`
    * `thread.list`
    * `chat.send` (calls existing chat pipeline rather than duplicating it)

**Security:**

* per-method authorization flags (admin_only / permissions)
* rate-limited invocations (see next task)

**Tests:**

* unknown method returns structured error
* permission-gated method rejects

---

# TASK-2026-02-06-004_rpc_method_registry_+_initial_methods: RPC method registry + initial methods

## TASK METADATA
- Campaign-ID: CAMPAIGN-2026-02-06-LOOP_INTEGRITY_AUTH_AND_DEFAULTS
- Task-ID: TASK-2026-02-06-004_rpc_method_registry_+_initial_methods
- Title: RPC method registry + initial methods
- Risk: MED
- Task artifact path: docs/tasks/TASK_2026_02_06_004_rpc_method_registry_initial_methods.md

## Objective
Introduce a minimal, explicit RPC method registry for the websocket layer so that incoming RPC calls resolve deterministically to known handlers, unknown methods fail with a structured error, and at least one permission-gated method is enforced.

## Scope
### In-scope
- Add an RPC registry + decorator (`@rpc_method`) that maps method names (strings) to callables.
- Implement a small initial method surface:
  - `ping`
  - `subscribe` / `unsubscribe`
  - `health.status`
  - `thread.list`
  - `chat.send` (MUST call the existing chat pipeline rather than duplicating it)
- Add per-method auth metadata (e.g., `admin_only`, `requires_auth`, or permissions marker) and enforce it.
- Add tests proving:
  - Unknown method returns a structured error (not a stack trace).
  - Permission-gated method is rejected.

### Out-of-scope
- Building a full permissions system or rate-limiter (explicitly deferred to later tasks).
- Refactoring unrelated websocket logic.
- Adding new persistence layers.

## Allowed files (STRICT)
> If you need to touch anything outside this list, STOP and emit a BLOCKER_PROMPT.

- guardian/ws/methods.py
- guardian/ws/*.py
- guardian/tests/**/test_*ws*.py
- guardian/tests/**/test_*rpc*.py
- tests/**/test_*ws*.py
- tests/**/test_*rpc*.py
- docs/tasks/TASK_2026_02_06_004_rpc_method_registry_initial_methods.md
- docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

## Dependencies / Prereqs (NO GUESSING)
Run these first and record any failures in the task summary.

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# locate websocket entrypoints + any existing rpc handling
rg -n "websocket|WebSocket|ws" guardian/ws guardian -S
rg -n "rpc|method_registry|subscribe\(|unsubscribe\(" guardian/ws guardian -S

# locate a reasonable place to add tests (pick existing suite if present)
rg -n "TestClient\(|websocket_connect\(" guardian/tests tests -S || true
```

## Command checklist (exact)
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# 0) REQUIRED: clean tree before starting
git status --porcelain -uall

# 1) Identify call path for websocket RPC dispatch
rg -n "websocket|WebSocket" guardian/ws guardian -S
rg -n "\"method\"|method\s*:\s*|rpc" guardian/ws guardian -S

# 2) Implement registry + decorator + initial methods (allowed files only)
#    - Add @rpc_method(name=..., admin_only=.../requires_auth=...) decorator
#    - Add registry dict and deterministic lookup
#    - Add structured error shape for unknown method

# 3) Add tests for unknown-method + permission-gated method
#    (choose an existing test module path from prereq discovery)

# 4) Run tests (choose the most relevant subset; fall back to broader suite)
python -m pytest -q guardian/tests tests || true

# 5) Confirm only allowed files changed
git status --porcelain -uall
```

## Expected outputs (success signals)
- RPC calls to known methods resolve via the registry (no ad-hoc if/else ladders).
- Unknown method returns a structured error response (include a stable error code and method name).
- At least one method is permission-gated and is rejected when the caller lacks permission.
- Tests added/updated and demonstrate the above behavior.

## Rollback / cleanup
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git restore --staged --worktree -- guardian/ws guardian/tests tests
rm -f .pytest_cache 2>/dev/null || true

git status --porcelain -uall
```

## Commit plan (MANUAL)
### Commit mode
- two-phase

### Commit A (implementation)
- Commit message (EXACT):
  - TASK-2026-02-06-004_rpc_method_registry_+_initial_methods: rpc registry + initial methods

- Manual commands:
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# add ONLY implementation + tests (no docs)
# NOTE: keep paths explicit after you see what changed
# Example (adjust to actual changed files):
# git add guardian/ws/methods.py guardian/ws/<other>.py guardian/tests/<test>.py

git add <EXPLICIT_ALLOWED_PATHS>

git commit --no-verify -m "TASK-2026-02-06-004_rpc_method_registry_+_initial_methods: rpc registry + initial methods"

git log -1 --oneline

git status --porcelain -uall
```

### Commit B (docs finalize + mapping)
- Commit message (EXACT):
  - TASK-2026-02-06-004_rpc_method_registry_+_initial_methods: docs finalize + mapping

- Manual commands:
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git add docs/tasks/TASK_2026_02_06_004_rpc_method_registry_initial_methods.md docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

git commit --no-verify -m "TASK-2026-02-06-004_rpc_method_registry_+_initial_methods: docs finalize + mapping"

git log -1 --oneline

git status --porcelain -uall
```

## Mapping
- TASK-2026-02-06-004_rpc_method_registry_+_initial_methods -> [<commitA>, <commitB>]

## Notes
- If websocket RPC dispatch lives outside `guardian/ws/`, STOP and emit a BLOCKER_PROMPT requesting the exact additional file path(s) to add to Allowed files.

## Summary (fill after completion)
- What changed:
- Commands run + key outputs:
- Tests:
- Commit A:
- Commit B:
- Final mapping:
  - TASK-2026-02-06-004_rpc_method_registry_+_initial_methods -> [<commitA>, <commitB>]