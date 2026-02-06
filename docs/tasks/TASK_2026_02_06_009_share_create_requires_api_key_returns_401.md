# TASK_2026_02_06_009_share_create_requires_api_key_returns_401

## Objective

Fix share creation auth test mismatch.

## Background

Test expects `/api/share` to return 401 without API key, but current behavior returns 200.

## Requirements

- API key enforcement must be consistent in runtime and tests
- Test behavior must match production semantics

## Acceptance Criteria

- Missing API key → 401
- Test `test_create_share_requires_api_key` passes reliably

## Files Likely Touched

- Share router
- Dependency injection / app setup
- Tests

## Commit Plan

- Commit A: backend/test fix
- Commit B: docs/task mapping update

# TASK_2026_02_06_009_share_create_requires_api_key_returns_401

## Metadata
- Task-ID: TASK-2026-02-06-009_share_create_requires_api_key_returns_401
- Campaign-ID: CAMPAIGN-2026-02-06-LOOP_INTEGRITY_AUTH_AND_DEFAULTS
- Task artifact: docs/tasks/TASK_2026_02_06_009_share_create_requires_api_key_returns_401.md
- Owner: resonant_jones
- Risk: HIGH
- Commit mode: two-phase

## Objective
Ensure share-link creation (`POST /api/share`) requires API key auth and returns **401** when the API key is missing, and make the corresponding test pass reliably.

## Scope
### In-scope
- Align runtime behavior + tests so `POST /api/share` without `X-API-Key` returns 401.
- Ensure router registration includes `require_api_key` (or equivalent) for **create** routes.
- Update/confirm the test `test_create_share_requires_api_key` asserts 401 and passes.

### Out-of-scope
- Changing share-link retrieval semantics (token-based GET access) beyond what is required to keep existing intended behavior.
- Refactors unrelated to share auth behavior.
- Any changes outside the Allowed files list.

## Allowed files (STRICT)
> Do not edit files outside this list.

- guardian/routes/share.py
- guardian/guardian_api.py
- guardian/core/dependencies.py
- tests/routes/test_share_links.py
- docs/tasks/TASK_2026_02_06_009_share_create_requires_api_key_returns_401.md
- docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

## Dependencies / Preconditions (NO GUESSING)
Run these commands and confirm expected signals before editing:

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# 0) REQUIRED: clean tree before starting
git status --porcelain -uall

# 1) confirm share router + create endpoint + auth dependency usage
rg -n "include_router\(share\.router|share\.router" guardian/guardian_api.py
rg -n "APIRouter\(" guardian/routes/share.py
rg -n "require_api_key" guardian/routes/share.py guardian/guardian_api.py guardian/core/dependencies.py

# 2) confirm the test exists and locate the failing assertion
rg -n "test_create_share_requires_api_key" tests/routes/test_share_links.py
```

Expected precondition outcomes:
- `git status --porcelain -uall` prints nothing.
- The share router is included from `guardian/guardian_api.py`.
- You can identify whether `require_api_key` is applied to the share router or to the create endpoint.
- The test `test_create_share_requires_api_key` is present in `tests/routes/test_share_links.py`.

## Execution plan
### Step-by-step commands (copy/paste)

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# 1) confirm clean scope
git status --porcelain -uall

# 2) run the narrowest test first
python -m pytest -q tests/routes/test_share_links.py -k "test_create_share_requires_api_key" \
  --maxfail=1

# 3) after edits, re-run the narrow test
python -m pytest -q tests/routes/test_share_links.py -k "test_create_share_requires_api_key" \
  --maxfail=1

# 4) optional: run all share link tests
python -m pytest -q tests/routes/test_share_links.py

# 5) confirm only allowed files changed
git status --porcelain -uall
```

## Expected results
Success looks like:
- `python -m pytest -q tests/routes/test_share_links.py -k "test_create_share_requires_api_key"` exits 0.
- The failing assertion is resolved: the test observes **401** when no API key is provided.
- `git status --porcelain -uall` shows changes only within the Allowed files list.

## Rollback / cleanup

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# discard local edits for this task (use with care)
git restore -- \
  guardian/routes/share.py \
  guardian/guardian_api.py \
  guardian/core/dependencies.py \
  tests/routes/test_share_links.py \
  docs/tasks/TASK_2026_02_06_009_share_create_requires_api_key_returns_401.md \
  docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

git status --porcelain -uall
```

## Commit plan (MANUAL; index.lock workaround)

### Commit A (implementation)
- Commit message (EXACT):
  - `TASK-2026-02-06-009_share_create_requires_api_key_returns_401: enforce API key on share create`

Manual commands:

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

git add \
  guardian/routes/share.py \
  guardian/guardian_api.py \
  guardian/core/dependencies.py \
  tests/routes/test_share_links.py

git commit --no-verify -m "TASK-2026-02-06-009_share_create_requires_api_key_returns_401: enforce API key on share create"

git log -1 --oneline

git status --porcelain -uall
```

### Commit B (docs finalize + mapping)
- Commit message (EXACT):
  - `TASK-2026-02-06-009_share_create_requires_api_key_returns_401: docs finalize + mapping`

Manual commands:

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

git add \
  docs/tasks/TASK_2026_02_06_009_share_create_requires_api_key_returns_401.md \
  docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

git commit --no-verify -m "TASK-2026-02-06-009_share_create_requires_api_key_returns_401: docs finalize + mapping"

git log -1 --oneline

git status --porcelain -uall
```

## Mapping
Update the campaign file with the real hashes:

- `TASK-2026-02-06-009_share_create_requires_api_key_returns_401 -> [<commitA>, <commitB>]`

## Notes
- If share-link retrieval is intentionally public/token-based, ensure only **creation** requires API key; do not accidentally lock down GET-by-token flows unless the test suite indicates otherwise.

## Summary (fill after completion)
- What changed:
- Commands run + key outputs:
- Final mapping:
  - TASK-2026-02-06-009_share_create_requires_api_key_returns_401 -> [<commitA>, <commitB>]