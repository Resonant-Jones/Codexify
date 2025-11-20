"""
Core Dependencies Module
~~~~~~~~~~~~~~~~~~~~~~~~~

Shared dependencies for Guardian API including authentication,
database connections, AI completions, and configuration.

This module is imported by route modules to avoid circular imports
with guardian_api.py.
"""

import logging
import os
import hmac
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse, urlunparse
from datetime import datetime, date, time

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Header
from fastapi.security.api_key import APIKeyHeader

from guardian.core import event_bus
from guardian.core.chat_db import ChatDB
from guardian.core.sqlitedb import SqliteChatLogDB
from guardian.core.pgdb import PgDB  # type: ignore
from guardian.config import get_settings
from guardian.context.broker import ContextBroker
from guardian.vector.store import VectorStore
from guardian.memory.query_memory import memory_store as _memory_store
from guardian.sensors.state import Sensors

# Try to import PgDB (PostgreSQL adapter)
try:
    from guardian.core.pgdb import PgDB  # type: ignore
except Exception as _pg_exc:
    PgDB = None  # type: ignore
    _PG_IMPORT_ERROR = _pg_exc
else:
    _PG_IMPORT_ERROR = None

# Try to import Groq provider
try:
    from guardian.providers.groq_client import get_groq_chat
except ModuleNotFoundError as e:
    logging.warning(f"[dependencies] Optional groq_client not available: {e}")
    def get_groq_chat() -> Any:  # type: ignore
        return None

logger = logging.getLogger(__name__)


# =========================
# Environment Loading
# =========================

def _load_env_chain() -> None:
    """
    Load .env files in priority order: base → mode-specific → local
    Each layer can override previous ones, but actual environment vars always win.
    """
    cwd = Path(__file__).resolve().parents[2]  # Go up to project root
    base = cwd / ".env"
    mode = os.getenv("GUARDIAN_ENV", "development").strip()
    backend_mode = cwd / f".env.backend.{mode}"
    local = cwd / ".env.local"

    loaded = []
    for p in (base, backend_mode, local):
        if p.exists():
            load_dotenv(p, override=False)
            loaded.append(str(p))
    logger.info(
        "[env] dotenv loaded (in order): %s",
        " -> ".join(loaded) if loaded else "<none>",
    )


# =========================
# Configuration
# =========================

# API key setup
API_KEY = os.getenv("GUARDIAN_API_KEY", "changeme")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Provider selection and Groq config
GUARDIAN_PROVIDER = os.getenv("GUARDIAN_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_DEFAULT = os.getenv("GROQ_MODEL", "moonshotai/kimi-k2-instruct-0905")
GROQ_FALLBACK_MODEL = (os.getenv("GROQ_FALLBACK_MODEL") or "").strip() or None

# Back/forward-compatible aliases
CHAT_PROVIDER = (os.getenv("GUARDIAN_CHAT_PROVIDER") or GUARDIAN_PROVIDER).lower()
DEFAULT_MODEL = os.getenv("GUARDIAN_DEFAULT_MODEL") or GROQ_MODEL_DEFAULT
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")

# Feature flags
ENABLE_BLIP_MODEL = os.getenv("ENABLE_BLIP_MODEL", "true").lower() in ("1", "true", "yes")
ENABLE_OUTBOX = os.getenv("ENABLE_OUTBOX", "1").lower() in ("1", "true", "yes")
ENABLE_CONNECTOR_WORKER = os.getenv("ENABLE_CONNECTOR_WORKER", "0").lower() in ("1", "true", "yes")
MEMORY_RETENTION_DAYS = int(os.getenv("MEMORY_RETENTION_DAYS", "90"))

# CORS configuration
_origins_env = os.getenv("GUARDIAN_ALLOWED_ORIGINS", "http://localhost:5173")
allowed_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]


# =========================
# Authentication
# =========================

