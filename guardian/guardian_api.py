"""
guardian_api module
~~~~~~~~~~~~~~~~~~~

Minimal FastAPI application wiring layer for the Guardian backend.

This module is responsible for:
- Creating the FastAPI app instance
- Loading environment configuration
- Initializing database and shared services
- Configuring middleware (CORS, static files)
- Including routers from guardian/routes/
- Wiring startup/shutdown hooks
- Providing a few unique endpoints that don't belong in specific routers

All route logic has been moved to appropriate router modules in guardian/routes/.
Shared dependencies (auth, DB, AI completion) are in guardian/core/dependencies.py.
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional
from uuid import uuid4

from fastapi import (
    Body,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

# Configure logging early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import core dependencies module (contains shared helpers)
from guardian.core import dependencies, event_bus, metrics
from guardian.core.config import (
    ConfigCoherenceError,
    assert_config_coherence,
    get_settings,
)
from guardian.core.db import load_guardian_db_from_env
from guardian.core.dependencies import (
    ENABLE_CONNECTOR_WORKER,
    ENABLE_OUTBOX,
    allowed_origins,
    init_database,
    init_services,
    require_api_key,
)
from guardian.core.media_signing import verify_media_signature
from guardian.core.outbox import (
    normalize_outbox_tenant_id,
    parse_last_event_id,
    parse_outbox_batch_size,
    parse_outbox_poll_interval,
)
from guardian.core.public_exposure import (
    DEFAULT_EXPOSURE_MODE,
    DEFAULT_PROFILE,
    DEFAULT_ROUTES_FILE,
    PublicExposureMiddleware,
)
from guardian.core.storage import ensure_storage_base_path
from guardian.queue import task_events
from guardian.queue.redis_queue import enqueue
from guardian.tasks.types import WarmupTask

# Optional Neo4j for graph endpoint
try:
    from neo4j import GraphDatabase

    NEO4J_AVAILABLE = True
except Exception:
    NEO4J_AVAILABLE = False
    logger.warning("[graph] Neo4j driver not available")

try:
    from guardian.graph.connection import connect_neo4j

    _NEO_CONNECT_AVAILABLE = True
except Exception:
    _NEO_CONNECT_AVAILABLE = False

# Optional RAG modules (removed unused imports)


# =========================
# Environment & Config Loading
# =========================

# Load environment files
dependencies._load_env_chain()

# Resolve API key after dotenv load (no silent fallback)
api_key = (os.getenv("GUARDIAN_API_KEY") or "").strip()
dependencies.API_KEY = api_key
if not api_key:
    logger.error(
        "[auth] GUARDIAN_API_KEY is missing. Set it in .env to start the backend."
    )
    raise SystemExit("GUARDIAN_API_KEY is required")

# Log API key (masked)
_mask = (
    (api_key[:4] + "…" + api_key[-4:])
    if api_key and len(api_key) > 8
    else api_key
)
logger.info("[auth] Using GUARDIAN_API_KEY=%s", _mask)

# Initialize primary chat database eagerly so router modules
# can safely import `chatlog_db` from core.dependencies.
dependencies.init_database()
chatlog_db = dependencies.chatlog_db

# Feature flags
OUTBOX_POLL_INTERVAL = parse_outbox_poll_interval(
    os.getenv("OUTBOX_POLL_INTERVAL", "1.0")
)
OUTBOX_BATCH_SIZE = parse_outbox_batch_size(
    os.getenv("OUTBOX_BATCH_SIZE", "100")
)
OUTBOX_TENANT_ID = normalize_outbox_tenant_id(
    os.getenv("OUTBOX_TENANT_ID", "default")
)


from guardian.realtime import collaboration

# Import all routers (after DB init so dependencies.chatlog_db is ready)
from guardian.routes import admin, agent, agent_orchestration, backfill
from guardian.routes import cron as cron_routes
from guardian.routes import (
    devtools,
    documents,
    embeddings,
    federation,
    health,
    memory,
    migration,
)
from guardian.routes import neo as neo_routes
from guardian.routes import research, share, threads, ui_session
from guardian.routes import websocket as websocket_routes
from guardian.routes.api_exports import router as exports_router
from guardian.routes.chat import api_chat_router
from guardian.routes.chat import router as chat_router
from guardian.routes.chat import simple_chat_router
from guardian.routes.codex import router as codex_router
from guardian.routes.codexify_router import router as codexify_router
from guardian.routes.connectors import _connector_worker
from guardian.routes.connectors import router as connectors_router
from guardian.routes.flows import router as flows_router
from guardian.routes.iddb import router as iddb_router
from guardian.routes.imprint import router as imprint_router
from guardian.routes.imprint import system_docs_router, system_prompt_router
from guardian.routes.media import router as media_router
from guardian.routes.memory import EPHEMERAL_MEMORY  # re-export for tests
from guardian.routes.personal_facts import router as personal_facts_router
from guardian.routes.projects import api_router as api_projects_router
from guardian.routes.projects import ensure_loose_threads_project
from guardian.routes.projects import router as projects_router
from guardian.routes.tools import api_router as api_tools_router
from guardian.routes.tools import router as tools_router

# =========================
# Application Lifespan Management
# =========================

# Global connector worker state
_CONNECTOR_WORKER_STOP: Optional[asyncio.Event] = None
_CONNECTOR_WORKER_TASK: Optional[asyncio.Task] = None


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Handles startup and shutdown logic.
    """
    global _CONNECTOR_WORKER_STOP, _CONNECTOR_WORKER_TASK

    # === STARTUP ===
    logger.info("[startup] Guardian API starting...")

    settings = get_settings()
    try:
        assert_config_coherence(settings)
    except ConfigCoherenceError as exc:
        logger.error("[startup] Config coherence check failed: %s", exc)
        raise

    if getattr(settings, "GUARDIAN_ENABLE_GRAPH_CONTEXT", False):
        logger.info("[graph] Knowledge graph context: ENABLED (Neo4j)")
    else:
        logger.info("[graph] Knowledge graph context: disabled")

    # Initialize database via shared initializer (idempotent)
    db = dependencies.init_database()

    # Initialize shared services (vector store, sensors)
    init_services(db)

    # Initialize Prometheus metrics
    metrics.set_db_backend(dependencies.DB_BACKEND)
    logger.info(
        "[metrics] Prometheus metrics initialized (db_backend=%s)",
        dependencies.DB_BACKEND,
    )

    # Bind memory route dependencies
    memory.bind_dependencies(
        chatlog_db_instance=db, require_api_key_func=require_api_key
    )

    guardian_db = None
    try:
        guardian_db = load_guardian_db_from_env()
    except Exception as exc:
        logger.warning("[startup] GuardianDB init failed: %s", exc)
    if guardian_db:
        cron_routes.configure_db(guardian_db)
        documents.configure_db(guardian_db)
        share.configure_db(guardian_db)
        websocket_routes.configure_db(guardian_db)
        agent_orchestration.configure_db(guardian_db)
        logger.info(
            "[startup] GuardianDB configured for cron/documents/share/websocket/agent_orchestration routes"
        )
        collaboration.configure_db(guardian_db)
        logger.info(
            "[startup] GuardianDB configured for cron/documents/share/collaboration/websocket routes"
        )

    # Configure durable outbox storage
    if ENABLE_OUTBOX:
        try:
            event_bus.configure_event_store(db)
            logger.info("[outbox] Durable event outbox enabled")
        except Exception:
            logger.exception(
                "[outbox] Failed to configure durable event outbox; falling back to in-memory hub"
            )

    # Ensure default "Loose Threads" project exists
    try:
        ensure_loose_threads_project()
    except Exception as exc:
        logger.error(
            "[startup] Failed to initialize Loose Threads project: %s", exc
        )

    # Ensure sync_jobs table exists
    try:
        db.ensure_sync_job_support()
    except Exception as e:
        logger.warning("[sync] Failed to ensure sync_jobs table: %s", e)

    # Seed/sync provider control-plane rows from /api/llm/catalog
    try:
        sync_stats = db.sync_inference_provider_rows_from_catalog()
        logger.info(
            "[startup] inference providers synced rows=%s created=%s updated=%s runtime_created=%s",
            sync_stats.get("provider_rows", 0),
            sync_stats.get("providers_created", 0),
            sync_stats.get("providers_updated", 0),
            sync_stats.get("runtime_created", 0),
        )
    except Exception as exc:
        logger.warning(
            "[startup] Failed to sync inference provider rows: %s", exc
        )

    # Initialize Neo4j connection if graph logging is enabled
    if (
        getattr(settings, "GUARDIAN_ENABLE_GRAPH_LOGGING", False)
        and _NEO_CONNECT_AVAILABLE
    ):
        try:
            connect_neo4j()
            logger.info("[graph] Neo4j connection initialized")
        except Exception as exc:
            logger.warning("[graph] Neo4j connection failed: %s", exc)

    # Optionally launch connector worker
    if ENABLE_CONNECTOR_WORKER:
        try:
            # Validate DB tables exist before launching worker
            db.list_connector_configs()
            stop_event = asyncio.Event()
            _CONNECTOR_WORKER_STOP = stop_event
            _CONNECTOR_WORKER_TASK = asyncio.create_task(
                _connector_worker(stop_event)
            )
            logger.info("[connectors] Background worker started")
        except Exception as exc:
            logger.error(
                "[connectors] Unable to initialize connector tables: %s", exc
            )

    # Enqueue warm-up task for local models (fire-and-forget)
    try:
        local_llm_model = os.getenv("LOCAL_LLM_MODEL") or getattr(
            settings, "LOCAL_LLM_MODEL", None
        )
        local_embed_model = os.getenv("LOCAL_EMBED_MODEL")

        def _norm_model(name: Optional[str]) -> str:
            return str(name or "").strip().lower()

        embed_models = {_norm_model(local_embed_model)}
        embed_models.discard("")

        models = []
        seen = set()
        for candidate in (local_llm_model, local_embed_model):
            norm = _norm_model(candidate)
            if not norm:
                continue
            if norm in embed_models:
                logger.info(
                    "[startup] skipping embedding-only warmup model=%s",
                    candidate,
                )
                continue
            if norm in seen:
                continue
            seen.add(norm)
            models.append(candidate)
        if models:
            task = WarmupTask(
                models=list(dict.fromkeys(models)), origin="startup"
            )
            enqueue(task, "codexify:queue:system")
            try:
                task_events.publish(
                    task.task_id,
                    "task.created",
                    {"type": task.type, "origin": task.origin},
                )
            except Exception:
                logger.debug("[startup] warmup task.created emit failed")
            logger.info(
                "[task] created type=%s id=%s origin=%s",
                task.type,
                task.task_id,
                task.origin,
            )
    except Exception as exc:
        logger.warning("[startup] warmup enqueue failed: %s", exc)

    logger.info("[startup] Guardian API ready")

    yield

    # === SHUTDOWN ===
    logger.info("[shutdown] Guardian API shutting down...")

    # Stop connector worker if running
    if _CONNECTOR_WORKER_STOP is not None:
        _CONNECTOR_WORKER_STOP.set()
    if _CONNECTOR_WORKER_TASK is not None:
        _CONNECTOR_WORKER_TASK.cancel()
        try:
            await _CONNECTOR_WORKER_TASK
        except asyncio.CancelledError:
            pass

    logger.info("[shutdown] Guardian API stopped")


