from fastapi import FastAPI, Query, Request
from pydantic import BaseModel
from typing import Optional, List
from guardian import GuardianDB,   # If your function is in guardian.py
from datetime import datetime
from pathlib import Path

init_db()
DB_PATH = Path("guardian.db")
db = GuardianDB(DB_PATH)

app = FastAPI(title="Guardian Codex API")

# CORS middleware for local/frontend use
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust origins as needed for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.testclient import TestClient
import httpx

class CapsuleCreate(BaseModel):
    summary: str
    child_ids: List[int]
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

@app.get("/ping")
def ping():
    return {"status": "Guardian awake!"}

# Patched: now using GuardianDB abstraction
@app.post("/log")
def log_entry(entry: LogEntry):
    timestamp = datetime.now().isoformat()
    db.insert_memory(
        timestamp=timestamp,
        command=entry.command,
        tag=entry.tag,
        agent=entry.agent,
        type_="log",
        parent_id=None,
    )
    return {"result": "Log stored!", "timestamp": timestamp}

# Patched: now using GuardianDB abstraction
@app.post("/summarize")
def summarize_entry(entry: SummaryEntry):
    timestamp = datetime.now().isoformat()
    db.insert_memory(
        timestamp=timestamp,
        command=entry.summary,
        tag=entry.tag,
        agent=entry.agent,
        type_="summary",
        parent_id=entry.parent_id,
    )
    return {"result": "Summary stored!", "timestamp": timestamp}

# Patched: now using GuardianDB abstraction
@app.get("/search")
def search(query: str = Query(...), limit: int = 10):
    rows = db.search_memory(query, limit)
    results = [{"timestamp": r["timestamp"], "command": r["command"], "tag": r["tag"], "agent": r["agent"]} for r in rows]
    return results

# Patched: now using GuardianDB abstraction
@app.get("/history")
def history(limit: int = 10, tag: Optional[str] = None, agent: Optional[str] = None):
    rows = db.history_entries(limit=limit, tag=tag, agent=agent)
    results = [{"timestamp": r["timestamp"], "command": r["command"], "tag": r["tag"], "agent": r["agent"]} for r in rows]
    return results

# --- Gemini Proxy Endpoints Below ---

client = TestClient(app)

class GeminiChatRequest(BaseModel):
    prompt: str
    model: Optional[str] = "gemini-1.5"

class GeminiChatResponse(BaseModel):
    model_used: str
    reply: str

GEMINI_API_URL = "https://api.gemini.ai/v1/chat"  # Replace with actual Gemini API URL
GEMINI_API_KEY = "your_gemini_api_key_here"      # Replace with your Gemini API key

@app.get("/")
def gemini_status():
    return {"status": "Gemini proxy is running"}

@app.get("/test")
def gemini_test():
    return {"ping": "pong"}

@app.post("/chat", response_model=GeminiChatResponse)
def gemini_chat(req: GeminiChatRequest):
    # Log incoming prompt to Guardian memory via /log endpoint
    prompt_log = LogEntry(command=f"User prompt: {req.prompt}", tag="gemini", agent="user")
    client.post("/log", json=prompt_log.dict())

    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": req.model,
        "prompt": req.prompt
    }
    try:
        response = httpx.post(GEMINI_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        reply_text = data.get("reply", "")

        # Log AI reply to Guardian memory via /log endpoint
        reply_log = LogEntry(command=f"AI reply: {reply_text}", tag="gemini", agent="ai")
        client.post("/log", json=reply_log.dict())

        return GeminiChatResponse(model_used=req.model, reply=reply_text)
    except Exception as e:
        return {"model_used": req.model, "reply": f"Error contacting Gemini API: {str(e)}"}