# ChatGPT Import Runbook (Repeatable)

This runbook is the repeatable way to import ChatGPT history and verify outcomes.

## 1) Choose the export file

The importer accepts content by schema, not filename. A valid file must be JSON with:

- top-level array
- conversation objects containing a `mapping` field

Examples in this repo:

- `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/conversations.json` (smaller)
- `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/docs/conversation.json` (larger)

## 2) CLI import (host, no Docker required)

Run from the repo root:

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
python scripts/chatgpt_import/import_chatgpt.py --file "/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/docs/conversation.json"
```

Notes:

- Use the larger file above to stress-test system behavior.
- If you want the smaller baseline import, replace with `conversations.json`.
- If no Postgres URL is set, the app falls back to SQLite (as shown in logs).

## 3) WebUI import (drag/drop or picker)

1. Open Settings -> Data -> Import from ChatGPT.
2. Drag any file onto the drop area, or click **Choose File**.
3. Click **Upload & Migrate**.
4. The backend validates content and returns:
   - success stats (`threads_imported`, `messages_imported`), or
   - a clear format error (for example: HTML/ZIP/metadata-only JSON).

## 4) Expected acceptance/rejection behavior

Accepted:

- Any filename or extension, as long as file content matches supported ChatGPT export JSON schema.

Rejected with explicit error:

- HTML export file (`chat.html`)
- ZIP archive uploaded directly
- metadata-only JSON like `shared_conversations.json` (missing `mapping`)
- malformed JSON

## 5) Quick verification after import

- Confirm success stats in UI or CLI output.
- Refresh thread list (UI emits refresh event on success).
- Optional: query DB/thread list endpoints to verify imported threads/messages exist.
