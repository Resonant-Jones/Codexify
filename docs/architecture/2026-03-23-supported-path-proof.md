# Supported Path Proof — 2026-03-23

## Environment
- Date: 2026-03-23
- Branch: `codex/supported-path-proof`
- Commit: `fae5c992b3b851e0b08c14ccef3eaed14f11e462`
- Runtime: local Docker Compose (backend, frontend, workers, db, redis, neo4j)
- Auth: `X-API-Key` header using container `GUARDIAN_API_KEY` (value redacted)
- Note: host-level `curl http://localhost:8888/*` was not reachable from this sandbox; all route probes were executed inside the backend container.

## Startup
**Commands executed**
- `docker compose up --build -d`
- `docker compose ps`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=120 frontend`

**Result**
- Backend container reported healthy and serving on `0.0.0.0:8888`.
- Frontend container started Vite dev server on `http://localhost:5173` (inside container) and `http://172.18.0.12:5173` (network).
- Frontend container reached backend via `http://backend:8888/ping` (HTTP 200).

## Core Runtime Surfaces
All requests made from inside `codexify-backend-1` using `requests` and `X-API-Key`.

| Route | Status | Evidence |
| --- | --- | --- |
| `/ping` | 200 | `{"status":"Guardian awake!"}` |
| `/projects` | 200 | Default project `General` returned |
| `/api/llm/catalog` | 200 | Catalog payload returned (initial 3s timeout; success at 10s) |
| `/api/events` | 200 | SSE connection accepted (no body read) |
| `/api/health` | 404 | `{"detail":"Not Found"}` |
| `/api/health/chat` | 404 | `{"detail":"Not Found"}` |
| `/api/health/llm` | 200 | Provider health payload returned |

## Chat Path
**Thread list**
- `GET /api/chat/threads` -> 200

**Create thread**
- `POST /api/chat/threads` -> 200
- Thread id: `1`

**User message**
- `POST /api/chat/1/messages` -> 200

**Completion**
- `POST /api/chat/1/complete` -> 200
- `acceptance_status=accepted`, `task_id=2ed6bca9-5113-4259-a33f-ddf40348c47a`
- Assistant reply returned via `GET /api/chat/1/messages`

**Banner behavior**
- `/api/health` and `/api/health/chat` return 404 while `/api/health/llm` returns 200. Runtime-health policy should classify this as `health_endpoint_missing` and suppress the degraded banner.
- Banner was not visually validated in a browser due to sandbox host-port restrictions.

## Document Path
**Upload**
- `POST /api/media/upload/document` -> 200
- Document id: `999ef9a5-21cc-43f0-bc91-7a079b9cdcaa`
- Initial `embedding_status=pending`

**Embedding lifecycle**
- `GET /api/media/documents?thread_id=1` -> `embedding_status=ready`
- `embedding_completed_at=2026-03-23T21:43:47.213854+00:00`

**Visibility**
- Document listed in `/api/media/documents` with signed `src_url` and embedding metadata.

## Retrieval Path
- `GET /api/chat/debug/rag-trace/1/latest` -> 200
- Trace response shows `documents: []` and `retrieval_mode: null` (no retrieval evidence for this run).

## Pass/Fail Summary
| Segment | Result | Notes |
| --- | --- | --- |
| Startup | PASS | Compose stack rebuilt and services healthy |
| Core runtime surfaces | PASS (with caveats) | `/api/health` and `/api/health/chat` 404; `/api/llm/catalog` required longer timeout |
| Chat path | PASS | Thread list, create, message, completion successful |
| Document path | PASS | Upload succeeded; embedding reached `ready` |
| Retrieval path | PARTIAL | Trace endpoint responded but no retrieved documents |

## Known Caveats
- Host-level `curl` to `http://localhost:8888` failed in this sandbox; all HTTP probes executed inside the backend container.
- `/api/health` and `/api/health/chat` return 404 (expected caveat); `/api/health/llm` returns 200.
- `/api/llm/catalog` timed out at 3 seconds; succeeded with a 10-second timeout.
- Retrieval trace returned no documents for this run; retrieval not demonstrated.
- Degraded banner suppression inferred from runtime-health policy; not visually confirmed in a browser.

## Final Conclusion
**Supported path partially proven.** Core runtime, chat, and document/embed paths are functional; retrieval was not demonstrated and UI banner behavior was not visually validated due to host sandbox constraints.
