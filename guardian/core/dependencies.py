"""
Core Dependencies Module
~~~~~~~~~~~~~~~~~~~~~~~~~

Shared dependencies for Guardian API including authentication,
database connections, AI completions, and configuration.

This module is imported by route modules to avoid circular imports
with guardian_api.py.
"""

import base64
import hashlib
import hmac
import logging
import os
import time as time_module
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from fastapi import Cookie, Depends, Header, HTTPException
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from guardian.config import get_settings
from guardian.context.broker import ContextBroker
from guardian.core import event_bus
from guardian.core.auth import verify_session_token
from guardian.core.chat_db import ChatDB
from guardian.core.chatlog_postgres import PostgresChatLogDB
from guardian.core.config import get_settings as get_core_settings
from guardian.core.db import GuardianDB, load_guardian_db_from_env
from guardian.core.egress import EgressDeniedError, assert_egress_allowed
from guardian.db.models import AuthenticatedPrincipal
from guardian.memory.query_memory import memory_store as _memory_store
from guardian.sensors.state import Sensors
from guardian.vector.store import VectorStore

try:  # Optional; only used when remote auth mode validates JWT bearer tokens.
    import jwt  # type: ignore
except Exception:  # pragma: no cover - optional dependency in some environments
    jwt = None  # type: ignore[assignment]

# Try to import Groq provider
try:
    from guardian.providers.groq_client import get_groq_chat
except ModuleNotFoundError as e:
    logging.warning(f"[dependencies] Optional groq_client not available: {e}")

    def get_groq_chat() -> Any:  # type: ignore
        return None


logger = logging.getLogger(__name__)

_SINGLE_USER_ID_ENV = "CODEXIFY_SINGLE_USER_ID"
_DEFAULT_SINGLE_USER_ID = "local"
_MULTI_USER_ENABLED_ENV = "CODEXIFY_MULTI_USER_ENABLED"


# =========================
# Environment Loading
# =========================


