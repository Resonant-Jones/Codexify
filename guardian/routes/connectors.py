"""
Connectors Routes
~~~~~~~~~~~~~~~~~

Management of external service connectors (GitHub, Google Drive, etc.)
and background sync worker.
"""

import asyncio
import datetime
import json
import logging
import os
import psycopg2
import psycopg2.extras
import random
import time
from typing import Any, Callable, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Import shared context from guardian_api
try:
    from guardian.core import event_bus
    from guardian.core.chat_db import ChatDB
    from guardian.guardian_api import chatlog_db, require_api_key, PG_DSN
    from guardian.connectors.github import sync_repo
except ImportError as e:
    logger.warning(f"[connectors] Import warning: {e}")
    chatlog_db = None
    require_api_key = lambda x: x
    PG_DSN = None


# Helper: recursively convert datetimes/times to ISO strings for JSON/DB
def _jsonify(obj: Any) -> Any:
    """Recursively convert datetimes and times into ISO strings so JSON/DB can accept them.
    Leaves other types untouched.
    """
    from datetime import datetime, date, time
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    return obj


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

# Exponential backoff configuration
BACKOFF_INITIAL_DELAY = 1.0  # Start with 1 second
BACKOFF_MAX_DELAY = 300.0  # Max 5 minutes
BACKOFF_MULTIPLIER = 2.0  # Double each time
BACKOFF_JITTER_RANGE = (0.8, 1.2)  # ±20% jitter
MAX_CONSECUTIVE_FAILURES = 10  # Max retries before extended backoff

_CONNECTOR_WORKER_STOP: Optional[asyncio.Event] = None
_CONNECTOR_WORKER_TASK: Optional[asyncio.Task] = None

# Monitoring counters
_CONNECTOR_WORKER_STATS = {
    "poll_cycles": 0,
    "empty_config_cycles": 0,
    "db_errors": 0,
    "retries": 0,
    "skipped_cycles": 0,
}


def _calculate_backoff_delay(
    attempt: int,
    base_delay: float = BACKOFF_INITIAL_DELAY,
    max_delay: float = BACKOFF_MAX_DELAY,
    multiplier: float = BACKOFF_MULTIPLIER,
    jitter_range: tuple = BACKOFF_JITTER_RANGE,
) -> float:
    """
    Calculate exponential backoff delay with jitter.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        multiplier: Exponential backoff multiplier
        jitter_range: Tuple of (min_factor, max_factor) for jitter

    Returns:
        Delay in seconds with jitter applied
    """
    # Calculate exponential delay: base * (multiplier ^ attempt)
    delay = base_delay * (multiplier ** attempt)

    # Cap at max_delay
    delay = min(delay, max_delay)

    # Apply random jitter to prevent thundering herd
    jitter_factor = random.uniform(jitter_range[0], jitter_range[1])
    return delay * jitter_factor


def get_connector_worker_stats() -> Dict[str, int]:
    """Get current worker monitoring statistics."""
    return dict(_CONNECTOR_WORKER_STATS)


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
        conn.rollback()
        conn.close()
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


async def _connector_worker(stop_event: asyncio.Event) -> None:
    """
    Background worker that polls for connector configs and runs syncs.

    Implements exponential backoff with jitter on DB failures and adaptive polling.
    Tracks monitoring metrics for observability.
    """
    logger.info(
        "[connectors] worker started interval=%ss (enabled=%s)",
        CONNECTOR_SYNC_INTERVAL,
        ENABLE_CONNECTOR_WORKER,
    )

    consecutive_failures = 0
    current_backoff_delay = BACKOFF_INITIAL_DELAY

    try:
        while not stop_event.is_set():
            _CONNECTOR_WORKER_STATS["poll_cycles"] += 1

            try:
                # Attempt to fetch connector configs with DB access
                configs = await _run_db(chatlog_db.list_connector_configs, "github")

                # Reset backoff on successful DB access
                if consecutive_failures > 0:
                    logger.info(
                        "[connectors] DB access recovered after %d failures",
                        consecutive_failures
                    )
                    consecutive_failures = 0
                    current_backoff_delay = BACKOFF_INITIAL_DELAY

                # Handle empty configs case
                if not configs:
                    _CONNECTOR_WORKER_STATS["empty_config_cycles"] += 1
                    logger.debug("[connectors] no github configs found, sleeping")
                    try:
                        await asyncio.wait_for(
                            stop_event.wait(),
                            timeout=CONNECTOR_SYNC_INTERVAL
                        )
                    except asyncio.TimeoutError:
                        continue
                    else:
                        break  # Stop event was set

                # Process all configs
                for cfg in configs:
                    if stop_event.is_set():
                        break
                    await _run_github_sync(cfg)

                # Normal polling interval with small jitter
                jitter_factor = random.uniform(0.95, 1.05)
                wait_time = CONNECTOR_SYNC_INTERVAL * jitter_factor

                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=wait_time)
                except asyncio.TimeoutError:
                    continue
                else:
                    break  # Stop event was set

            except Exception as db_error:
                # DB access failed - apply exponential backoff
                consecutive_failures += 1
                _CONNECTOR_WORKER_STATS["db_errors"] += 1
                _CONNECTOR_WORKER_STATS["retries"] += 1

                # Calculate backoff delay with jitter
                current_backoff_delay = _calculate_backoff_delay(
                    attempt=min(consecutive_failures - 1, MAX_CONSECUTIVE_FAILURES)
                )

                logger.warning(
                    "[connectors] DB error (attempt %d/%d): %s. Retrying in %.1fs",
                    consecutive_failures,
                    MAX_CONSECUTIVE_FAILURES + 1,
                    str(db_error),
                    current_backoff_delay,
                )

                # Check if we've exceeded max failures
                if consecutive_failures > MAX_CONSECUTIVE_FAILURES:
                    logger.error(
                        "[connectors] exceeded %d consecutive failures, "
                        "entering extended backoff mode (delay=%.1fs)",
                        MAX_CONSECUTIVE_FAILURES,
                        current_backoff_delay,
                    )
                    _CONNECTOR_WORKER_STATS["skipped_cycles"] += 1

                # Wait with backoff before retry
                try:
                    await asyncio.wait_for(
                        stop_event.wait(),
                        timeout=current_backoff_delay
                    )
                except asyncio.TimeoutError:
                    continue  # Retry after backoff
                else:
                    break  # Stop event was set

    except asyncio.CancelledError:  # pragma: no cover
        logger.debug("[connectors] worker cancelled")
        raise
    finally:
        logger.info(
            "[connectors] worker stopped (stats: %s)",
            _CONNECTOR_WORKER_STATS
        )


