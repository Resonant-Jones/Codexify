# =========================
# Imports
# =========================

"""guardian_api module

High‑level FastAPI entry point for the Guardian backend.

This module wires together all major API routes, including:

- **Chat** – creation, listing, and streaming of chat threads and messages.
- **Memory** – CRUD operations for short‑term, mid‑term, and long‑term memory entries.
- **Connectors** – management of external service connectors (GitHub, Google Drive, etc.).
- **Tools & Jobs** – a minimal tool‑execution dispatcher and job status endpoint.
- **Health & Diagnostics** – endpoints for service health checks, configuration debugging, and system status.

It also sets up CORS middleware, loads environment variables, configures logging,
and provides API‑key authentication for all protected routes.

The implementation relies on the `guardian.core` database adapters, the
`guardian.config` loader, and optional AI back‑ends (Gemini, Groq, etc.).
"""

import asyncio
import json
import logging
import datetime

# Standard Library
import os
import secrets
from contextlib import suppress
from threading import Lock
from datetime import datetime, date, time
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import requests
import psycopg2, psycopg2.extras
from dotenv import load_dotenv
from fastapi import (
    Body,
    APIRouter,
    Cookie,
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError, ConfigDict
from starlette.responses import StreamingResponse

# Configure logging EARLY (before any logger.* calls)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Additional imports for default project creation
# Optional SQLAlchemy ProgrammingError import (may be unused)
try:
    from sqlalchemy.exc import ProgrammingError  # type: ignore
except Exception:  # pragma: no cover
    ProgrammingError = Exception  # type: ignore

# Import ORM models from canonical location
try:
    from guardian.db.models import Project
    logger.info("[imports] Using guardian.db.models.Project")
except ImportError as e:
    logger.warning("[imports] Could not import Project model: %s", e)
    Project = None  # type: ignore

# Import for Neo4j graph endpoint
from fastapi import APIRouter, HTTPException
from neo4j import GraphDatabase
import os

# DB adapters
from guardian.core import event_bus
from guardian.core.chat_db import ChatDB
from guardian.core.db import GuardianDB
from guardian.config.db_defaults import DEFAULT_PG_DSN
from guardian.routes.codexify_router import router as codexify_router
from guardian.routes.api_exports import router as exports_router
from guardian.routes.media import router as media_router

from guardian.connectors.github import sync_repo

# Optional Neo4j driver session provider
try:
    # Prefer local db.neo module; falls back to unavailable if not present
    from db.neo import get_session as get_neo_session  # type: ignore
    from db.neo import UserNode, MessageNode, ThreadNode
    NEO4J_AVAILABLE = True
except Exception as e:  # pragma: no cover
    logging.warning(f"[Codexify ⚠️] Neo4j driver not available: {e}")
    get_neo_session = None  # type: ignore
    NEO4J_AVAILABLE = False

# --- RAG modules import (for /upload-chat) ---
try:
    from backend.rag.enhanced_rag import EnhancedRAG
    from backend.rag.embedder import Embedder
    from backend.rag.parser import parse_chat_history
except Exception as e:
    logging.warning(f"[RAG] Failed to import RAG modules: {e}")

try:
    from guardian.core.pgdb import PgDB  # type: ignore
except Exception as _pg_exc:  # pragma: no cover
    PgDB = None  # type: ignore
    _pg_import_error = _pg_exc
else:
    _pg_import_error = None
_PG_IMPORT_ERROR = _pg_import_error
from io import BytesIO

import numpy as np

# Vision/captioning imports
from PIL import Image
from transformers import (
    AutoModelForVision2Seq,
    AutoProcessor,
    BlipForConditionalGeneration,
    BlipProcessor,
)

# Internal
from guardian.config import get_settings
from guardian.routes import agent, memory, research, threads, documents, share
from guardian.realtime import collaboration
from guardian.core.auth import issue_session_token, verify_session_token, require_auth
from guardian.context.broker import ContextBroker
from guardian.vector.store import VectorStore
from guardian.memory.query_memory import memory_store as _memory_store
from guardian.sensors.state import Sensors

# Optional AI Backend
chat_with_ai: Optional[Callable[[List[Dict[str, str]]], str]] = None  # placeholder for optional AI backend
try:
    from guardian.core.ai_router import chat_with_ai as _chat_with_ai
    chat_with_ai = _chat_with_ai
except ModuleNotFoundError as e:
    logging.warning(f"[Codexify ⚠️] Optional chat_with_ai module not available: {e}")

# Optional Groq provider
try:
    from guardian.providers.groq_client import get_groq_chat  # lazy Groq client factory
except ModuleNotFoundError as e:
    logging.warning(f"[Codexify ⚠️] Optional groq_client not available: {e}")

    def get_groq_chat() -> Any:  # type: ignore
        return None

# API Key authentication is enforced on all major endpoints (except /ping, /test, /)
# Pass `X-API-Key` header with your requests.

# ---- Env loading (backend) -----------------------------------------------
def _load_env_chain() -> None:
    """
    Load .env files in priority order: base → mode-specific → local
    Each layer can override previous ones, but actual environment vars always win.
    """
    cwd = Path(__file__).resolve().parents[1]
    base = cwd / ".env"
    mode = os.getenv("GUARDIAN_ENV", "development").strip()
    backend_mode = cwd / f".env.backend.{mode}"
    local = cwd / ".env.local"

    loaded = []
    for p in (base, backend_mode, local):
        if p.exists():
            # load with override=False so real env vars still take precedence
            load_dotenv(p, override=False)
            loaded.append(str(p))
    logger.info(
        "[env] dotenv loaded (in order): %s",
        " -> ".join(loaded) if loaded else "<none>",
    )


_load_env_chain()

# API key dependency setup (re-read after dotenv)
API_KEY = os.getenv("GUARDIAN_API_KEY", "changeme")
_mask = (API_KEY[:4] + "…" + API_KEY[-4:]) if API_KEY and len(API_KEY) > 8 else API_KEY
logger.info("[auth] Using GUARDIAN_API_KEY=%s", _mask)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str = Depends(api_key_header)):
    """
    Validate API key authentication.
    Returns the API key if valid, raises 401 if invalid or missing.
    Does not log the provided key to avoid leaking secrets.
    """
    if api_key != API_KEY:
        logger.warning("Unauthorized API key attempt")
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return api_key


# Load configuration from environment variables
GEMINI_API_URL = os.getenv("GEMINI_API_URL", "https://api.gemini.ai/v1/chat")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_gemini_api_key_here")

