# Obsidian Sync Recon

## Scope
Recon only for the Obsidian/local knowledge-source path. No activation or behavior changes. Evidence is grounded in repo inspection with explicit file paths and symbols. Runtime context is taken from the fresh `docker compose up --build --force-recreate` rebuild described in the task prompt.

## Fresh Runtime Context
- From the fresh rebuild context provided: frontend dev server up on `5173`, backend `/ping` repeatedly healthy, and TTS `/health` repeatedly healthy.
- From the same rebuild context: warmup reported a timeout against local model `qwen3.5:27b` at `http://100.109.4.57:11434/api/chat`. This is a model warmup signal only, not a knowledge-source readiness signal.
- No runtime signal was provided for Obsidian ingestion or connector sync; this report treats Obsidian readiness as unproven by runtime evidence.

## Existing Obsidian-Related Surfaces
- `guardian/cli/ingest_cli.py` — `ingest_obsidian`, `_parse_frontmatter`, `_yield_md_files`: CLI ingestion that walks a local directory for `.md` files, parses YAML frontmatter, and emits `{text, meta}` items with `path`, `tags`, and `title` to `VectorStore.add_texts`.
- `guardian/vector/store.py` — `VectorStore.add_texts`, `_metadata_namespace`, `Embedder.embed_and_index`: vector-store wrapper used by the Obsidian CLI that normalizes metadata namespaces and indexes into the configured embedding store.
- `backend/rag/embedder.py` — `LocalSemanticEmbedder.embed_and_index`, `Embedder`: embeds and stores text into FAISS or Chroma with default collection `codexify_vault`, which is the downstream store that the Obsidian CLI targets.
- `guardian/runtime/embed/embedder.py` — `CodexifyEmbedder`: runtime embedder for Chroma/FAISS using `CODEXIFY_CHROMA_PATH` and `CODEXIFY_COLLECTION`, aligning the runtime store configuration with the CLI ingest path.
- `docker-compose.yml` — `CODEXIFY_VECTOR_STORE`, `CODEXIFY_CHROMA_PATH`, `CODEXIFY_COLLECTION`: Compose wiring for workers shows the vector store configuration and persistent `./.chroma` path used by ingestion and retrieval.
- `guardian/memoryos/retriever.py` — `MemoryOSRetriever`: vector-store search is the core retrieval path for RAG context assembly. Inference: Obsidian vectors ingested via `VectorStore` would surface through this retriever.
- `guardian/routes/health.py` — `health_vector`: vector store add+search probe; this is the only built-in observability surface for vector store health.
- `guardian/db/models.py` — `ConnectorConfig`, `ConnectorRun`, `RawDocument`, `SyncJob`: connector and sync bookkeeping tables exist, but no Obsidian connector type is defined in code.
- `guardian/routes/connectors.py` — `CONNECTOR_REGISTRY`, `_connector_worker`, `_ingest_github_for_config`, `connector.sync` event emission: sync pipeline exists for GitHub only; no Obsidian connector registration or ingestion path is present.
- `config/supported_profiles/v1-local-core-web-mcp.yaml` — `route_posture.quarantined` includes `connectors`: the connectors routes are quarantined in the local-core profile.
- `frontend/src/features/settings/SettingsView.tsx` — connectors tab UI exists but is generic; it renders `ConnectorCard` entries supplied by `useConnectors`.
- `frontend/src/features/connectors/useConnectors.ts` — fetches `/api/connectors` (or `/connectors`) and subscribes to `connector.sync` events; no Obsidian-specific handling exists.
- `frontend/src/features/connectors/connectorLogos.ts` — only `github` is registered for connector branding.
- `docs/infra/ingestion.md` and `docs/tasks/TASK_2026_03_03_001_harden_obsidian_frontmatter.md` — documentation calls out `python -m guardian.cli.ingest_cli ingest-obsidian --dir /path/to/vault` as the supported manual ingestion path.

