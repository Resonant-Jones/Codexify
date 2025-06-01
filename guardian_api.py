from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
from typing import List, Optional
from pydantic import BaseModel

class CapsuleCreate(BaseModel):
    summary: str
    child_ids: List[int]
    tag: Optional[str] = None
    agent: Optional[str] = None
from datetime import datetime
from pathlib import Path
from guardian import init_db  # If your function is in guardian.py
init_db()
DB_PATH = Path("guardian.db")

app = FastAPI(title="Guardian Codex API")

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

@app.post("/log")
def log_entry(entry: LogEntry):
    timestamp = datetime.now().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO memory (timestamp, command, tag, agent) VALUES (?, ?, ?, ?)",
            (timestamp, entry.command, entry.tag, entry.agent)
        )
        cursor.execute(
            "INSERT INTO memory_fts (rowid, command, tag, agent) VALUES (last_insert_rowid(), ?, ?, ?)",
            (entry.command, entry.tag, entry.agent)
        )
        conn.commit()
    return {"result": "Log stored!", "timestamp": timestamp}

@app.post("/summarize")
def summarize_entry(entry: SummaryEntry):
    timestamp = datetime.now().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO memory (timestamp, command, tag, type, parent_id, agent) VALUES (?, ?, ?, ?, ?, ?)",
            (timestamp, entry.summary, entry.tag, "summary", entry.parent_id, entry.agent)
        )
        cursor.execute(
            "INSERT INTO memory_fts (rowid, command, tag, agent) VALUES (last_insert_rowid(), ?, ?, ?)",
            (entry.summary, entry.tag, entry.agent)
        )
        conn.commit()
    return {"result": "Summary stored!", "timestamp": timestamp}

@app.get("/search")
def search(query: str = Query(...), limit: int = 10):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT memory.timestamp, memory.command, memory.tag, memory.agent FROM memory_fts JOIN memory ON memory_fts.rowid = memory.id WHERE memory_fts MATCH ? ORDER BY memory.id DESC LIMIT ?",
            (query, limit)
        )
        rows = cursor.fetchall()
    results = [{"timestamp": t, "command": c, "tag": tag, "agent": agent} for t, c, tag, agent in rows]
    return results

@app.get("/history")
def history(limit: int = 10, tag: Optional[str] = None, agent: Optional[str] = None):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        if tag and agent:
            cursor.execute(
                "SELECT timestamp, command, tag, agent FROM memory WHERE tag = ? AND agent = ? ORDER BY id DESC LIMIT ?",
                (tag, agent, limit)
            )
        elif tag:
            cursor.execute(
                "SELECT timestamp, command, tag, agent FROM memory WHERE tag = ? ORDER BY id DESC LIMIT ?",
                (tag, limit)
            )
        elif agent:
            cursor.execute(
                "SELECT timestamp, command, tag, agent FROM memory WHERE agent = ? ORDER BY id DESC LIMIT ?",
                (agent, limit)
            )
        else:
            cursor.execute(
                "SELECT timestamp, command, tag, agent FROM memory ORDER BY id DESC LIMIT ?",
                (limit,)
            )
        rows = cursor.fetchall()
    results = [{"timestamp": t, "command": c, "tag": tag, "agent": agent} for t, c, tag, agent in rows]
    return results