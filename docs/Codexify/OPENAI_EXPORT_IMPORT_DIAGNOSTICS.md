# OpenAI Export Import Diagnostics

This note documents the V1 OpenAI export importer diagnostics lane. It covers
both the legacy `conversations.json` export shape and newer sharded export
folders that store conversation and asset payloads in opaque files.

For archive-scale imports (5,000+ conversations) with resumable checkpointing,
see [`OPENAI_EXPORT_RESUMABLE_IMPORT.md`](OPENAI_EXPORT_RESUMABLE_IMPORT.md).

## Supported Export Shapes

Codexify now inspects OpenAI export folders by content, not by filename alone.
The detector recursively scans a selected export root and classifies every file
before import.

Supported inputs include:

- legacy exports containing `conversations.json`
- modern or sharded exports containing folders such as `conversations__*.part-*`
- `workspace*` folders, `Unassigned`, and `report.html`
- opaque `.dat` files that may contain JSON, JSONL, HTML, images, ZIP payloads,
  PDFs, media, binary attachment data, or unknown blobs

The legacy `conversations.json` importer path is preserved. If
`conversations.json` is present, legacy conversation import behavior remains the
primary lane.

## Diagnostic Mode

Use diagnostic mode when inspecting an unknown export before mutating the
database:

```bash
python -m scripts.chatgpt_import.cli_migrate import:openai \
  --path /path/to/OpenAI-export \
  --diagnose
```

Diagnostic mode scans and writes reports only. It does not import threads,
messages, or embeddings.

Reports are written to `logs/openai_import` by default. Override the output
directory with:

```bash
python -m scripts.chatgpt_import.cli_migrate import:openai \
  --path /path/to/OpenAI-export \
  --diagnose \
  --diagnostic-dir /path/to/diagnostics
```

## Diagnostic Outputs

The diagnostic lane writes:

- `openai_export_diagnostic.json`
- `openai_export_diagnostic.md`

The JSON report records each scanned file with:

- relative and absolute path
- file size
- extension
- detected content kind
- first bytes / magic signature
- parse success or parse failure
- detected top-level JSON keys when applicable
- whether the file looked like a conversation candidate

The Markdown summary is intended for quick operator review. The JSON report is
the durable forensic artifact.

## Content Classification

Classification is content-sniffing based. The adapter probes magic bytes and
payload structure instead of trusting `.dat` or other extensions.

Detected kinds include:

- JSON object payloads
- JSON array payloads
- JSONL payloads
- HTML
- ZIP
- PNG, JPEG, GIF, WebP
- PDF
- common audio/video payloads
- unknown binary blobs

Unknown blobs are not treated as failed conversations. They are preserved in the
diagnostic inventory as orphaned export assets unless a future import layer can
link them to conversation records.

## Import Behavior

For JSON, JSON array, and JSONL files, the importer inspects schemas for
conversation-like records. It looks for stable hints such as:

- `title`
- `create_time`
- `update_time`
- `mapping`
- `messages`
- `conversation_id`
- `message`
- `author`
- `content`
- `parts`

Unknown schemas are logged and skipped safely. The adapter does not crash when a
JSON payload is valid but not conversation-shaped.

If candidate conversations are found, import remains idempotent: re-importing
the same source thread/message identifiers avoids duplicate conversations and
messages.

## Assets And Unknown Payloads

Images and binary payloads are classified as export assets. If the importer can
link an asset to a conversation, it can be preserved as an attachment record in
future attachment-aware lanes. If no link is available, the file is reported as
an orphaned export asset.

The V1 diagnostic posture is intentionally forensic: Codexify records what it
found instead of silently discarding unknown payloads.

## Resumable Import CLI

The `import:openai-conversations` command provides the primary import path
for production use. It supports bounded batches, checkpoint-based resume,
and staged import (threads, personal facts, embeddings as separate passes).

