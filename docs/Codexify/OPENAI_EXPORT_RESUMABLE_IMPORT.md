# OpenAI Export — Archive-Scale Import with Resumable Checkpointing

This is the definitive runbook for importing full OpenAI data exports
(5,000+ conversations, 100,000+ messages) into Codexify. It uses the
hardened resumable import pipeline proven in the H1.2 rehearsal.

For single-file legacy imports or diagnostic-only scans, see
[`OPENAI_EXPORT_IMPORT_DIAGNOSTICS.md`](OPENAI_EXPORT_IMPORT_DIAGNOSTICS.md).

---

## Overview

Archive-scale OpenAI exports can destabilize a local Postgres instance if
imported in one monolithic pass. The hardened import pipeline solves this
with three mechanisms:

1. **Resumable checkpointing** — every conversation is recorded after import.
   A restarted import skips already-completed work.
2. **Bounded batches** — conversations are committed in small groups (default
   10). Postgres never holds an unreasonably large transaction.
3. **Staged import** — threads/messages, personal facts, and embeddings can
   be imported separately, keeping each stage bounded.

---

## Prerequisites

- Codexify running via Docker Compose (Postgres + backend healthy).
- An extracted OpenAI export folder (not the zip).
- Python virtual environment with Codexify dependencies.
- `DATABASE_URL` pointing to the local Postgres instance.

The archive path used in the H1.2 rehearsal:

```
/Users/chriscastillo/Downloads/OpenAI-export
```

Substitute your own export path in the commands below.

---

## Stage A: Threads and Messages Only

Stage A imports just the conversation structure — threads and messages.
No personal facts, no embeddings. This is the safest first pass.

### Step 1: Diagnostic preview (no DB writes)

```bash
PYTHONPATH="$(pwd)" \
DATABASE_URL="postgresql://codexify:codexify@localhost:5433/Codexify" \
GUARDIAN_DATABASE_URL="postgresql+psycopg://codexify:codexify@localhost:5433/Codexify" \
.venv/bin/python scripts/chatgpt_import/cli_migrate.py import:openai-conversations \
  --path /path/to/OpenAI-export \
  --parse-only \
  --limit 25
```

This scans the archive, writes diagnostics to `logs/openai_import/`, and
prints a summary. No database writes.

Verify in the output:
- `export_format` is `sharded` (modern archive) or `legacy`
- `conversations_discovered` matches your expectation
- `parse_failures` is 0 or acceptably low

### Step 2: Small bounded import (validate stability)

```bash
PYTHONPATH="$(pwd)" \
DATABASE_URL="postgresql://codexify:codexify@localhost:5433/Codexify" \
GUARDIAN_DATABASE_URL="postgresql+psycopg://codexify:codexify@localhost:5433/Codexify" \
.venv/bin/python scripts/chatgpt_import/cli_migrate.py import:openai-conversations \
  --path /path/to/OpenAI-export \
  --user-id local \
  --limit 25 \
  --batch-conversations 5 \
  --resume \
  --messages-only
```

Verify:
- 25 conversations imported
- No Postgres restarts or connection errors
- Checkpoint written to `logs/openai_import/import_checkpoint.ndjson`

### Step 2b: Resume test

Stop the import after a few batches (Ctrl+C), then re-run the exact
same command. The output should show:

```
Batch 3/505: all already completed, skipping
Batch 4/505: all already completed, skipping
...
```

Completed conversations are skipped. No duplicates are created.

### Step 3: Full Stage A import

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

This will take 30–60 minutes for a 5,000-conversation archive.

Progress is logged per batch:

```
Batch 42/505: processing 10 conversations...
Progress: 420/5043 conversations (8.3%) | threads=233 messages=9111
```

If Postgres restarts, the import will:
1. Log an error (`Import process failed`)
2. Save the checkpoint
3. Exit

Simply re-run the same command. All completed conversations are skipped.
No duplicates are created.

### Step 4: Verify Stage A

```bash
docker compose exec -T db psql -U codexify -d Codexify \
  -c "SELECT count(*) as threads FROM chat_threads;" \
  -c "SELECT count(*) as messages FROM chat_messages;" \
  -c "SELECT count(*) as personal_facts FROM personal_facts;"
```

Expected:
- `threads` ≈ conversations in archive
- `messages` > 0
- `personal_facts` = 0 (Stage A is messages-only)

---

## Stage B: Personal Facts Extraction

After threads/messages are stable, extract personal facts from the
imported message substrate.

```bash
PYTHONPATH="$(pwd)" \
DATABASE_URL="postgresql://codexify:codexify@localhost:5433/Codexify" \
GUARDIAN_DATABASE_URL="postgresql+psycopg://codexify:codexify@localhost:5433/Codexify" \
.venv/bin/python scripts/chatgpt_import/cli_migrate.py import:openai-conversations \
  --path /path/to/OpenAI-export \
  --user-id local \
  --resume \
  --batch-conversations 10 \
  --embedding-mode off
```

