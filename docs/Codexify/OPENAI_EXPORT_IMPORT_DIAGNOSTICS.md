# OpenAI Export Import Diagnostics

This note documents the V1 OpenAI export importer diagnostics lane. It covers
both the legacy `conversations.json` export shape and newer sharded export
folders that store conversation and asset payloads in opaque files.

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