```bash
# Diagnostic preview (no DB writes)
PYTHONPATH="$(pwd)" \
DATABASE_URL="postgresql://codexify:codexify@localhost:5433/Codexify" \
GUARDIAN_DATABASE_URL="postgresql+psycopg://codexify:codexify@localhost:5433/Codexify" \
.venv/bin/python scripts/chatgpt_import/cli_migrate.py import:openai-conversations \
  --path /path/to/OpenAI-export \
  --parse-only \
  --limit 25

# Full Stage A import (messages only, resumable)
PYTHONPATH="$(pwd)" \
DATABASE_URL="postgresql://codexify:codexify@localhost:5433/Codexify" \
GUARDIAN_DATABASE_URL="postgresql+psycopg://codexify:codexify@localhost:5433/Codexify" \
.venv/bin/python scripts/chatgpt_import/cli_migrate.py import:openai-conversations \
  --path /path/to/OpenAI-export \
  --user-id local \
  --resume --batch-conversations 10 --messages-only

# Stage B (personal facts extraction from stable messages)
PYTHONPATH="$(pwd)" \
DATABASE_URL="postgresql://codexify:codexify@localhost:5433/Codexify" \
GUARDIAN_DATABASE_URL="postgresql+psycopg://codexify:codexify@localhost:5433/Codexify" \
.venv/bin/python scripts/chatgpt_import/cli_migrate.py import:openai-conversations \
  --path /path/to/OpenAI-export \
  --user-id local \
  --resume \
  --batch-conversations 10
```

Key flags:

| Flag | Default | Purpose |
|------|---------|---------|
| `--resume` | off | Skip conversations already in checkpoint |
| `--batch-conversations` | 10 | Conversations per DB commit |
| `--messages-only` | off | Import threads/messages only; skip embeddings + personal facts |
| `--disable-personal-facts` | off | Skip personal facts extraction (Stage A) |
| `--parse-only` | off | Scan + write diagnostics, no DB writes |
| `--limit N` | none | Import only first N conversations |

Stage B does not have a dedicated `--disable-embeddings` flag. Keep
`--messages-only` and `--disable-personal-facts` omitted, and leave
`--embedding-mode` at its default unless you explicitly need a different
embedding pass.

For the full workflow, see [`OPENAI_EXPORT_RESUMABLE_IMPORT.md`](OPENAI_EXPORT_RESUMABLE_IMPORT.md).

## Manifest File Protection

Modern OpenAI exports include an `__export_file_manifests__/` directory with
a `conversations.json` file that contains **file manifest metadata**, not
conversation records (keys: `file_name`, `file_size`, `export_id`,
`manifest_version`).

The adapter protects against manifest misdetection with three layers:

1. **Path exclusion** — files under `__export_file_manifests__/` are excluded
   from legacy format detection.
2. **Payload validation** — candidate `conversations.json` files are validated
   for conversation-shaped content (keys like `mapping`, `messages`).
3. **Manifest rejection** — payloads containing only file-metadata keys are
   rejected even if they happen to pass path checks.

No manifest file will trigger a legacy import or be imported as a conversation.

## Schema And Migration Scope

No database migration was added for this importer slice.

The V1 adapter uses existing import and persistence contracts. Attachment
linking is represented in diagnostics unless the current import path can safely
associate a payload with an imported conversation.

## Validation Proof Chain

This documentation reflects the following committed proof chain:

- `7614afcc5d911faa2791d820a28dea023ee0481f` - added the OpenAI export adapter
  with legacy and sharded diagnostics/import support.
- `3b11738c98bf1da735b6f8369d9252dd628d1cee` - added the task prompt scraper
  over the same export inspection lane.
- `493f1086e8c7287b5b8eb0c8c5f07d5c20b5d01a` - repaired `numpy` and `typer`
  validation dependencies.
- `67a395837812a939526f79907213a562fc4cc2f6` - isolated the OpenAI adapter
  test `psycopg` stub so migration tests no longer depend on test order.
- `604b09879bd895a1f4a44247f5f0214bc8d0c537` - repaired the real runtime/base
  `psycopg` dependency contract.

Validated lanes after those commits:

- `pytest --collect-only tests/routes/test_migration_routes.py` collected 12
  tests.
- `pytest -v tests/routes/test_migration_routes.py` passed 12 tests.
- `pytest --collect-only tests/migration` collected 17 tests.
- `pytest -v tests/migration` passed 12 tests with 5 environment-dependent
  skips.
- `pytest -v tests/migration/test_openai_export_adapter.py` passed 6 tests.
- `pytest -v tests/migration/test_openai_export_task_scraper.py` passed 6
  tests.
- `python -m scripts.chatgpt_import.cli_migrate import:openai --help` executed.
- `python -m scripts.chatgpt_import.cli_migrate export-scraper:tasks --help`
  executed.