# =========================
# FastAPI App Creation
# =========================

app = FastAPI(
    title="Guardian Codex API",
    description="Unified API for chat, memory, connectors, and tools",
    version="1.0.0",
    lifespan=app_lifespan,
)

exposure_mode = os.getenv("GUARDIAN_EXPOSURE_MODE", DEFAULT_EXPOSURE_MODE)
public_routes_file = os.getenv(
    "GUARDIAN_PUBLIC_ROUTES_FILE", DEFAULT_ROUTES_FILE
)
public_profile = os.getenv("GUARDIAN_PUBLIC_PROFILE", DEFAULT_PROFILE)

app.add_middleware(
    PublicExposureMiddleware,
    exposure_mode=exposure_mode,
    routes_file=public_routes_file,
    profile=public_profile,
)
logger.info(
    "[public_exposure] mode=%s profile=%s routes_file=%s",
    exposure_mode,
    public_profile,
    public_routes_file,
)


def _get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        return request_id
    header_id = request.headers.get("X-Request-ID")
    if header_id:
        request.state.request_id = header_id
        return header_id
    request_id = str(uuid4())
    request.state.request_id = request_id
    return request_id


# =========================
# Middleware Configuration
# =========================


# Request-id middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = _get_request_id(request)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = _get_request_id(request)
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": request_id},
        headers=getattr(exc, "headers", None),
    )
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = _get_request_id(request)
    logger.exception(
        "[error] Unhandled exception request_id=%s method=%s path=%s query_params=%s",
        request_id,
        request.method,
        request.url.path,
        dict(request.query_params),
    )
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "request_id": request_id},
    )
    response.headers["X-Request-ID"] = request_id
    return response


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("[CORS] Allowed origins: %s", allowed_origins)

