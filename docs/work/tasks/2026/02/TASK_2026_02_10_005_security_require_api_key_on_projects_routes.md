# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_SECURITY_HARDENING
- Task ID: 005
- Title: Enforce require_api_key across projects endpoints
- Finding: FINDING-2026-02-10-003
- Risk: HIGH

## Allowed Files
- guardian/routes/projects.py
- tests/routes/test_projects_routes.py

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. rg -n 'APIRouter|require_api_key|@router|@api_router' guardian/routes/projects.py
4. pytest tests/routes/test_projects_routes.py -q
5. for f in $(git diff --name-only); do case $f in guardian/routes/projects.py|tests/routes/test_projects_routes.py) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- GET/PATCH/DELETE project routes require API key dependency.
- Missing/invalid credentials produce 401.
- Route tests assert both unauthorized and authorized paths.

## Rollback / Cleanup
- git restore --staged guardian/routes/projects.py tests/routes/test_projects_routes.py || true
- git restore guardian/routes/projects.py tests/routes/test_projects_routes.py || true

## Dependencies / Prereqs
- command -v git >/dev/null
- command -v rg >/dev/null
- command -v pytest >/dev/null
