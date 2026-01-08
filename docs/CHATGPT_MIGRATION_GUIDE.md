# ChatGPT Migration & Embedding Pipeline

> Import your ChatGPT conversation history into Codexify/Guardian and make it searchable through embeddings.

This guide explains how to migrate ChatGPT conversations into Codexify's database and ensure all messages get embedded for RAG-powered chat context.

## Table of Contents

- [Overview](#overview)
- [Design Rationale](#design-rationale)
- [Mental Model](#mental-model)
- [Prerequisites](#prerequisites)
- [Migration Paths](#migration-paths)
- [Step-by-Step Instructions](#step-by-step-instructions)
- [Verification](#verification)
- [Common Failure Modes](#common-failure-modes)
- [Troubleshooting](#troubleshooting)

---

## Overview

**What problem does this solve?**

When you switch from ChatGPT to Codexify, you lose access to your conversation history. This pipeline:

1. **Imports** your ChatGPT conversations into Codexify's PostgreSQL database
2. **Embeds** message content into a vector store (FAISS or Chroma) for semantic search
3. **Enables** Guardian to use your historical conversations as context when responding

**Key insight:** Migration and embedding are **intentionally separate steps**. Migration gets your data into the database fast. Embedding backfill happens afterward (or in parallel) and can be retried independently if it fails.

---

## Design Rationale

### Why UI-First Migration

Codexify is a **consumer-first application**. The UI is the canonical interface for importing your ChatGPT history:

1. **Simplicity**: Upload a file, click a button, done. No terminal, no Docker commands, no environment variables.
2. **Accessibility**: Non-technical users can migrate without learning CLI tools.
3. **Integrated Experience**: The UI shows progress, handles errors gracefully, and immediately makes imported threads visible.
4. **Single Path**: One upload flow, one backend endpoint, one migration engine—no confusion about which tool to use.

**The UI calls the same backend API endpoint (`POST /upload-chatgpt-export`) that powers all migration paths.** This ensures consistency regardless of how you trigger the import.

### Why CLI is Secondary

The CLI migration path exists for **advanced users** who need:

- Batch automation (scripted imports)
- Headless environments (servers without browsers)
- Debugging and development
- Integration with CI/CD pipelines

**CLI is not deprecated**—it's intentionally positioned as an advanced tool. If you're comfortable with Docker and terminal commands, CLI gives you more control. But most users should use the UI.

### Why Embedding is Separate from Migration

Migration and embedding serve different purposes and have different characteristics:

| Aspect | Migration | Embedding |
| ------ | --------- | --------- |
| **Purpose** | Store structured data (threads, messages) | Create vector representations for search |
| **Speed** | Fast (~1000 msg/min) | Slower (~100-500 msg/min) |
| **Failure Mode** | Atomic per-conversation | Can fail per-message |
| **Retry** | Re-run safely (idempotent) | Backfill worker handles gaps |
| **Dependency** | Database only | Requires embedding model |

**Benefits of separation:**

- Import 10,000 messages quickly, embed in background
- UI shows threads immediately (search works as embeddings complete)
- Embedding failures don't block migration
- Can re-embed with different models without re-importing

### Why Embedding is Idempotent

The embedding backfill worker is designed to be **safe to re-run**:

- Checks if message already has embedding before processing
- Skips already-embedded messages
- Can be interrupted and resumed
- Handles partial failures gracefully

This means you can run the backfill worker multiple times without creating duplicate embeddings or corrupting data.

---

## Mental Model

### Why Guardian refuses to respond without grounded context

Guardian is designed to be **grounded in your actual knowledge**. When you chat with a thread, Guardian:

1. Retrieves the thread's message history from PostgreSQL
2. Uses the latest user message to **query the vector store** for relevant context
3. Passes retrieved context + thread history to the LLM
4. Streams the response back to you

**If a thread has no usable context** (empty messages, or embeddings don't exist), Guardian returns:
```
HTTP 400: "Thread has no usable context"
```

This is a **feature, not a bug**. Guardian won't hallucinate. If your messages aren't embedded, Guardian can't ground its response in your data.

### Why migration and embedding are separate

**Migration** is I/O-bound (writing to Postgres):
- Fast (~1000 messages/minute)
- Stores structured data (threads, messages, metadata)
- Can fail and retry without losing progress

**Embedding** is compute-bound (running ML models):
- Slower (~100-500 messages/minute depending on backend)
- Creates vector representations for semantic search
- Can be paused, resumed, or run in batches

**By separating them**, you can:
- Import 10,000 messages in 10 minutes
- Embed them in the background over 30 minutes
- Use the UI immediately (threads appear, but search is incomplete until embeddings finish)

---

## Prerequisites

### Services (Docker Compose)

Ensure these services are running:

```bash
docker compose up -d db redis
```

| Service | Port | Purpose |
|---------|------|---------|
| **PostgreSQL** | 5433:5432 | Stores chat threads and messages |
| **Redis** | 6379 | Event bus and caching |
| **Neo4j** (optional) | 7687, 7474 | Legacy CLI migration path |

### Environment Variables

Create or update your `.env` file:

```bash
# Required: Database connection
DATABASE_URL=postgresql://codexify:codexify@localhost:5433/Codexify
GUARDIAN_DATABASE_URL=${DATABASE_URL}

# Required: Local embedding model (absolute path)
LOCAL_EMBED_MODEL=/models/bge-large-en-v1.5

# Required: Vector store backend
CODEXIFY_VECTOR_STORE=faiss  # or 'chroma'

# Optional: Embedding worker tuning
EMBED_BATCH_SIZE=32
EMBED_MAX_BATCHES=0  # 0 = unlimited
EMBED_SLEEP_SECONDS=0
EMBED_DRY_RUN=false

# Optional: OpenAI embeddings (cloud alternative)
OPENAI_API_KEY=sk-...  # if using OpenAI embeddings instead of local
```

### ChatGPT Export File

1. Go to [ChatGPT Settings → Data Controls → Export Data](https://chat.openai.com/settings)
2. Request export (takes up to 24 hours)
3. Download and extract `conversations.json`

---

## Migration Paths

Codexify supports **two migration paths**. The UI is the recommended path for most users.

### Path A: UI Migration (Recommended)

**This is the primary, recommended way to import your ChatGPT history.**

**When to use:**

- You're a typical Codexify user
- You want the simplest possible experience
- You're running the full Codexify stack (Docker Compose)

**How it works:**

1. Open the Codexify UI at `http://localhost:5173`
2. Navigate to Settings → Import
3. Upload your `conversations.json` file
4. Watch the progress indicator
5. Your threads appear immediately

**Pros:**

- Zero configuration required
- Visual feedback and error handling
- Threads visible immediately after import
- Embeddings created inline (when possible)

**Cons:**

- Requires the UI to be running
- Less control over batch sizes and options

**Under the hood:** The UI calls `POST /upload-chatgpt-export` on the backend, which uses the same migration engine as the CLI.

---

### Path B: CLI Migration (Advanced)

**For power users, automation, and headless environments.**

**When to use:**

- You need to automate imports (scripted/CI)
- You're running in a headless environment
- You want detailed terminal output
- You're debugging migration issues

**How it works:**

```bash
# Using Docker (recommended for CLI)
docker compose run --rm --profile cli chatgpt-migrate --file /data/conversations.json

# Or with a mounted file
docker compose run --rm --profile cli chatgpt-migrate --file /app/conversations.json
```

**Pros:**

- Full control over import process
- Rich terminal output with progress
- Can be scripted and automated
- Works in headless environments

**Cons:**

- Requires Docker knowledge
- More complex than UI upload

**Entry point:** `scripts/chatgpt_import/import_chatgpt.py`

---

### Path C: Direct API (Programmatic)

**For developers integrating migration into custom workflows.**

```bash
curl -X POST http://localhost:8888/upload-chatgpt-export \
  -H "X-User-Id: me" \
  -H "X-Api-Key: ${GUARDIAN_API_KEY}" \
  -F "file=@./conversations.json"
```

**Response:**
```json
{
  "threads_imported": 42,
  "messages_imported": 1337
}
```

This is the same endpoint the UI uses. Useful for building custom import tools or integrating with other systems.

---

## Step-by-Step Instructions

### Path A: UI Migration (Recommended)

**This is the easiest way to import your ChatGPT history.**

#### Step 1: Start Codexify

```bash
docker compose up -d
```

Wait for all services to be healthy (this may take a minute on first run):

```bash
docker compose ps
# All services should show "healthy" or "running"
```

#### Step 2: Open the UI

Navigate to <http://localhost:5173> in your browser.

#### Step 3: Import Your Conversations

1. Click on **Settings** (gear icon) in the sidebar
2. Navigate to **Import** or **Data Migration**
3. Click **Upload ChatGPT Export**
4. Select your `conversations.json` file
5. Click **Import**

You'll see a progress indicator while the import runs.

#### Step 4: Verify Import

After the import completes:

1. Navigate to **Threads** in the sidebar
2. You should see your imported conversations listed
3. Click on any thread to view the conversation

**That's it!** Your ChatGPT history is now in Codexify.

#### Step 5: (Optional) Run Embedding Backfill

If some messages didn't get embedded during import, run the backfill worker:

```bash
docker compose exec backend python -m guardian.workers.embedding_backfill_worker
```

This is idempotent—safe to run multiple times.

---

### Path B: CLI Migration (Advanced)

**For automation, headless environments, or debugging.**

#### CLI Step 1: Ensure Services Are Running

```bash
docker compose up -d db migrator
# Wait for migrator to complete
docker compose logs migrator --follow
```

#### CLI Step 2: Place Your Export File

Option A: Mount a data directory:
```bash
mkdir -p data
cp /path/to/conversations.json data/
```

Option B: Place in project root:
```bash
cp /path/to/conversations.json ./conversations.json
```

#### CLI Step 3: Run CLI Migration

```bash
# Using the data directory mount
docker compose run --rm --profile cli chatgpt-migrate --file /data/conversations.json

# Or using the root mount
docker compose run --rm --profile cli chatgpt-migrate --file /app/conversations.json
```

**Expected output:**

```text
======================================================================
  ChatGPT → Codexify Migration
  Dual-Engine Import: Neo4j + Chroma
======================================================================

Validating configuration...
Resolved ChatGPT export path: /data/conversations.json
Loading ChatGPT export from: /data/conversations.json
Loaded file (1234567 bytes)
Using Codexify user_id: me

----------------------------------------------------------------------
Starting Dual-Engine Import
----------------------------------------------------------------------

Import complete!
   • Threads: 42
   • Messages: 1337

======================================================================
Migration Complete!
======================================================================
   Your Companion has awakened in Codexify!
   Time elapsed: 12.34s
   Messages processed: 1337

Your conversations are alive and ready to explore.
```

#### CLI Step 4: Verify Import

```bash
docker compose exec db psql -U codexify -d Codexify -c "
SELECT COUNT(*) AS threads FROM chat_threads;
SELECT COUNT(*) AS messages FROM chat_messages;
"
```

#### CLI Step 5: (Optional) Run Embedding Backfill

```bash
docker compose exec backend python -m guardian.workers.embedding_backfill_worker
```

---

## Verification

### Database Verification

**PostgreSQL (UI and CLI paths):**

```sql
-- Check thread count
SELECT COUNT(*) FROM chat_threads;

-- Check message count
SELECT COUNT(*) FROM chat_messages;

-- Check recent threads
SELECT id, title, created_at
FROM chat_threads
ORDER BY created_at DESC
LIMIT 10;

-- Check embedding metadata (if schema migration applied)
SELECT COUNT(*) AS embedded_count
FROM chat_messages
WHERE embedded_at IS NOT NULL;
```

You can run these queries via Docker:

```bash
docker compose exec db psql -U codexify -d Codexify
```

### Vector Store Verification

**FAISS:**
```python
from guardian.vector.store import VectorStore

store = VectorStore()
# Query for a known message
results = store.query("tell me about Python", k=5)
print(f"Found {len(results)} results")
for r in results:
    print(f"- {r['meta']['thread_id']}: {r['text'][:100]}...")
```

**Chroma:**
```python
import chromadb

client = chromadb.PersistentClient(path="./chroma")
collection = client.get_collection("chatgpt_messages")

print(f"Total embeddings: {collection.count()}")

# Query test
results = collection.query(
    query_texts=["tell me about Python"],
    n_results=5
)
print(f"Found {len(results['ids'][0])} results")
```

---

## Common Failure Modes

### 1. "Thread has no usable context"

**Symptoms:**
- UI loads thread, but clicking "Complete" returns HTTP 400
- Error message: `Thread has no usable context`

**What it means:**
The thread exists in the database, but all messages are empty or invalid. This happens when:
- ChatGPT export contains only metadata nodes (no actual message text)
- Messages have `content: null` or empty strings
- System messages with empty `parts` arrays

**Solution:**
This is expected for some ChatGPT threads (they export UI state, not conversations). The migration correctly skips these. **No action needed** — these threads are not usable and won't appear in search.

**How to identify:**
```sql
-- Find threads with no valid messages
SELECT t.id, t.title, COUNT(m.id) as msg_count
FROM chat_threads t
LEFT JOIN chat_messages m ON t.id = m.thread_id
GROUP BY t.id, t.title
HAVING COUNT(m.id) = 0;
```

---

### 2. Backfill embedding only a handful of messages

**Symptoms:**
- Migration reports `messages_imported: 1000`
- Backfill worker reports `embedded 10 messages`
- Vector store count is much less than message count

**What it means:**
The migration successfully embedded most messages inline, and the backfill worker only processed the ones that were missed.

**Solution:**
This is **correct behavior**. The backfill worker is idempotent and only embeds messages that don't already exist in the vector store.

**Verification:**
```bash
# Check vector store count
docker compose exec backend python -c "
from guardian.vector.store import VectorStore
store = VectorStore()
print(f'Vector store has {store.embedder._chroma_collection.count() if hasattr(store.embedder, \"_chroma_collection\") else \"N/A\"} embeddings')
"
```

If the count is close to your message count, **you're done**.

---

### 3. UI completing silently with no assistant response

**Symptoms:**
- Click "Complete" in UI
- Loading spinner appears briefly
- No assistant message appears
- No error shown in UI
- Backend logs show: `Thread has no usable context` or similar

**What it means:**
One of:
1. Thread has no valid messages (see failure mode #1)
2. Vector store is not initialized
3. Embeddings don't exist for this thread
4. LLM provider key is missing

**Solution:**

**Check 1: Does thread have messages?**
```sql
SELECT COUNT(*) FROM chat_messages WHERE thread_id = 123;
```

**Check 2: Are embeddings present?**
```python
# For Chroma
collection.get(where={"thread_id": 123})
```

**Check 3: Is LLM provider configured?**
```bash
docker compose exec backend env | grep -E "GROQ_API_KEY|OPENAI_API_KEY|LOCAL_CHAT_MODEL"
```

**Check 4: Check backend logs:**
```bash
docker compose logs backend --tail=100 | grep -i "error\|warning\|thread"
```

---

### 4. Migration silently skipped embeddings

**Symptoms:**
- Migration returns `threads_imported: 42, messages_imported: 1337`
- No mention of embeddings in output
- Backfill worker shows `embedded 1337 messages` (all of them)

**What it means:**
The vector store was not initialized during migration. This was a known issue fixed in commit `500dbab3`.

**Solution:**
Run the embedding backfill worker (Step 4 above). This is normal and expected.

**Root cause (for developers):**
The migration code checks if `_vector_store` exists before attempting inline embedding:
```python
if _vector_store:
    try:
        _vector_store.add_texts([{"text": msg["content"], "meta": meta}])
    except Exception as e:
        logger.warning(f"Failed to embed imported message {mid}: {e}")
```

If `_vector_store` is `None`, embeddings are silently skipped. The fix ensures VectorStore is initialized before migration:
```python
if not _vector_store:
    from guardian.vector.store import VectorStore
    _vector_store = VectorStore()
    dependencies._vector_store = _vector_store
```

---

## Troubleshooting

### "LOCAL_EMBED_MODEL is not set"

**Error:**
```
RuntimeError: LOCAL_EMBED_MODEL is not set; cannot record embedding metadata.
```

**Solution:**
Set the environment variable to an absolute path:
```bash
export LOCAL_EMBED_MODEL=/models/bge-large-en-v1.5
```

Or add to `.env`:
```bash
LOCAL_EMBED_MODEL=/models/bge-large-en-v1.5
```

**Why absolute path?**
The embedding worker needs to record which model was used for each embedding. Relative paths are ambiguous (relative to what?). Absolute paths ensure consistency across containers and processes.

---

### "Database DSN not configured"

**Error:**
```
RuntimeError: Database DSN not configured. Set GUARDIAN_DATABASE_URL or DATABASE_URL.
```

**Solution:**
Set one of these environment variables:
```bash
export DATABASE_URL=postgresql://codexify:codexify@localhost:5433/Codexify
# or
export GUARDIAN_DATABASE_URL=$DATABASE_URL
```

**Precedence:**
The worker checks in this order:
1. `GUARDIAN_DATABASE_URL`
2. `DATABASE_URL`
3. `GUARDIAN_DB_URL`

---

### Backfill worker exits immediately

**Symptoms:**
```
INFO [backfill] starting embedding backfill worker
INFO [backfill] no more pending messages to embed, exiting
INFO [backfill] complete — embedded 0 messages
```

**What it means:**
All messages are already embedded. The worker is idempotent and exits when there's no work to do.

**Verification:**
Run a query to confirm embeddings exist:
```python
# For Chroma
collection = client.get_collection("chatgpt_messages")
print(collection.count())
```

---

### "HTTPException: Thread has no usable context"

See [Common Failure Mode #1](#1-thread-has-no-usable-context) above.

---

### Neo4j connection failed (CLI Path)

**Error:**
```
neo4j.exceptions.ServiceUnavailable: Could not connect to bolt://localhost:7687
```

**Solution:**

1. **Check if Neo4j is running:**
   ```bash
   docker compose ps neo4j
   ```

2. **Check credentials:**
   Default in `docker-compose.yml` is `neo4j/codexify`. Update CLI command:
   ```bash
   --neo4j-user neo4j --neo4j-pass codexify
   ```

3. **Check port binding:**
   ```bash
   docker compose logs neo4j | grep -i "bolt"
   ```

4. **Test connection manually:**
   ```bash
   docker compose exec neo4j cypher-shell -u neo4j -p codexify
   ```

---

### OpenAI API rate limit exceeded (CLI Path)

**Error during CLI migration:**
```
⚠️ OpenAI API Error: Rate limit exceeded
```

**Solution:**

1. **Reduce batch size:**
   ```bash
   --batch-size 5
   ```

2. **Skip embeddings and run backfill later:**
   ```bash
   --skip-embeddings
   ```

3. **Upgrade OpenAI tier** or **switch to local embeddings** (Path A).

---

### Empty messages skipped

**Log message:**
```
[chatgpt_migration] Skipped empty message node
```

**What it means:**
ChatGPT exports include metadata nodes without actual message content. These are automatically filtered out during import.

**This is normal and expected.** No action needed.

---

## Advanced Usage

### Dry Run Mode

Test the backfill worker without making changes:

```bash
EMBED_DRY_RUN=true python -m guardian.workers.embedding_backfill_worker
```

Output:
```
INFO [backfill][dry-run] Would add 32 embeddings to vector store
```

---

### Batch Size Tuning

Control how many messages are embedded per batch:

```bash
# Small batches (less memory, more API calls)
EMBED_BATCH_SIZE=8 python -m guardian.workers.embedding_backfill_worker

# Large batches (more memory, fewer API calls)
EMBED_BATCH_SIZE=128 python -m guardian.workers.embedding_backfill_worker
```

**Recommended:**
- Local embeddings (FAISS/Chroma): `32-64`
- OpenAI embeddings: `20` (rate limit consideration)

---

### Limit Total Batches

Process a fixed number of batches then exit:

```bash
EMBED_MAX_BATCHES=10 python -m guardian.workers.embedding_backfill_worker
```

Useful for:
- Testing without processing entire dataset
- Incremental migration in production
- Rate limit management

---

### Sleep Between Batches

Add delay to avoid overwhelming embedding backend:

```bash
EMBED_SLEEP_SECONDS=2 python -m guardian.workers.embedding_backfill_worker
```

---

## Reference

### Database Tables

**chat_threads:**
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `user_id` | TEXT | User ID (e.g., "me") |
| `title` | TEXT | Thread title |
| `summary` | TEXT | "Imported from ChatGPT" |
| `project_id` | INTEGER | Default: 1 (Loose Threads) |
| `created_at` | TIMESTAMP | Thread creation time |
| `updated_at` | TIMESTAMP | Last update time |

**chat_messages:**
| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT | Primary key |
| `thread_id` | INTEGER | FK to chat_threads |
| `role` | TEXT | 'user', 'assistant', 'system' |
| `content` | TEXT | Message text |
| `created_at` | TIMESTAMP | Message creation time |
| `embedded_at` | TIMESTAMP | Embedding timestamp (nullable) |
| `embedding_model` | TEXT | Model used (nullable) |
| `embedding_backend` | TEXT | Backend used (nullable) |
| `embedding_schema_version` | INTEGER | Schema version (nullable) |

**Note:** Embedding metadata fields (`embedded_at`, `embedding_model`, etc.) are defined in the schema but not yet populated by the current migration/backfill code. They're reserved for future use.

---

### Vector Store Metadata

**Chroma/FAISS metadata format:**
```python
{
    "message_id": 12345,           # ChatMessage.id
    "thread_id": 42,               # ChatThread.id
    "role": "user",                # Message role
    "created_at": "2025-01-05T12:00:00",  # ISO timestamp
    "source": "chatgpt_import",    # Import source
    "embed_schema_version": 1,     # Schema version
    "embedding_model": "/models/bge-large-en-v1.5"  # Model used
}
```

---

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | - | PostgreSQL connection string |
| `GUARDIAN_DATABASE_URL` | - | `$DATABASE_URL` | Alias for DATABASE_URL |
| `LOCAL_EMBED_MODEL` | ✅ | - | Absolute path to embedding model |
| `CODEXIFY_VECTOR_STORE` | - | `faiss` | Vector backend: `faiss` or `chroma` |
| `EMBED_BATCH_SIZE` | - | `32` | Messages per batch |
| `EMBED_MAX_BATCHES` | - | `0` (unlimited) | Max batches to process |
| `EMBED_SLEEP_SECONDS` | - | `0` | Sleep between batches |
| `EMBED_DRY_RUN` | - | `false` | Dry run mode (no writes) |
| `OPENAI_API_KEY` | - | - | OpenAI API key (if using cloud embeddings) |

---

### Migration Statistics

**Backend API Response:**
```json
{
  "threads_imported": 42,
  "messages_imported": 1337
}
```

**CLI Output (logs/migration_summary.json):**
```json
{
  "started_at": "2025-01-05T12:00:00",
  "completed_at": "2025-01-05T12:00:42",
  "file": "./conversations.json",
  "threads": 42,
  "messages": 1337,
  "relationships": 1295,
  "embeddings_successful": 1337,
  "embeddings_failed": 0,
  "elapsed_seconds": 42.0
}
```

**Backfill Worker Output:**
```
INFO [backfill] complete — embedded 1337 messages (dry_run=False)
```

---

## Summary

| Step | Command | Duration | Critical? |
|------|---------|----------|-----------|
| 1. Export from ChatGPT | Via web UI | 0-24 hours | ✅ Required |
| 2. Start database | `docker compose up -d db` | 10 seconds | ✅ Required |
| 3. Import conversations | `curl -X POST .../upload-chatgpt-export` | 1-5 minutes | ✅ Required |
| 4. Run backfill worker | `python -m guardian.workers.embedding_backfill_worker` | 5-30 minutes | ⚠️ Recommended |
| 5. Verify embeddings | Check vector store count | 10 seconds | ℹ️ Optional |

**Total time:** 10-60 minutes (depending on conversation volume)

**You're done!** Your ChatGPT history is now searchable in Guardian. Try chatting with a thread and notice how Guardian uses your historical context to inform responses.

---

## Related Documentation

- [Backend API Reference](../README.md#api-endpoints)
- [Vector Store Configuration](../guardian/vector/README.md)
- [Embedding Worker Architecture](../guardian/workers/README.md)
- [Database Schema Migrations](../guardian/db/migrations/README.md)
- [Original CLI Migration README](../scripts/chatgpt_import/README.md)
