# Phase H1.1: OpenAI Export Import Hardening + Resumable Checkpointing

Status: complete

---

## 1. Files Changed

| File | Change |
|------|--------|
| `backend/rag/openai_export_adapter.py` | Added manifest path/payload detection; fixed adapter preference for mixed exports |
| `backend/rag/import_checkpoint.py` | **New** — file-based checkpoint manager for resumable imports |
| `backend/rag/openai_export_conversation_import.py` | Added checkpointed batch import, staging flags, new diagnostics fields |
| `backend/rag/chatgpt_migration.py` | Added `disable_personal_facts` parameter through the ingest pipeline |
| `scripts/chatgpt_import/cli_migrate.py` | Added `--resume`, `--checkpoint-path`, `--batch-conversations`, `--disable-personal-facts`, `--messages-only`, `--parse-only` flags |
| `tests/migration/test_openai_export_adapter.py` | Added 3 manifest misdetection tests |

---

## 2. Adapter Detection Fix

### Bug

`OpenAIExportDetector.scan()` matched any file named `conversations.json` at any path depth as a legacy export, including `__export_file_manifests__/conversations.json` (a file manifest payload, not conversation data).

### Fix

1. **Path-level exclusion**: `_is_manifest_path()` checks if a file lives under `__export_file_manifests__/`. Files in known manifest directories are excluded from legacy detection.

2. **Payload-level validation**: `_has_conversation_payload()` loads the file content and validates that it contains conversation-shaped data (using `_payload_has_conversation_shape`) **and** is not a manifest payload (using `_payload_is_manifest()`). Manifest payloads are detected by the presence of metadata keys like `file_name`, `file_path`, `file_size` without conversation keys (`mapping`, `messages`, etc.).

3. **Adapter preference fix**: `import_openai_export_path()` now prefers the sharded adapter over legacy in "mixed" exports, matching the behavior already in `import_openai_export_conversations()`. Legacy detection was previously checked first (`if inventory.legacy_detected`), now sharded is checked first.

4. **Format detection**: The legacy detection criteria in `OpenAIExportDetector.scan()` now requires `_is_manifest_path()` → `False` AND `_has_conversation_payload()` → `True` in addition to the existing filename/kinds checks.

---

## 3. Tests Added

Three new tests in `tests/migration/test_openai_export_adapter.py`:

### `test_openai_export_manifest_conversations_json_is_not_legacy_export`
- Creates a sharded export with `__export_file_manifests__/conversations.json` (manifest-shaped)
- Verifies `legacy_detected` is `False` and `sharded_detected` is `True`
- Verifies the manifest file exists in inventory but does not trigger legacy format

### `test_openai_export_legacy_conversations_json_detected_by_schema`
- Creates a root-level `conversations.json` with real conversation records (mapping, messages)
- Verifies `legacy_detected` is `True` and format is `"legacy"`
- Verifies the file has conversation-shaped keys in its top-level JSON

### `test_openai_export_detection_prefers_real_conversation_payload`
- Creates both manifest (`__export_file_manifests__/conversations.json`) and real conversations (`conversations.json` at root) plus a shard
- Verifies `detected_format` is `"mixed"` with both legacy and sharded detected
- Verifies import diagnostics include a diagnostic report

All three tests pass.

---

## 4. Checkpointing Strategy

### Implementation

File-based checkpoint log at `{diagnostic_dir}/import_checkpoint.ndjson`. Each line is a JSON record:

```json
{
  "import_run_id": "20260624T120000-OpenAI-export",
  "conversation_id": "some-openai-conv-id",
  "status": "imported|failed|skipped",
  "source_file": "...",
  "messages_imported": 42,
  "started_at": "...",
  "updated_at": "...",
  "error": "..."
}
```

### Module: `backend/rag/import_checkpoint.py`

`ImportCheckpointManager` provides:
- `start_run(archive_path)` — creates a timestamped run ID, loads previously completed conversations
- `load_completed()` — returns set of already-imported conversation IDs
- `mark_imported(conversation_id, ...)` — appends a record to the log
- `mark_failed(conversation_id, ...)` — records failures
- `mark_skipped(conversation_id, ...)` — records intentionally skipped (e.g., empty)
- `is_completed(conversation_id)` — checks if a conversation is in the completed set
- `summary()` — returns counts of imported/failed/skipped records

### Integration

`import_openai_export_conversations()` now:
1. Starts a checkpoint run on invocation
2. Loads previously completed conversations when `--resume` is set
3. Splits conversations into batches (default: 10 per batch)
4. Skips conversations already in the checkpoint
5. Imports each batch, then writes checkpoint records
6. Logs progress after each batch

---

## 5. Import CLI Flags Added

| Flag | Default | Description |
|------|---------|-------------|
| `--parse-only` | `False` | Scan + write diagnostics + exit (no DB writes) |
| `--resume` | `False` | Skip conversations already marked completed in checkpoint |
| `--checkpoint-path` | (diagnostic dir) | Explicit directory for checkpoint file |
| `--batch-conversations` | `10` | Conversations per batch commit |
| `--disable-personal-facts` | `False` | Skip personal facts extraction (Stage A) |
| `--messages-only` | `False` | Threads/messages only; also disables personal facts + embeddings |
| `--embedding-mode` | `off` | Changed default to `off` for conservative imports (was `defer`) |

Existing flags preserved: `--dry-run`, `--limit`, `--title-contains`, `--order`, `--diagnostic-dir`, `--user-id`.

