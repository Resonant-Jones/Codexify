# Doc-Gen Loop Validation (Task 009)

Deterministic procedure to prove `/api/documents/generate` persists drafts that immediately surface through `/api/threads/{thread_id}/documents`. Covers the INFO audit finding `FINDING-2026-02-16-009`.

## Preconditions
- Working directory: repository root.
- `GUARDIAN_API_KEY` exported in the shell that runs the checks.
- Tooling present locally:
  - `docker --version` must succeed.
  - `docker compose version` must succeed.
  - `curl --version` and `jq --version` recommended (required for the script below).

## Deterministic Script (preferred)
Runbook automation lives at `scripts/validate_doc_gen.sh` and encodes the audit commands, pass/fail gates, and `thread_id=1` fallback logic.

```bash
# Start the backend stack, generate a markdown doc, assert persistence
GUARDIAN_API_KEY=... ./scripts/validate_doc_gen.sh
```

Script guarantees:
- Boots `db`, `redis`, `backend` via `docker compose up -d db redis backend` and waits for `/health`.
- Issues the audit curl for generation (defaults to `thread_id=1`, prompt `"Write a short audit note."`, format `"markdown"`).
- Lists `/api/threads/{thread_id}/documents` and fails if the new `document_id` is absent.
- Detects 404 for `thread_id=1`, creates a replacement via `POST /api/threads`, and re-runs the validation with the returned identifier so the run never silently passes against a missing thread.

Exit codes:
- `0` → pass (doc id + content existed and thread listing contained the id with a relation value).
- Non-zero → fail with the offending JSON payload echoed to stdout/stderr for triage.

## Manual Validation Checklist
Follow these steps if scripting is not possible. Treat each command as **must run verbatim**; adjust only the API key.

1. **Start required services**
   ```bash
   docker compose up -d db redis backend
   ```
   - Pass: command exits 0 and containers are listed under `docker compose ps`.
   - Fail: any non-zero exit or missing containers — inspect compose logs before proceeding.

2. **Generate a document via authenticated curl**
   ```bash
   curl -sS \
     -H "X-API-Key: $GUARDIAN_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"thread_id":1,"prompt":"Write a short audit note.","format":"markdown"}' \
     http://localhost:8888/api/documents/generate
   ```
   - Pass: JSON body includes `"ok": true`, a non-empty `document_id` (UUID), and `content` string text.
   - Fail: missing `document_id`/`content`, `ok != true`, or HTTP status ≥ 400 (commonly 404 when thread `1` does not exist or 401 when the API key is absent).

3. **List thread documents to confirm persistence**
   ```bash
   curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/api/threads/1/documents
   ```
   - Pass: JSON body includes `"ok": true` and `documents` array where one element has `id` matching the `document_id` returned in step 2 along with `relation` (e.g., `"attached"`) and `created_at` ISO timestamp.
   - Fail: HTTP 404 (thread missing) or the generated `document_id` is absent from `documents` — indicates persistence/linking failure.

Record each pass/fail outcome in your run log; rerun the full sequence after remediation to keep determinism.

## Handling Missing `thread_id=1`
If step 2 or 3 returns `404` with `detail: "Thread 1 not found"`, create a baseline thread and retry:

```bash
curl -sS \
  -H "X-API-Key: $GUARDIAN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"Doc Gen Validation Thread"}' \
  http://localhost:8888/api/threads
```

- Pass: response contains `{"thread_id": <int>}`. Export `THREAD_ID=<int>` and rerun the script or manual steps replacing `1` with the new id.
- Fail: no `thread_id` key or HTTP error — fix API auth or ensure `db` is migrated before repeating the validation.

Document all deviations (e.g., reassigned `THREAD_ID`) alongside the validation logs so future doc-gen runs can reuse the confirmed thread.
