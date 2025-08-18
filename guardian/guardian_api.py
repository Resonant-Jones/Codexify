# =========================
# Imports
# =========================

# Standard Library
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from guardian.routes.codexify_router import router as codexify_router

# Third-Party
import requests
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

# Internal
from guardian.config import get_settings
from guardian.core.db import GuardianDB
from guardian.threads_structure.threads import get_thread_summary
from guardian.routes import research, memory, agent, threads

# Optional AI Backend
try:
    from guardian.core.ai_router import chat_with_ai
except ModuleNotFoundError as e:
    chat_with_ai = None
    logging.warning(f"[Codexify ⚠️] Optional chat_with_ai module not available: {e}")

# API Key authentication is enforced on all major endpoints (except /ping, /test, /)
# Pass `X-API-Key` header with your requests.

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API key dependency setup
API_KEY = os.getenv("GUARDIAN_API_KEY", "changeme")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        # Do not log the provided key to avoid leaking secrets.
        logger.warning("Unauthorized attempt with API key")
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return api_key


# Load configuration from environment variables
DB_PATH = Path(os.getenv("GUARDIAN_DB_PATH", "guardian.db"))
GEMINI_API_URL = os.getenv("GEMINI_API_URL", "https://api.gemini.ai/v1/chat")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_gemini_api_key_here")

# Initialize database
db = GuardianDB(DB_PATH)

# Ensure db uses the new chat_log-aware GuardianDB!
settings = get_settings()
chatlog_db = GuardianDB(settings.GUARDIAN_DB_PATH)

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
        db.insert_memory(
            timestamp=timestamp,
            command=entry.command,
            tag=entry.tag,
            agent=entry.agent,
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
        db.insert_memory(
            timestamp=timestamp,
            command=entry.summary,
            tag=entry.tag,
            agent=entry.agent,
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
        rows = db.search_memory(query, limit)
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
        rows = db.history_entries(limit=limit, tag=tag, agent=agent)
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
    # For simplicity, this fetches all; you can add pagination if needed
    with chatlog_db as db:
        conn = db._get_connection()
        c = conn.cursor()
        query = "SELECT thread_id, parent_thread_id, session_id, summary, created_at, user_id, project_id FROM threads WHERE 1=1"
        params = []
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        c.execute(query, params)
        rows = c.fetchall()
    results = [
        {
            "thread_id": row[0],
            "parent_thread_id": row[1],
            "session_id": row[2],
            "summary": row[3],
            "created_at": row[4],
            "user_id": row[5],
            "project_id": row[6],
        }
        for row in rows
    ]
    return {"threads": results}


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


@app.post("/thread", summary="Create a new thread", tags=["Threads"])
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


@app.post(
    "/chat",
    response_model=GeminiChatResponse,
    summary="Send chat prompt to Gemini API",
    tags=["Gemini Proxy"],
)
def gemini_chat(req: GeminiChatRequest, api_key: str = Depends(require_api_key)):
    """
    Send a chat prompt to the Gemini AI API and log the interaction in Guardian memory.

    Args:
        req (GeminiChatRequest): The chat request containing prompt and optional model.

    Returns:
        GeminiChatResponse: The response from Gemini API including model used and reply text.
    """
    # Log incoming prompt to Guardian memory via /log endpoint
    prompt_log = LogEntry(
        command=f"User prompt: {req.prompt}", tag="gemini", agent="user"
    )
    try:
        # In production, log directly to db instead of internal POST
        db.insert_memory(
            timestamp=datetime.now().isoformat(),
            command=prompt_log.command,
            tag=prompt_log.tag,
            agent=prompt_log.agent,
            type_="log",
            parent_id=None,
        )
    except Exception as e:
        logger.warning(f"Failed to log user prompt: {e}")

    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": req.model, "prompt": req.prompt}
    try:
        response = requests.post(
            GEMINI_API_URL, json=payload, headers=headers, timeout=30
        )
        response.raise_for_status()
        data = response.json()
        reply_text = data.get("reply", "")

        # Log AI reply to Guardian memory directly
        reply_log = LogEntry(
            command=f"AI reply: {reply_text}", tag="gemini", agent="ai"
        )
        try:
            db.insert_memory(
                timestamp=datetime.now().isoformat(),
                command=reply_log.command,
                tag=reply_log.tag,
                agent=reply_log.agent,
                type_="log",
                parent_id=None,
            )
        except Exception as e:
            logger.warning(f"Failed to log AI reply: {e}")

        logger.info("Gemini chat interaction logged successfully")
        return GeminiChatResponse(model_used=req.model, reply=reply_text)
    except requests.HTTPError as http_err:
        logger.error(f"HTTP error contacting Gemini API: {http_err}")
        raise HTTPException(
            status_code=response.status_code, detail=f"Gemini API error: {http_err}"
        )
    except Exception as e:
        logger.error(f"Error contacting Gemini API: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error contacting Gemini API: {str(e)}"
        )


@app.get("/whoami", summary="Get agent profile and identity", tags=["Agent"])
def whoami(
    agent_id: str = Header(..., description="Agent or User ID"),
    api_key: str = Depends(require_api_key),
):
    profile = db.get_agent_profile(agent_id)
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
    db.upsert_agent_profile(agent_id, **updates)
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
    db.upsert_agent_profile(agent_id, summarization_frequency=frequency)
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
    allowed, msg = db.check_summarization_allowed(agent_id, requested_by)
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
        session_id=session_id, user_id=user_id, limit=limit
    )
    results = [
        {
            "id": row[0],
            "timestamp": row[1],
            "session_id": row[2],
            "user_id": row[3],
            "role": row[4],
            "message": row[5],
            "response": row[6],
            "backend": row[7],
            "model": row[8],
            "agent": row[9],
            "tag": row[10],
            "extra": row[11],
        }
        for row in history
    ]
    return {"history": results}


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
        session_id=session_id, user_id=user_id, limit=limit
    )
    if not history:
        return {"summary": "No chat history found for this session."}

    # Compose LLM-ready message format (chronological)
    messages = []
    for row in reversed(history):
        # row: id, timestamp, session_id, user_id, role, message, response, backend, model, agent, tag, extra
        if row[4] == "user" and row[5]:
            messages.append({"role": "user", "content": row[5]})
        elif row[4] == "assistant" and row[6]:
            messages.append({"role": "assistant", "content": row[6]})

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
