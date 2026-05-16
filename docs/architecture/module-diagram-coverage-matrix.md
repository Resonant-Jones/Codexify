Purpose: Track which high-coupling runtime modules require module-level diagrams, why they require them, and what diagram work remains.
Last updated: 2026-05-11
Source anchors:
- docs/architecture/modules-and-ownership.md
- docs/architecture/flows.md
- docs/architecture/runtime-diagrams-v1.md
- docs/architecture/system-overview.md

# Module Diagram Coverage Matrix

Diagram Review Marker: 2026-05-11

## Scope

- First pass targets high-coupling runtime modules only.
- Baseline runtime/global diagrams are canonical and remain in place:
  - `runtime-diagrams-v1.md`
  - `flows.md`
  - `modules-and-ownership.md`

## Coverage Matrix

| Module | Blast Radius | Current Diagram Coverage | Diagram Needed | Required Diagram Type | Owner/Reviewer | Status | Last Reviewed |
|---|---|---|---|---|---|---|---|
| Chat completion lane (`routes/chat.py`, `chat_completion_service.py`, `workers/chat_worker.py`) | high | Global runtime topology and sequence coverage exists; module-level failure branch ownership view is partial | yes | Context Map, Primary Sequence, State/Data Boundary | Core loop cluster reviewer | planned | 2026-05-11 |
| Context and retrieval broker (`context/broker.py`, `memoryos/retriever.py`) | high | Covered in critical flows at system level; module-level trust-boundary map is partial | yes | Context Map, Primary Sequence, State/Data Boundary | Core loop cluster reviewer | planned | 2026-05-11 |
| Media/document ingestion and embedding (`routes/media.py`, `routes/documents.py`, `workers/document_embed_worker.py`) | high | Global ingestion sequence exists; per-module retry/backpressure visibility is partial | yes | Context Map, Primary Sequence, State/Data Boundary | Retrieval and ingestion cluster reviewer | planned | 2026-05-11 |
| Command bus execution surface (`routes/command_bus.py`, `command_bus/`) | high | Global ownership and flow mention exists; module-level policy/idempotency boundary map is partial | yes | Context Map, Primary Sequence, State/Data Boundary | Platform and control-plane cluster reviewer | planned | 2026-05-11 |
| Queue and task transport (`queue/redis_queue.py`, `queue/task_events.py`) | high | Runtime topology shows queue role; module-level lifecycle visibility and failure branch mapping is partial | yes | Context Map, Primary Sequence, State/Data Boundary | Platform and control-plane cluster reviewer | planned | 2026-05-11 |
| Persistence boundary (`db/models.py`, `core/db.py`, migrations) | high | Data/storage boundary exists globally; module-level source-of-truth and consistency contract view is partial | yes | Context Map, Primary Sequence, State/Data Boundary | Platform and control-plane cluster reviewer | planned | 2026-05-11 |

## Status Values

- `planned`: Diagram set is required but not yet added at module level.
- `in_progress`: Diagram work exists and is under active review.
- `done`: Diagram set exists and metadata is current.
- `deferred`: Intentionally postponed with rationale documented.

## Maintenance Rule

- Any new `high` blast-radius module entry must have an explicit `Diagram Needed` value of `yes` or `no`.
- If runtime source docs change materially, update this matrix (or `diagram-governance.md`) review marker.
