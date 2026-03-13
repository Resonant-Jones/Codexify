# Task 002 - Decision Task: local-only API key boundary and remote JWT/session requirement
Preflight: git status --porcelain -uall must be empty

Source finding: FINDING-2026-02-11-007
Risk: MED

Goal: encode the security boundary decision and enforce/document that browser-distributed static API keys are local-only; remote deployments require per-user session/JWT.

Allowed files:
- guardian/core/dependencies.py
- .env.template
- .env.example
- docs/reference/security/auth-boundary-decision.md
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
6. git status --porcelain -uall | awk '{print $2}' | grep -Ev '^(guardian/core/dependencies.py|.env.template|.env.example|docs/reference/security/auth-boundary-decision.md|tests/core/test_auth_boundary.py)$'
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
- git restore --staged --worktree guardian/core/dependencies.py .env.template .env.example docs/reference/security/auth-boundary-decision.md tests/core/test_auth_boundary.py
- git clean -fd docs/reference/security/auth-boundary-decision.md tests/core/test_auth_boundary.py

Runner constraints:
- Must not proceed with dirty tree.
- Must stop if out-of-scope files appear.
- This task is the dedicated decision container; no unresolved policy questions may spill into other tasks.

## Completion Summary (Runner)

- Status: success

- Summary: Implemented and enforced the auth boundary decision.

Changes made:
- `guardian/core/dependencies.py:129` adds `GUARDIAN_AUTH_MODE` boundary logic:
  - `local` mode keeps existing static API key behavior.
  - `remote` mode rejects `X-API-Key` and requires session/JWT via `Authorization: Bearer` or `gc_session` cookie.
  - Remote mode now fails closed with `500` if no signing secret is configured.
- `guardian/core/dependencies.py:201` adds a robust session-token fallback verifier so valid session tokens are not randomly rejected when signature bytes contain `.`.
- `.env.template:11` and `.env.example:11` now document boundary config:
  - `GUARDIAN_AUTH_MODE=local|remote`
  - local-only `VITE_GUARDIAN_API_KEY` guidance
  - `GUARDIAN_SESSION_SECRET` / `GUARDIAN_JWT_SECRET` for remote mode
- Added decision record: `docs/reference/security/auth-boundary-decision.md:1`.
- Added proof tests: `tests/core/test_auth_boundary.py:1` covering:
  - local mode accepts static API key
  - remote mode rejects static key in `X-API-Key`
  - remote mode rejects static key in bearer header
  - remote mode accepts session token bearer
  - remote mode accepts session cookie
  - remote mode accepts JWT bearer

- Implementation commit hash: 51534c03652802917bcfaa53e420a2ab8a7d56c9

- Receipt update commit hash: (see campaign mapping)

- Tests ran: pytest -q tests/core/test_auth_boundary.py, python -m py_compile guardian/core/dependencies.py tests/core/test_auth_boundary.py

- Notes: Working tree now includes modifications to `.env.example`, `.env.template`, `guardian/core/dependencies.py`, and new files `docs/reference/security/auth-boundary-decision.md`, `tests/core/test_auth_boundary.py`.

<details>
<summary>Structured task_result.json</summary>

```json
{
  "status": "success",
  "summary": "Implemented and enforced the auth boundary decision.\n\nChanges made:\n- `guardian/core/dependencies.py:129` adds `GUARDIAN_AUTH_MODE` boundary logic:\n  - `local` mode keeps existing static API key behavior.\n  - `remote` mode rejects `X-API-Key` and requires session/JWT via `Authorization: Bearer` or `gc_session` cookie.\n  - Remote mode now fails closed with `500` if no signing secret is configured.\n- `guardian/core/dependencies.py:201` adds a robust session-token fallback verifier so valid session tokens are not randomly rejected when signature bytes contain `.`.\n- `.env.template:11` and `.env.example:11` now document boundary config:\n  - `GUARDIAN_AUTH_MODE=local|remote`\n  - local-only `VITE_GUARDIAN_API_KEY` guidance\n  - `GUARDIAN_SESSION_SECRET` / `GUARDIAN_JWT_SECRET` for remote mode\n- Added decision record: `docs/reference/security/auth-boundary-decision.md:1`.\n- Added proof tests: `tests/core/test_auth_boundary.py:1` covering:\n  - local mode accepts static API key\n  - remote mode rejects static key in `X-API-Key`\n  - remote mode rejects static key in bearer header\n  - remote mode accepts session token bearer\n  - remote mode accepts session cookie\n  - remote mode accepts JWT bearer",
  "tests_ran": [
    "pytest -q tests/core/test_auth_boundary.py",
    "python -m py_compile guardian/core/dependencies.py tests/core/test_auth_boundary.py"
  ],
  "commit_hash": "51534c03652802917bcfaa53e420a2ab8a7d56c9",
  "implementation_commit_hash": "51534c03652802917bcfaa53e420a2ab8a7d56c9",
  "receipt_update_commit_hash": "",
  "notes": "Working tree now includes modifications to `.env.example`, `.env.template`, `guardian/core/dependencies.py`, and new files `docs/reference/security/auth-boundary-decision.md`, `tests/core/test_auth_boundary.py`."
}
```

</details>
