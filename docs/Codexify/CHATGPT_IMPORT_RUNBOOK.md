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

## WebUI Import (drag/drop or picker)

1. Open Settings -> Data -> Import from ChatGPT.
2. Drag any file onto the drop area, or click **Choose File**.
3. Click **Upload & Migrate**.
4. The backend validates content and returns:
   - success stats (`threads_imported`, `messages_imported`), or
   - a clear format error (for example: HTML/ZIP/metadata-only JSON).

**Note**: The WebUI upload path is designed for single-file `conversations.json`
exports. For full archive folders, use the CLI.

---

## Expected Acceptance/Rejection Behavior

Accepted:

- Any filename or extension, as long as file content matches supported
  ChatGPT export JSON schema.
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