def _dotenv_disabled() -> bool:
    return os.getenv("CODEXIFY_DISABLE_DOTENV", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _load_env_chain() -> None:
    """
    Load .env files in priority order: base → mode-specific → local
    Each layer can override previous ones, but actual environment vars always win.
    """
    if _dotenv_disabled():
        logger.info(
            "[env] dotenv loading skipped (CODEXIFY_DISABLE_DOTENV set)"
        )
        return

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

# API key setup (must be explicitly provided via env/.env; no silent defaults)
API_KEY = (os.getenv("GUARDIAN_API_KEY") or "").strip()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Provider selection and Groq config
GUARDIAN_PROVIDER = os.getenv("GUARDIAN_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_DEFAULT = os.getenv("GROQ_MODEL", "moonshotai/kimi-k2-instruct-0905")
GROQ_FALLBACK_MODEL = (os.getenv("GROQ_FALLBACK_MODEL") or "").strip() or None

# Back/forward-compatible aliases
CHAT_PROVIDER = (
    os.getenv("GUARDIAN_CHAT_PROVIDER") or GUARDIAN_PROVIDER
).lower()
DEFAULT_MODEL = os.getenv("GUARDIAN_DEFAULT_MODEL") or GROQ_MODEL_DEFAULT
GROQ_BASE_URL = os.getenv(
    "GROQ_BASE_URL", "https://api.groq.com/openai/v1"
).rstrip("/")

# Feature flags
ENABLE_BLIP_MODEL = os.getenv("ENABLE_BLIP_MODEL", "true").lower() in (
    "1",
    "true",
    "yes",
)
ENABLE_OUTBOX = os.getenv("ENABLE_OUTBOX", "1").lower() in ("1", "true", "yes")
ENABLE_CONNECTOR_WORKER = os.getenv("ENABLE_CONNECTOR_WORKER", "0").lower() in (
    "1",
    "true",
    "yes",
)
MEMORY_RETENTION_DAYS = int(os.getenv("MEMORY_RETENTION_DAYS", "90"))

# CORS configuration
_origins_env = os.getenv(
    "GUARDIAN_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,tauri://localhost,http://tauri.localhost,https://tauri.localhost",
)
allowed_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]


# =========================
# Authentication
# =========================


def _exposure_mode() -> str:
    """
    Resolve endpoint exposure mode.

    - local_safe: default development boundary.
    - public_allowlist: externally exposed boundary.
    """
    raw = (os.getenv("GUARDIAN_EXPOSURE_MODE") or "local_safe").strip().lower()
    if raw in {"", "local_safe", "local"}:
        return "local_safe"
    if raw in {"public_allowlist"}:
        return "public_allowlist"
    logger.warning(
        "Unknown GUARDIAN_EXPOSURE_MODE=%r; defaulting to local_safe",
        raw,
    )
    return "local_safe"


def _auth_mode() -> str:
    """
    Resolve auth boundary mode.

    - local: static API keys are allowed.
    - remote: static API keys are rejected; only session/JWT tokens are allowed.
    """
    if _exposure_mode() == "public_allowlist":
        return "remote"

    raw = (os.getenv("GUARDIAN_AUTH_MODE") or "local").strip().lower()
    if raw in {"", "local", "localhost", "loopback"}:
        return "local"
    if raw in {"remote", "cloud", "hosted", "public", "prod", "production"}:
        return "remote"
    logger.warning(
        "Unknown GUARDIAN_AUTH_MODE=%r; defaulting to remote mode for safety",
        raw,
    )
    return "remote"


def _env_bool(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _allow_user_header_override() -> bool:
    return _env_bool("DEBUG", default=False) or _env_bool(
        "LOCAL_DEV", default=False
    )


def get_single_user_id() -> str:
    """
    Resolve the canonical single-user principal for this deployment.
    """
    configured = (os.getenv(_SINGLE_USER_ID_ENV) or "").strip()
    return configured or _DEFAULT_SINGLE_USER_ID


def _coerce_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _multi_user_mode_enabled() -> bool:
    try:
        settings = get_core_settings()
        return bool(getattr(settings, "CODEXIFY_MULTI_USER_ENABLED", False))
    except Exception:
        return _env_bool(_MULTI_USER_ENABLED_ENV, default=False)


@dataclass(frozen=True)
class RequestUserScope:
    """Resolved request identity with legacy and durable principal fields."""

    user_id: str = ""
    subject_id: str | None = None
    account_id: str | None = None
    multi_user_enabled: bool = False


_PRINCIPAL_SESSION_FACTORY: Any = None
_PRINCIPAL_SESSION_DSN: str | None = None


def _principal_database_url() -> str | None:
    settings = get_core_settings()
    configured = (
        getattr(settings, "GUARDIAN_DATABASE_URL", None)
        or os.getenv("GUARDIAN_DATABASE_URL")
        or os.getenv("DATABASE_URL")
    )
    candidate = (configured or "").strip()
    return candidate or None


def _principal_session_factory() -> Any:
    global _PRINCIPAL_SESSION_DSN
    global _PRINCIPAL_SESSION_FACTORY

    dsn = _principal_database_url()
    if not dsn:
        raise RuntimeError(
            "Stable principal mapping requires GUARDIAN_DATABASE_URL or DATABASE_URL"
        )

    if _PRINCIPAL_SESSION_FACTORY is None or _PRINCIPAL_SESSION_DSN != dsn:
        engine = create_engine(dsn, future=True)
        _PRINCIPAL_SESSION_FACTORY = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
        )
        _PRINCIPAL_SESSION_DSN = dsn

    return _PRINCIPAL_SESSION_FACTORY


def _resolve_authenticated_subject(
    authorization: object = None,
    gc_session: object = None,
) -> str | None:
    auth = _coerce_text(authorization)
    token = ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    if token:
        ok, subject = verify_session_token(token)
        if ok:
            return subject

    cookie_token = _coerce_text(gc_session)
    if cookie_token:
        ok, subject = verify_session_token(cookie_token)
        if ok:
            return subject
    return None


def _resolve_account_id_for_subject(subject_id: str) -> str | None:
    subject = (subject_id or "").strip()
    if not subject:
        return None

    try:
        Session = _principal_session_factory()
        with Session() as session:
            account_id = session.scalar(
                select(AuthenticatedPrincipal.account_id).where(
                    AuthenticatedPrincipal.subject_id == subject
                )
            )
    except RuntimeError as exc:
        logger.error(
            "[auth] stable principal mapping unavailable: %s", str(exc)
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Server misconfigured: stable principal mapping database is not configured"
            ),
        ) from exc
    except Exception as exc:
        logger.exception(
            "[auth] stable principal lookup failed for subject=%s", subject
        )
        raise HTTPException(
            status_code=500,
            detail="Server misconfigured: stable principal lookup failed",
        ) from exc

    if account_id is None:
        return None
    cleaned = str(account_id).strip()
    return cleaned or None