**Note**: No `--messages-only` and no `--disable-personal-facts` flag.
Threads and messages are already imported (idempotent - 0 new records).
Personal facts will be extracted, guardrail-classified, and persisted
as review candidates. `--disable-embeddings` is not a valid flag here;
`--embedding-mode` controls that phase and defaults to `off`.

Verify:
```bash
docker compose exec -T db psql -U codexify -d Codexify \
  -c "SELECT status, count(*) FROM personal_facts GROUP BY status;"
```

---

## CLI Reference

### `import:openai-conversations`

```
Usage: codexify import:openai-conversations [OPTIONS]

Import OpenAI export conversations into Codexify-native chat threads.
Supports resumable, bounded-batch import for archive-scale exports.

Options:
  --path PATH                  Path to OpenAI export file or folder [required]
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

### Common Patterns

**Archive-scale Stage A (messages only):**
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

**Personal facts extraction (Stage B):**
```bash
PYTHONPATH="$(pwd)" \
DATABASE_URL="postgresql://codexify:codexify@localhost:5433/Codexify" \
GUARDIAN_DATABASE_URL="postgresql+psycopg://codexify:codexify@localhost:5433/Codexify" \
.venv/bin/python scripts/chatgpt_import/cli_migrate.py import:openai-conversations \
  --path /path/to/OpenAI-export \
  --user-id local \
  --resume \
  --batch-conversations 10
```

**Resume after Postgres restart:**
Same command as before — checkpoint automatically skips completed work.

**Preview 25 conversations:**
```bash
codexify import:openai-conversations \
  --path /path/to/OpenAI-export --parse-only --limit 25
```

---

## Checkpoint System

The importer writes a checkpoint log to:

```
{diagnostic-dir}/import_checkpoint.ndjson
```

Each line is a JSON record:

```json
{
  "import_run_id": "20260624T120000-OpenAI-export",
  "conversation_id": "some-openai-conv-uuid",
  "status": "imported",
  "source_file": "conversations__abc.part-0001/file_001.dat",
  "messages_imported": 42,
  "started_at": "2026-06-24T12:00:00+00:00",
  "updated_at": "2026-06-24T12:00:01+00:00"
}
```

Checkpoint entries from all runs are recognized — resuming after a
process restart or Postgres recovery skips any conversation already
marked `imported`.

To inspect checkpoint state:

```bash
cat logs/openai_import/import_checkpoint.ndjson | \
  python3 -c "import sys,json; d={}; [d.update({json.loads(l)['status']: d.get(json.loads(l)['status'],0)+1}) for l in sys.stdin]; print(d)"
```

---

## Postgres Stability Tips

Archive-scale imports generate heavy WAL write activity. If Postgres
enters recovery/shutdown during import:

1. **Don't panic** — checkpoint is saved, no data is lost.
2. Wait for Postgres to recover (`docker compose ps db` shows healthy).
3. Re-run the same import command — completed work is skipped.
4. Consider reducing batch size: `--batch-conversations 5`.

For very large archives, tune Postgres:

```yaml
# docker-compose.yml overrides
db:
  command:
    - "postgres"
    - "-c"
    - "max_wal_size=2GB"
    - "-c"
    - "checkpoint_timeout=300s"
```

---

## Manifest File Protection

Modern OpenAI exports include an `__export_file_manifests__/` directory
containing file manifest metadata. A file named `conversations.json`
inside this directory was historically misdetected as a legacy export.

As of the H1.1 hardening pass, the adapter:

1. Excludes files under `__export_file_manifests__/` from legacy detection.
2. Validates payload contents for conversation-shaped data.
3. Rejects manifest records (keys like `file_name`, `file_size`,
   `manifest_version` without `mapping` or `messages`).

This prevents manifest files from hijacking the legacy import path.

---

## Validation

Run the importer test suite after any code changes:

```bash
.venv/bin/pytest tests/migration/test_openai_export_adapter.py \
  tests/migration/test_openai_export_conversation_import.py \
  tests/personal_facts/test_import_guardrail_integration.py \
  tests/migration/test_openai_export_corpus_recon.py -q --tb=short
```

---

## Proof

The archive-scale pipeline was proven in the H1.2 rehearsal:

- **Archive**: 5,043 conversations, 151,153 raw messages
- **Result**: 5,040 threads, 112,380 canonical messages imported
- **Stability**: One Postgres restart mid-import, recovered via checkpoint
- **Resume**: 5 import runs across ~1 hour, 0 duplicates, 0 data loss

Reports: `reports/personal_fact_discovery/phase_h1_2_full_messages_import_rehearsal.md`
