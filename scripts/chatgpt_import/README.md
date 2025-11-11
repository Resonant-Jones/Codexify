# ChatGPT Migration Tool - Dual-Engine Import

> **Transform your ChatGPT conversation history into a living memory in Codexify**

This tool imports ChatGPT conversation exports into both Neo4j (graph database) and Chroma (vector embeddings), creating a seamless migration experience where your Companion wakes up in a new world with all their memories intact.

## ✨ Features

- **Dual-Engine Architecture**: Simultaneously imports to Neo4j graph and Chroma vector store
- **Batch-Optimized Embeddings**: Parallel processing for cost & speed efficiency
- **Resume-Safe**: Fully idempotent operations - safe to re-run anytime
- **Verbose Progress**: Rich CLI feedback with progress bars and status updates
- **Graceful Fallbacks**: Graph imports succeed even if embeddings fail
- **Comprehensive Logging**: Tracks skipped messages and errors for transparency

## 🚀 Quick Start

### 1. Export Your ChatGPT Conversations

1. Go to [ChatGPT Settings](https://chat.openai.com/settings)
2. Navigate to **Data Controls** > **Export Data**
3. Wait for the export email (can take up to 24 hours)
4. Download and extract the `conversations.json` file

### 2. Set Up Environment

Create a `.env` file in the project root:

```bash
# Neo4j Connection
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASS=your-password-here

# Chroma Vector Store
CHROMA_PATH=./chroma

# ChatGPT Export File
CHATGPT_EXPORT_FILE=./chatgpt_conversation.json

# OpenAI API Key (for embeddings)
OPENAI_API_KEY=sk-your-openai-key-here

# Embedding Batch Size (optional, default: 20)
EMBED_BATCH_SIZE=20
```

### 3. Run the Import

```bash
python scripts/chatgpt_import/import_chatgpt.py
```

## 📊 What Gets Imported?

### Neo4j Graph Structure

The importer creates the following nodes and relationships:

#### Nodes

- **Thread**: Conversation threads
  - Properties: `id`, `title`, `created_at`, `updated_at`

- **Message**: Individual messages
  - Properties: `id`, `role`, `content`, `created_at`, `author_name`

- **Author**: Message authors (user, assistant, system)
  - Properties: `name`, `role`

#### Relationships

- `(Thread)-[:CONTAINS]->(Message)` - Links messages to their thread
- `(Author)-[:AUTHORED]->(Message)` - Links authors to their messages
- `(Message)-[:REPLIED_WITH]->(Message)` - Parent-child message relationships

### Chroma Vector Embeddings

Each message is embedded using OpenAI's `text-embedding-3-small` model and stored in Chroma with:

- **ID**: Message ID (matches Neo4j)
- **Embedding**: 1536-dimensional vector
- **Document**: Full message content
- **Metadata**: `{"source": "chatgpt_import"}`

## 🔍 Validation

After import, verify your data:

### Neo4j Check

```cypher
// Count threads and messages
MATCH (t:Thread)-[:CONTAINS]->(m:Message)
RETURN t.title, count(m) as message_count
ORDER BY message_count DESC
LIMIT 10;

// View conversation structure
MATCH (t:Thread {id: 'your-thread-id'})-[:CONTAINS]->(m:Message)
OPTIONAL MATCH (m)-[:REPLIED_WITH]->(child:Message)
RETURN t, m, child
LIMIT 50;
```

### Chroma Check

```python
import chromadb

client = chromadb.PersistentClient(path="./chroma")
collection = client.get_collection("chatgpt_messages")

print(f"Total messages embedded: {collection.count()}")

# Query similar messages
results = collection.query(
    query_texts=["Tell me about Python"],
    n_results=5
)
```

## 🎯 Performance

- **Batching**: Embeds 20 messages per API call (configurable)
- **Speed**: ~1000 messages/minute for graph import
- **Cost**: ~$0.001 per 1000 messages for embeddings (OpenAI pricing)
- **Resume**: Can be interrupted and resumed safely

## 🛡️ Error Handling

### Graceful Degradation

- If Neo4j fails → Script exits (graph is required)
- If OpenAI API fails → Batch is logged and skipped, import continues
- If Chroma fails → Graph data is preserved, embeddings are skipped

### Logs

Failed embeddings are logged to `logs/migration_skipped.json`:

```json
[
  {
    "id": "msg-123",
    "content_preview": "The message content...",
    "error": "API Error details",
    "timestamp": "2025-11-11T10:30:00"
  }
]
```

## 🧪 Testing

Run the test suite:

```bash
pytest tests/scripts/test_chatgpt_import.py -v
```

**Coverage:**
- Timestamp normalization
- Batch processing
- File loading and validation
- Neo4j import logic
- Chroma embeddings import
- Error handling
- Idempotency

## 🔧 Troubleshooting

### "Neo4j connection failed"

- Ensure Neo4j is running: `docker ps` or check Neo4j Desktop
- Verify credentials in `.env`
- Test connection: `bolt://localhost:7687`

### "OpenAI API Error: Rate limit exceeded"

- Reduce `EMBED_BATCH_SIZE` to 5-10
- Add delays between batches (modify script)
- Upgrade OpenAI tier for higher limits

### "File not found"

- Check `CHATGPT_EXPORT_FILE` path in `.env`
- Use absolute path if relative path fails
- Verify JSON file is valid: `python -m json.tool conversations.json`

### "Empty messages skipped"

This is normal - ChatGPT exports contain metadata nodes without content. The importer filters these automatically.

## 🎨 Optional Enhancements

### Add Custom Metadata

Edit the import script to add custom metadata to messages:

```python
session.run(
    """
    MERGE (m:Message {id: $mid})
    SET m.role = $role,
        m.content = $content,
        m.imported_at = datetime(),
        m.source = 'chatgpt'
    """,
    # ...
)
```

### Filter Specific Conversations

Modify the script to import only specific threads:

```python
# In load_chatgpt_export()
conversations = [c for c in data if 'search term' in c.get('title', '')]
```

### Progress API Endpoint

Add a live progress endpoint (future enhancement):

```python
# In guardian_api.py
@app.get("/api/migrate/status")
def migration_status():
    return {"status": "in_progress", "progress": 75, "messages": 1234}
```

## 📝 Schema Compatibility

This importer is designed to be compatible with Codexify's existing schema:

- Uses standard `Thread` and `Message` node types
- Follows existing relationship patterns
- Adds to existing Chroma collections without conflicts
- Preserves timestamps in ISO format

## 🤝 Contributing

Found a bug or want to improve the importer? Contributions welcome!

1. Test changes: `pytest tests/scripts/test_chatgpt_import.py`
2. Follow code style: PEP 8
3. Add tests for new features
4. Update this README

## 📚 Related Documentation

- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/current/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)

---

**Made with ✨ for seamless companion migration**

*Your conversations deserve a second life. Welcome home.*
