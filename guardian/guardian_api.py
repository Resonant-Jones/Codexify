# =========================
# Imports
# =========================

"""guardian_api module

Provides FastAPI routes for the Guardian backend, handling chat, memory,
and connector APIs. Includes authentication, environment loading, and
integration with various providers.
"""

import asyncio
import json
import logging

# Standard Library
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

# Third-Party
import requests
from dotenv import load_dotenv
from fastapi import (
    Body,
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
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

# DB adapters
from guardian.core.chat_db import ChatDB
from guardian.core.db import GuardianDB
from guardian.routes.codexify_router import router as codexify_router

try:
    from guardian.core.pgdb import PgDB  # type: ignore
except Exception as _pg_exc:  # pragma: no cover
    PgDB = None  # type: ignore
    _PG_IMPORT_ERROR = _pg_exc
else:
    _PG_IMPORT_ERROR = None
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
from guardian.routes import agent, memory, research, threads

# Optional AI Backend
try:
    from guardian.core.ai_router import chat_with_ai
except ModuleNotFoundError as e:
    chat_with_ai = None
    logging.warning(f"[Codexify ⚠️] Optional chat_with_ai module not available: {e}")

# Optional Groq provider
try:
    from guardian.providers.groq_client import get_groq_chat  # lazy Groq client factory
except ModuleNotFoundError as e:
    # Fallback: define a stub that signals unavailability
    def get_groq_chat():  # type: ignore
        return None

    logging.warning(f"[Codexify ⚠️] Optional groq_client not available: {e}")

# API Key authentication is enforced on all major endpoints (except /ping, /test, /)
# Pass `X-API-Key` header with your requests.

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---- Env loading (backend) -----------------------------------------------
def _load_env_chain() -> None:
    """Load .env files in backend-friendly order without clobbering OS env.
    Order: .env -> .env.backend.<mode> -> .env.local
    The later files win when a key is not already in the environment.
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
    if api_key != API_KEY:
        # Do not log the provided key to avoid leaking secrets.
        logger.warning("Unauthorized attempt with API key")
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return api_key


# Load configuration from environment variables
GEMINI_API_URL = os.getenv("GEMINI_API_URL", "https://api.gemini.ai/v1/chat")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_gemini_api_key_here")

# Provider selection and Groq config
GUARDIAN_PROVIDER = os.getenv("GUARDIAN_PROVIDER", "gemini").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_DEFAULT = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")

# Vision model for image captioning
# Always attempt to load the fast BLIP processor first, then fallback if necessary
try:
    processor = BlipProcessor.from_pretrained(
        "Salesforce/blip-image-captioning-base", use_fast=True
    )
except Exception as e:
    logging.warning(f"Fast BLIP processor unavailable, falling back to slow: {e}")
    processor = BlipProcessor.from_pretrained(
        "Salesforce/blip-image-captioning-base", use_fast=False
    )
vision_model = BlipForConditionalGeneration.from_pretrained(
    "Salesforce/blip-image-captioning-base"
)

# Mondream (symbolic/QA-style) initialization
# Gate behind env flag to avoid noisy startup if not needed

_ENABLE_MONDREAM = os.getenv("GUARDIAN_ENABLE_MONDREAM", "0").lower() in (
    "1",
    "true",
    "yes",
)
mondream_processor = None
mondream_model = None
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
def crop_to_content(pil_img, threshold: int = 10):
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


# ────────────────────────── DB backend selection ────────────────────────────
settings = get_settings()

PG_DSN = os.getenv("GUARDIAN_DB_URL") or os.getenv("DATABASE_URL")
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
else:
    if DB_PATH == "__DISABLE_SQLITE__":
        raise RuntimeError(
            "SQLite disabled but no Postgres DSN supplied; set GUARDIAN_DB_URL or DATABASE_URL"
        )
    effective_sqlite_path = DB_PATH or str(Path("guardian.db"))
    chatlog_db = GuardianDB(effective_sqlite_path)
    DB_BACKEND = "sqlite"

logger.info("📦 DB backend selected: %s", DB_BACKEND)
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

# ---- Memory retention and ephemeral silo
MEMORY_RETENTION_DAYS = int(os.getenv("MEMORY_RETENTION_DAYS", "90"))
EPHEMERAL_MEMORY: list[dict] = []
try:
    from datetime import timedelta

    cutoff = (datetime.utcnow() - timedelta(days=MEMORY_RETENTION_DAYS)).isoformat()
    pruned = chatlog_db.prune_midterm(cutoff)
    if pruned:
        logger.info("[memory] pruned %d expired midterm entries", pruned)
except Exception as _e:
    logger.debug("[memory] prune skipped: %s", _e)

# Initialize FastAPI app
app = FastAPI(title="Guardian Codex API")

# Include routers for modular endpoints
app.include_router(threads.router, prefix="/threads")
app.include_router(research.router, prefix="/research")
app.include_router(memory.router, prefix="/memory")
app.include_router(agent.router, prefix="/agent")
app.include_router(codexify_router)
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
# Tools & Jobs (minimal scaffold)
# =========================
# In-memory job registry (ok for dev; replace with persistent store for prod)
JOBS: Dict[str, dict] = {}


class ToolRequest(BaseModel):
    name: str
    args: dict = Field(default_factory=dict)


class ToolResponse(BaseModel):
    job_id: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    result: dict = Field(default_factory=dict)


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


def _build_connectors() -> List[dict]:
    # Allow operators to declare available connectors via env
    raw = os.getenv("GUARDIAN_CONNECTORS", "google_drive,github")
    ids = [c.strip() for c in raw.split(",") if c.strip()]
    out: List[dict] = []
    for cid in ids:
        out.append(
            {
                "id": cid,
                "name": _display_name(cid),
                "status": _connector_status_from_env(cid),
                "auth": None,
                "syncInterval": "manual",
                "scopes": [],
                "options": [],
            }
        )
    return out


# In-memory list; rebuilt on process start
CONNECTORS: List[dict] = _build_connectors()

# In-memory config and secrets (replace with DB in production)
CONNECTOR_CONFIGS: Dict[str, dict] = {}
CONNECTOR_SECRETS: Dict[str, dict] = {}
AUTH_TX: Dict[str, dict] = {}

# Registry metadata for richer UI
CONNECTOR_REGISTRY: Dict[str, dict] = {
    "github": {
        "id": "github",
        "name": "GitHub",
        "capabilities": {
            "supportsOAuth": True,
            "supportsApiKey": False,
            "supportsLocal": False,
        },
        "requiredFields": [
            {
                "key": "client_id",
                "label": "Client ID",
                "type": "string",
                "secret": False,
            },
            {
                "key": "client_secret",
                "label": "Client Secret",
                "type": "string",
                "secret": True,
            },
        ],
        "scopes": ["repo", "read:org"],
        "options": [
            {
                "key": "syncInterval",
                "label": "Sync every",
                "type": "select",
                "options": ["manual", "15m", "1h", "6h"],
                "value": "1h",
            }
        ],
    },
    "google_drive": {
        "id": "google_drive",
        "name": "Google Drive",
        "capabilities": {
            "supportsOAuth": False,
            "supportsApiKey": True,
            "supportsLocal": False,
        },
        "requiredFields": [
            {"key": "api_key", "label": "API Key", "type": "string", "secret": True},
        ],
        "scopes": [],
        "options": [
            {
                "key": "syncInterval",
                "label": "Sync every",
                "type": "select",
                "options": ["manual", "15m", "1h", "6h"],
                "value": "manual",
            }
        ],
    },
}


@app.get("/api/connectors", tags=["Connectors"])
def list_connectors():
    """Return connectors enriched with metadata and config flags."""
    logger.info("[connectors] GET /api/connectors count=%d", len(CONNECTORS))
    out = []
    for c in CONNECTORS:
        cid = c.get("id")
        meta = CONNECTOR_REGISTRY.get(cid, {"requiredFields": [], "capabilities": {}})
        cfg = CONNECTOR_CONFIGS.get(cid, {})
        # Determine needsAdminSecret: any required secret missing
        needs = False
        for f in meta.get("requiredFields", []):
            if f.get("secret") and not CONNECTOR_SECRETS.get(cid, {}).get(f["key"]):
                needs = True
        oc = {**c}
        oc.update(
            {
                "capabilities": meta.get("capabilities"),
                "requiredFields": meta.get("requiredFields"),
                "scopes": meta.get("scopes", []),
                "options": meta.get("options", []),
                "needsAdminSecret": needs,
            }
        )
        out.append(oc)
    return out


@app.patch("/api/connectors/{connector_id}", tags=["Connectors"])
def update_connector(connector_id: str, updates: dict = Body(...)):
    """Apply shallow updates to a connector in the in-memory stub.
    - Accept only known fields; reject unknown with 400.
    - Always return the updated connector object.
    """
    allowed = {"status", "auth", "syncInterval", "scopes", "options", "name"}
    unknown = [k for k in updates.keys() if k not in allowed]
    if unknown:
        logger.warning(
            "[connectors] PATCH unknown fields id=%s fields=%s", connector_id, unknown
        )
        raise HTTPException(
            status_code=400, detail={"error": f"Unknown fields: {', '.join(unknown)}"}
        )

    for c in CONNECTORS:
        if c.get("id") == connector_id:
            before_status = c.get("status")
            for key in allowed:
                if key in updates:
                    c[key] = updates[key]
            logger.info(
                "[connectors] PATCH id=%s status=%s->%s",
                connector_id,
                before_status,
                c.get("status"),
            )
            return c

    raise HTTPException(status_code=404, detail={"error": "Connector not found"})


@app.get("/api/connectors/{connector_id}", tags=["Connectors"])
def get_connector(connector_id: str):
    for c in CONNECTORS:
        if c.get("id") == connector_id:
            meta = CONNECTOR_REGISTRY.get(connector_id, {})
            cfg = CONNECTOR_CONFIGS.get(connector_id, {})
            needs = False
            for f in meta.get("requiredFields", []):
                if f.get("secret") and not CONNECTOR_SECRETS.get(connector_id, {}).get(
                    f["key"]
                ):
                    needs = True
            out = {
                **c,
                **{
                    "capabilities": meta.get("capabilities"),
                    "requiredFields": meta.get("requiredFields", []),
                    "scopes": meta.get("scopes", []),
                    "options": meta.get("options", []),
                    "needsAdminSecret": needs,
                    "config": {
                        k: (
                            "••••"
                            if any(
                                f.get("key") == k and f.get("secret")
                                for f in meta.get("requiredFields", [])
                            )
                            else v
                        )
                        for k, v in {
                            **cfg,
                            **CONNECTOR_SECRETS.get(connector_id, {}),
                        }.items()
                    },
                },
            }
            return out
    raise HTTPException(status_code=404, detail={"error": "Connector not found"})


@app.post("/api/connectors/{connector_id}/config", tags=["Connectors"])
def set_connector_config(connector_id: str, body: Dict[str, dict] = Body(...)):
    meta = CONNECTOR_REGISTRY.get(connector_id)
    if not meta:
        raise HTTPException(status_code=404, detail={"error": "Connector not found"})
    fields = body.get("fields", {})
    allowed = {f["key"]: f for f in meta.get("requiredFields", [])}
    unknown = [k for k in fields.keys() if k not in allowed]
    if unknown:
        logger.warning(
            "[connectors] CONFIG unknown keys id=%s fields=%s", connector_id, unknown
        )
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": f"Unknown fields: {', '.join(unknown)}"},
        )
    # Persist split by secret flag
    cfg = CONNECTOR_CONFIGS.setdefault(connector_id, {})
    sec = CONNECTOR_SECRETS.setdefault(connector_id, {})
    for k, v in fields.items():
        if allowed[k].get("secret"):
            sec[k] = v
        else:
            cfg[k] = v
    logger.info(
        "[connectors] CONFIG id=%s updated keys=%s", connector_id, list(fields.keys())
    )
    # Return masked config
    masked = {
        k: ("••••" if allowed[k].get("secret") else v)
        for k, v in {**cfg, **sec}.items()
        if k in allowed
    }
    return {"ok": True, "id": connector_id, "config": masked}


@app.post("/api/connectors/github/authorize", tags=["Connectors"])
def github_authorize(body: Dict[str, str] = Body(...)):
    cid = "github"
    redirect_uri = body.get("redirectUri")
    if not redirect_uri:
        raise HTTPException(status_code=400, detail={"error": "redirectUri required"})
    client_id = CONNECTOR_CONFIGS.get(cid, {}).get("client_id") or os.getenv(
        "GITHUB_CLIENT_ID"
    )
    if not client_id:
        raise HTTPException(
            status_code=400, detail={"error": "Client ID missing; set via config first"}
        )
    # PKCE (simplified): generate state and code_verifier; we only return state and authUrl
    import base64
    import hashlib
    import secrets

    def b64url(b: bytes) -> str:
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

    code_verifier = b64url(secrets.token_bytes(32))
    challenge = b64url(hashlib.sha256(code_verifier.encode()).digest())
    state = b64url(secrets.token_bytes(16))
    AUTH_TX[state] = {
        "connector_id": cid,
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
        "ts": datetime.utcnow().isoformat(),
    }
    scope = "repo read:org"
    auth_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&state={state}&code_challenge={challenge}&code_challenge_method=S256"
    )
    logger.info("[connectors] AUTHORIZE id=github state=%s", state)
    return {"authUrl": auth_url, "state": state}


@app.get("/api/connectors/github/callback", tags=["Connectors"])
def github_callback(code: str = Query(...), state: str = Query(...)):
    tx = AUTH_TX.pop(state, None)
    if not tx:
        raise HTTPException(status_code=400, detail={"error": "Invalid state"})
    # In production: exchange code for tokens at GitHub; here we simulate success
    CONNECTOR_SECRETS.setdefault("github", {})["access_token"] = "gho_simulated"
    # Mark status connected
    for c in CONNECTORS:
        if c["id"] == "github":
            c["status"] = "connected"
    logger.info("[connectors] CALLBACK id=github state=%s ok", state)
    # Redirect back to UI
    return {"ok": True, "message": "Authorized"}


@app.post("/api/connectors/{connector_id}/test", tags=["Connectors"])
def connector_test(connector_id: str):
    if connector_id == "github":
        ok = bool(CONNECTOR_SECRETS.get("github", {}).get("access_token"))
        return {"ok": ok, "message": "Connection OK" if ok else "Not connected"}
    return {"ok": True, "message": "Connection OK"}


@app.post("/api/connectors/{connector_id}/sync", tags=["Connectors"])
def connector_sync(connector_id: str):
    jid = str(uuid4())
    JOBS[jid] = {
        "status": "done",
        "result": {"connector": connector_id, "synced": True},
    }
    logger.info("[connectors] SYNC id=%s job_id=%s", connector_id, jid)
    return {"ok": True, "job_id": jid}


@app.get("/health/connectors", tags=["Connectors"])
def connectors_health():
    total = len(CONNECTORS)
    connected = sum(1 for c in CONNECTORS if c.get("status") == "connected")
    return {"ok": True, "count": total, "connected": connected}


@app.get("/jobs/{job_id}", tags=["Tools"])
def jobs_get(job_id: str):
    job = JOBS.get(job_id, {})
    status = job.get("status", "unknown")
    progress = 100 if status == "done" else 0
    last_error = job.get("error") if status == "error" else None
    return {"status": status, "progress": progress, "last_error": last_error}


# =========================
# Event System for Real-time Updates
# =========================


# In-memory event system (simple for MVP, can be replaced with Redis later)
class EventManager:
    def __init__(self):
        self.subscribers = []

    def subscribe(self):
        """Subscribe to events - returns a generator for SSE"""
        queue = []
        self.subscribers.append(queue)
        return queue

    def unsubscribe(self, queue):
        """Unsubscribe from events"""
        if queue in self.subscribers:
            self.subscribers.remove(queue)

    def emit(self, event_type: str, data: dict):
        """Emit an event to all subscribers"""
        event_data = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        # Remove dead subscribers
        dead_subscribers = []
        for queue in self.subscribers:
            try:
                queue.append(event_data)
            except:
                dead_subscribers.append(queue)

        # Clean up dead subscribers
        for queue in dead_subscribers:
            self.unsubscribe(queue)


event_manager = EventManager()

# =========================
# Chat Threads API
# =========================


@app.post("/api/chat/threads", tags=["Chat"])
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


@app.get("/api/chat/threads", tags=["Chat"])
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


@app.post("/api/chat/{thread_id}/messages")
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
    event_manager.emit(
        "message.created",
        {"thread_id": thread_id, "message_id": mid, "role": role, "content": content},
    )

    return {
        "ok": True,
        "message": {
            "id": mid,
            "thread_id": thread_id,
            "role": role,
            "content": content,
        },
    }


@app.get("/api/chat/{thread_id}/messages")
def chat_list_messages(thread_id: int, limit: int = 50, offset: int = 0):
    items = chatlog_db.list_messages(thread_id, limit=limit, offset=offset)
    total = chatlog_db.count_messages(thread_id)
    return {"ok": True, "total": total, "messages": items}


@app.delete("/api/chat/{thread_id}/messages/{message_id}")
def chat_delete_message(thread_id: int, message_id: int):
    chatlog_db.delete_message(thread_id, message_id)
    chatlog_db.write_audit_log(
        "delete", "chat_message", str(message_id), user_id="default"
    )
    return {"ok": True}


# =========================
# Thread management
# =========================


@app.patch("/api/chat/threads/{thread_id}", tags=["Chat"])
def patch_thread(thread_id: int, body: Dict[str, object] = Body(...)):
    if body is None:
        return JSONResponse(
            status_code=400, content={"ok": False, "error": "No fields provided"}
        )

    title: Optional[str] = None
    summary: Optional[str] = None

    if "title" in body:
        raw_title = body.get("title")
        title = (str(raw_title).strip() if raw_title is not None else "") or "New Chat"

    if "summary" in body:
        raw_summary = body.get("summary")
        summary = str(raw_summary).strip() if raw_summary is not None else ""

    project_id = body.get("project_id") if "project_id" in body else None
    normalized_project: Optional[int] = None
    if project_id is not None:
        try:
            normalized_project = int(project_id)
        except (TypeError, ValueError):
            normalized_project = None

    if title is None and summary is None and project_id is None:
        return JSONResponse(
            status_code=400, content={"ok": False, "error": "No valid fields to update"}
        )

    try:
        existing = chatlog_db.get_chat_thread(thread_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Thread not found")

        updated = chatlog_db.update_thread(
            thread_id,
            title=title,
            project_id=normalized_project if project_id is not None else None,
            summary=summary,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Thread not found")

        refreshed = chatlog_db.get_chat_thread(thread_id)
        if refreshed:
            chatlog_db.write_audit_log(
                "update",
                "chat_thread",
                str(thread_id),
                user_id=refreshed.get("user_id", "default"),
            )
        return {"ok": True, "thread": refreshed}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update chat thread %s: %s", thread_id, exc)
        return JSONResponse(
            status_code=500, content={"ok": False, "error": "Failed to update thread"}
        )


@app.delete("/api/chat/threads/{thread_id}")
def delete_thread(thread_id: int):
    try:
        chatlog_db.delete_thread(thread_id)
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})


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
            "thread_id": row[0],
            "session_id": row[1],
            "summary": row[2],
            "created_at": row[3],
            "user_id": row[4],
            "project_id": row[5],
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


@app.post("/projects", summary="Create a project", tags=["Projects"], status_code=201)
def create_project_api(body: ProjectCreate, api_key: str = Depends(require_api_key)):
    try:
        pid = chatlog_db.create_project(body.name, body.description or "")
        return {"project_id": pid}
    except Exception as e:
        # Log full exception for backend diagnostics
        logger.exception("Failed to create project")
        # In development include the error message to aid debugging; keep generic in production
        env = os.getenv("GUARDIAN_ENV", "development")
        if env == "development":
            raise HTTPException(
                status_code=500, detail=f"Failed to create project: {e}"
            )
        raise HTTPException(status_code=500, detail="Failed to create project")


@app.get("/projects", summary="List projects", tags=["Projects"])
def list_projects_api(api_key: str = Depends(require_api_key)):
    try:
        rows = chatlog_db.list_projects()
        results = [
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "description": (r.get("description") or ""),
                "created_at": r.get("created_at"),
                "updated_at": r.get("updated_at"),
            }
            for r in (rows or [])
        ]
        return {"projects": results}
    except Exception:
        logger.exception("Failed to list projects")
        raise HTTPException(status_code=500, detail="Failed to list projects")


@app.delete("/projects/{project_id}", summary="Delete a project", tags=["Projects"])
def delete_project_api(project_id: int, api_key: str = Depends(require_api_key)):
    try:
        ok = chatlog_db.delete_project(project_id)
    except Exception:
        logger.exception("Failed to delete project %s", project_id)
        raise HTTPException(status_code=500, detail="Failed to delete project")
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"deleted": True}


# =========================
# Gemini Proxy Endpoints
# =========================


@app.get("/", summary="Gemini proxy status", tags=["Gemini Proxy"])
def gemini_status():
    """
    Check the status of the Gemini proxy service.
    """
    logger.debug("Gemini status check requested")
    return {"status": "Gemini proxy is running"}


@app.get("/test", summary="Gemini proxy test endpoint", tags=["Gemini Proxy"])
def gemini_test():
    """
    Simple test endpoint for the Gemini proxy.
    """
    logger.debug("Gemini test endpoint called")
    return {"ping": "pong"}


# Unified chat endpoint supporting Gemini and Groq
@app.post(
    "/chat",
    response_model=GeminiChatResponse,
    summary="Send chat prompt to active provider (Gemini or Groq)",
    tags=["Chat"],
)
def unified_chat(
    prompt: str = Form(..., description="The chat prompt"),
    caption_model: str = Form(
        "blip", description="Vision model to use: blip or mondream"
    ),
    model: Optional[str] = Form(None, description="LLM model to use (optional)"),
    files: List[UploadFile] = File([], description="Optional file attachments"),
    api_key: str = Depends(require_api_key),
):
    """
    Send a chat prompt to the active LLM provider (controlled by GUARDIAN_PROVIDER).
    Logs the prompt/response to memory. Provider options: 'gemini' (default), 'groq'.
    """
    # Log incoming prompt (best-effort; don't fail chat if logging fails)
    try:
        chatlog_db.insert_memory_event(
            content=f"User prompt: {prompt}",
            tag=GUARDIAN_PROVIDER,
            agent="user",
            type_="log",
            parent_id=None,
        )
    except Exception as e:
        logger.debug(f"Prompt log failed (non-fatal): {e}")

    # Handle image attachments (real captioning)
    if files:
        captions = []
        for f in files:
            if f.content_type.startswith("image/"):
                # Read+crop
                data = f.file.read()
                img = Image.open(BytesIO(data)).convert("RGB")
                img = crop_to_content(img)
                if (
                    caption_model.lower() == "mondream"
                    and mondream_processor
                    and mondream_model
                ):
                    # Mondream symbolic caption
                    inputs = mondream_processor(images=img, return_tensors="pt")
                    enc = mondream_model.encode_image(**inputs)
                    answer = mondream_model.answer_question(
                        enc,
                        mondream_processor.tokenizer,
                        "Describe every symbolic element in this image.",
                    )
                    captions.append(answer.strip())
                else:
                    # BLIP general caption
                    inputs = processor(images=img, return_tensors="pt")
                    outputs = vision_model.generate(**inputs)
                    caption = processor.decode(outputs[0], skip_special_tokens=True)
                    captions.append(caption)
        if captions:
            prompt = (
                "Here’s what I see in your image:\n"
                + "\n".join(f"- {c}" for c in captions)
                + "\n\n"
                + prompt
            )

    provider = GUARDIAN_PROVIDER

    # GROQ branch
    if provider == "groq":
        gc = get_groq_chat()
        if not gc:
            raise HTTPException(status_code=503, detail="Groq provider not available")
        # Normalize model name: drop any prefix before ':'
        raw_model = model or GROQ_MODEL_DEFAULT
        real_model = raw_model.split(":", 1)[-1]
        try:
            reply_text = gc(prompt, model=real_model)
        except Exception as e:
            logger.error(f"Error contacting Groq API: {e}")
            raise HTTPException(status_code=502, detail=f"Groq API error: {e}")

        # Log AI reply (best-effort)
        try:
            chatlog_db.insert_memory_event(
                content=f"AI reply: {reply_text}",
                tag="groq",
                agent="ai",
                type_="log",
                parent_id=None,
            )
        except Exception as e:
            logger.debug(f"Reply log failed (non-fatal): {e}")

        return GeminiChatResponse(model_used=f"groq:{real_model}", reply=reply_text)

    # GEMINI branch (default)
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": model, "prompt": prompt}
    try:
        response = requests.post(
            GEMINI_API_URL, json=payload, headers=headers, timeout=30
        )
        response.raise_for_status()
        data = response.json()
        reply_text = data.get("reply", "")

        try:
            chatlog_db.insert_memory_event(
                content=f"AI reply: {reply_text}",
                tag="gemini",
                agent="ai",
                type_="log",
                parent_id=None,
            )
        except Exception as e:
            logger.debug(f"Reply log failed (non-fatal): {e}")

        logger.info("Chat interaction logged successfully")
        return GeminiChatResponse(model_used=model or "gemini-1.5", reply=reply_text)
    except requests.HTTPError as http_err:
        logger.error(f"HTTP error contacting Gemini API: {http_err}")
        raise HTTPException(
            status_code=getattr(response, "status_code", 502),
            detail=f"Gemini API error: {http_err}",
        )
    except Exception as e:
        logger.error(f"Error contacting Gemini API: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error contacting Gemini API: {str(e)}"
        )


# Streaming chat endpoint (SSE)
@app.get(
    "/chat/stream", summary="Stream chat tokens from active provider", tags=["Chat"]
)
async def stream_chat(
    request: Request,
    prompt: str = Query(..., description="The chat prompt"),
    provider: Optional[str] = Query(None, description="Provider to use"),
    model: Optional[str] = Query(None, description="Model to use (optional)"),
):
    """
    Stream chat responses token-by-token via SSE.
    """
    # use provided provider or fall back to env default
    provider = (provider or GUARDIAN_PROVIDER).lower()

    # Validate availability BEFORE starting the stream to avoid response-started errors
    gc = get_groq_chat() if provider == "groq" else None
    if provider == "groq" and not gc:
        raise HTTPException(status_code=503, detail="Groq provider not available")

    # Normalize model name for streaming
    raw_model = model or GROQ_MODEL_DEFAULT
    real_model = raw_model.split(":", 1)[-1]

    async def event_generator():
        if provider == "groq":
            for token in gc.stream(prompt, real_model):  # type: ignore[union-attr]
                yield f"data: {token}\n\n"
                if await request.is_disconnected():
                    break
        else:
            # Fallback: synchronous Gemini response as single-chunk SSE
            response = requests.post(
                GEMINI_API_URL,
                json={"model": model, "prompt": prompt},
                headers={"Authorization": f"Bearer {GEMINI_API_KEY}"},
                timeout=30,
            )
            response.raise_for_status()
            reply = response.json().get("reply", "")
            yield f"data: {reply}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/whoami", summary="Get agent profile and identity", tags=["Agent"])
def whoami(
    agent_id: str = Header(..., description="Agent or User ID"),
    api_key: str = Depends(require_api_key),
):
    profile = chatlog_db.get_agent_profile(agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Agent profile not found.")
    return profile


@app.post("/profile", summary="Update agent profile fields", tags=["Agent"])
def update_profile(
    agent_id: str = Header(..., description="Agent or User ID"),
    updates: dict = Body(...),
    api_key: str = Depends(require_api_key),
):
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided.")
    chatlog_db.upsert_agent_profile(agent_id, **updates)
    return {"message": "Profile updated."}


@app.post(
    "/profile/frequency",
    summary="Set/toggle agent summarization frequency",
    tags=["Agent"],
)
def set_frequency(
    agent_id: str = Header(..., description="Agent or User ID"),
    frequency: str = Body(..., embed=True),
    api_key: str = Depends(require_api_key),
):
    if frequency not in ["daily", "weekly", "monthly"]:
        raise HTTPException(status_code=400, detail="Invalid frequency.")
    chatlog_db.upsert_agent_profile(agent_id, summarization_frequency=frequency)
    return {"message": f"Frequency set to {frequency}."}


@app.get(
    "/summarization/check",
    summary="Check if summarization is allowed for agent",
    tags=["Agent"],
)
def summarization_check(
    agent_id: str = Query(...),
    requested_by: str = Query("ai"),
    api_key: str = Depends(require_api_key),
):
    allowed, msg = chatlog_db.check_summarization_allowed(agent_id, requested_by)
    return {"allowed": allowed, "message": msg}


@app.post(
    "/research", summary="Run research agent (web/codex/hybrid)", tags=["Research"]
)
def research_agent(
    query: str = Body(..., embed=True, description="What do you want to research?"),
    mode: str = Body("web", embed=True, description="'web', 'codex', or 'hybrid'"),
    api_key: str = Depends(require_api_key),
):
    """
    Run the research agent (web, codex, or hybrid mode) and return a markdown research report.
    """
    import asyncio

    from guardian.core.research.Modules.agent import Agent, Planner
    from guardian.core.research.Modules.main import generate_report, read_config

    config = read_config()
    planner = Planner(**config.get("planner", {}))
    agents = [Agent(**a) for a in config.get("agents", [])]

    report = asyncio.run(generate_report(query, planner, agents))
    return {"mode": mode, "report": report}


# =========================
# SSE Endpoint for Real-time Updates
# =========================


@app.get("/api/events", tags=["Events"])
async def events_stream(request: Request):
    """
    Server-Sent Events endpoint for real-time updates.
    Emits events for message creation, thread updates, etc.
    """

    async def event_generator():
        queue = event_manager.subscribe()
        try:
            while True:
                # Check for new events
                if queue:
                    event = queue.pop(0)
                    yield f"data: {json.dumps(event)}\n\n"

                # Send heartbeat every 15 seconds
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"

                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)

                # Check if client disconnected
                if await request.is_disconnected():
                    break
        except asyncio.CancelledError:
            pass
        finally:
            event_manager.unsubscribe(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# =========================
# Chat Log v2 Endpoints
# =========================


# /history/v2: Retrieve chat logs from new chat_log table
@app.get("/history/v2", summary="Retrieve chat log history (v2)", tags=["Memory"])
def chat_log_history(
    session_id: str = Query(..., description="Session ID to fetch"),
    user_id: str = Query("default", description="User ID"),
    limit: int = Query(20, ge=1, le=200, description="Number of messages"),
    api_key: str = Depends(require_api_key),
):
    """
    Returns latest chat logs for a session/user, from the new chat_log table.
    """
    history = chatlog_db.get_chat_history(
        session_id=session_id,
        user_id=user_id,
        limit=limit,
    )
    # `history` is already a list of dicts with the proper keys; return as-is
    return {"history": history}


# /summarize/v2: Summarize recent chat logs using active LLM
@app.post("/summarize/v2", summary="Summarize chat log history (v2)", tags=["Memory"])
def summarize_chat_log(
    session_id: str = Query(..., description="Session ID to summarize"),
    user_id: str = Query("default", description="User ID"),
    limit: int = Query(20, ge=1, le=200, description="How many messages to summarize"),
    api_key: str = Depends(require_api_key),
):
    """
    Summarizes chat history for a session/user using the currently active LLM backend.
    """
    history = chatlog_db.get_chat_history(
        session_id=session_id,
        user_id=user_id,
        limit=limit,
    )
    if not history:
        return {"summary": "No chat history found for this session."}

    # Compose LLM-ready message format (chronological)
    messages = []
    for row in reversed(history):
        # row is a dict with keys: id, timestamp, session_id, user_id, role, message, response, backend, model, agent, tag, extra
        if row.get("role") == "user" and row.get("message"):
            messages.append({"role": "user", "content": row["message"]})
        elif row.get("role") == "assistant" and row.get("response"):
            messages.append({"role": "assistant", "content": row["response"]})

    summary_prompt = [
        {
            "role": "system",
            "content": "Summarize this conversation for future recall. Capture all key facts, emotional beats, and decisions. Be specific.",
        }
    ] + messages

    if not chat_with_ai:
        raise HTTPException(status_code=503, detail="LLM backend is not available.")
    summary = chat_with_ai(summary_prompt)
    return {"summary": summary}
