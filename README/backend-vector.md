# Backend Vector Store Options

The backend now supports pluggable vector stores. The default backend remains **pgvector** so existing PostgreSQL installations continue to work without additional configuration.

## Selecting a backend

1. Ensure the required dependencies are installed:
   - `pgvector` Python package and the Postgres `vector` extension for the pgvector backend.
   - `chromadb` Python package for the Chroma backend (already listed in requirements).
2. Set the `VECTOR_STORE` environment variable before launching the backend:

   ```bash
   # Use pgvector (default)
   export VECTOR_STORE=pgvector

   # Or switch to Chroma
   export VECTOR_STORE=chroma
   export CHROMA_PERSIST_DIRECTORY=./data/chroma  # optional persistence override
   ```
3. Restart the backend service so the change takes effect.

The active backend can also be managed through `.env` by adding `VECTOR_STORE=pgvector` (or `chroma`).

## Postgres prerequisites

Make sure the `vector` extension is enabled in your database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

The backend will attempt to create the required `embeddings` table automatically if it does not exist.

## Migrating from pgvector to Chroma

A helper script, `scripts/migrate_pgvector_to_chroma.py`, performs a one-shot export from the existing `embeddings` table into Chroma collections. Before running it:

- **Always create a fresh backup of your Postgres database.** The script is read-only for Postgres, but backing up ensures you can recover from unexpected issues.
- Provision a persistent directory for Chroma if you want the data to survive restarts (via `CHROMA_PERSIST_DIRECTORY`).

Run the migration manually once you are ready:

```bash
poetry run python scripts/migrate_pgvector_to_chroma.py \
  --database-url "$DATABASE_URL" \
  --chroma-directory ./data/chroma
```

The script prints progress, the total number of embeddings copied, and any errors encountered. After verifying the import, update your `.env` or deployment configuration to set `VECTOR_STORE=chroma` and restart the backend.