def get_request_user_id(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    gc_session: Optional[str] = Cookie(None, alias="gc_session"),
) -> str:
    """
    Resolve request user identity.

    In default single-user mode, `X-User-Id` is only honored when explicit
    local debug flags are enabled and otherwise falls back to the configured
    single-user identity.

    When CODEXIFY_MULTI_USER_ENABLED=true, the request must carry an
    authenticated subject from the existing session/JWT path.
    """
    if _multi_user_mode_enabled():
        subject = _resolve_authenticated_subject(authorization, gc_session)
        if subject:
            return subject
        logger.warning(
            "Rejected request without authenticated subject in multi-user mode"
        )
        raise HTTPException(
            status_code=401,
            detail=(
                "Multi-user mode requires an authenticated session/JWT subject"
            ),
        )

    candidate = _coerce_text(x_user_id)
    allow_override = _allow_user_header_override()
    if candidate and allow_override:
        logger.debug(
            "[auth] honoring X-User-Id override due to DEBUG/LOCAL_DEV"
        )
        return candidate
    if candidate and not allow_override:
        logger.debug(
            "[auth] ignoring X-User-Id override outside DEBUG/LOCAL_DEV"
        )
    return get_single_user_id()


def get_request_user_scope(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    gc_session: Optional[str] = Cookie(None, alias="gc_session"),
) -> RequestUserScope:
    """
    Resolve the current request identity scope.

    Single-user mode preserves the legacy `user_id` fallback behavior.
    Multi-user mode exposes the authenticated subject and stable account id.
    """
    if _multi_user_mode_enabled():
        subject_id = _resolve_authenticated_subject(authorization, gc_session)
        if not subject_id:
            logger.warning(
                "Rejected request without authenticated subject in multi-user mode"
            )
            raise HTTPException(
                status_code=401,
                detail=(
                    "Multi-user mode requires an authenticated session/JWT subject"
                ),
            )

        account_id = _resolve_account_id_for_subject(subject_id)
        if not account_id:
            logger.warning(
                "Rejected request without stable principal mapping subject=%s",
                subject_id,
            )
            raise HTTPException(
                status_code=401,
                detail=(
                    "Multi-user mode requires a stable account_id mapping for the authenticated subject"
                ),
            )

        return RequestUserScope(
            user_id=account_id,
            subject_id=subject_id,
            account_id=account_id,
            multi_user_enabled=True,
        )

    return RequestUserScope(
        user_id=get_request_user_id(x_user_id, authorization, gc_session),
        subject_id=None,
        account_id=None,
        multi_user_enabled=False,
    )


