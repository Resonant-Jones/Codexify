# Task 006 - Fix stale document-generation happy-path test
Preflight: git status --porcelain -uall must be empty

Source finding: FINDING-2026-02-11-008
Risk: MED

Goal: update happy-path payload to include required thread_id and preserve explicit 400 coverage for missing-thread branch.

Allowed files:
- guardian/tests/test_document_gen_endpoint.py

Dependencies/prereqs (commands):
- command -v pytest

Command checklist:
1. Preflight: git status --porcelain -uall must be empty
2. git status --porcelain -uall
3. If step 2 is non-empty, STOP and run: git stash push --include-untracked --message 'preflight-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-006-cleanup'
4. pytest -q guardian/tests/test_document_gen_endpoint.py::test_document_generate_happy_path
5. git status --porcelain -uall | awk '{print $2}' | grep -Ev '^(guardian/tests/test_document_gen_endpoint.py)$'
6. If step 5 prints any path, STOP and run: git stash push --include-untracked --message 'cleanup-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-006-out-of-scope'
7. pytest -q guardian/tests/test_document_gen_endpoint.py guardian/tests/test_document_gen_persist_and_link.py
8. rg -n 'thread_id is required' guardian/routes/documents.py guardian/tests/test_document_gen_endpoint.py

Expected outputs:
- Step 2 returns no lines.
- Step 5 returns no lines (grep exit 1).
- Happy-path test exits 0.
- Combined doc-gen test command exits 0.
- Missing-thread branch remains explicitly validated.

Rollback/cleanup commands:
- git stash push --include-untracked --message 'rollback-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-006'
- git restore --staged --worktree guardian/tests/test_document_gen_endpoint.py

Runner constraints:
- Must not proceed with dirty tree.
- Must stop if out-of-scope files appear.
- Any contract decision beyond test correction must be moved to a dedicated Decision task artifact.

## Completion Summary (Runner)

- Status: success

- Summary: Updated stale document-generation endpoint tests to align with current route requirements in `guardian/tests/test_document_gen_endpoint.py`.

Changes made:
- Happy-path test now includes required `thread_id` in request payload.
- Happy-path test now stubs DB/session thread lookup via `_get_db` so persistence path is valid.
- Happy-path test now fixes `uuid4` for deterministic `document_id` assertion.
- Prompt-validation test now includes `thread_id` so it remains focused on prompt validation.
- Added dedicated failure coverage for missing `thread_id` (`400` with `"thread_id is required"`).

- Implementation commit hash: bbfc81fbeea483fbcb5bda9ef0bce92c46d2423c

- Receipt update commit hash: (see campaign mapping)

- Tests ran: pytest -q guardian/tests/test_document_gen_endpoint.py guardian/tests/test_document_gen_pipeline.py guardian/tests/test_document_gen_persist_and_link.py, pytest -q guardian/tests/test_document_gen_endpoint.py

- Notes: Targeted updated test module passes. The broader 3-file run had one unrelated existing failure: `guardian/tests/test_document_gen_pipeline.py::test_document_gen_requires_api_key` returned 500 (LLM path reached) instead of expected 401.

<details>
<summary>Structured task_result.json</summary>

```json
{
  "status": "success",
  "summary": "Updated stale document-generation endpoint tests to align with current route requirements in `guardian/tests/test_document_gen_endpoint.py`.\n\nChanges made:\n- Happy-path test now includes required `thread_id` in request payload.\n- Happy-path test now stubs DB/session thread lookup via `_get_db` so persistence path is valid.\n- Happy-path test now fixes `uuid4` for deterministic `document_id` assertion.\n- Prompt-validation test now includes `thread_id` so it remains focused on prompt validation.\n- Added dedicated failure coverage for missing `thread_id` (`400` with `\"thread_id is required\"`).",
  "tests_ran": [
    "pytest -q guardian/tests/test_document_gen_endpoint.py guardian/tests/test_document_gen_pipeline.py guardian/tests/test_document_gen_persist_and_link.py",
    "pytest -q guardian/tests/test_document_gen_endpoint.py"
  ],
  "commit_hash": "bbfc81fbeea483fbcb5bda9ef0bce92c46d2423c",
  "implementation_commit_hash": "bbfc81fbeea483fbcb5bda9ef0bce92c46d2423c",
  "receipt_update_commit_hash": "",
  "notes": "Targeted updated test module passes. The broader 3-file run had one unrelated existing failure: `guardian/tests/test_document_gen_pipeline.py::test_document_gen_requires_api_key` returned 500 (LLM path reached) instead of expected 401."
}
```

</details>
