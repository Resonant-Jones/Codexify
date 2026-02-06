# TASK-2026-02-06-009_share_create_requires_api_key_returns_401

## Metadata
- Campaign-ID: CAMPAIGN-2026-02-06-LOOP_INTEGRITY_AUTH_AND_DEFAULTS
- Task-ID: TASK-2026-02-06-009_share_create_requires_api_key_returns_401
- Title: Share create requires API key and returns 401 when missing
- Task artifact: docs/tasks/TASK_2026_02_06_009_share_create_requires_api_key_returns_401.md
- Risk: HIGH
- Commit mode: two-phase

## Objective
Ensure the **share creation** endpoint is protected by API-key auth and responds with **401 Unauthorized** when missing credentials, matching test expectations and security intent.

## Scope
### In-scope
- Enforce API key auth on **POST /api/share** (share-link creation).
- Ensure unauthenticated share creation returns **401** (not 200).
- Keep share retrieval semantics unchanged unless required by existing tests.

### Out-of-scope
- Changing share-link retrieval/token validation behavior beyond what’s required for tests.
- Broader auth refactors across unrelated routers.

## Allowed files (STRICT)
> Do not modify files outside this list.

- guardian/routes/share.py
- guardian/guardian_api.py
- tests/routes/test_share_links.py
- docs/tasks/TASK_2026_02_06_009_share_create_requires_api_key_returns_401.md
- docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

## Dependencies / Prereqs (NO GUESSING)
Run these to confirm the relevant files exist and locate current auth wiring:

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# Required: clean tree
git status --porcelain -uall

# Confirm files exist
ls -la guardian/routes/share.py guardian/guardian_api.py tests/routes/test_share_links.py

# Locate router registration and any auth dependencies
rg -n "include_router\(share\.router\)|share\.router" guardian/guardian_api.py
rg -n "APIRouter\(" guardian/routes/share.py
rg -n "require_api_key|Depends\(" guardian/routes/share.py guardian/guardian_api.py

# Confirm test expectation that unauthenticated POST returns 401
rg -n "test_create_share_requires_api_key|/api/share" tests/routes/test_share_links.py
```

## Command checklist (copy/paste)
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# 0) REQUIRED: must be clean before starting
git status --porcelain -uall

# 1) Run the targeted failing test first (establish baseline)
pytest -q tests/routes/test_share_links.py::test_create_share_requires_api_key

# 2) Implement fix within allowed files only
#    Goal: POST /api/share returns 401 when X-API-Key is missing.
#    Preferred approach:
#      - Add require_api_key dependency either at router level (APIRouter dependencies)
#        OR at include_router registration in guardian_api.py.
#    Constraint:
#      - Ensure this does NOT unintentionally break share retrieval routes unless tests require it.

# 3) Re-run the targeted test
pytest -q tests/routes/test_share_links.py::test_create_share_requires_api_key

# 4) Optional: run the share-links test module (if fast enough)
pytest -q tests/routes/test_share_links.py

# 5) Confirm only allowed files changed
git status --porcelain -uall
```

## Expected results
Success looks like:
- `pytest -q tests/routes/test_share_links.py::test_create_share_requires_api_key` exits **0**.
- The unauthenticated request in that test returns **401**.
- `git status --porcelain -uall` shows modifications only within **Allowed files (STRICT)**.

## Rollback / cleanup
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# Revert allowed-file edits if needed
git restore -- guardian/routes/share.py guardian/guardian_api.py tests/routes/test_share_links.py

# If task doc edits need reverting too
git restore -- docs/tasks/TASK_2026_02_06_009_share_create_requires_api_key_returns_401.md

git status --porcelain -uall
```

## Commit plan (MANUAL; index.lock workaround)

### Commit A (implementation)
- Commit message (EXACT):
  - `TASK-2026-02-06-009_share_create_requires_api_key_returns_401: enforce api-key on share create`

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# Stage implementation + tests only (no campaign/task docs in Commit A)
git add guardian/routes/share.py guardian/guardian_api.py tests/routes/test_share_links.py

git commit --no-verify -m "TASK-2026-02-06-009_share_create_requires_api_key_returns_401: enforce api-key on share create"

git log -1 --oneline

git status --porcelain -uall
```

### Commit B (docs finalize + mapping)
- Commit message (EXACT):
  - `TASK-2026-02-06-009_share_create_requires_api_key_returns_401: docs finalize + mapping`

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# Stage docs only
git add docs/tasks/TASK_2026_02_06_009_share_create_requires_api_key_returns_401.md \
  docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

git commit --no-verify -m "TASK-2026-02-06-009_share_create_requires_api_key_returns_401: docs finalize + mapping"

git log -1 --oneline

git status --porcelain -uall
```

## Campaign mapping
Update the campaign mapping line to:

- `TASK-2026-02-06-009_share_create_requires_api_key_returns_401 -> [<commitA>, <commitB>]`

## Summary (fill after completion)
- What changed:
- Commands run + key outputs:
- Commit A:
- Commit B:
- Final mapping:
  - `TASK-2026-02-06-009_share_create_requires_api_key_returns_401 -> [<commitA>, <commitB>]`
