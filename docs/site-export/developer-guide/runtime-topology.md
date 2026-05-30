# Runtime Topology

This page summarizes the implemented runtime components on the supported local path.
It is a topology map, not a deployment promise beyond the supported Compose stack.

## Implemented Components

- React frontend for the browser UI and desktop shell rendering.
- FastAPI backend for HTTP routes, SSE surfaces, and startup orchestration.
- Postgres as the primary system of record.
- Redis for queues, locks, task events, and other coordination state.
- Worker processes for chat, embeddings, and scheduled or background execution.
- Vector store for semantic retrieval.
- Optional Neo4j for graph-enrichment and graph-related features.
- Desktop shell as an optional client shell, not a replacement for the supported local runtime path.

## Supported Path

The supported runtime path remains local Docker Compose.
That path is the truth surface for release posture and operational interpretation.

Other packaging or shell options may exist, but they do not widen the supported runtime promise on their own.

## Topology Notes

- The frontend talks to the backend over local runtime URLs and browser/session state.
- The backend coordinates queue-backed work and persists state to Postgres.
- Workers execute the queued work and write results back through the same durable stores.
- Retrieval, ingestion, and optional graph context are all layered on top of the same core runtime spine.

## Trust Boundaries

- Client to backend is an application trust boundary.
- Backend to providers is a provider-runtime boundary.
- Backend to storage backends is a persistence boundary.
- Backend to peers is a federation or sync boundary, where enabled.

This topology is built for bounded local-first operation first, not for ambient network expansion.
