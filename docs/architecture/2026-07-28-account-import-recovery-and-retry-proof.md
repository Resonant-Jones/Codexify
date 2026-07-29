# Account Import Recovery and Retry Proof

## Metadata

| Field | Value |
|---|---|
| Date | 2026-07-28 |
| Branch | `main` |
| Starting commit | `ba8a7c655` — Establish Guardian frame-first mobile shell |
| Tested commit | `6f77c9e4d` — Add failed account import retry seam |
| Mount-parity repair commit | `a9203b801` — Repair tester account import staging continuity |
| Retry-seam commit | `6f77c9e4d` — Add failed account import retry seam |

## Target Job

| Field | Value |
|---|---|
| Job ID | `dd352267-583b-4ce9-84e8-0e145c041db2` |
| Account owner | `Resonant Jones` |
| Legacy staging root | `<legacy-worktree-root>/data/imports` |
| Canonical staging root | `<canonical-repo-root>/data/imports` |
| Staging locator | `account-imports/5f40c23a2784cdcb/dd352267-583b-4ce9-84e8-0e145c041db2` |

## Staging Recovery

### Source and destination posture

| Metric | Source | Destination |
|---|---|---|
| File count | 6875 | 6875 |
| Byte count | 5038342512 | 5038342512 |
| Aggregate SHA-256 | `63ffd66df80d40ed19d0d1c8ac354e44f372412d13b981ab962e01b334fdf905` | `63ffd66df80d40ed19d0d1c8ac354e44f372412d13b981ab962e01b334fdf905` |

### Tree-digest comparison

**Match.** Source and destination manifest-line digests are byte-identical (`cmp` exit 0).

### Source immutability proof

Source was remeasured after copy: manifest SHA-256 remains `63ffd66df...`. No source files were modified, added, or deleted during the copy operation.

### `.DS_Store` visibility

- Source: `unzipped-folders/.DS_Store` — present
- Destination: `unzipped-folders/.DS_Store` — present
- Backend container: visible at `/app/data/imports/<staging-locator>/unzipped-folders/.DS_Store`
- Worker container (non-consuming): visible at the same path

## Retry Admission

### Pre-retry job state

- Status: `failed`
- Owner: `Resonant Jones`
- Imported threads: 0
- Imported messages: 0
- Imported media: 0
- Failure count: 1
- Original error: `File not found: .../unzipped-folders/.DS_Store`

### Authentication

- Token type: HMAC-signed session token (GUARDIAN_SESSION_SECRET)
- Subject: `Resonant Jones`
- Token stored in Redis (`session:` prefix)
- Identity verified via `GET /api/imports/openai-account/{job_id}` returning the target job

### Retry endpoint invocation

- `POST /api/imports/openai-account/dd352267-583b-4ce9-84e8-0e145c041db2/retry`
- Request body: none
- Response status: `202` (first call), `409` (second call — idempotency proven)
- Response status: `queued`
- Response owner: `Resonant Jones`

### Accepted retry receipt

- Checkpoint `retry_attempts`: `[{"attempt": 1, "accepted": true, ...}]`
- Original `error_details` preserved
- `failure_count` remained 1

## Worker Execution

### Startup

- Command: `dc up -d --build --no-deps worker-account-import`
- Only `worker-account-import` was recreated; all other services remained at 28+ hours uptime
- Worker log: `worker started queue=codexify:queue:account-import recovered=1`

### Job lifecycle

| Metric | Pre-retry | Post-import |
|---|---|---|
| Status | `failed` | `completed_with_warnings` |
| Threads imported | 0 | 5043 |
| Messages imported | 0 | 112436 |
| Media imported | 0 | 6603 |
| Duplicates | 0 | 2078 |
| Skipped | 0 | 100 |
| Warnings | 0 | 433 |
| Failure count | 1 | 1 |
| Owner | `Resonant Jones` | `Resonant Jones` |

### Processing timeline

- Worker started: 17:26:30 UTC
- First checkpoint: 17:27:43 UTC
- Conversation phase: ~17:27 through ~17:49 UTC (5043 threads, 112436 messages)
- Media phase: ~17:49 through ~18:03 UTC (6603 media items)
- Completed: 18:03:32 UTC
- Total elapsed: ~37 minutes

## Ownership Verification

| Entity | `Resonant Jones` count (post-retry) | `local` count (post-retry) |
|---|---|---|
| Projects | — | 0 |
| Threads | 5043 | 0 |
| Messages | — | 0 |

Mismatch query returned zero rows. All imported records remain inside the `Resonant Jones` account boundary.

## Failure Receipt Preservation

Original error details remain intact:

```json
[{
  "code": "account_import_worker_failed",
  "message": "File not found: account-imports/5f40c23a2784cdcb/dd352267-583b-4ce9-84e8-0e145c041db2/unzipped-folders/.DS_Store"
}]
```

`failure_count` was not reset. Retry-attempt metadata was appended to `checkpoint.retry_attempts` without erasing historical `error_details`.

## Test Results

```bash
.venv/bin/python -m pytest -v \
  tests/routes/test_migration_routes.py \
  tests/rag/test_openai_export_account_import.py \
  tests/workers/test_account_import_worker.py \
  tests/contracts/test_protocol_tokens.py \
  tests/ops/test_codexify_tester_services.py
```

Result: **91 passed**, 0 failed.

## Final Outcome

**`GO`**

### What is now true

- The 4.8 GB staged payload was recovered from the legacy worktree and copied to the canonical staging root with byte-exact fidelity.
- The supported retry endpoint (`POST /api/imports/openai-account/{job_id}/retry`) accepted the job, verified ownership, validated zero-write counters, confirmed canonical staging visibility, transitioned `failed → queued`, and published exactly one queue task.
- The account-import worker consumed the job through the canonical queue, resolved the canonical staging tree, and completed the import.
- Final imported counts: 5043 threads, 112436 messages, 6603 media items.
- All imported records belong to `Resonant Jones`. Zero records were written under `local`.
- Original failure receipt (`error_details`) is preserved. `failure_count` was not reset.
- Duplicate retry request after acceptance returned `409` (idempotency proven).
- Source staged data was not modified, deleted, or re-uploaded.

### What is not yet proven

- Long-term stability of the imported data (searchability, retrieval, UI rendering).
- Whether all 433 warnings are benign or some indicate recoverable issues.

### What the next task may safely assume

- The account-import retry seam works end-to-end for zero-write failed jobs with canonical staging.
- The repaired tester orchestration (`--project-directory`) ensures consistent staging resolution between backend and worker.
- Staged payloads can be recovered from legacy worktrees to the canonical root via bit-exact copy without re-upload.

## Confirmations

- ✅ No manual SQL transition occurred.
- ✅ No second retry request occurred after a successful `202`.
- ✅ No re-upload occurred. The legacy staged data was copied, not re-transferred from a browser.
- ✅ No source data was deleted. The legacy worktree staging tree remains intact.
- ✅ No historical `local` import was migrated.
- ✅ No unrelated service was restarted. Only `backend` (retry route rebuild) and `worker-account-import` (import execution) were recreated.
- ✅ No private upload data was committed to the repository.