# Signed media serving base path
media_storage_path = ensure_storage_base_path().resolve()
logger.info("[media] Signed media delivery enabled from %s", media_storage_path)


# =========================
# Router Inclusion
# =========================

# Health endpoints (no prefix to preserve /health/chat paths)
app.include_router(health.router)

# Admin endpoints (auth, session, config debugging)
app.include_router(admin.router)

# Neo graph logging (safe stub; exposed under /api/neo/…)
app.include_router(neo_routes.router, prefix="/api")

# Chat endpoints (includes /chat/*, /api/chat/*, and simple chat endpoints)
app.include_router(chat_router)
app.include_router(simple_chat_router)
app.include_router(api_chat_router)
app.include_router(imprint_router)
app.include_router(system_prompt_router)
app.include_router(system_docs_router)
app.include_router(iddb_router)
app.include_router(backfill.router)
app.include_router(embeddings.router)

# Core feature routers
app.include_router(threads.router)
app.include_router(projects_router)
app.include_router(api_projects_router)
app.include_router(memory.router)
app.include_router(personal_facts_router)
app.include_router(agent.router, prefix="/agent")
app.include_router(research.router, prefix="/research")
app.include_router(documents.router)
app.include_router(share.router)
app.include_router(federation.router)
app.include_router(collaboration.router)
app.include_router(connectors_router)
app.include_router(media_router, prefix="/api/media")
app.include_router(flows_router)
app.include_router(tools_router)
app.include_router(api_tools_router)
app.include_router(exports_router)
app.include_router(codex_router)
app.include_router(codexify_router)
app.include_router(migration.router)
app.include_router(devtools.router)
app.include_router(websocket_routes.router)
app.include_router(cron_routes.router)
app.include_router(ui_session.router)
app.include_router(agent_orchestration.router)
app.include_router(agent_orchestration.chat_router)