def _remote_token_secrets() -> List[str]:
    """
    Collect candidate secrets for remote session/JWT validation.

    GUARDIAN_SESSION_SECRET is preferred. GUARDIAN_JWT_SECRET and
    GUARDIAN_API_KEY are accepted for compatibility with existing setups.
    """
    secrets: List[str] = []
    for env_name in (
        "GUARDIAN_SESSION_SECRET",
        "GUARDIAN_JWT_SECRET",
        "GUARDIAN_API_KEY",
    ):
        value = (os.getenv(env_name) or "").strip()
        if value and value not in secrets:
            secrets.append(value)
    return secrets


def _is_valid_remote_token(token: str) -> bool:
    """
    Validate a remote-mode bearer/cookie token as session or JWT.
    """
    raw = token.strip()
    if not raw:
        return False

    # First check native Guardian session tokens.
    ok, _subject = verify_session_token(raw)
    if ok:
        return True
    if _verify_session_token_fallback(raw):
        return True

    # Then check JWT tokens signed with configured secrets.
    if jwt is None:
        return False

    for secret in _remote_token_secrets():
        try:
            jwt.decode(
                raw,
                secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            return True
        except Exception:
            continue

    return False


def _verify_session_token_fallback(token: str) -> bool:
    """
    Fallback validator for Guardian session tokens.

    `guardian.core.auth.verify_session_token` splits raw token bytes on every '.'
    and can reject valid tokens when signature bytes contain '.'. This parser uses
    the first three delimiters only and treats the remainder as signature bytes.
    """
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        dot1 = raw.find(b".")
        dot2 = raw.find(b".", dot1 + 1) if dot1 >= 0 else -1
        dot3 = raw.find(b".", dot2 + 1) if dot2 >= 0 else -1
        if dot1 < 0 or dot2 < 0 or dot3 < 0:
            return False

        payload = raw[:dot3]
        exp_raw = raw[dot1 + 1 : dot2]
        sig = raw[dot3 + 1 :]
        if not sig:
            return False

        exp = int(exp_raw.decode("utf-8", "ignore"))
        if exp < int(time_module.time()):
            return False

        for secret in _remote_token_secrets():
            digest = hmac.new(
                secret.encode("utf-8"),
                payload,
                hashlib.sha256,
            ).digest()
            if hmac.compare_digest(sig, digest):
                return True
    except Exception:
        return False
    return False


def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    gc_session: Optional[str] = Cookie(None, alias="gc_session"),
) -> str:
    """
    Validate request auth at the local/remote boundary.

    Local mode (default):
    - Accepts static API keys from X-API-Key and Bearer headers.

    Remote mode:
    - Rejects static API keys.
    - Requires session/JWT via Bearer token or gc_session cookie.

    Note: GUARDIAN_EXPOSURE_MODE=public_allowlist always forces remote mode.
    """
    mode = _auth_mode()
    if mode == "remote":
        if x_api_key and x_api_key.strip():
            logger.warning(
                "Rejected static API key in remote auth mode (local-only key boundary)"
            )
            raise HTTPException(
                status_code=401,
                detail="Remote mode requires session/JWT auth; X-API-Key is local-only",
            )

        secrets = _remote_token_secrets()
        if not secrets:
            logger.error(
                "Remote auth mode misconfigured: no session/JWT secret configured"
            )
            raise HTTPException(
                status_code=500,
                detail=(
                    "Server misconfigured: remote auth mode requires "
                    "GUARDIAN_SESSION_SECRET or GUARDIAN_JWT_SECRET"
                ),
            )

        bearer_token: Optional[str] = None
        if authorization and authorization.lower().startswith("bearer "):
            bearer_token = authorization[7:].strip() or None
        if bearer_token and _is_valid_remote_token(bearer_token):
            return bearer_token

        if gc_session and _is_valid_remote_token(gc_session):
            return gc_session

        logger.warning(
            "Unauthorized remote auth attempt (session/JWT required)"
        )
        raise HTTPException(
            status_code=401,
            detail="Remote mode requires a valid session/JWT token",
        )

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

    # Fallback: allow direct env GUARDIAN_API_KEY, otherwise fail closed.
    if not allowed:
        env_key = (os.getenv("GUARDIAN_API_KEY") or "").strip()
        if env_key:
            allowed.append(env_key)
        else:
            logger.error(
                "GUARDIAN_API_KEY is not configured; set it in .env or the environment."
            )
            raise HTTPException(
                status_code=500,
                detail="Server misconfigured: GUARDIAN_API_KEY is not set",
            )

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