## Current Architectural Posture
Direct local vault access exists only as a one-shot CLI ingest that reads from the filesystem (`guardian/cli/ingest_cli.py:ingest_obsidian`) and pushes content into the vector store (`guardian/vector/store.py:VectorStore.add_texts`). Indexed retrieval from local files is present via the vector store and RAG retriever (`backend/rag/embedder.py:LocalSemanticEmbedder.embed_and_index`, `guardian/memoryos/retriever.py:MemoryOSRetriever`). Materialized sync or replicated note state is not present for Obsidian; there is no Obsidian connector type or sync workflow registered (`guardian/routes/connectors.py:CONNECTOR_REGISTRY`, `guardian/db/models.py:ConnectorConfig/ConnectorRun/RawDocument/SyncJob`). The codebase is closest to local vault as source of truth with a derived local vector index.

## Dormant Sync Table Assessment
The only sync-related tables in the repo are generic connector artifacts: `sync_jobs` (`guardian/db/models.py:SyncJob`, `sql/complete_schema.sql:sync_jobs`) plus `connector_configs`, `connector_runs`, and `raw_documents` (`guardian/db/models.py:ConnectorConfig/ConnectorRun/RawDocument`). These tables do not currently buy anything for a local-only first exposure because the Obsidian CLI ingest bypasses connectors and writes directly to the vector store. They are not required for indexing-only retrieval in the current codepath; ingestion and retrieval operate without them. They are most relevant for future lineage, change tracking, or multi-device workflows where you would want a durable sync ledger, run history, and raw note snapshots before transforming into memory entries or embeddings.

## Minimum Path To First Exposure
- Backend: expose a minimal API or worker entrypoint that calls `ingest_obsidian` (or a refactored equivalent service) so ingestion can run without manual CLI, and optionally record a lightweight run status in `sync_jobs` or `connector_runs` (`guardian/cli/ingest_cli.py:ingest_obsidian`, `guardian/db/models.py:SyncJob/ConnectorRun`).
- Frontend: add an Obsidian connector card or local-vault setup panel that collects a local vault path and triggers ingestion; the existing connectors UI can host this but currently only GitHub is surfaced (`frontend/src/features/settings/SettingsView.tsx`, `frontend/src/features/connectors/useConnectors.ts`, `frontend/src/features/connectors/connectorLogos.ts`).
- Config: unquarantine connectors or add a dedicated route for local vault ingestion in the supported profile (`config/supported_profiles/v1-local-core-web-mcp.yaml`) and define a config key for the vault path (e.g., env or DB config).
- Indexing flow: ensure ingestion writes a stable namespace or tag for Obsidian items so retrieval can filter or report source, and add idempotency/dedup logic keyed by file path + mtime or content hash (currently `ingest_obsidian` re-adds everything).
- Observability/status reporting: wire ingestion outcomes to `connector.sync` events or a new `obsidian.ingest` event, and surface results in UI and `/health/vector` telemetry (`guardian/routes/connectors.py:_emit_connector_event`, `guardian/routes/health.py:health_vector`).

## Risks And Unknowns
- Stack boot health is supported by the fresh rebuild context (`/ping` and `/health` successes), but that does not validate any Obsidian path or vector-store content. This is a runtime signal, not proof of ingestion readiness.
- Model warmup timed out against `qwen3.5:27b` per the rebuild context; this is a local inference readiness issue and not evidence of Obsidian ingest readiness.
- Obsidian readiness remains unproven: there is no runtime evidence of `ingest_obsidian` being executed, no Obsidian connector registration, and connectors are quarantined in the current supported profile (`guardian/cli/ingest_cli.py:ingest_obsidian`, `guardian/routes/connectors.py:CONNECTOR_REGISTRY`, `config/supported_profiles/v1-local-core-web-mcp.yaml`).
- The repo suggests a local ingestion path exists, but there is no confirmed runtime proof of retrieval behavior for Obsidian-derived vectors; the health probe only checks add+search mechanics, not content (`guardian/routes/health.py:health_vector`).

## Recommendation
Choose “local vault as source of truth + derived local index.” It has the smallest blast radius because it reuses the existing CLI ingest and vector store without introducing new sync semantics, and it maximizes implementation leverage by aligning with the current RAG retriever (`guardian/cli/ingest_cli.py:ingest_obsidian`, `guardian/vector/store.py:VectorStore.add_texts`, `guardian/memoryos/retriever.py:MemoryOSRetriever`). It is also the most beta-honest: no claim of multi-device sync or replicated note state, just local indexing and retrieval. The sync tables can be revisited later if a multi-device or lineage-tracked workflow is explicitly required.