logger.info("[routers] All routers included")


# =========================
# Unique Endpoints (Not in Routers)
# =========================


# Compatibility aliases for legacy codex routes
@app.get("/codex/entries", include_in_schema=False)
def codex_entries_compat():
    """Compatibility alias for legacy clients; redirect to the canonical /api route."""
    return RedirectResponse(url="/api/codex/entries")


@app.get("/codex/entries/{entry_id}", include_in_schema=False)
def codex_entry_compat(entry_id: str):
    """Compatibility alias for legacy clients; redirect to the canonical /api route."""
    return RedirectResponse(url=f"/api/codex/entries/{entry_id}")


@app.get("/codex/entries/{entry_id}/export", include_in_schema=False)
def codex_entry_export_compat(entry_id: str):
    """Compatibility alias for legacy clients; redirect to the canonical /api route."""
    return RedirectResponse(url=f"/api/codex/entries/{entry_id}/export")


@app.get("/codex/{entry_id}/source", include_in_schema=False)
def codex_entry_source_compat(entry_id: str):
    """Compatibility alias for codex source provenance route."""
    return RedirectResponse(url=f"/api/codex/{entry_id}/source")


@app.get("/api/events", tags=["Events"])
async def stream_events(
    request: Request,
    last_id_query: int = Query(0, alias="last_id"),
    last_event_id_header: Optional[str] = Header(None, alias="Last-Event-ID"),
    api_key: str = Depends(require_api_key),
):
    """
    Stream domain events from the durable events_outbox as Server-Sent Events.

    - Resumes from `last_id` query param or `Last-Event-ID` header.
    - Emits a `retry: 3000` hint on connect.
    - Periodically polls the outbox and sends `ping` events when idle.
    - Deletes events up to the last delivered id so the outbox does not grow unbounded.
    """
    from starlette.responses import StreamingResponse

    async def event_stream() -> AsyncGenerator[str, None]:
        # Prefer explicit header over query, fall back to zero.
        last_id = parse_last_event_id(last_event_id_header, last_id_query)

        # Initial retry hint expected by many SSE clients.
        yield "retry: 3000\n\n"

        heartbeat_elapsed = 0.0
        heartbeat_interval = 15.0  # seconds

        while True:
            if await request.is_disconnected():
                break

            events = event_bus.fetch_events_after(
                last_id,
                limit=OUTBOX_BATCH_SIZE,
                tenant_id=OUTBOX_TENANT_ID,
            )
            max_id_seen = last_id

            if events:
                for ev in events:
                    ev_id_raw = ev.get("id")
                    topic = ev.get("topic") or "message"
                    payload = ev.get("payload") or {}
                    raw_tenant = ev.get("tenant_id")
                    event_tenant = normalize_outbox_tenant_id(
                        raw_tenant if isinstance(raw_tenant, str) else None
                    )
                    if event_tenant != OUTBOX_TENANT_ID:
                        continue

                    try:
                        ev_id = int(ev_id_raw)
                    except (TypeError, ValueError):
                        logger.debug(
                            "[outbox] skipping event with invalid id=%r",
                            ev_id_raw,
                        )
                        continue

                    try:
                        data_str = json.dumps(payload, default=str)
                    except Exception:
                        data_str = "{}"

                    # Emit SSE event
                    yield f"id: {ev_id}\n"
                    yield f"event: {topic}\n"
                    yield f"data: {data_str}\n\n"

                    if ev_id and ev_id > max_id_seen:
                        max_id_seen = ev_id

                # Update last_id for next poll
                last_id = max_id_seen

                # Keep outbox events intact so concurrent clients can resume
                # independently without losing events due to destructive cleanup.

                # Reset heartbeat timer
                heartbeat_elapsed = 0.0
            else:
                # No events, check heartbeat
                heartbeat_elapsed += OUTBOX_POLL_INTERVAL
                if heartbeat_elapsed >= heartbeat_interval:
                    yield f": ping\n\n"
                    heartbeat_elapsed = 0.0

            # Poll interval
            await asyncio.sleep(OUTBOX_POLL_INTERVAL)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/tasks/{task_id}/events", tags=["Tasks"])
