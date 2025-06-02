import os
import logging
from fastapi import FastAPI, Query, Request, HTTPException
from fastapi import Depends
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import Optional, List
from guardian import GuardianDB  # If your function is in guardian.py
from datetime import datetime
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
import requests
from fastapi import Header, Body

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
        logger.warning("Unauthorized attempt with API key: %s", api_key)
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return api_key

# Load configuration from environment variables
DB_PATH = Path(os.getenv("GUARDIAN_DB_PATH", "guardian.db"))
GEMINI_API_URL = os.getenv("GEMINI_API_URL", "https://api.gemini.ai/v1/chat")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_gemini_api_key_here")

# Initialize database
db = GuardianDB(DB_PATH)

app = FastAPI(title="Guardian Codex API")

# CORS middleware for local/frontend use
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust origins as needed for security
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
    api_key: str = Depends(require_api_key)
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
            {"timestamp": r["timestamp"], "command": r["command"], "tag": r["tag"], "agent": r["agent"]}
            for r in rows
        ]
        logger.info(f"Search performed with query: {query}, results found: {len(results)}")
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search operation failed")
    return results

@app.get("/history", summary="Retrieve history entries with optional filters", tags=["Memory"])
def history(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of entries to return"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    agent: Optional[str] = Query(None, description="Filter by agent"),
    start_date: Optional[str] = Query(None, description="Filter entries from this date (inclusive), format YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Filter entries up to this date (inclusive), format YYYY-MM-DD"),
    api_key: str = Depends(require_api_key)
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
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

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
            {"timestamp": r["timestamp"], "command": r["command"], "tag": r["tag"], "agent": r["agent"]}
            for r in filtered_rows
        ]
        logger.info(f"History retrieved with filters - tag: {tag}, agent: {agent}, start_date: {start_date}, end_date: {end_date}, entries returned: {len(results)}")
    except Exception as e:
        logger.error(f"Failed to retrieve history entries: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history entries")
    return results

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

@app.post("/chat", response_model=GeminiChatResponse, summary="Send chat prompt to Gemini API", tags=["Gemini Proxy"])
def gemini_chat(req: GeminiChatRequest, api_key: str = Depends(require_api_key)):
    """
    Send a chat prompt to the Gemini AI API and log the interaction in Guardian memory.

    Args:
        req (GeminiChatRequest): The chat request containing prompt and optional model.

    Returns:
        GeminiChatResponse: The response from Gemini API including model used and reply text.
    """
    # Log incoming prompt to Guardian memory via /log endpoint
    prompt_log = LogEntry(command=f"User prompt: {req.prompt}", tag="gemini", agent="user")
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
        "Content-Type": "application/json"
    }
    payload = {
        "model": req.model,
        "prompt": req.prompt
    }
    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        reply_text = data.get("reply", "")

        # Log AI reply to Guardian memory directly
        reply_log = LogEntry(command=f"AI reply: {reply_text}", tag="gemini", agent="ai")
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
        raise HTTPException(status_code=response.status_code, detail=f"Gemini API error: {http_err}")
    except Exception as e:
        logger.error(f"Error contacting Gemini API: {e}")
        raise HTTPException(status_code=500, detail=f"Error contacting Gemini API: {str(e)}")

@app.get("/whoami", summary="Get agent profile and identity", tags=["Agent"])
def whoami(
    agent_id: str = Header(..., description="Agent or User ID"),
    api_key: str = Depends(require_api_key)
):
    profile = db.get_agent_profile(agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Agent profile not found.")
    return profile

@app.post("/profile", summary="Update agent profile fields", tags=["Agent"])
def update_profile(
    agent_id: str = Header(..., description="Agent or User ID"),
    updates: dict = Body(...),
    api_key: str = Depends(require_api_key)
):
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided.")
    db.upsert_agent_profile(agent_id, **updates)
    return {"message": "Profile updated."}

@app.post("/profile/frequency", summary="Set/toggle agent summarization frequency", tags=["Agent"])
def set_frequency(
    agent_id: str = Header(..., description="Agent or User ID"),
    frequency: str = Body(..., embed=True),
    api_key: str = Depends(require_api_key)
):
    if frequency not in ["daily", "weekly", "monthly"]:
        raise HTTPException(status_code=400, detail="Invalid frequency.")
    db.upsert_agent_profile(agent_id, summarization_frequency=frequency)
    return {"message": f"Frequency set to {frequency}."}

@app.get("/summarization/check", summary="Check if summarization is allowed for agent", tags=["Agent"])
def summarization_check(
    agent_id: str = Query(...),
    requested_by: str = Query("ai"),
    api_key: str = Depends(require_api_key)
):
    allowed, msg = db.check_summarization_allowed(agent_id, requested_by)
    return {"allowed": allowed, "message": msg}

@app.post("/summarize", summary="Trigger summarization for agent if allowed", tags=["Agent"])
def trigger_summarization(
    agent_id: str = Header(..., description="Agent or User ID"),
    requested_by: str = Body("ai"),
    force: bool = Body(False),
    api_key: str = Depends(require_api_key)
):
    allowed, msg = db.check_summarization_allowed(agent_id, requested_by, force)
    if not allowed:
        raise HTTPException(status_code=403, detail=msg)
    db.increment_summarization_count(agent_id, requested_by)
    # Place actual summarization call/hook here as needed
    return {"message": "Summarization performed.", "details": msg}