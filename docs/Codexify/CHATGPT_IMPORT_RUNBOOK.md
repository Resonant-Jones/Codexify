# ChatGPT Import Runbook (Repeatable)

This runbook is the repeatable way to import ChatGPT history and verify outcomes.

For the newer forensic OpenAI export adapter, including sharded `.dat` export
folders and diagnostic-only scans, see
[`OPENAI_EXPORT_IMPORT_DIAGNOSTICS.md`](OPENAI_EXPORT_IMPORT_DIAGNOSTICS.md).

For archive-scale imports (5,000+ conversations) with resumable checkpointing,
see [`OPENAI_EXPORT_RESUMABLE_IMPORT.md`](OPENAI_EXPORT_RESUMABLE_IMPORT.md).

---

## Quick Start: Import an OpenAI Export

The recommended CLI path for importing an OpenAI export folder:

```bash
PYTHONPATH="$(pwd)" \
DATABASE_URL="postgresql://codexify:codexify@localhost:5433/Codexify" \
GUARDIAN_DATABASE_URL="postgresql+psycopg://codexify:codexify@localhost:5433/Codexify" \
.venv/bin/python scripts/chatgpt_import/cli_migrate.py import:openai-conversations \
  --path /path/to/OpenAI-export \
  --user-id local \
  --resume \
  --batch-conversations 10 \
  --messages-only
```

This imports threads and messages only (Stage A). Embeddings and personal
facts are deferred to later stages.

### Preview without importing

```bash
PYTHONPATH="$(pwd)" \
DATABASE_URL="postgresql://codexify:codexify@localhost:5433/Codexify" \
GUARDIAN_DATABASE_URL="postgresql+psycopg://codexify:codexify@localhost:5433/Codexify" \
.venv/bin/python scripts/chatgpt_import/cli_migrate.py import:openai-conversations \
  --path /path/to/OpenAI-export --parse-only --limit 25
```

### Full CLI reference

```
Usage: codexify import:openai-conversations [OPTIONS]

Options:
  --path PATH                  Path to OpenAI export file/folder [required]
  --parse-only                 Scan + diagnostics only, no DB writes
  --dry-run                    Diagnose without writing to DB
  --limit INTEGER              Limit to first N conversations
  --title-contains TEXT        Filter by title substring
  --user-id TEXT               Codexify user_id (default: local identity)
  --diagnostic-dir PATH        Output directory [default: logs/openai_import]
  --order TEXT                 Import order: file, newest, oldest, updated
  --embedding-mode TEXT        Embedding: defer, enqueue, off [default: off]
  --resume                     Skip conversations already in checkpoint
  --checkpoint-path TEXT       Explicit checkpoint directory
  --batch-conversations INT    Conversations per batch [default: 10]
  --disable-personal-facts     Skip personal facts extraction (Stage A)
  --messages-only              Threads/messages only; no embeddings or facts
```

---

## Legacy CLI import (single file)

For single-file legacy `conversations.json` exports (not the sharded
archive format), the original import script is still available:

```bash
python scripts/chatgpt_import/import_chatgpt.py --file "/path/to/conversations.json"
```

Notes:

- If no Postgres URL is set, the app falls back to SQLite.
- The legacy path does not support checkpointing, staged import, or
  sharded archive detection. Prefer `import:openai-conversations` for
  production use.

---

## WebUI account import (current path)

For the user's complete ChatGPT/OpenAI account export, use the account-owned
staged import path:

1. Open Settings -> Data -> Import Conversation History.
2. Select **OpenAI (ChatGPT)**.
3. Use **Choose Folder** for the extracted export directory, or drop the
   complete directory.
4. A single ZIP, JSON, or readable `.dat` file can also be selected through
   **Choose File** or dropped. The current modal stages it through the same
   account-import coordinator.
5. Keep the page open until the transfer reaches **Accepted — continuing in
   background**. After queue acceptance, the worker continues independently and
   the modal polls `GET /api/imports/openai-account/{job_id}` until terminal status.

The current coordinator:

- preflights backend availability;
- creates an account-owned durable job;
- uploads files in bounded batches (up to 25 files or approximately 32 MiB);
- preserves each browser-relative path;
- commits only after the declared file count and byte count are staged; and
- polls `GET /api/imports/openai-account/{job_id}` until terminal status.

Folder selection starts this flow immediately. It is not the legacy synchronous
single-file upload route.

### WebUI versus direct compatibility route

The account-import WebUI uses:

- `POST /api/imports/openai-account`
- `POST /api/imports/openai-account/{job_id}/files`
- `POST /api/imports/openai-account/{job_id}/commit`
- `GET /api/imports/openai-account/{job_id}`

The older `POST /api/upload-chatgpt-export` route remains a compatibility path
for callers that submit one legacy `conversations.json` file or one readable
modern `.dat` conversation shard. It is not the route for a complete
multi-file account export and should not be used to qualify the account-import
worker.

### Supported-format matrix