# Provider selection and Groq config
GUARDIAN_PROVIDER = os.getenv("GUARDIAN_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_DEFAULT = os.getenv("GROQ_MODEL", "moonshotai/kimi-k2-instruct-0905")
GROQ_FALLBACK_MODEL = (os.getenv("GROQ_FALLBACK_MODEL") or "").strip() or None

# Back/forward-compatible aliases so both legacy and new env names work
CHAT_PROVIDER = (os.getenv("GUARDIAN_CHAT_PROVIDER") or GUARDIAN_PROVIDER).lower()
DEFAULT_MODEL = os.getenv("GUARDIAN_DEFAULT_MODEL") or GROQ_MODEL_DEFAULT
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")

# Minimal Groq completion helper for chat API (robust, fallback support)
def _groq_complete(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    *,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Call Groq's OpenAI-compatible /chat/completions and return assistant text.
    - Handles multiple possible response shapes (message.content as str or list, choice.text).
    - Detects provider-style error strings that sometimes appear inside a 200 payload.
    - Optionally retries once with GROQ_FALLBACK_MODEL if the first attempt yields empty/invalid text.
    """
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")

    def _extract_text(data: Dict[str, Any]) -> str:
        try:
            choices = data.get("choices") or []
            if not choices:
                return ""
            ch0 = choices[0] or {}
            # OpenAI-style: choices[0].message.content
            msg = ch0.get("message")
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, str):
                    return content.strip()
                # Some providers return a list of parts
                if isinstance(content, list):
                    parts: List[str] = []
                    for p in content:
                        if isinstance(p, str):
                            parts.append(p)
                        elif isinstance(p, dict):
                            v = p.get("text") or p.get("content")
                            if isinstance(v, str):
                                parts.append(v)
                    if parts:
                        return "".join(parts).strip()
            # Fallbacks sometimes used by wrappers
            for k in ("text", "content"):
                v = ch0.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
        except Exception:
            pass
        return ""

    def _looks_like_provider_error(text: str) -> bool:
        t = text.strip().lower()
        if not t:
            return True
        # Heuristic: upstream error echoed as "..., message='Not Found', url='https://api.siliconflow.cn/v1/chat/completions'"
        if "not found" in t and "completions" in t:
            return True
        if t.startswith("error:") or "invalid model" in t or "unknown model" in t:
            return True
        return False

    url = f"{GROQ_BASE_URL}/chat/completions"
    primary_model = (model or DEFAULT_MODEL) or "moonshotai/kimi-k2-instruct-0905"
    candidates: List[str] = [primary_model]
    if GROQ_FALLBACK_MODEL and GROQ_FALLBACK_MODEL != primary_model:
        candidates.append(GROQ_FALLBACK_MODEL)

    last_error_detail: Optional[str] = None

    for use_model in candidates:
        try:
            resp = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"model": use_model, "messages": messages},
                timeout=60,
            )
        except Exception as e:
            last_error_detail = f"request failed: {e.__class__.__name__}"
            continue

        if resp.status_code != 200:
            # try to keep error concise and non-secret
            try:
                err = resp.json()
            except Exception:
                err = (resp.text or "")[:200]
            last_error_detail = f"HTTP {resp.status_code}: {str(err)[:150]}"
            continue

        try:
            data = resp.json()
        except Exception as e:
            last_error_detail = f"bad json: {e.__class__.__name__}"
            continue

        text = _extract_text(data)
        # Some upstreams incorrectly stuff errors into a 200 'content' field; detect and reject
        if _looks_like_provider_error(text):
            last_error_detail = f"invalid-content shape for model '{use_model}': {text[:120]}"
            continue

        if text:
            return text

        last_error_detail = f"empty-content for model '{use_model}'"

    # If we made it here, both primary (and fallback if any) failed
    raise HTTPException(
        status_code=502,
        detail=f"Groq completion failed: {last_error_detail or 'unknown error'}",
    )

# Feature flag: enable/disable BLIP vision model
ENABLE_BLIP_MODEL = os.getenv("ENABLE_BLIP_MODEL", "true").lower() in ("1", "true", "yes")

ENABLE_OUTBOX = os.getenv("ENABLE_OUTBOX", "1").lower() in ("1", "true", "yes")
_ENABLE_SSE_FILTER_RAW = os.getenv("ENABLE_SSE_FILTER", "0")
ENABLE_SSE_FILTER = bool(os.getenv("ENABLE_SSE_FILTER", "0"))
ENABLE_SSE_FILTER = _ENABLE_SSE_FILTER_RAW.lower() in ("1", "true", "yes")
OUTBOX_POLL_INTERVAL = float(os.getenv("OUTBOX_POLL_INTERVAL", "1.0"))
OUTBOX_BATCH_SIZE = int(os.getenv("OUTBOX_BATCH_SIZE", "100"))

# Vision model for image captioning
processor = None
vision_model = None
if ENABLE_BLIP_MODEL:
    try:
        processor = BlipProcessor.from_pretrained(
            "Salesforce/blip-image-captioning-base", use_fast=True
        )
    except Exception as e:
        logging.warning(f"Fast BLIP processor unavailable, falling back to slow: {e}")
        processor = BlipProcessor.from_pretrained(
            "Salesforce/blip-image-captioning-base", use_fast=False
        )
    try:
        vision_model = BlipForConditionalGeneration.from_pretrained(
            "Salesforce/blip-image-captioning-base"
        )
    except Exception as e:
        logging.error(f"BLIP vision model failed to load: {e}")
        processor = None
        vision_model = None
    logging.info("BLIP model loaded: ENABLE_BLIP_MODEL=%s", ENABLE_BLIP_MODEL)
else:
    logging.info("BLIP model loading skipped: ENABLE_BLIP_MODEL=%s", ENABLE_BLIP_MODEL)

# Mondream (symbolic/QA-style) initialization
# Gate behind env flag to avoid noisy startup if not needed

_ENABLE_MONDREAM = os.getenv("GUARDIAN_ENABLE_MONDREAM", "0").lower() in (
    "1",
    "true",
    "yes",
)
mondream_processor: Any = None
mondream_model: Any = None
if _ENABLE_MONDREAM:
    mondream_dir = Path(__file__).resolve().parents[1] / "models" / "mondream1"
    repo_spec = str(mondream_dir) if mondream_dir.exists() else "vikhyatk/mondream1"
    try:
        mondream_processor = AutoProcessor.from_pretrained(
            repo_spec, trust_remote_code=True
        )
        mondream_model = AutoModelForVision2Seq.from_pretrained(
            repo_spec, trust_remote_code=True
        )
        logger.info("Mondream model loaded")
    except Exception as e:
        logging.warning(f"Failed to load Mondream model: {e}")


# Helper: crop to content for image captioning
def crop_to_content(pil_img: Image.Image, threshold: int = 10) -> Image.Image:
    """
    Trim away black borders only by scanning edges, leaving interior black content intact.
    """
    gray = pil_img.convert("L")
    arr = np.array(gray)
    h, w = arr.shape

    # find top edge
    top = 0
    for i in range(h):
        if arr[i, :].max() > threshold:
            top = i
            break

    # find bottom edge
    bottom = h
    for i in range(h - 1, -1, -1):
        if arr[i, :].max() > threshold:
            bottom = i + 1
            break

    # find left edge
    left = 0
    for j in range(w):
        if arr[:, j].max() > threshold:
            left = j
            break

    # find right edge
    right = w
    for j in range(w - 1, -1, -1):
        if arr[:, j].max() > threshold:
            right = j + 1
            break

    # ensure we have a valid crop
    if left >= right or top >= bottom:
        return pil_img

    # apply crop
    return pil_img.crop((left, top, right, bottom))



def _mask_dsn(dsn: str) -> str:
    try:
        parsed = urlparse(dsn)
        netloc = parsed.netloc
        if "@" in netloc:
            creds, hostinfo = netloc.split("@", 1)
            if ":" in creds:
                user = creds.split(":", 1)[0]
                creds = f"{user}:***"
            netloc = f"{creds}@{hostinfo}"
        return urlunparse(parsed._replace(netloc=netloc))
    except Exception:
        return dsn

# Helper: recursively convert datetimes/times to ISO strings for JSON/DB
def _jsonify(obj: Any) -> Any:
    """Recursively convert datetimes and times into ISO strings so JSON/DB can accept them.
    Leaves other types untouched.
    """
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [ _jsonify(v) for v in obj ]
    return obj


# ────────────────────────── DB backend selection ────────────────────────────
settings = get_settings()

PG_DSN = os.getenv("DATABASE_URL", DEFAULT_PG_DSN)
DB_PATH = os.getenv("GUARDIAN_DB_PATH")  # may be "__DISABLE_SQLITE__"
chatlog_db: ChatDB
effective_sqlite_path: Optional[str] = None

if PG_DSN:
    if PgDB is None:
        raise RuntimeError(
            "Postgres DSN provided but PgDB adapter is unavailable"
        ) from _PG_IMPORT_ERROR
    chatlog_db = PgDB(PG_DSN)  # type: ignore[arg-type]
    DB_BACKEND = "postgres"
    logger.info("[db] Using PostgreSQL DSN: %s", _mask_dsn(PG_DSN))
else:
    if DB_PATH == "__DISABLE_SQLITE__":
        raise RuntimeError(
            "SQLite disabled but no Postgres DSN supplied; set GUARDIAN_DB_URL or DATABASE_URL"
        )
    effective_sqlite_path = DB_PATH or str(Path("guardian.db"))
    chatlog_db = GuardianDB(effective_sqlite_path)
    DB_BACKEND = "sqlite"
    logger.info("[db] Using SQLite path: %s", effective_sqlite_path)

logger.info("📦 DB backend selected: %s", DB_BACKEND)

# Initialize shared ContextBroker dependencies (vector store + sensors)
_vector_store = VectorStore()
_sensors = Sensors(chatlog_db)

# Configure durable outbox storage when enabled
if ENABLE_OUTBOX:
    try:
        event_bus.configure_event_store(chatlog_db)
        logger.info("[outbox] durable event outbox enabled")
    except Exception:
        logger.exception("[outbox] failed to configure durable event outbox; falling back to in-memory hub")
# ─────────────────────────────────────────────────────────────────────────────

SQLITE_PATH = effective_sqlite_path if DB_BACKEND == "sqlite" else None


# Helper: ensure "Loose Threads" project exists at startup
def _ensure_loose_threads_project():
    try:
        chatlog_db.ensure_project(
            "Loose Threads", "Default bucket for unassigned threads"
        )
    except Exception as e:
        logger.warning("[projects] Failed to ensure Loose Threads project: %s", e)


_ensure_loose_threads_project()

try:
    chatlog_db.ensure_sync_job_support()
except Exception as e:
    logger.warning("[sync] Failed to ensure sync_jobs table: %s", e)

# ---- Memory retention and ephemeral silo
MEMORY_RETENTION_DAYS = int(os.getenv("MEMORY_RETENTION_DAYS", "90"))
EPHEMERAL_MEMORY: List[Dict[str, Any]] = []
try:
    from datetime import timedelta

    # Use timezone-aware UTC timestamps to avoid deprecation warnings
    cutoff = (datetime.now(datetime.UTC) - timedelta(days=MEMORY_RETENTION_DAYS)).isoformat()
    pruned = chatlog_db.prune_midterm(cutoff)
    if pruned:
        logger.info("[memory] pruned %d expired midterm entries", pruned)
except Exception as _e:
    logger.debug("[memory] prune skipped: %s", _e)

logger.info("[startup] ENABLE_BLIP_MODEL=%s", ENABLE_BLIP_MODEL)
logger.info("[startup] chat provider=%s model=%s fallback=%s base=%s", CHAT_PROVIDER, DEFAULT_MODEL, GROQ_FALLBACK_MODEL, GROQ_BASE_URL)

# Initialize FastAPI app with lifespan (replaces deprecated on_event handlers)

async def app_lifespan(app: FastAPI):
    global _CONNECTOR_WORKER_STOP, _CONNECTOR_WORKER_TASK
    # Startup: optionally launch connector worker
    if ENABLE_CONNECTOR_WORKER:
        try:
            # Validate DB tables exist before launching worker
            chatlog_db.list_connector_configs()
            stop_event = asyncio.Event()
            _CONNECTOR_WORKER_STOP = stop_event
            _CONNECTOR_WORKER_TASK = asyncio.create_task(_connector_worker(stop_event))
        except Exception as exc:
            logger.error("[connectors] unable to initialise connector tables: %s", exc)
    yield
    # Shutdown: stop worker if running
    if _CONNECTOR_WORKER_STOP is not None:
        _CONNECTOR_WORKER_STOP.set()
    if _CONNECTOR_WORKER_TASK is not None:
        _CONNECTOR_WORKER_TASK.cancel()
        with suppress(asyncio.CancelledError):
            await _CONNECTOR_WORKER_TASK
    _CONNECTOR_WORKER_STOP = None
    _CONNECTOR_WORKER_TASK = None


app = FastAPI(title="Guardian Codex API", lifespan=app_lifespan)

# Neo4j health endpoint (appears only when driver import succeeded)
if NEO4J_AVAILABLE and get_neo_session:
    from fastapi import Depends
    @app.get("/health/neo4j", tags=["Health"])
    async def neo4j_health(session=Depends(get_neo_session)):
        try:
            await session.run("RETURN 1 AS ok")
            return {"ok": True}
        except Exception as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(exc))

# =========================
# Neo4j Graph Endpoint
# =========================
@app.get('/graph', summary='Return graph data from Neo4j', tags=['Graph'])
def get_graph(scope: str = 'codexify'):
    uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'test')

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to connect to Neo4j: {e}')

    nodes, links = [], []
    try:
        with driver.session() as session:
            result = session.run('MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 250')
            for record in result:
                a, r, b = record['a'], record['r'], record['b']
                nodes.extend([
                    {"id": a.element_id, "label": a.get('name', list(a.labels)[0] if a.labels else 'Node'), "type": list(a.labels)[0] if a.labels else 'node'},
                    {"id": b.element_id, "label": b.get('name', list(b.labels)[0] if b.labels else 'Node'), "type": list(b.labels)[0] if b.labels else 'node'}
                ])
                links.append({"source": a.element_id, "target": b.element_id, "label": r.type})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Graph query failed: {e}')
    finally:
        driver.close()

    unique_nodes = list({n['id']: n for n in nodes}.values())
    return {"nodes": unique_nodes, "links": links}

# Include routers for modular endpoints
app.include_router(threads.router, prefix="/threads")
app.include_router(research.router, prefix="/research")
app.include_router(memory.router, prefix="/memory")
app.include_router(agent.router, prefix="/agent")
app.include_router(codexify_router)
# --- API Routers ---
app.include_router(documents.router)
app.include_router(share.router)
app.include_router(collaboration.router)
app.include_router(exports_router)
app.include_router(media_router, prefix="/api/media", tags=["media"])

# Mount static files for media storage
# Serves uploaded files from /app/media at /media URL path
try:
    media_storage_path = os.getenv('STORAGE_BASE_PATH', '/app/media')
    Path(media_storage_path).mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=media_storage_path), name="media")
    logger.info(f"[media] Static file serving enabled at /media -> {media_storage_path}")
except Exception as e:
    logger.warning(f"[media] Could not mount static files at {media_storage_path}: {e}")

# Meta / Self-Check endpoint for quick diagnostics (no auth by design, like /healthz)
meta_router = APIRouter(prefix="/meta", tags=["Meta"])


@meta_router.get("/selfcheck")
async def meta_selfcheck():
    result = epistemic_self_check(
        intent="runtime_status",
        available_functions=["base_operation", "query_processing"],
        context={"system": "guardian_api"},
    )
    try:
        log_dir = Path(__file__).resolve().parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "selfcheck.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(result) + "\n")
    except Exception as _e:
        logger.debug("[meta] failed to write selfcheck log: %s", _e)
    return result


app.include_router(meta_router)
# CORS middleware for local/frontend use
# Configure allowed origins via environment variable for production safety.
# GUARDIAN_ALLOWED_ORIGINS can be a comma-separated list of origins.
_origins_env = os.getenv("GUARDIAN_ALLOWED_ORIGINS", "http://localhost:5173")
allowed_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# Upload Chat for RAG Embedding
# =========================
from fastapi import UploadFile, File
from fastapi.responses import JSONResponse

@app.post("/upload-chat")
async def upload_chat(file: UploadFile = File(...)):
    content = await file.read()
    try:
        text_blocks = parse_chat_history(content.decode("utf-8"))
        embedder = Embedder()
        results = embedder.embed_documents(text_blocks)
        return JSONResponse({"embedded": len(results)})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# =========================
# Tools & Jobs (minimal scaffold)
# =========================
# In-memory job registry (ok for dev; replace with persistent store for prod)
JOBS: Dict[str, Dict[str, Any]] = {}


class ToolRequest(BaseModel):
    name: str
    args: dict = Field(default_factory=dict)


class ToolResponse(BaseModel):
    job_id: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    result: dict = Field(default_factory=dict)


class ThreadDTO(BaseModel):
    id: int
    user_id: str
    title: str
    summary: str = ""
    project_id: Optional[int] = None
    parent_id: Optional[int] = None
    archived_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Pydantic v2: replace deprecated orm_mode with from_attributes
    model_config = ConfigDict(from_attributes=True)


class ThreadUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    project_id: Optional[int] = None
    archived: Optional[bool] = None


class ThreadBranchRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    project_id: Optional[int] = None


@app.post("/tools/execute", response_model=ToolResponse, tags=["Tools"])
def tools_execute(body: ToolRequest, api_key: str = Depends(require_api_key)):
    """
    Minimal tools dispatcher. For now, just echoes args and marks job done.
    Replace with real tool routing/execution as needed.
    """
    jid = str(uuid4())
    # Example: no-op tool that returns provided args
    result = {"ok": True, "tool": body.name, "args": body.args}
    JOBS[jid] = {"status": "done", "result": result}
    logger.info("Tools.execute: %s job_id=%s", body.name, jid)
    return {"job_id": jid}


# =========================
# Connectors (stubbed API for frontend settings)
# =========================


def _connector_status_from_env(connector_id: str) -> str:
    """Heuristic: mark as connected if an env token that looks relevant exists.
    Examples: GITHUB_TOKEN, GOOGLE_DRIVE_TOKEN, NOTION_TOKEN, SLACK_BOT_TOKEN, etc.
    """
    cid = connector_id.upper()
    candidates = [
        f"{cid}_TOKEN",
        f"{cid}_API_KEY",
        f"{cid}_KEY",
        f"{cid}_ACCESS_TOKEN",
    ]
    for k in candidates:
        if os.getenv(k):
            return "connected"
    return "disconnected"


def _display_name(connector_id: str) -> str:
    return connector_id.replace("_", " ").title()



def _read_sync_interval(default: str = "300") -> int:
    raw = os.getenv("CONNECTOR_SYNC_INTERVAL")
    if raw is None:
        raw = os.getenv("GUARDIAN_CONNECTOR_SYNC_INTERVAL", default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = int(default)
    return max(30, value)


CONNECTOR_REGISTRY: Dict[str, Dict[str, Any]] = {
    "github": {
        "id": "github",
        "name": "GitHub",
        "capabilities": {
            "supportsOAuth": False,
            "supportsApiKey": True,
            "supportsLocal": False,
        },
        "requiredFields": [
            {"key": "owner", "label": "Owner", "type": "string"},
            {"key": "repo", "label": "Repository", "type": "string"},
        ],
        "scopes": ["repo", "read:org"],
        "options": [],
    }
}

ENABLE_CONNECTOR_WORKER = os.getenv("ENABLE_CONNECTOR_WORKER", "0").lower() in (
    "1",
    "true",
    "yes",
)
CONNECTOR_SYNC_INTERVAL = _read_sync_interval()

_CONNECTOR_WORKER_STOP: Optional[asyncio.Event] = None
_CONNECTOR_WORKER_TASK: Optional[asyncio.Task] = None


class ConnectorCreate(BaseModel):
    name: str
    type: str
    settings: Dict[str, Any] = Field(default_factory=dict)


class ConnectorUpdate(BaseModel):
    settings: Optional[Dict[str, Any]] = None


class ConnectorConfigFields(BaseModel):
    fields: Dict[str, Any]


def _required_settings_for_type(type_: str) -> List[str]:
    if type_ == "github":
        return ["owner", "repo"]
    return []


def _serialize_connector_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    settings = cfg.get("settings") or {}
    meta = CONNECTOR_REGISTRY.get(cfg.get("type", ""), {})
    last_run = cfg.get("last_run")
    status = "disconnected"
    last_sync_at = None
    error_message = None
    if last_run:
        status_map = {
            "succeeded": "connected",
            "running": "running",
            "failed": "error",
        }
        status = status_map.get(last_run.get("status"), "error")
        last_sync_at = last_run.get("finished_at") or last_run.get("started_at")
        error_message = last_run.get("error")
    return {
        "id": cfg.get("name"),
        "configId": cfg.get("id"),
        "name": cfg.get("name"),
        "type": cfg.get("type"),
        "settings": settings,
        "status": status,
        "lastRun": last_run,
        "lastSyncAt": last_sync_at,
        "errorMessage": error_message,
        "auth": None,
        "syncInterval": settings.get("syncInterval", "manual"),
        "scopes": meta.get("scopes", []),
        "options": meta.get("options", []),
        "capabilities": meta.get("capabilities"),
        "requiredFields": meta.get("requiredFields"),
        "needsAdminSecret": False,
    }


def _get_connector_by_name(name: str) -> Dict[str, Any]:
    cfg = chatlog_db.get_connector_config(name)
    if not cfg:
        raise HTTPException(status_code=404, detail={"error": "Connector not found"})
    last_run = chatlog_db.get_last_connector_run(cfg["id"])
    cfg["last_run"] = last_run
    return cfg


def _validate_connector_settings(type_: str, settings: Dict[str, Any]) -> None:
    required = _required_settings_for_type(type_)
    missing = [key for key in required if not settings.get(key)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Missing required settings: {', '.join(missing)}"},
        )


def _emit_connector_event(config: Dict[str, Any], run: Dict[str, Any]) -> None:
    payload = {
        "connector": config.get("name"),
        "connector_id": config.get("id"),
        "type": config.get("type"),
        "run_id": run.get("id"),
        "status": run.get("status"),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
        "document_count": run.get("document_count"),
        "error": run.get("error"),
    }
    # Ensure datetimes (or other non-JSON types) are serialized safely before storing
    event_bus.emit_event("connector.sync", _jsonify(payload))


@app.get("/api/connectors", tags=["Connectors"])
def list_connectors():
    configs = chatlog_db.list_connector_configs_with_last_run()
    return [_serialize_connector_config(cfg) for cfg in configs]


@app.post("/api/connectors", tags=["Connectors"])
def create_connector(cfg: ConnectorCreate):
    cfg_type = cfg.type.lower()
    if cfg_type not in CONNECTOR_REGISTRY:
        raise HTTPException(status_code=400, detail={"error": "Unsupported connector type"})
    if chatlog_db.get_connector_config(cfg.name):
        raise HTTPException(status_code=400, detail={"error": "Connector name already exists"})
    _validate_connector_settings(cfg_type, cfg.settings)
    stored = chatlog_db.create_connector_config(cfg.name, cfg_type, cfg.settings)
    stored["last_run"] = None
    return _serialize_connector_config(stored)


@app.get("/api/connectors/{connector_name}", tags=["Connectors"])
def get_connector(connector_name: str):
    cfg = _get_connector_by_name(connector_name)
    return _serialize_connector_config(cfg)


@app.patch("/api/connectors/{connector_name}", tags=["Connectors"])
def patch_connector(connector_name: str, update: ConnectorUpdate):
    cfg = _get_connector_by_name(connector_name)
    if update.settings is not None:
        merged = {**(cfg.get("settings") or {}), **update.settings}
        _validate_connector_settings(cfg["type"], merged)
        cfg = chatlog_db.update_connector_config(connector_name, config=merged)
        cfg["last_run"] = chatlog_db.get_last_connector_run(cfg["id"])
    return _serialize_connector_config(cfg)


@app.post("/api/connectors/{connector_name}/config", tags=["Connectors"])
def update_connector_fields(connector_name: str, payload: ConnectorConfigFields):
    cfg = _get_connector_by_name(connector_name)
    merged = {**(cfg.get("settings") or {}), **payload.fields}
    _validate_connector_settings(cfg["type"], merged)
    cfg = chatlog_db.update_connector_config(connector_name, config=merged)
    cfg["last_run"] = chatlog_db.get_last_connector_run(cfg["id"])
    return _serialize_connector_config(cfg)


@app.post("/api/connectors/{connector_name}/test", tags=["Connectors"])
def connector_test(connector_name: str) -> Dict[str, str]:
    _get_connector_by_name(connector_name)
    return {"ok": "True", "message": "Connection not validated in offline mode"}


@app.post("/api/connectors/{connector_name}/sync", tags=["Connectors"])
async def connector_sync(connector_name: str):
    cfg = _get_connector_by_name(connector_name)
    await _schedule_github_sync(cfg)
    return {"ok": True}


@app.post("/api/connectors/{connector_name}/authorize", tags=["Connectors"])
def connector_authorize_not_supported(connector_name: str):
    raise HTTPException(
        status_code=400,
        detail={"error": "OAuth authorization is not supported for this connector"},
    )


@app.get("/api/connectors/{connector_name}/status", tags=["Connectors"])
def connector_status(connector_name: str) -> Dict[str, Any]:
    cfg = _get_connector_by_name(connector_name)
    serialized = _serialize_connector_config(cfg)
    return {
        "ok": True,
        "connector": serialized,
        "status": serialized.get("status"),
        "latest_run": serialized.get("lastRun"),
    }


@app.get("/health/connectors", tags=["Connectors"])
def connectors_health() -> Dict[str, object]:
    connectors = chatlog_db.list_connector_configs_with_last_run()
    total = len(connectors)
    healthy = 0
    for cfg in connectors:
        run = cfg.get("last_run")
        if run and run.get("status") == "succeeded":
            healthy += 1
    return {"ok": "True", "count": total, "connected": healthy}


async def _schedule_github_sync(config: Dict[str, Any]) -> None:
    if config.get("type") != "github":
        logger.info("[connectors] sync skipped for unsupported type %s", config.get("type"))
        return
    loop = asyncio.get_running_loop()
    loop.create_task(_run_github_sync(config))


async def _run_github_sync(config: Dict[str, Any]) -> None:
    settings = config.get("settings") or {}
    # Explicitly cast settings to Dict[str, Any]
    if not isinstance(settings, dict):
        settings = dict(settings)
    owner = str(settings.get("owner") or "")
    repo = str(settings.get("repo") or "")
    if not owner or not repo:
        logger.error("[connectors] missing owner/repo for %s", str(config.get("name")))
        return
    token = os.getenv("GITHUB_TOKEN")
    loop = asyncio.get_running_loop()
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    run = await _run_db(
        chatlog_db.create_connector_run,
        config["id"],
        status="running",
        started_at=started_at,
    )
    run["document_count"] = 0
    _emit_connector_event(config, run)
    try:
        # Explicitly typecast owner/repo to str for run_in_executor
        docs = await loop.run_in_executor(None, sync_repo, owner, repo, token)
        await _run_db(chatlog_db.upsert_raw_documents, config["id"], docs)
        logger.info(
            "[connectors] github sync stored %d docs for %s/%s",
            len(docs),
            str(owner),
            str(repo),
        )
        finished = datetime.datetime.now(datetime.timezone.utc).isoformat()
        run = await _run_db(
            chatlog_db.complete_connector_run,
            run["id"],
            status="succeeded",
            finished_at=finished,
            error=None,
        )
        run["document_count"] = len(docs)
        _emit_connector_event(config, run)
    except Exception as exc:  # pragma: no cover - network failure logging
        logger.exception(
            "[connectors] github sync failed for %s/%s: %s", str(owner), str(repo), exc
        )
        finished = datetime.datetime.now(datetime.timezone.utc).isoformat()
        run = await _run_db(
            chatlog_db.complete_connector_run,
            run["id"],
            status="failed",
            finished_at=finished,
            error=str(exc),
        )
        run["document_count"] = 0
        _emit_connector_event(config, run)


# --- One-shot ingest of GitHub raw_documents into memory_entries ---

def _ingest_github_for_config(connector_name: str) -> dict:
    """Transform raw_documents for the given connector into memory_entries.
    Dedups on (silo,key) so re-running is safe. Emits a durable outbox event.
    """
    dsn = os.environ.get("DATABASE_URL") or PG_DSN
    if not dsn:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    # Keep any single query from hanging forever
    try:
        cur.execute("SET LOCAL statement_timeout = 15000")  # 15s
    except Exception:
        pass
    logger.info("[ingest] begin github ingest name=%s", connector_name)

    # Resolve the connector and its owner/repo
    cur.execute(
        """
        SELECT id, config->>'owner' AS owner, config->>'repo' AS repo
          FROM connector_configs
         WHERE name = %s
        """,
        (connector_name,),
    )
    cfg = cur.fetchone()
    if not cfg:
        conn.rollback(); conn.close()
        raise HTTPException(status_code=404, detail="Connector not found")

    # Fetch raw docs for the connector
    cur.execute(
        """
        SELECT id, external_id, payload::text AS payload
          FROM raw_documents
         WHERE config_id = %s
         ORDER BY id
        """,
        (cfg["id"],),
    )
    rows = cur.fetchall()

    inserted = 0
    for r in rows:
        try:
            payload = json.loads(r["payload"]) if isinstance(r["payload"], str) else (r["payload"] or {})
        except Exception:
            # Skip malformed rows but continue ingesting others
            continue
        # Heuristic type classification
        typ = "issue"
        if isinstance(payload, dict):
            if payload.get("pull_request") is not None:
                typ = "pr"
            elif payload.get("sha"):
                typ = "commit"

        key = f"gh:{cfg['owner']}/{cfg['repo']}:{typ}:{r['external_id']}"
        doc = {
            "type": typ,
            "repo": f"{cfg['owner']}/{cfg['repo']}",
            "external_id": r["external_id"],
            "title": (payload or {}).get("title"),
            "body": (payload or {}).get("body"),
            "url": (payload or {}).get("html_url"),
            "state": (payload or {}).get("state"),
            "number": (payload or {}).get("number"),
            "author": ((payload or {}).get("user") or {}).get("login"),
            "labels": [lbl.get("name") for lbl in (payload or {}).get("labels", []) if isinstance(lbl, dict)],
            "created_at": (payload or {}).get("created_at"),
            "updated_at": (payload or {}).get("updated_at"),
        }

        cur.execute(
            """
            INSERT INTO memory_entries (silo, key, payload)
            SELECT %s, %s, %s::json
            WHERE NOT EXISTS (
              SELECT 1 FROM memory_entries WHERE silo=%s AND key=%s
            )
            """,
            ("github", key, json.dumps(doc), "github", key),
        )
        inserted += cur.rowcount

    # Telemetry counts
    cur.execute("SELECT COUNT(*) AS n FROM raw_documents WHERE config_id=%s", (cfg["id"],))
    raw_total = int(cur.fetchone()["n"])
    cur.execute("SELECT COUNT(*) AS n FROM memory_entries WHERE silo='github'")
    mem_total = int(cur.fetchone()["n"])

    conn.commit()
    conn.close()

    # Durable event for SSE (emit after commit so readers can see the rows)
    event_bus.emit_event(
        "memory.ingest",
        {"source": "github", "connector": connector_name, "inserted": inserted}
    )
    logger.info(
        "[ingest] completed github ingest name=%s inserted=%s raw_total=%s mem_total=%s",
        connector_name, inserted, raw_total, mem_total
    )
    return {"inserted": inserted, "raw_total": raw_total, "mem_total": mem_total}


@app.post("/api/connectors/{name}/ingest", tags=["Connectors"])
def api_ingest_connector(name: str, api_key: str = Depends(require_api_key)):
    """One-shot transform of GitHub raw_documents -> memory_entries for this connector.
    Returns insert count and totals; also emits a `memory.ingest` SSE event via the durable outbox.
    """
    try:
        logger.info("[ingest] API request received for connector=%s", name)
        result = _ingest_github_for_config(name)
        logger.info("[ingest] API ingest done for connector=%s -> %s", name, result)
        return {"ok": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _connector_worker(stop_event: asyncio.Event) -> None:
    logger.info(
        "[connectors] worker started interval=%ss (enabled=%s)",
        CONNECTOR_SYNC_INTERVAL,
        ENABLE_CONNECTOR_WORKER,
    )
    try:
        while not stop_event.is_set():
            configs = await _run_db(chatlog_db.list_connector_configs, "github")
            if not configs:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=CONNECTOR_SYNC_INTERVAL)
                except asyncio.TimeoutError:
                    continue
                else:
                    break
            for cfg in configs:
                if stop_event.is_set():
                    break
                await _run_github_sync(cfg)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=CONNECTOR_SYNC_INTERVAL)
            except asyncio.TimeoutError:
                continue
    except asyncio.CancelledError:  # pragma: no cover
        logger.debug("[connectors] worker cancelled")
        raise
    finally:
        logger.info("[connectors] worker stopped")


# on_event startup/shutdown migrated to lifespan above


async def _run_db(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


# =========================
# Chat Threads API
# =========================


@app.post("/chat/threads", tags=["Chat"])
def chat_create_thread(body: dict = Body(...)):
    """Create a chat thread and return identifier metadata."""
    try:
        payload = body or {}
        raw_title = payload.get("title")
        title = (
            str(raw_title).strip() if raw_title is not None else "New Chat"
        ) or "New Chat"
        raw_user = payload.get("user_id")
        user_id = str(raw_user) if raw_user not in (None, "") else "default"
        raw_summary = payload.get("summary")
        summary = str(raw_summary).strip() if raw_summary is not None else ""
        project_id = payload.get("project_id")
        normalized_project: Optional[int] = None
        if project_id is not None:
            try:
                normalized_project = int(project_id)
            except (TypeError, ValueError):
                normalized_project = None
        if normalized_project is None:
            # default to Loose Threads (id=1)
            normalized_project = 1

        # Idempotency guard: check for recent empty thread from same user
        recent_thread = chatlog_db.get_recent_thread(user_id)
        if recent_thread:
            # If recent thread exists and has no messages, reuse it
            recent_id = recent_thread.get("id")
            if recent_id and chatlog_db.count_messages(recent_id) == 0:
                logger.info(
                    "Reusing recent empty thread %s for user %s", recent_id, user_id
                )
                return {"ok": True, "id": recent_id, "thread": recent_thread}

        record = chatlog_db.create_chat_thread(
            user_id=user_id,
            title=title,
            summary=summary,
            project_id=normalized_project,
        )
        chatlog_db.write_audit_log(
            "create", "chat_thread", str(record["id"]), user_id=user_id
        )
        return {"ok": True, "id": record["id"], "thread": record}
    except Exception as exc:
        logger.exception("Failed to create chat thread: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create chat thread")


@app.get("/chat/threads", tags=["Chat"])
def chat_list_threads():
    """Return the list of persisted chat threads."""
    try:
        threads = chatlog_db.list_chat_threads()
        return {"ok": True, "threads": threads}
    except Exception as exc:
        logger.exception("Failed to list chat threads: %s", exc)
        return {"ok": True, "threads": []}


# =========================
# Chat API (persisted messages)
# =========================


@app.post("/chat/{thread_id}/messages")
def chat_post_message(thread_id: int, body: Dict[str, str] = Body(...)):
    role = body.get("role")
    content = body.get("content", "").strip()
    if not role or not content:
        return JSONResponse(
            status_code=400, content={"ok": False, "error": "role and content required"}
        )
    owner = body.get("user_id") or "default"
    try:
        chatlog_db.ensure_chat_thread(
            thread_id=thread_id,
            user_id=str(owner),
            title="New Chat",
            summary="",
            project_id=1,  # always assign to Loose Threads by default
        )
    except Exception as exc:
        logger.exception("Failed to ensure chat thread %s exists: %s", thread_id, exc)
        raise HTTPException(status_code=500, detail="Failed to persist chat message")
    mid = chatlog_db.create_message(thread_id, role, content)
    chatlog_db.write_audit_log("create", "chat_message", str(mid), user_id=str(owner))

    # Emit event for real-time updates
    event_bus.emit_event(
        "message.created",
        {
            "thread_id": thread_id,
            "message_id": mid,
            "role": role,
            "content": content,
        },
    )

    # --- Neo4j sync ---
    try:
        # Import here in case not already
        from datetime import datetime
        import uuid
        # Use string IDs for Neo4j
        message_id = str(mid)
        thread_id_str = str(thread_id)
        user_id_str = str(owner)
        message_text = content

        neo_user = UserNode.nodes.get_or_none(user_id=user_id_str)
        if not neo_user:
            neo_user = UserNode(user_id=user_id_str, name=user_id_str).save()

        neo_thread = ThreadNode.nodes.get_or_none(thread_id=thread_id_str)
        if not neo_thread:
            neo_thread = ThreadNode(thread_id=thread_id_str).save()

        neo_msg = MessageNode(
            message_id=message_id,
            content=message_text,
            created_at=datetime.utcnow()
        ).save()

        neo_msg.user.connect(neo_user)
        neo_msg.thread.connect(neo_thread)

    except Exception as e:
        print(f"[Neo4j Sync Error] {e}")

    return {
        "ok": True,
        "message": {
            "id": mid,
            "thread_id": thread_id,
            "role": role,
            "content": content,
        },
    }


@app.get("/chat/{thread_id}/messages")
def chat_list_messages(thread_id: int, limit: int = 50, offset: int = 0):
    items = chatlog_db.list_messages(thread_id, limit=limit, offset=offset)
    total = chatlog_db.count_messages(thread_id)
    return {"ok": True, "total": total, "messages": items}


# Generate an assistant reply for the given thread using the configured provider and persist it
@app.post("/chat/{thread_id}/complete", tags=["Chat"])
async def chat_complete(thread_id: int, body: Dict[str, Any] = Body(default_factory=dict)):
    """
    Generate an assistant reply for the given thread using the configured provider
    and persist it as a new message (role='assistant'). Emits message.created.
    Optional body:
      - model: override model name
      - max_context: how many recent messages to include (default 50)
    """
    try:
        limit = int(body.get("max_context") or 50)
        items = chatlog_db.list_messages(thread_id, limit=limit, offset=0)

        # Shape OpenAI-style messages; drop empty or literal "null" content
        context: List[Dict[str, str]] = []
        for m in items:
            role = str(m.get("role") or "").strip()
            content = m.get("content")
            if isinstance(content, str) and content.strip() and content.strip().lower() != "null":
                context.append({"role": role, "content": content})

        if not context:
            raise HTTPException(status_code=400, detail="Thread has no usable context")

        if CHAT_PROVIDER != "groq":
            raise HTTPException(status_code=500, detail=f"Unsupported provider: {CHAT_PROVIDER}")

        # Build ContextBroker bundle using latest user message as query
        latest_message = ""
        for m in reversed(items):
            if str(m.get("role") or "").strip() == "user":
                lm = str(m.get("content") or "").strip()
                if lm:
                    latest_message = lm
                    break

        depth = str(body.get("depth") or "normal").strip().lower()
        bundle: Optional[Dict[str, Any]] = None
        try:
            broker = ContextBroker(chatlog_db, _vector_store, _memory_store, _sensors)
            bundle = await broker.assemble(thread_id, query=latest_message, depth=depth)
        except Exception as e:
            logger.warning("[context] broker assemble failed (depth=%s): %s", depth, e)
            bundle = None

        model = body.get("model") or DEFAULT_MODEL
        assistant_text = _groq_complete(context, model=model, context=bundle)

        mid = chatlog_db.create_message(thread_id, "assistant", assistant_text)
        try:
            chatlog_db.write_audit_log("create", "chat_message", str(mid), user_id="bot")
        except Exception:
            pass

        try:
            event_bus.emit_event("message.created", {"thread_id": thread_id, "message_id": mid, "role": "assistant"})
        except Exception:
            logger.debug("[live] emit message.created failed", exc_info=True)

        return {"ok": True, "message": {"id": mid, "thread_id": thread_id, "role": "assistant", "content": assistant_text}}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("complete failed: %s", exc)
        raise HTTPException(status_code=500, detail="completion_failed")


@app.delete("/chat/{thread_id}/messages/{message_id}")
def chat_delete_message(thread_id: int, message_id: int):
    chatlog_db.delete_message(thread_id, message_id)
    chatlog_db.write_audit_log(
        "delete", "chat_message", str(message_id), user_id="default"
    )
    return {"ok": True}


# =========================
# Thread management
# =========================


def _normalize_thread_title(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw).strip()
    return text or "New Chat"


def _normalize_thread_summary(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    return str(raw).strip()


def _apply_thread_update(thread_id: int, update: ThreadUpdate) -> Dict[str, Any]:
    payload = update.dict(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    updated_field_keys = [key for key in ("title", "summary", "project_id") if key in payload]
    existing = chatlog_db.get_chat_thread(thread_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Thread not found")

    title_value = _normalize_thread_title(payload.get("title")) if "title" in payload else None
    summary_value = _normalize_thread_summary(payload.get("summary")) if "summary" in payload else None
    project_present = "project_id" in payload
    project_value = payload.get("project_id") if project_present else None
    archived_present = "archived" in payload
    archived_requested = payload.get("archived") if archived_present else None

    has_field_updates = any(
        field is not None for field in (
            title_value if "title" in payload else None,
            summary_value if "summary" in payload else None,
            project_value if project_present else None,
        )
    ) or project_present and payload.get("project_id") is None

    if not has_field_updates and not archived_present:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    if has_field_updates:
        updated = chatlog_db.update_thread(
            thread_id,
            title=title_value if "title" in payload else None,
            summary=(summary_value if "summary" in payload else None),
            project_id=project_value if project_present else None,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Thread not found")

    refreshed = chatlog_db.get_chat_thread(thread_id)
    if not refreshed:
        raise HTTPException(status_code=404, detail="Thread not found")

    if has_field_updates:
        chatlog_db.write_audit_log(
            "update",
            "chat_thread",
            str(thread_id),
            user_id=refreshed.get("user_id", "default"),
        )
        event_bus.emit_event(
            "thread.updated",
            {
                "thread": refreshed,
                "changes": {key: payload.get(key) for key in updated_field_keys},
            },
        )
        logger.info(
            "[threads] updated thread_id=%s fields=%s",
            thread_id,
            updated_field_keys or list(payload.keys()),
        )

    if archived_requested is True:
        # Archive if not already archived
        if not refreshed.get("archived_at"):
            archived = chatlog_db.archive_thread(thread_id)
            if archived:
                refreshed = archived
                event_bus.emit_event("thread.archived", {"thread": archived})
                logger.info("[threads] archived thread_id=%s", thread_id)
                chatlog_db.write_audit_log(
                    "archive",
                    "chat_thread",
                    str(thread_id),
                    user_id=archived.get("user_id", "default"),
                )
        else:
            logger.debug("Thread %s already archived", thread_id)
    elif archived_requested is False:
        # Unarchive if currently archived
        if refreshed.get("archived_at"):
            unarchived = chatlog_db.unarchive_thread(thread_id)
            if unarchived:
                refreshed = unarchived
                event_bus.emit_event("thread.unarchived", {"thread": unarchived})
                logger.info("[threads] unarchived thread_id=%s", thread_id)
                chatlog_db.write_audit_log(
                    "unarchive",
                    "chat_thread",
                    str(thread_id),
                    user_id=unarchived.get("user_id", "default"),
                )
        else:
            logger.debug("Thread %s already unarchived", thread_id)

    return refreshed


@app.post("/chat/{thread_id}/branch", response_model=ThreadDTO, tags=["Chat"])
def branch_thread(
    thread_id: int,
    body: Optional[ThreadBranchRequest] = Body(default=None),
    api_key: str = Depends(require_api_key),
):
    payload = body or ThreadBranchRequest()
    parent = chatlog_db.get_chat_thread(thread_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Thread not found")

    title = _normalize_thread_title(payload.title)
    if title is None:
        base_title = parent.get("title") or "New Chat"
        title = f"{base_title} (branch)"

    summary = _normalize_thread_summary(payload.summary)
    if summary is None:
        summary = parent.get("summary") or ""

    project_id: Optional[int]
    if payload.project_id is not None:
        project_id = payload.project_id
    else:
        project_id = parent.get("project_id")
        try:
            project_id = int(project_id) if project_id is not None else None
        except (TypeError, ValueError):
            project_id = None

    child = chatlog_db.create_chat_thread(
        user_id=parent.get("user_id", "default"),
        title=title,
        summary=summary,
        project_id=project_id,
        parent_id=parent["id"],
    )

    chatlog_db.write_audit_log(
        "create",
        "chat_thread",
        str(child["id"]),
        user_id=child.get("user_id", "default"),
    )

    event_bus.emit_event(
        "thread.branch",
        {
            "parent": {
                "id": parent.get("id"),
                "title": parent.get("title"),
                "archived_at": parent.get("archived_at"),
                "project_id": parent.get("project_id"),
            },
            "child": child,
        },
    )

    return child


@app.patch("/chat/{thread_id}", response_model=ThreadDTO, tags=["Chat"])
def update_thread(thread_id: int, payload: ThreadUpdate, api_key: str = Depends(require_api_key)):
    updated = _apply_thread_update(thread_id, payload)
    return updated


@app.patch("/chat/threads/{thread_id}", tags=["Chat"])
def patch_thread(thread_id: int, body: Dict[str, object] = Body(...)):
    try:
        update = ThreadUpdate(**(body or {}))
        refreshed = _apply_thread_update(thread_id, update)
        return {"ok": True, "thread": refreshed}
    except ValidationError as err:
        logger.warning("Invalid payload for thread update: %s", err)
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Invalid payload"},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update chat thread %s: %s", thread_id, exc)
        return JSONResponse(
            status_code=500, content={"ok": False, "error": "Failed to update thread"}
        )


@app.delete("/chat/{thread_id}")
def delete_thread(thread_id: int, force: bool = Query(False)):
    """Hard delete a thread regardless of archived state."""
    deleted = chatlog_db.delete_thread(thread_id, force=force)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Thread not found or not deletable (archive first or set force=true)"
        )
    try:
        event_bus.emit_event("thread.deleted", {"thread_id": thread_id})
    except Exception:
        pass
    logger.info("[threads] deleted thread_id=%s", thread_id)
    return {"ok": True}
# =========================
# Memory API (ephemeral, midterm, longterm)
# =========================


def _silo_valid(s: str) -> bool:
    return s in ("ephemeral", "midterm", "longterm")


@app.get("/api/memory/{silo}")
def memory_list(silo: str, limit: int = 50, offset: int = 0):
    if not _silo_valid(silo):
        return JSONResponse(
            status_code=400, content={"ok": False, "error": "invalid silo"}
        )
    if silo == "ephemeral":
        items = EPHEMERAL_MEMORY[offset : offset + limit]
        return {"ok": True, "count": len(EPHEMERAL_MEMORY), "entries": items}
    items = chatlog_db.list_memories(silo, limit=limit, offset=offset)
    count = chatlog_db.count_memories(silo)
    return {"ok": True, "count": count, "entries": items}


@app.post("/api/memory/{silo}")
def memory_create(silo: str, body: Dict[str, object] = Body(...)):
    if not _silo_valid(silo):
        return JSONResponse(
            status_code=400, content={"ok": False, "error": "invalid silo"}
        )
    content = str(body.get("content", "")).strip()
    tags = ",".join(body.get("tags", []) or [])
    pinned = bool(body.get("pinned", False))
    if not content:
        return JSONResponse(
            status_code=400, content={"ok": False, "error": "content required"}
        )
    if silo == "ephemeral":
        entry = {
            "id": len(EPHEMERAL_MEMORY) + 1,
            "user_id": "default",
            "silo": "ephemeral",
            "content": content,
            "tags": tags,
            "pinned": pinned,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        EPHEMERAL_MEMORY.append(entry)
        return {"ok": True, "entry": entry}
    eid = chatlog_db.add_memory("default", silo, content, tags=tags, pinned=pinned)
    chatlog_db.write_audit_log("create", "memory_entry", str(eid), user_id="default")
    return {"ok": True, "id": eid}


@app.patch("/api/memory/{silo}/{entry_id}")
def memory_update(silo: str, entry_id: int, body: Dict[str, object] = Body(...)):
    if not _silo_valid(silo):
        return JSONResponse(
            status_code=400, content={"ok": False, "error": "invalid silo"}
        )
    if silo == "ephemeral":
        for e in EPHEMERAL_MEMORY:
            if e.get("id") == entry_id:
                if "content" in body:
                    e["content"] = str(body["content"])
                if "tags" in body:
                    e["tags"] = ",".join(body.get("tags", []) or [])
                if "pinned" in body:
                    e["pinned"] = bool(body["pinned"])
                e["updated_at"] = datetime.utcnow().isoformat()
                return {"ok": True}
        return JSONResponse(
            status_code=404, content={"ok": False, "error": "not found"}
        )
    chatlog_db.update_memory(
        entry_id,
        content=body.get("content"),
        tags=(
            ",".join(body.get("tags", []) or [])
            if body.get("tags") is not None
            else None
        ),
        pinned=body.get("pinned") if body.get("pinned") is not None else None,
    )
    chatlog_db.write_audit_log(
        "update", "memory_entry", str(entry_id), user_id="default"
    )
    return {"ok": True}


@app.delete("/api/memory/{silo}/{entry_id}")
def memory_delete(silo: str, entry_id: int):
    if not _silo_valid(silo):
        return JSONResponse(
            status_code=400, content={"ok": False, "error": "invalid silo"}
        )
    if silo == "ephemeral":
        idx = next(
            (i for i, e in enumerate(EPHEMERAL_MEMORY) if e.get("id") == entry_id), -1
        )
        if idx >= 0:
            EPHEMERAL_MEMORY.pop(idx)
            return {"ok": True}
        return JSONResponse(
            status_code=404, content={"ok": False, "error": "not found"}
        )
    chatlog_db.delete_memory(entry_id)
    chatlog_db.write_audit_log(
        "delete", "memory_entry", str(entry_id), user_id="default"
    )
    return {"ok": True}


# =========================
# Health endpoints for chat/memory
# =========================


@app.get("/health/memory")
def health_memory():
    return {
        "ok": True,
        "silos": {
            "ephemeral": len(EPHEMERAL_MEMORY),
            "midterm": chatlog_db.count_memories("midterm"),
            "longterm": chatlog_db.count_memories("longterm"),
        },
    }


@app.get("/health/chat")
def health_chat():
    try:
        threads = chatlog_db.count_chat_threads()
        messages = chatlog_db.count_all_messages()
    except Exception as _e:
        logger.warning("[health/chat] check failed: %s", _e)
        threads = 0
        messages = 0
    return {"ok": True, "threads": threads, "messages": messages, "backend": DB_BACKEND}


# =========================
# Projects management
# =========================


@app.patch("/projects/{project_id}")
def patch_project(project_id: int, body: Dict[str, object] = Body(...)):
    name = body.get("name")
    description = body.get("description")
    try:
        chatlog_db.update_project(
            project_id,
            name=name if name is not None else None,
            description=description if description is not None else None,
        )
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})


@app.delete("/projects/{project_id}")
def delete_project_and_eject(project_id: int):
    # Eject threads from this project first
    try:
        chatlog_db.eject_threads_from_project(project_id)
    except Exception as e:
        logger.warning("eject threads failed: %s", e)
    # Delete project row
    try:
        deleted = chatlog_db.delete_project(project_id)
        if not deleted:
            return JSONResponse(
                status_code=404, content={"ok": False, "error": "Project not found"}
            )
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})


# =========================
# Pydantic Models
# =========================


class CapsuleCreate(BaseModel):
    summary: str
    child_ids: List[int] = []
    tag: Optional[str] = None
    agent: Optional[str] = None


class LogEntry(BaseModel):
    command: str
    tag: Optional[str] = None
    agent: Optional[str] = "system"


class SummaryEntry(BaseModel):
    parent_id: int
    summary: str
    tag: Optional[str] = None
    agent: Optional[str] = "system"


class GeminiChatRequest(BaseModel):
    prompt: str
    model: Optional[str] = "gemini-1.5"


class GeminiChatResponse(BaseModel):
    model_used: str
    reply: str


# =========================
# Memory Management Endpoints
# =========================


@app.get("/ping", summary="Health check endpoint", tags=["Memory"])
def ping():
    """
    Simple health check endpoint to verify that the Guardian API is awake.
    """
    logger.debug("Ping request received")
    return {"status": "Guardian awake!"}


# =========================
# Diagnostics Endpoints
# =========================
@app.get(
    "/authz/debug", tags=["Diag"], summary="Echo masked API key received in header"
)
def authz_debug(api_key: str = Depends(require_api_key)):
    """Return the masked API key received via X-API-Key, masked for safety."""
    key = api_key or ""
    masked = (key[:4] + "…" + key[-4:]) if len(key) > 8 else key
    return {"received_api_key": masked}

# --- Session token minting ---------------------------------------------------
class SessionRequest(BaseModel):
    ttl_seconds: int | None = None

@app.post("/auth/session", tags=["Auth"], summary="Exchange API key for a short-lived session token")
def create_session(body: SessionRequest, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    expected = os.getenv("GUARDIAN_API_KEY") or ""
    if not (x_api_key and secrets.compare_digest(x_api_key, expected)):
        raise HTTPException(status_code=401, detail="API key required to mint session")
    token, exp = issue_session_token(subject="web", ttl_seconds=body.ttl_seconds or 24 * 3600)
    return {"token": token, "expires": exp}

from fastapi import Response

@app.post("/auth/session/cookie", tags=["Auth"], summary="Mint a session token and set it as an HttpOnly cookie")
def create_session_cookie(
    response: Response,
    body: SessionRequest,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    expected = os.getenv("GUARDIAN_API_KEY") or ""
    if not (x_api_key and secrets.compare_digest(x_api_key, expected)):
        raise HTTPException(status_code=401, detail="API key required to mint session")
    token, exp = issue_session_token(subject="web", ttl_seconds=body.ttl_seconds or 24 * 3600)
    max_age = (body.ttl_seconds or 24 * 3600)
    # NOTE: set secure=True when serving over HTTPS
    response.set_cookie("gc_session", token, max_age=max_age, httponly=True, samesite="Lax", secure=False)
    return {"ok": True, "expires": exp}


# Health endpoint for diagnostics
@app.get("/healthz", tags=["Diag"], summary="DB health and table existence")
def healthz():
    """
    Returns DB target and existence of projects/chat_threads for quick diagnostics.
    """
    db_target = PG_DSN if DB_BACKEND == "postgres" else SQLITE_PATH
    projects_exists = False
    threads_exists = False
    try:
        projects_exists = chatlog_db.table_exists("projects")
        threads_exists = chatlog_db.table_exists("chat_threads")
    except Exception as e:
        logger.warning("/healthz check failed: %s", e)
    return {
        "db_target": db_target,
        "backend": DB_BACKEND,
        "projects_table_exists": projects_exists,
        "chat_threads_table_exists": threads_exists,
    }


# Debug config endpoint (development only)
@app.get(
    "/debug/config",
    tags=["Diag"],
    summary="Return masked config for debugging (development only)",
)
def debug_config(api_key: str = Depends(require_api_key)):
    """
    Return a small, masked snapshot of runtime config useful for local debugging.
    This endpoint requires a valid X-API-Key header and is intended for dev use only.
    """
    env = os.getenv("GUARDIAN_ENV", "development")
    masked_key = (
        (API_KEY[:4] + "…" + API_KEY[-4:]) if API_KEY and len(API_KEY) > 8 else API_KEY
    )
    db_target = PG_DSN if DB_BACKEND == "postgres" else SQLITE_PATH
    return {
        "env": env,
        "db_target": db_target,
        "db_backend": DB_BACKEND,
        "provider": GUARDIAN_PROVIDER,
        "allowed_origins": allowed_origins,
        "masked_api_key": masked_key,
        "groq_available": bool(get_groq_chat()),
    }


@app.post("/log", summary="Log a command entry", tags=["Memory"])
def log_entry(entry: LogEntry, api_key: str = Depends(require_api_key)):
    """
    Log a command entry into the Guardian memory database.

    Args:
        entry (LogEntry): The log entry data.

    Returns:
        dict: Confirmation message with timestamp.
    """
    timestamp = datetime.now().isoformat()
    try:
        chatlog_db.insert_memory_event(
            content=entry.command,
            tag=entry.tag,
            agent=entry.agent or "system",
            type_="log",
            parent_id=None,
        )
        logger.info(f"Log entry stored: {entry.command}")
    except Exception as e:
        logger.error(f"Failed to store log entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to store log entry")
    return {"result": "Log stored!", "timestamp": timestamp}


@app.post("/summarize", summary="Store a summary entry", tags=["Memory"])
def summarize_entry(entry: SummaryEntry, api_key: str = Depends(require_api_key)):
    """
    Store a summary related to a parent entry in the Guardian memory database.

    Args:
        entry (SummaryEntry): The summary entry data.

    Returns:
        dict: Confirmation message with timestamp.
    """
    timestamp = datetime.now().isoformat()
    try:
        chatlog_db.insert_memory_event(
            content=entry.summary,
            tag=entry.tag,
            agent=entry.agent or "system",
            type_="summary",
            parent_id=entry.parent_id,
        )
        logger.info(f"Summary entry stored for parent_id {entry.parent_id}")
    except Exception as e:
        logger.error(f"Failed to store summary entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to store summary entry")
    return {"result": "Summary stored!", "timestamp": timestamp}



@app.get("/search", summary="Search memory entries", tags=["Memory"])
def search(
    query: str = Query(..., description="Search query string"),
    limit: int = Query(10, ge=1, le=100),
    api_key: str = Depends(require_api_key),
):
    """
    Search the Guardian memory entries matching the query string.

    Args:
        query (str): The search query.
        limit (int): Maximum number of results to return.

    Returns:
        List[dict]: List of matching memory entries.
    """
    try:
        rows = chatlog_db.search_memory(query, limit)
        results = [
            {
                "timestamp": r["timestamp"],
                "command": r["command"],
                "tag": r["tag"],
                "agent": r["agent"],
            }
            for r in rows
        ]
        logger.info(
            f"Search performed with query: {query}, results found: {len(results)}"
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search operation failed")
    return results


# --- GitHub-specific memory search endpoint ---
@app.get(
    "/api/github/search",
    summary="Search GitHub memory (github silo)",
    tags=["Memory"],
)
def github_memory_search(
    query: str = Query(
        ...,
        description="Search query string (full‑text over GitHub issues/PRs)",
    ),
    repo: Optional[str] = Query(
        None,
        description="Optional owner/repo filter (e.g. Resonant-Jones/guardian-backend)",
    ),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of results to return"
    ),
    api_key: str = Depends(require_api_key),
):
    """
    Search the GitHub documents that were ingested into the `memory_entries`
    table (silo='github'). Supports an optional `repo` filter.
    """
    try:
        rows = chatlog_db.search_github_memory(query, repo=repo, limit=limit)
        results = []
        for r in rows:
            payload = r.get("payload") or {}
            results.append(
                {
                    "id": r["id"],
                    "key": r["key"],
                    "repo": payload.get("repo"),
                    "type": payload.get("type"),
                    "title": payload.get("title"),
                    "url": payload.get("url"),
                    "state": payload.get("state"),
                    "created_at": payload.get("created_at"),
                }
            )
        return {"ok": True, "count": len(results), "results": results}
    except Exception as exc:
        logger.error("GitHub memory search failed: %s", exc)
        raise HTTPException(
            status_code=500, detail="GitHub memory search failed"
        )


@app.get(
    "/history",
    summary="Retrieve history entries with optional filters",
    tags=["Memory"],
)
def history(
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of entries to return"
    ),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    agent: Optional[str] = Query(None, description="Filter by agent"),
    start_date: Optional[str] = Query(
        None, description="Filter entries from this date (inclusive), format YYYY-MM-DD"
    ),
    end_date: Optional[str] = Query(
        None,
        description="Filter entries up to this date (inclusive), format YYYY-MM-DD",
    ),
    api_key: str = Depends(require_api_key),
):
    """
    Retrieve history entries from Guardian memory with optional filtering by tag, agent, and date range.

    Args:
        limit (int): Maximum number of entries to return.
        tag (Optional[str]): Filter entries by tag.
        agent (Optional[str]): Filter entries by agent.
        start_date (Optional[str]): Filter entries from this date (inclusive).
        end_date (Optional[str]): Filter entries up to this date (inclusive).

    Returns:
        List[dict]: List of filtered history entries.
    """
    # Validate date formats
    start_dt = None
    end_dt = None
    try:
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as ve:
        logger.error(f"Invalid date format in history filters: {ve}")
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD."
        )

    try:
        rows = chatlog_db.history_entries(limit=limit, tag=tag, agent=agent)
        filtered_rows = []
        for r in rows:
            entry_dt = datetime.fromisoformat(r["timestamp"])
            if start_dt and entry_dt < start_dt:
                continue
            if end_dt and entry_dt > end_dt:
                continue
            filtered_rows.append(r)
        results = [
            {
                "timestamp": r["timestamp"],
                "command": r["command"],
                "tag": r["tag"],
                "agent": r["agent"],
            }
            for r in filtered_rows
        ]
        logger.info(
            f"History retrieved with filters - tag: {tag}, agent: {agent}, start_date: {start_date}, end_date: {end_date}, entries returned: {len(results)}"
        )
    except Exception as e:
        logger.error(f"Failed to retrieve history entries: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve history entries"
        )
    return results


# =========================
# Thread Lineage Endpoints
# =========================


class ThreadCreateRequest(BaseModel):
    parent_thread_id: int = None
    session_id: str = None
    summary: str = ""
    user_id: str = "default"
    project_id: str = None


@app.get("/threads", summary="List all threads", tags=["Threads"])
def list_threads(
    user_id: str = Query(None, description="Filter by user_id"),
    project_id: str = Query(None, description="Filter by project_id"),
    api_key: str = Depends(require_api_key),
):
    """
    List all threads. Optionally filter by user or project.
    """
    try:
        items = chatlog_db.list_threads(user_id=user_id, project_id=project_id)
        return {"threads": items}
    except Exception as exc:
        if (
            "no such table" in str(exc).lower()
            or getattr(exc, "pgcode", None) == "42P01"
        ):
            return {"threads": []}
        logger.exception("Thread listing failed")
        raise HTTPException(status_code=500, detail="Thread listing failed")


@app.get("/thread/{thread_id}", summary="Get thread details", tags=["Threads"])
def get_thread(thread_id: int, api_key: str = Depends(require_api_key)):
    """
    Get details for a specific thread by thread_id.
    """
    row = chatlog_db.get_thread(thread_id)
    if not row:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {
        "thread_id": row[0],
        "parent_thread_id": row[1],
        "session_id": row[2],
        "summary": row[3],
        "created_at": row[4],
        "user_id": row[5],
        "project_id": row[6],
    }


@app.get("/thread/{thread_id}/children", summary="List child threads", tags=["Threads"])
def get_child_threads(thread_id: int, api_key: str = Depends(require_api_key)):
    """
    List all child threads for a parent thread.
    """
    rows = chatlog_db.get_child_threads(thread_id)
    results = [
        {
            "thread_id": row.get("id"),
            "user_id": row.get("user_id"),
            "title": row.get("title"),
            "summary": row.get("summary"),
            "project_id": row.get("project_id"),
            "parent_id": row.get("parent_id"),
            "archived_at": row.get("archived_at"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }
        for row in rows
    ]
    return {"children": results}


@app.get("/thread/{thread_id}/summary", summary="Get thread summary", tags=["Threads"])
def get_thread_summary(thread_id: int, api_key: str = Depends(require_api_key)):
    """
    Get the summary for a thread.
    """
    summary = chatlog_db.get_thread_summary(thread_id)
    return {"thread_id": thread_id, "summary": summary}


@app.post("/thread", summary="Create a new thread", tags=["Threads"], status_code=201)
def create_thread(req: ThreadCreateRequest, api_key: str = Depends(require_api_key)):
    """
    Create a new thread with optional parent, summary, session, user, and project.
    Returns the new thread_id.
    """
    thread_id = chatlog_db.create_thread(
        parent_thread_id=req.parent_thread_id,
        session_id=req.session_id,
        summary=req.summary,
        user_id=req.user_id,
        project_id=req.project_id,
    )
    return {"thread_id": thread_id}


# Alias: POST /threads (frontend convenience)
@app.post(
    "/threads",
    summary="Create a new thread (alias of /thread)",
    tags=["Threads"],
    status_code=201,
)
def create_thread_alias(
    req: ThreadCreateRequest, api_key: str = Depends(require_api_key)
):
    return create_thread(req, api_key)


# =========================
# Projects Endpoints
# =========================


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""