def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    """
    Validate API key authentication using dynamic settings.

    Accepts credentials via:
    - X-API-Key header
    - Authorization: Bearer <token>

    Valid keys are sourced from:
    - settings.GUARDIAN_API_KEY
    - settings.GUARDIAN_API_KEYS (comma-separated list)
    """
    candidates: List[str] = []
    if x_api_key:
        token = x_api_key.strip()
        if token:
            candidates.append(token)
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            candidates.append(token)

    if not candidates:
        logger.warning("Unauthorized API key attempt (missing)")
        raise HTTPException(status_code=401, detail="Missing API key")

    try:
        settings = get_settings()
        allowed: List[str] = []
        primary = getattr(settings, "GUARDIAN_API_KEY", None)
        if isinstance(primary, str) and primary.strip():
            allowed.append(primary.strip())
        raw_multi = getattr(settings, "GUARDIAN_API_KEYS", None)
        if isinstance(raw_multi, str) and raw_multi.strip():
            for token in raw_multi.replace(";", ",").split(","):
                val = token.strip()
                if val:
                    allowed.append(val)
    except Exception:
        allowed = []

    # Fallback: allow direct env GUARDIAN_API_KEY or a deterministic
    # test-time default when settings are not configured.
    if not allowed:
        env_key = os.getenv("GUARDIAN_API_KEY") or "invalid-by-default"
        allowed.append(env_key.strip())

    for candidate in candidates:
        for allowed_key in allowed:
            if hmac.compare_digest(candidate, allowed_key):
                return candidate

    logger.warning("Unauthorized API key attempt")
    raise HTTPException(status_code=401, detail="Invalid API key")


def require_api_key(api_key: str = Depends(verify_api_key)) -> str:
    """
    Backward-compatible wrapper around verify_api_key.

    Existing routes depending on require_api_key automatically gain
    the dynamic Settings-based behavior without code changes.
    """
    return api_key


def get_current_user(api_key: str = Depends(require_api_key)) -> str:
    """
    Extract user ID from validated API key.
    For now, returns 'default' - can be extended for multi-user support.
    """
    return "default"


# =========================
# Database Setup
# =========================

# This will be initialized by init_database() / guardian_api.py at startup
chatlog_db: Optional[Any] = None
DB_BACKEND: Optional[str] = None
SQLITE_PATH: Optional[str] = None


def init_database() -> Optional[Any]:
    """
    Initialize the database backend (PostgreSQL or SQLite).
    Called by guardian_api.py during startup.
    Returns the initialized ChatDB instance.
    """
    global chatlog_db, DB_BACKEND, SQLITE_PATH

    if chatlog_db is not None:
        return chatlog_db

    settings = get_settings()
    db_path = getattr(settings, "GUARDIAN_DB_PATH", None)
    db_url = getattr(settings, "GUARDIAN_DATABASE_URL", None)

    if db_path:
        # Prefer SQLite when a GUARDIAN_DB_PATH is configured.
        path_str = str(db_path)
        chatlog_db = SqliteChatLogDB(path_str)
        DB_BACKEND = "sqlite"
        SQLITE_PATH = path_str
        logger.info("[db] Using SQLite chatlog DB at %s", path_str)
        return chatlog_db

    if db_url:
        # Fall back to Postgres when a GUARDIAN_DATABASE_URL is explicitly set.
        chatlog_db = PgDB(db_url)  # type: ignore[arg-type]
        # PgDB manages its own schema via migrations; no explicit ensure_schema required.
        DB_BACKEND = "postgres"
        SQLITE_PATH = None
        logger.info("[db] Using PostgreSQL chatlog DB DSN=%s", _mask_dsn(db_url))
        return chatlog_db

    logger.warning(
        "[db] No chatlog DB configured (GUARDIAN_DB_PATH and GUARDIAN_DATABASE_URL are both unset)"
    )
    return None


# =========================
# Shared Services
# =========================

# These will be initialized by guardian_api.py at startup
_vector_store: Optional[VectorStore] = None
_sensors: Optional[Sensors] = None


def init_services(db: ChatDB) -> tuple[VectorStore, Sensors]:
    """
    Initialize shared services (vector store, sensors).
    Called by guardian_api.py during startup.
    """
    global _vector_store, _sensors
    _vector_store = VectorStore()
    _sensors = Sensors(db)
    return _vector_store, _sensors


# =========================
# Helper Functions
# =========================

def _mask_dsn(dsn: str) -> str:
    """Mask password in database connection string for safe logging."""
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


def _jsonify(obj: Any) -> Any:
    """
    Recursively convert datetimes and times into ISO strings so JSON/DB can accept them.
    Leaves other types untouched.
    """
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    return obj