async def stream_task_events(
    request: Request,
    task_id: str,
    last_id_query: str = Query("0-0", alias="last_id"),
    last_event_id_header: Optional[str] = Header(None, alias="Last-Event-ID"),
    api_key: str = Depends(require_api_key),
):
    """
    Stream task events from Redis by task_id as Server-Sent Events.

    - Resumes from `last_id` query param or `Last-Event-ID` header.
    - Emits a `retry: 3000` hint on connect.
    - Stops streaming on task completion, failure, or cancellation.
    """
    from starlette.responses import StreamingResponse

    async def event_stream() -> AsyncGenerator[str, None]:
        last_id = str(last_event_id_header or last_id_query or "0-0")
        if "-" not in last_id:
            last_id = "0-0"
        yield "retry: 3000\n\n"

        heartbeat_elapsed = 0.0
        heartbeat_interval = 15.0
        block_ms = int(os.getenv("TASK_EVENT_BLOCK_MS", "15000"))

        while True:
            if await request.is_disconnected():
                break

            try:
                events = await asyncio.to_thread(
                    task_events.read_events,
                    task_id,
                    last_id,
                    block_ms=block_ms,
                    count=100,
                )
            except Exception as exc:
                logger.warning("[task-events] read failed: %s", exc)
                await asyncio.sleep(1)
                continue

            if events:
                for ev_id, ev in events:
                    data_str = json.dumps(ev.get("data") or {}, default=str)
                    yield f"id: {ev_id}\n"
                    yield f"event: {ev.get('type') or 'task.event'}\n"
                    yield f"data: {data_str}\n\n"
                    last_id = ev_id

                    if ev.get("type") in (
                        "task.completed",
                        "task.cancelled",
                        "task.failed",
                    ):
                        return

                heartbeat_elapsed = 0.0
            else:
                heartbeat_elapsed += block_ms / 1000.0
                if heartbeat_elapsed >= heartbeat_interval:
                    yield ": ping\n\n"
                    heartbeat_elapsed = 0.0

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/graph", summary="Return graph data from Neo4j", tags=["Graph"])
def get_graph(
    scope: str = "codexify",
    api_key: str = Depends(require_api_key),
):
    """
    Fetch graph data from Neo4j for visualization.
    Returns nodes and links for the specified scope.
    """
    _ = api_key
    if not NEO4J_AVAILABLE:
        raise HTTPException(
            status_code=503, detail="Neo4j driver not available"
        )

    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = (
        os.getenv("NEO4J_PASSWORD") or os.getenv("NEO4J_PASS") or ""
    ).strip()
    if not password:
        raise HTTPException(
            status_code=503,
            detail="NEO4J_PASSWORD is not configured",
        )

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to Neo4j: {e}"
        )

    nodes, links = [], []
    try:
        with driver.session() as session:
            result = session.run("MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 250")
            for record in result:
                a, r, b = record["a"], record["r"], record["b"]
                nodes.extend(
                    [
                        {
                            "id": a.element_id,
                            "label": a.get(
                                "name",
                                list(a.labels)[0] if a.labels else "Node",
                            ),
                            "type": list(a.labels)[0] if a.labels else "node",
                        },
                        {
                            "id": b.element_id,
                            "label": b.get(
                                "name",
                                list(b.labels)[0] if b.labels else "Node",
                            ),
                            "type": list(b.labels)[0] if b.labels else "node",
                        },
                    ]
                )
                links.append(
                    {
                        "source": a.element_id,
                        "target": b.element_id,
                        "label": r.type,
                    }
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    finally:
        driver.close()

    # Deduplicate nodes by id
    unique_nodes = {n["id"]: n for n in nodes}.values()
    return {"nodes": list(unique_nodes), "links": links}


# (Removed redundant /upload-chat endpoint; use guardian/routes/migration.py instead)


@app.get("/media/{file_path:path}", include_in_schema=False)
def serve_signed_media(
    file_path: str,
    sig: Optional[str] = Query(None),
):
    requested_path = "/" + str(Path("media") / file_path).replace("\\", "/")
    if not verify_media_signature(requested_path, sig):
        raise HTTPException(status_code=401, detail="Invalid media signature")

    try:
        candidate = (media_storage_path / file_path).resolve()
        candidate.relative_to(media_storage_path)
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid media path")

    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Media not found")

    return FileResponse(candidate)


# =========================
# Root Endpoint
# =========================


@app.get("/", tags=["Root"])
def root():
    """API root endpoint with basic information."""
    return {
        "service": "Guardian Codex API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


# =========================
# Module Exports
# =========================

# Export app and selected globals for tests and ASGI servers
__all__ = ["app", "chatlog_db", "EPHEMERAL_MEMORY"]

logger.info("[guardian_api] Module loaded successfully")


# Regression guard: ensure core exports remain present (fail loudly if truncated).
if __name__ == "guardian.guardian_api":
    assert app is not None, "guardian_api.app missing"
