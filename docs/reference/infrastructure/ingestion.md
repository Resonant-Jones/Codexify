# Ingestion Guide

## What this wires up
- **Sync**: `/api/sync/event`, `/api/sync/subscribe`, `/health/sync`
- **Retrieval**: `/api/retrieve`, `/health/vector`
- **Vector store**: local SQLite index at `${GUARDIAN_INDEX_DIR:-guardian_index}/index.sqlite`

## Env knobs

GUARDIAN_INDEX_DIR=guardian_index
EMBEDDING_BACKEND=stub   # or ‘local’ if you have sentence-transformers cached
EMBEDDING_DIM=128

EMBEDDING_MODEL=all-MiniLM-L6-v2

## Obsidian markdown
```bash
python -m guardian.cli.ingest_cli ingest-obsidian --dir /path/to/your/vault
```
- Parses minimal YAML frontmatter (title, tags).
- Stores `{text, meta:{path,tags,title}}` into the vector store.

## Conversation chunks (JSON list)
```bash
python -m guardian.cli.ingest_cli ingest-conversations --dir /path/to/jsons
```
- Expects items with `{message, role, ts, thread}`.
- Stores `{text, meta:{role,ts,thread,path}}`.

## Quick smoke

```bash
# Start app however you do locally (uvicorn etc.)
curl -s localhost:8000/health/vector
curl -s -X POST localhost:8000/api/retrieve -H 'content-type: application/json' \
  -d '{"q":"orchestration","k":2}'
```

## Notes
- Defaults are offline-safe. Switch `EMBEDDING_BACKEND=local` only on a machine with the model cached.
- Index is append-only; re-ingest is fine.

## Unified Media Identity (UIIAL)
- Every ingested media artifact gets a canonical `media_assets` record.
- Identity is orthogonal:
  - `media_kind`: `document | image | audio | video | other`
  - `provenance`: `uploaded | generated | imported | system`
- Generated images are represented as `media_kind=image` + `provenance=generated`.
- Deterministic naming contract:
  - `deterministic_id = YYYYMMDD-hash8`
  - `system_name = <deterministic_id>--<normalized_slug>.<ext?>`
  - Storage path is `MEDIA_STORAGE_PREFIX[(media_kind, provenance)] + system_name`.
- Human labels are preserved in `media_aliases` and never discarded.
- `/api/media/upload/document`, `/api/media/upload/image`, and `/api/media/generate/image` all write canonical asset identities and link origin rows via `asset_id`.
- `/api/media/resolve` resolves user-facing names/prompts/aliases to canonical asset identity.