def get_current_user(
    api_key: str = Depends(require_api_key),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    gc_session: Optional[str] = Cookie(None, alias="gc_session"),
) -> str:
    """
    Resolve current user from the effective request scope.
    """
    _ = api_key
    return get_request_user_id(x_user_id, authorization, gc_session)


# =========================
# Database Setup
# =========================

# This will be initialized by init_database() / guardian_api.py at startup
chatlog_db: Optional[Any] = None
DB_BACKEND: str = "postgres"
PG_DSN: Optional[str] = None


def init_database() -> Optional[Any]:
    """
    Initialize the database backend (PostgreSQL).
    Called by guardian_api.py during startup.
    Returns the initialized ChatDB instance.
    """
    global chatlog_db, PG_DSN

    if chatlog_db is not None:
        return chatlog_db

    settings = get_settings()
    db_url = getattr(settings, "GUARDIAN_DATABASE_URL", None) or os.getenv(
        "DATABASE_URL"
    )

    if db_url:
        # Fall back to Postgres when a GUARDIAN_DATABASE_URL is explicitly set.
        chatlog_db = PostgresChatLogDB(db_url)  # type: ignore[arg-type]
        # PgDB/PostgresChatLogDB manage schema via migrations; no explicit ensure_schema required.
        PG_DSN = db_url
        logger.info(
            "[db] Using PostgreSQL chatlog DB DSN=%s", _mask_dsn(db_url)
        )
        return chatlog_db

    logger.warning(
        "[db] No chatlog DB configured (GUARDIAN_DATABASE_URL or DATABASE_URL must be set)"
    )
    return None


def get_database_dsn() -> Optional[str]:
    """Return the configured database DSN without raising."""
    if PG_DSN:
        return PG_DSN
    return os.getenv("GUARDIAN_DATABASE_URL") or os.getenv("DATABASE_URL")


def get_capability_issuance_db() -> GuardianDB:
    """Return a GuardianDB instance suitable for capability issuance tooling."""
    resolved = load_guardian_db_from_env()
    if resolved is not None:
        if isinstance(resolved, GuardianDB):
            return resolved
        if hasattr(resolved, "get_session"):
            return resolved  # type: ignore[return-value]

    db_url = get_database_dsn()
    if not db_url:
        raise RuntimeError(
            "Capability issuance requires GUARDIAN_DATABASE_URL or DATABASE_URL"
        )
    return GuardianDB(db_url)


# =========================
# Shared Services
# =========================

# These will be initialized by guardian_api.py at startup
_vector_store: Optional[VectorStore] = None
_sensors: Optional[Sensors] = None
_embedder_preflight_cache: Optional[dict[str, Any]] = None
_embedder_preflight_cache_ts: float = 0.0


def init_services(db: ChatDB) -> tuple[VectorStore, Sensors]:
    """
    Initialize shared services (vector store, sensors).
    Called by guardian_api.py during startup.
    """
    global _vector_store, _sensors
    _vector_store = VectorStore()
    _sensors = Sensors(db)
    return _vector_store, _sensors