async def _run_db(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


router = APIRouter(prefix="/api/connectors", tags=["Connectors"])


@router.get("")
def list_connectors():
    """List all connector configurations with their last run status."""
    configs = chatlog_db.list_connector_configs_with_last_run()
    return [_serialize_connector_config(cfg) for cfg in configs]


@router.post("")
def create_connector(cfg: ConnectorCreate):
    """Create a new connector configuration."""
    cfg_type = cfg.type.lower()
    if cfg_type not in CONNECTOR_REGISTRY:
        raise HTTPException(status_code=400, detail={"error": "Unsupported connector type"})
    if chatlog_db.get_connector_config(cfg.name):
        raise HTTPException(status_code=400, detail={"error": "Connector name already exists"})
    _validate_connector_settings(cfg_type, cfg.settings)
    stored = chatlog_db.create_connector_config(cfg.name, cfg_type, cfg.settings)
    stored["last_run"] = None
    return _serialize_connector_config(stored)


@router.get("/{connector_name}")
def get_connector(connector_name: str):
    """Get a specific connector configuration by name."""
    cfg = _get_connector_by_name(connector_name)
    return _serialize_connector_config(cfg)


@router.patch("/{connector_name}")
def patch_connector(connector_name: str, update: ConnectorUpdate):
    """Update a connector's settings."""
    cfg = _get_connector_by_name(connector_name)
    if update.settings is not None:
        merged = {**(cfg.get("settings") or {}), **update.settings}
        _validate_connector_settings(cfg["type"], merged)
        cfg = chatlog_db.update_connector_config(connector_name, config=merged)
        cfg["last_run"] = chatlog_db.get_last_connector_run(cfg["id"])
    return _serialize_connector_config(cfg)


@router.post("/{connector_name}/config")
def update_connector_fields(connector_name: str, payload: ConnectorConfigFields):
    """Update specific configuration fields for a connector."""
    cfg = _get_connector_by_name(connector_name)
    merged = {**(cfg.get("settings") or {}), **payload.fields}
    _validate_connector_settings(cfg["type"], merged)
    cfg = chatlog_db.update_connector_config(connector_name, config=merged)
    cfg["last_run"] = chatlog_db.get_last_connector_run(cfg["id"])
    return _serialize_connector_config(cfg)


@router.post("/{connector_name}/test")
def connector_test(connector_name: str) -> Dict[str, str]:
    """Test a connector connection (offline mode returns stub response)."""
    _get_connector_by_name(connector_name)
    return {"ok": "True", "message": "Connection not validated in offline mode"}


@router.post("/{connector_name}/sync")
async def connector_sync(connector_name: str):
    """Trigger a manual sync for the specified connector."""
    cfg = _get_connector_by_name(connector_name)
    await _schedule_github_sync(cfg)
    return {"ok": True}


@router.post("/{connector_name}/authorize")
def connector_authorize_not_supported(connector_name: str):
    """OAuth authorization endpoint (not supported for current connectors)."""
    raise HTTPException(
        status_code=400,
        detail={"error": "OAuth authorization is not supported for this connector"},
    )


@router.get("/{connector_name}/status")
def connector_status(connector_name: str) -> Dict[str, Any]:
    """Get the current status of a connector including its latest run."""
    cfg = _get_connector_by_name(connector_name)
    serialized = _serialize_connector_config(cfg)
    return {
        "ok": True,
        "connector": serialized,
        "status": serialized.get("status"),
        "latest_run": serialized.get("lastRun"),
    }


@router.post("/{name}/ingest")
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


# Health endpoint
@router.get("/health", tags=["Health"])
def connectors_health() -> Dict[str, object]:
    """Get health status of all connectors."""
    connectors = chatlog_db.list_connector_configs_with_last_run()
    total = len(connectors)
    healthy = 0
    for cfg in connectors:
        run = cfg.get("last_run")
        if run and run.get("status") == "succeeded":
            healthy += 1
    return {"ok": "True", "count": total, "connected": healthy}


@router.get("/worker/stats", tags=["Monitoring"])
def connector_worker_stats() -> Dict[str, Any]:
    """
    Get monitoring statistics for the connector background worker.

    Returns metrics including:
    - poll_cycles: Total number of polling cycles
    - empty_config_cycles: Cycles where no configs were found
    - db_errors: Database connection/query failures
    - retries: Number of retry attempts after failures
    - skipped_cycles: Cycles skipped due to extended backoff
    """
    return {
        "ok": True,
        "worker_enabled": ENABLE_CONNECTOR_WORKER,
        "sync_interval": CONNECTOR_SYNC_INTERVAL,
        "stats": get_connector_worker_stats(),
    }
