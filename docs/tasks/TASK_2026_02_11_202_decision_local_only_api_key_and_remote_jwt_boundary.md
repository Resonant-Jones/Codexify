# Task 002 - Decision Task: local-only API key boundary and remote JWT/session requirement
Preflight: git status --porcelain -uall must be empty

Source finding: FINDING-2026-02-11-007
Risk: MED

Goal: encode the security boundary decision and enforce/document that browser-distributed static API keys are local-only; remote deployments require per-user session/JWT.

Allowed files:
- guardian/core/dependencies.py
- .env.template
- .env.example
- docs/security/auth-boundary-decision.md
- tests/core/test_auth_boundary.py

Dependencies/prereqs (commands):
- printenv GUARDIAN_API_KEY >/dev/null
- printenv VITE_GUARDIAN_API_KEY >/dev/null
- command -v pytest
- command -v rg

Command checklist:
1. Preflight: git status --porcelain -uall must be empty
2. git status --porcelain -uall
3. If step 2 is non-empty, STOP and run: git stash push --include-untracked --message 'preflight-CAMPAIGN_2026_02_11_SECURITY_BOUNDARY-002-cleanup'
4. rg -n 'VITE_GUARDIAN_API_KEY|X-API-Key' frontend/src/lib/api.ts .env.template .env.example
5. rg -n 'verify_api_key|require_api_key' guardian/core/dependencies.py
6. git status --porcelain -uall | awk '{print $2}' | grep -Ev '^(guardian/core/dependencies.py|.env.template|.env.example|docs/security/auth-boundary-decision.md|tests/core/test_auth_boundary.py)$'
7. If step 6 prints any path, STOP and run: git stash push --include-untracked --message 'cleanup-CAMPAIGN_2026_02_11_SECURITY_BOUNDARY-002-out-of-scope'
8. pytest -q tests/core/test_auth_boundary.py

Expected outputs:
- Step 2 returns no lines.
- Step 6 returns no lines (grep exit 1).
- Decision record exists and explicitly states remote deployments must use session/JWT auth.
- API-key local-only guard behavior is validated by tests.
- Pytest exits 0.

Rollback/cleanup commands:
- git stash push --include-untracked --message 'rollback-CAMPAIGN_2026_02_11_SECURITY_BOUNDARY-002'
- git restore --staged --worktree guardian/core/dependencies.py .env.template .env.example docs/security/auth-boundary-decision.md tests/core/test_auth_boundary.py
- git clean -fd docs/security/auth-boundary-decision.md tests/core/test_auth_boundary.py

Runner constraints:
- Must not proceed with dirty tree.
- Must stop if out-of-scope files appear.
- This task is the dedicated decision container; no unresolved policy questions may spill into other tasks.