def get_vector_store() -> VectorStore:
    """Return the shared runtime vector store, creating it on first use."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def _embedder_preflight_cache_ttl_seconds() -> float:
    raw = (os.getenv("EMBEDDER_PREFLIGHT_CACHE_TTL_SECONDS") or "5").strip()
    try:
        ttl = float(raw)
    except ValueError:
        ttl = 5.0
    return max(0.0, ttl)


def get_embedder_preflight_status(
    *, force_refresh: bool = False
) -> dict[str, Any]:
    """Return cached embedder preflight status without constructing VectorStore."""

    global _embedder_preflight_cache, _embedder_preflight_cache_ts

    ttl = _embedder_preflight_cache_ttl_seconds()
    now = time_module.monotonic()
    if (
        not force_refresh
        and _embedder_preflight_cache is not None
        and ttl > 0.0
        and (now - _embedder_preflight_cache_ts) <= ttl
    ):
        return dict(_embedder_preflight_cache)

    from backend.rag.embedder import inspect_embedder_preflight

    try:
        payload = inspect_embedder_preflight()
    except Exception as exc:
        logger.warning(
            "[dependencies] embedder preflight failed: %s",
            str(exc),
        )
        payload = {
            "backend": "unknown",
            "model": None,
            "ready": False,
            "present": None,
            "reason": f"embedder preflight failed: {exc}",
        }

    _embedder_preflight_cache = dict(payload)
    _embedder_preflight_cache_ts = now
    return dict(payload)


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

    try:
        assert_egress_allowed("groq")
    except EgressDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500, detail="GROQ_API_KEY not configured"
        )

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
                context_parts.append(
                    "**Semantic Context:**\n" + "\n".join(sem_parts)
                )

        # Add memory context
        if context.get("memory"):
            mem_parts = []
            for item in context["memory"]:
                txt = item.get("text", "") or item.get("content", "")
                if txt:
                    mem_parts.append(f"- {txt}")
            if mem_parts:
                context_parts.append(
                    "**Memory Context:**\n" + "\n".join(mem_parts)
                )

        # Add sensors/state context
        if context.get("sensors"):
            sensor_info = []
            sensors = context["sensors"]
            if sensors.get("timestamp"):
                sensor_info.append(f"Timestamp: {sensors['timestamp']}")
            if sensors.get("thread_count") is not None:
                sensor_info.append(f"Active Threads: {sensors['thread_count']}")
            if sensor_info:
                context_parts.append(
                    "**System State:**\n" + "\n".join(sensor_info)
                )

        # Insert the context system message *after* any leading system prompts
        if context_parts:
            system_context = "\n\n".join(context_parts)

            # Find index after the last leading system message, so the primary
            # Guardian persona/system prompt (if present) stays first.
            insert_at = 0
            for idx, msg in enumerate(enriched_messages):
                if msg.get("role") == "system":
                    insert_at = idx + 1
                else:
                    break

            enriched_messages.insert(
                insert_at,
                {
                    "role": "system",
                    "content": f"You have access to the following context:\n\n{system_context}",
                },
            )

        # Log diagnostic info if provided
        if context.get("diagnostics"):
            diag = context["diagnostics"]
            logger.info(
                "[completion] RAG depth=%s semantic=%d memory=%d sensors=%s",
                diag.get("depth", "unknown"),
                diag.get("semantic_count", 0),
                diag.get("memory_count", 0),
                bool(diag.get("sensors_included", False)),
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
                logger.error(
                    "[groq] HTTP %d: %s", resp.status_code, resp.text[:200]
                )
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
        logger.info(
            "[groq] retrying with fallback model=%s", GROQ_FALLBACK_MODEL
        )
        result = _attempt_completion(GROQ_FALLBACK_MODEL)
        if result:
            return result

    # All attempts failed
    raise HTTPException(
        status_code=500,
        detail=f"Groq completion failed for model={target_model}",
    )


# =========================
# Exports
# =========================

__all__ = [
    # Authentication
    "verify_api_key",
    "require_api_key",
    "get_current_user",
    "get_request_user_scope",
    "get_request_user_id",
    "RequestUserScope",
    "get_single_user_id",
    "API_KEY",
    # Database
    "chatlog_db",
    "init_database",
    "DB_BACKEND",
    "PG_DSN",
    "get_database_dsn",
    "get_capability_issuance_db",
    # Services
    "_vector_store",
    "_sensors",
    "_memory_store",
    "init_services",
    "get_vector_store",
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
