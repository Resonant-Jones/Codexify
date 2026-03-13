# TASK-2026-02-11-202_security_uploader_auth_headers_non_proxy: Add explicit auth headers to uploader media requests

## Metadata

- Preflight requirement: `git status --porcelain -uall` must be empty.
- Source finding: `FINDING-2026-02-11-003`
- Risk: HIGH

## Objective

Goal: remove dev-proxy auth dependency by ensuring uploader requests to media endpoints carry explicit auth headers in direct-backend deployments.

## Allowed files (STRICT)

- frontend/src/hooks/useUploader.ts
- frontend/src/lib/api.ts
- frontend/src/tests/uploader_document_auth.spec.ts

## Dependencies / prereqs

```bash
printenv GUARDIAN_API_KEY >/dev/null
```
```bash
printenv VITE_GUARDIAN_API_KEY >/dev/null
```
```bash
redis-cli ping
```
```bash
pg_isready
```
```bash
pgrep -fl worker-document-embed
```
```bash
command -v pnpm
```
```bash
command -v pytest
```

## Command checklist

1. Preflight: git status --porcelain -uall must be empty
2. git status --porcelain -uall
3. If step 2 is non-empty, STOP and run:
   - `git stash push --include-untracked --message 'preflight-CAMPAIGN_2026_02_11_SECURITY_BOUNDARY-001-cleanup'`
4. rg -n '/api/media/upload/document|/api/media/upload/image|X-API-Key' frontend/src/hooks/useUploader.ts frontend/src/lib/api.ts
5. git status --porcelain -uall | awk '{print $2}' | grep -Ev '^(frontend/src/hooks/useUploader.ts|frontend/src/lib/api.ts|frontend/src/tests/uploader_document_auth.spec.ts)$'
6. If step 5 prints any path, STOP and run:
   - `git stash push --include-untracked --message 'cleanup-CAMPAIGN_2026_02_11_SECURITY_BOUNDARY-001-out-of-scope'`
7. pnpm -C frontend vitest run src/tests/uploader_document_auth.spec.ts
8. pytest -q tests/routes/test_media_routes.py guardian/tests/test_document_embed_worker.py

## Expected outputs

- Step 2 returns no lines.
- Step 5 returns no lines (grep exit 1).
- Vitest command exits 0.
- Pytest command exits 0.
- Upload requests to media endpoints include explicit auth header behavior in direct-backend mode.

## Rollback / cleanup

```bash
git stash push --include-untracked --message 'rollback-CAMPAIGN_2026_02_11_SECURITY_BOUNDARY-001'
git restore --staged --worktree frontend/src/hooks/useUploader.ts frontend/src/lib/api.ts frontend/src/tests/uploader_document_auth.spec.ts
git clean -fd frontend/src/tests/uploader_document_auth.spec.ts
```

## Runner constraints

- Must not proceed with dirty tree.
- Must stop if out-of-scope files appear.
- Any architecture/policy decision must be handled in a dedicated Decision task, not as a follow-up question.

## Completion Summary (Runner)

- Status: success
- Summary: Implemented non-proxy explicit auth header behavior for uploader media requests and added frontend regression coverage.
- Changes made:
  - `frontend/src/hooks/useUploader.ts`: added `buildUploaderHeaders(...)` to attach `X-API-Key` only when `VITE_USE_PROXY` is disabled and a key is present.
  - Applied that helper to uploader media calls:
    - `/api/media/upload/image`
    - `/api/media/upload/document` (multipart)
    - `/api/media/upload/document` JSON fallback path
  - Added `frontend/src/tests/uploader_document_auth.spec.ts` with regression tests covering:
    - non-proxy mode adds `X-API-Key`
    - proxy mode does not add explicit `X-API-Key`
- Scope/guardrails:
  - Preflight tree was clean before edits.
  - Final changes are only in allowed files:
    - `frontend/src/hooks/useUploader.ts`
    - `frontend/src/tests/uploader_document_auth.spec.ts`
  - No out-of-scope file changes detected.
- Implementation commit hash: 61abeae02dca26525172eb51d31b6c803699141d
- Receipt update commit hash: (see campaign mapping)
- Tests ran:
  - git status --porcelain -uall (pre/post checks, clean preflight and in-scope post-change)
  - git status --porcelain -uall | awk '{print $2}' | grep -Ev '^(frontend/src/hooks/useUploader.ts|frontend/src/lib/api.ts|frontend/src/tests/uploader_document_auth.spec.ts)$' (no out-of-scope paths)
  - pnpm vitest run src/tests/uploader_document_auth.spec.ts --environment jsdom (PASS)
  - pytest -q tests/routes/test_media_routes.py guardian/tests/test_document_embed_worker.py (PASS)
- Notes: `pnpm -C frontend ...` is not supported by the installed pnpm CLI in this environment (`ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL`), so the frontend test was run from the `frontend` directory with an explicit jsdom environment to execute the same target file.

<details>
<summary>Structured task_result.json</summary>

```json
{
  "status": "success",
  "summary": "Implemented non-proxy explicit auth header behavior for uploader media requests and added frontend regression coverage.\n\nChanges made:\n- `frontend/src/hooks/useUploader.ts`: added `buildUploaderHeaders(...)` to attach `X-API-Key` only when `VITE_USE_PROXY` is disabled and a key is present.\n- Applied that helper to uploader media calls:\n  - `/api/media/upload/image`\n  - `/api/media/upload/document` (multipart)\n  - `/api/media/upload/document` JSON fallback path\n- Added `frontend/src/tests/uploader_document_auth.spec.ts` with regression tests covering:\n  - non-proxy mode adds `X-API-Key`\n  - proxy mode does not add explicit `X-API-Key`\n\nScope/guardrails:\n- Preflight tree was clean before edits.\n- Final changes are only in allowed files:\n  - `frontend/src/hooks/useUploader.ts`\n  - `frontend/src/tests/uploader_document_auth.spec.ts`\n- No out-of-scope file changes detected.",
  "tests_ran": [
    "git status --porcelain -uall (pre/post checks, clean preflight and in-scope post-change)",
    "git status --porcelain -uall | awk '{print $2}' | grep -Ev '^(frontend/src/hooks/useUploader.ts|frontend/src/lib/api.ts|frontend/src/tests/uploader_document_auth.spec.ts)$' (no out-of-scope paths)",
    "pnpm vitest run src/tests/uploader_document_auth.spec.ts --environment jsdom (PASS)",
    "pytest -q tests/routes/test_media_routes.py guardian/tests/test_document_embed_worker.py (PASS)"
  ],
  "commit_hash": "61abeae02dca26525172eb51d31b6c803699141d",
  "implementation_commit_hash": "61abeae02dca26525172eb51d31b6c803699141d",
  "receipt_update_commit_hash": "",
  "notes": "`pnpm -C frontend ...` is not supported by the installed pnpm CLI in this environment (`ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL`), so the frontend test was run from the `frontend` directory with an explicit jsdom environment to execute the same target file."
}
```

</details>