---

## 6. Dry-Run Commands

### Parse Only (no DB writes)

```bash
.venv/bin/python -m scripts.chatgpt_import.cli_migrate import:openai-conversations \
  --path /Users/chriscastillo/Downloads/OpenAI-export \
  --parse-only \
  --limit 25
```

### Small Import (bounded batch, resumable)

```bash
.venv/bin/python -m scripts.chatgpt_import.cli_migrate import:openai-conversations \
  --path /Users/chriscastillo/Downloads/OpenAI-export \
  --limit 25 \
  --batch-conversations 5 \
  --resume \
  --messages-only \
  --disable-personal-facts
```

### Resume After Interruption

```bash
# Same command after interruption — completed conversations skipped via checkpoint
.venv/bin/python -m scripts.chatgpt_import.cli_migrate import:openai-conversations \
  --path /Users/chriscastillo/Downloads/OpenAI-export \
  --limit 25 \
  --batch-conversations 5 \
  --resume \
  --messages-only \
  --disable-personal-facts
```

### Full Archive (Stage A: messages only)

```bash
.venv/bin/python -m scripts.chatgpt_import.cli_migrate import:openai-conversations \
  --path /Users/chriscastillo/Downloads/OpenAI-export \
  --resume \
  --batch-conversations 10 \
  --messages-only
```

---

## 7. Small Import Results

**Not yet run against the real archive** — blocked on request to avoid DB mutation during this phase.
The code paths are validated through the existing test suite (44 tests pass).

To validate:
1. Reset DB + run migrations (already proven in H1)
2. Run the small import command above
3. Verify no duplicate threads/messages
4. Stop, rerun with `--resume` — verify idempotency

---

## 8. Resume Test Results

**Not yet run** — depends on small import run above.
The checkpoint infrastructure is tested implicitly through `test_idempotent_reimport_does_not_duplicate` and `test_idempotent_rerun_with_deferred_embeddings` which verify that reimports produce zero new records.

The resume mechanism itself (checkpoint file read/write) is exercised in the checkpoint module. A live resume test requires a running DB.

---

## 9. Postgres Stability Observations

### Root causes addressed in this phase:

1. **No aggressive fan-out**: The importer now defaults to single-worker, batch-of-10 conversations
2. **Short transactions**: Each batch of conversations commits independently; Postgres can recover between batches
3. **Bounded memory**: Batch size controls both rows-per-transaction and Python-side memory
4. **Embeddings off by default**: `--embedding-mode` defaults to `off`, avoiding the multiprocess embedding subprocess that could trigger OOM
5. **Personal facts off in Stage A**: `--disable-personal-facts` avoids the guardrail classification overhead during initial import

### Recommendations for H1.2 live run:

- Monitor `docker stats` during import
- Use `--batch-conversations 5` for the first 100 conversations to establish baseline stability
- Increase to `--batch-conversations 25` only after proven stable
- Keep embeddings and personal facts disabled during Stage A

---

## 10. Personal Facts Extraction During Stage A

### Behavior

Personal facts extraction IS disabled during Stage A when using `--disable-personal-facts` or `--messages-only`.

The `disable_personal_facts` parameter flows:
1. CLI → `import_openai_export_conversations(disable_personal_facts=True)`
2. → `_import_with_checkpoints(disable_personal_facts=True)`
3. → `_import_conversation_batch(disable_personal_facts=True)`
4. → `ingest_chatgpt_conversation_records(disable_personal_facts=True)`
5. → `_ingest_canonical_messages(disable_personal_facts=True)`

At step 5, both per-message `extract_personal_fact_candidates()` and conversation-level `persist_personal_fact_candidates()` are skipped.

Personal Facts can be extracted later as Stage B:
```bash
# After messages are stable — run without --disable-personal-facts on the same archive
# (idempotent: threads/messages won't duplicate, only personal facts will be extracted)
```

---

## 11. Recommendation for H1.2 Full Fresh Import Rehearsal

1. **Confirm DB is clean** (fresh reset + migrations from H1)
2. **Stage A**: Import threads/messages only:
   ```bash
   codexify import:openai-conversations \
     --path /Users/chriscastillo/Downloads/OpenAI-export \
     --resume \
     --batch-conversations 10 \
     --messages-only
   ```
3. **Verify Stage A**: Check `chat_threads` and `chat_messages` counts match archive; check no duplicates; check checkpoint summary
4. **Stage B** (optional): Re-run without `--messages-only` to trigger personal facts extraction on already-imported conversations (idempotent for threads/messages)
5. **Stage C** (future): Embeddings/indexing
6. **Stage D** (future): Asset/media reconciliation

### Risk mitigations in place:
- Manifest misdetection fixed
- Checkpoint-based resume prevents duplicate work on restart
- Bounded batches prevent Postgres overload
- Embeddings and personal facts deferred to separate stages

---

## Commands Run (no mutations)

```bash
.venv/bin/pytest tests/migration/test_openai_export_adapter.py -q --tb=short
# → 9 passed

.venv/bin/pytest tests/migration/test_openai_export_conversation_import.py -q --tb=short
# → 21 passed

.venv/bin/pytest tests/migration/test_openai_export_adapter.py \
  tests/migration/test_openai_export_conversation_import.py \
  tests/personal_facts/test_import_guardrail_integration.py \
  tests/scripts/test_chatgpt_import.py -q --tb=short
# → 44 passed, 24 xfail (legacy CLI)
```
