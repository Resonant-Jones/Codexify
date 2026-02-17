# Deterministic Doc Upload + Embedding Validation (Task 007)

## Purpose
This artifact closes FINDING-2026-02-16-006 by providing a deterministic way to prove the doc-upload loop works end to end: upload → persist/list → embedding worker marks the document `ready`. The steps below must run on a clean git tree and only touch files allowed by Task 007.

## Preconditions
- `git status --porcelain -uall` returns empty before and after the run.
- `docker --version` and `docker compose version` succeed.
- The `.env` already exports `GUARDIAN_API_KEY`; the backend honors `http://localhost:8888`.
- `/media` URLs exposed by the backend are reachable (depends on Task 003 outcome) so that returned `src_url` values can be fetched if needed.
- `test.txt` exists at repo root (used as the deterministic upload payload).

## Quick sanity check (route reachability)
Run the audited list endpoint even if the backend is still starting; the `|| true` suffix keeps the workflow moving while capturing any error payload:
```sh
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" \
  "http://localhost:8888/api/media/documents?limit=5" || true
```
Record the HTTP code/output in the operator log if the call fails.

## Deterministic command flow
1. **Boot required services**
   ```sh
   docker compose up -d db redis backend worker-document-embed
   ```
   - Pass: all four services report `running` in `docker compose ps`.
   - Fail: any service exits or is missing; stop and fix compose config.

2. **Upload a document via the audited curl command**
   ```sh
   curl -sS \
     -H "X-API-Key: $GUARDIAN_API_KEY" \
     -F "file=@test.txt" \
     -F "project_id=1" \
     -F "thread_id=1" \
     http://localhost:8888/api/media/upload/document
   ```
   Expected JSON response keys (non-empty strings unless noted):
   | field | description | pass criteria |
   | --- | --- | --- |
   | `id` | Numeric uploaded_document identifier | Present and > 0 |
   | `src_url` | Fetchable `/media/...` URL for the uploaded file | Present and starts with `http://localhost:8888/media/` |
   | `embedding_status` | Initial status emitted by backend | Equals `pending` or `processing` |

3. **List recent documents to verify persistence**
   ```sh
   curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" \
     "http://localhost:8888/api/media/documents?limit=5"
   ```
   - Pass: Response is JSON with `documents` array containing the uploaded `id`, plus `embedding_status` and `src_url` fields.
   - Fail: Missing document entry, malformed payload, or HTTP error.

4. **Poll for embedding completion**
   Repeat step 3 up to 12 times (5s interval). Pass condition: the document's `embedding_status` becomes `ready` while `updated_at` increases monotonically. Fail if timeout or `embedding_status` transitions to `failed`.

5. **Confirm the embed worker is running**
   ```sh
   docker compose ps worker-document-embed
   ```
   - Pass: status column contains `running` (case-insensitive).
   - Fail: exited, restarting, or absent container → indicates the worker is not processing jobs.

## Script automation
`scripts/validate_doc_upload_embedding.sh` codifies the steps above. It:
- Enforces the clean-tree preflight.
- Starts the compose services.
- Executes the audited upload and list curl calls.
- Parses responses to assert the pass/fail conditions.
- Polls until `embedding_status` is `ready` while ensuring `worker-document-embed` stays `running`.
- Emits a final PASS/FAIL summary and exits non-zero on failure.

Run it from repo root:
```sh
./scripts/validate_doc_upload_embedding.sh
```

## Pass/Fail matrix
| outcome | description | resulting action |
| --- | --- | --- |
| PASS | All checks succeed, `embedding_status` becomes `ready`, worker stays running. | Script exits 0 and logs PASS. |
| FAIL-DOC-UPLOAD | Upload curl missing required fields or HTTP != 200. | Script exits 1 after printing response body. |
| FAIL-LIST | `/api/media/documents` does not include uploaded id. | Script exits 1 and recommends inspecting backend logs. |
| FAIL-EMBED | Status never becomes `ready` (timeout or `failed`). | Script exits 1 and prints last known status. |
| FAIL-WORKER | `worker-document-embed` not `running`. | Script exits 1 with compose diagnostics. |

Document whenever `/media` access is blocked (e.g., CDN proxy or Task 003 incomplete) because `src_url` fetch validation cannot be performed. Mark the run as inconclusive until upstream fix lands.
