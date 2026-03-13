# TASK-2026-02-16-003 Namespace Vector Retrieval Single User

## Task ID
- TASK-2026-02-16-003_namespace_vector_retrieval_single_user

## Goal
- Add namespace metadata and namespace-aware filtering for vector retrieval to prevent cross-context leakage in single-user mode.

## Files Touched
- `guardian/vector/store.py`
- `backend/rag/embedder.py`
- `guardian/context/broker.py`
- `guardian/memoryos/retriever.py`
- `guardian/routes/codexify_router.py`
- `guardian/retrieve/api.py`
- `guardian/workers/chat_worker.py`
- `guardian/workers/chat_embedding_worker.py`
- `guardian/workers/embedding_backfill_worker.py`
- `guardian/tests/test_vector_store_namespace.py`
- `guardian/tests/test_embedder_namespace.py`
- `guardian/tests/test_context_broker_integration.py`
- `guardian/tests/test_context_broker_memory.py`
- `tests/core/test_context_broker_depth.py`

## Tests Run
- `pytest -v guardian/tests/test_vector_store_namespace.py guardian/tests/test_embedder_namespace.py guardian/tests/test_context_broker_integration.py guardian/tests/test_context_broker_memory.py guardian/tests/context/test_broker_graph_context.py`
  - Result: `11 passed`
- `pytest -v tests/core/test_context_broker_depth.py`
  - Result: `39 passed`
- `pytest -v`
  - Result: `1 failed, 673 passed, 15 skipped, 33 xfailed, 11 xpassed`
  - Unrelated pre-existing failure outside touched scope:
    - `tests/integration/test_rag_integration_loop.py::test_rag_integration_memory_loop`
    - Failure context: environment/system prompt dependency issue (`db` hostname unresolved) causing missing RAG memory context in test harness.

## Notes/Risks
- Added namespace assignment at ingestion (`thread:<id>`, `project:<id>`, fallback `global`) in `VectorStore.add_texts`.
- Added namespace filtering in vector retrieval for FAISS and Chroma backends.
  - FAISS path performs full-index candidate scan when namespace filter is set, then filters and truncates to `k`.
  - Chroma path applies `where={"namespace": <value>}`.
- Added namespace propagation through retrieval services:
  - `ContextBroker` now scopes semantic + memory retrieval to `thread:<thread_id>`.
  - `MemoryOSRetriever.retrieve(...)` now accepts optional `namespace`.
- Added backward-compatible fallbacks when alternate vector stores/retrievers do not support namespace kwargs (TypeError fallback to legacy signature).

## Commit A (Code/Tests)
- `a30da6248d36cb4ec7e3ce78e2adfe33248f8626`

## Commit B (Docs/Mapping)
- `<pending>`