# =========================
# Groq Completion Helper
# =========================

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
    - Injects assembled context (semantic + memory) from ContextBroker if provided.

    Args:
        messages: List of chat messages in OpenAI format
        model: Model name to use (defaults to DEFAULT_MODEL)
        context: Optional context bundle from ContextBroker

    Returns:
        Assistant's response text

    Raises:
        HTTPException: If GROQ_API_KEY not configured or completion fails
    """
    import requests

    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")

    # Inject RAG context as system message if broker provided a bundle
    enriched_messages = list(messages)  # Copy to avoid modifying original
    if context:
        context_parts: List[str] = []

        # Add semantic context from RAG
        if context.get("semantic"):
            sem_parts = []
            for item in context["semantic"]:
                snippet = item.get("content", "") or item.get("snippet", "")
                if snippet:
                    sem_parts.append(f"- {snippet}")
            if sem_parts:
                context_parts.append("**Semantic Context:**\n" + "\n".join(sem_parts))

        # Add memory context
        if context.get("memory"):
            mem_parts = []
            for item in context["memory"]:
                txt = item.get("text", "") or item.get("content", "")
                if txt:
                    mem_parts.append(f"- {txt}")
            if mem_parts:
                context_parts.append("**Memory Context:**\n" + "\n".join(mem_parts))

        # Add sensors/state context
        if context.get("sensors"):
            sensor_info = []
            sensors = context["sensors"]
            if sensors.get("timestamp"):
                sensor_info.append(f"Timestamp: {sensors['timestamp']}")
            if sensors.get("thread_count") is not None:
                sensor_info.append(f"Active Threads: {sensors['thread_count']}")
            if sensor_info:
                context_parts.append("**System State:**\n" + "\n".join(sensor_info))

        # Prepend as system message
        if context_parts:
            system_context = "\n\n".join(context_parts)
            enriched_messages.insert(0, {
                "role": "system",
                "content": f"You have access to the following context:\n\n{system_context}"
            })

        # Log diagnostic info if provided
        if context.get("diagnostics"):
            diag = context["diagnostics"]
            logger.info(
                "[completion] RAG depth=%s semantic=%d memory=%d sensors=%s",
                diag.get("depth", "unknown"),
                diag.get("semantic_count", 0),
                diag.get("memory_count", 0),
                bool(diag.get("sensors_included", False))
            )

    target_model = model or DEFAULT_MODEL
    url = f"{GROQ_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": target_model, "messages": enriched_messages}

    def _attempt_completion(m: str) -> Optional[str]:
        """Single attempt at completion with given model."""
        payload["model"] = m
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            if resp.status_code != 200:
                logger.error("[groq] HTTP %d: %s", resp.status_code, resp.text[:200])
                return None

            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                logger.warning("[groq] no choices in response")
                return None

            choice = choices[0]

            # Handle choice.text (legacy format)
            if "text" in choice:
                txt = str(choice["text"]).strip()
                if txt and not txt.lower().startswith("error"):
                    return txt

            # Handle choice.message.content (standard format)
            msg = choice.get("message", {})
            content = msg.get("content")

            # content can be a string or a list of content parts
            if isinstance(content, str):
                txt = content.strip()
                if txt and not txt.lower().startswith("error"):
                    return txt
            elif isinstance(content, list):
                # Concatenate text from content parts
                parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        parts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        parts.append(part)
                txt = " ".join(parts).strip()
                if txt and not txt.lower().startswith("error"):
                    return txt

            return None
        except Exception as exc:
            logger.exception("[groq] request failed for model=%s: %s", m, exc)
            return None

    # Try primary model
    result = _attempt_completion(target_model)
    if result:
        return result

    # Try fallback if configured
    if GROQ_FALLBACK_MODEL and GROQ_FALLBACK_MODEL != target_model:
        logger.info("[groq] retrying with fallback model=%s", GROQ_FALLBACK_MODEL)
        result = _attempt_completion(GROQ_FALLBACK_MODEL)
        if result:
            return result

    # All attempts failed
    raise HTTPException(
        status_code=500,
        detail=f"Groq completion failed for model={target_model}"
    )


# =========================
# Exports
# =========================

__all__ = [
    # Authentication
    "verify_api_key",
    "require_api_key",
    "get_current_user",
    "API_KEY",

    # Database
    "chatlog_db",
    "init_database",
    "DB_BACKEND",
    "PG_DSN",
    "SQLITE_PATH",

    # Services
    "_vector_store",
    "_sensors",
    "_memory_store",
    "init_services",
    "event_bus",

    # AI Completion
    "_groq_complete",
    "get_groq_chat",
    "DEFAULT_MODEL",
    "GUARDIAN_PROVIDER",

    # Configuration
    "allowed_origins",
    "ENABLE_BLIP_MODEL",
    "ENABLE_OUTBOX",
    "ENABLE_CONNECTOR_WORKER",
    "MEMORY_RETENTION_DAYS",

    # Helpers
    "_mask_dsn",
    "_jsonify",
]