| Export shape | CLI / worker | Current account-import WebUI | Direct compatibility route |
|---|---:|---:|---:|
| Legacy `conversations.json` | Supported | Supported as a single staged file | Supported |
| Modern readable JSON/JSONL `.dat` shard | Supported | Supported as a single staged file or inside a folder | Supported as one shard |
| Modern `conversations__*.part-*`, `workspace*`, or `Unassigned` tree | Supported | Supported through folder upload | Not supported as one request |
| One ZIP containing the export tree | CLI expects extracted folder | Supported; worker expands a single staged ZIP | Rejected |
| HTML/report-only or manifest-only payload | Diagnostic inventory only | Fails closed with no conversation import | Rejected |
| Images and PDFs referenced by imported messages | Imported when the worker can retain the file | Imported with provenance warnings where evidence is incomplete | Not the purpose of this route |
| Audio/video/opaque unsupported binaries | Inventoried and reported as skipped/warnings | Retained in diagnostics; not searchable message content | Rejected |

The adapter classifies payloads by content and schema rather than trusting the
`.dat` suffix. A `.dat` file containing a ZIP signature is treated as a ZIP
payload; a ZIP nested inside a multi-file folder is currently inventoried rather
than recursively expanded. That is a concrete compatibility boundary to inspect
against the actual Business export.

## Ownership, resumability, and provenance

Account-import route identity is server-derived. The client does not choose the
canonical owner; the service queries jobs by both `job_id` and authenticated
`user_id`, and the worker carries that same owner through staging,
materialization, canonical thread/message writes, and embedding handoff.

The importer is idempotent on the source conversation/message identity:

- canonical threads are matched by owner, `origin_system=openai`, and source
  conversation ID;
- messages are matched by canonical thread and source message ID; and
- the account job checkpoint records confirmed conversation IDs after durable
  provenance verification.

There are two different resume boundaries:

1. The CLI importer can resume across process/database interruptions from
   `import_checkpoint.ndjson`.
2. The background worker can requeue queued/running jobs after startup and
   replay the durable conversation checkpoint. A browser transfer that ends
   while still `receiving` is not silently resumed; the UI reports that the
   transfer must be selected again. Failed account jobs are retryable only when
   they are zero-write and their staged bytes are still available.

Imported provenance is retained at multiple layers:

- thread metadata carries `source_thread_id`, `import_source`,
  `import_profile`, and adapter format/source-path metadata;
- message metadata carries `source_thread_id`, `source_message_id`,
  source timestamps, raw role/content metadata, import origin, and embedding
  state; and
- embedding payload metadata carries the owner, canonical thread/message IDs,
  source IDs, and `chatgpt_import` source label.

Images and PDFs are handled separately from conversation text. The worker can
retain them as account-owned media/document records and link them when the
export contains explicit message references. Ambiguous or unsupported assets are
not guessed into a conversation; they remain warnings/orphan inventory. Full
attachment continuity is therefore not established for arbitrary Business
export payloads.

## Retrieval integration and qualification status

Imported messages are canonical `chat_messages` rows owned by the importing
account. The account worker defers message embedding to the import-embedding
handoff; the embedding worker writes owner- and thread-scoped vector metadata.
The normal context broker and chat path are the intended retrieval surface, with
user/thread/project scope checks remaining in force.

This is not yet complete natural continuity evidence. The September 23 R4
qualification reached browser folder upload, canonical persistence, automatic
embedding, and backend/worker vector parity, then stopped before a normal chat
question, provider context capture, answer persistence, and a negative
cross-account scope control. The release state correctly remains `HOLD`.

The acceptance bar for the actual export is therefore:

1. diagnose the archive without database writes;
2. inspect the detected format, conversation count, parse failures, and
   attachment inventory;
3. run a bounded synthetic or selected-sample import in an isolated runtime;
4. verify owner-scoped canonical persistence and replay/idempotency;
5. verify vector readiness and normal conversation retrieval; and
6. only then import the complete private archive into the user's canonical
   personal store.

The existing frontend Playwright migration coverage is compatibility-route coverage
with mocked API responses. It does not prove the current folder-selection,
account-job, worker-materialization, or natural-retrieval path; those remain
separate acceptance work.

## Expected Acceptance/Rejection Behavior

Accepted:

- A single legacy `conversations.json` file whose content matches the supported
  ChatGPT export schema.
- A single modern OpenAI `.dat` conversation shard containing readable
  JSON/JSONL conversation records.
- Sharded export folders with `conversations__*.part-*` directories and
  `.dat` files.
- Legacy `conversations.json` at the export root.

Rejected with explicit error:

- HTML export file (`chat.html`)
- ZIP archive uploaded directly
- Metadata-only JSON like `shared_conversations.json` (missing `mapping`)
- Malformed JSON
- `__export_file_manifests__/conversations.json` (manifest metadata, not
  conversation data — correctly excluded)

---

## Quick Verification After Import

- Confirm success stats in CLI output or diagnostics JSON.
- Refresh thread list (UI emits refresh event on success).
- Query DB directly:

```bash
docker compose exec -T db psql -U codexify -d Codexify \
  -c "SELECT count(*) as threads FROM chat_threads;" \
  -c "SELECT count(*) as messages FROM chat_messages;" \
  -c "SELECT role, count(*) FROM chat_messages GROUP BY role;"
```

- Check for duplicates (should return 0):

```bash
docker compose exec -T db psql -U codexify -d Codexify -c "
SELECT count(*) as duplicate_messages FROM (
  SELECT thread_id, extra_meta->>'source_message_id', count(*)
  FROM chat_messages
  WHERE extra_meta->>'source_message_id' IS NOT NULL
  GROUP BY thread_id, extra_meta->>'source_message_id'
  HAVING count(*) > 1
) sub;
"
```

- Inspect checkpoint state:

```bash
wc -l logs/openai_import/import_checkpoint.ndjson
```
