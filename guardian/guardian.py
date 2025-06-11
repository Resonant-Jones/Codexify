#!/usr/bin/env python3
import typer
import json
import sqlite3
from typing import Optional
from datetime import datetime
from pathlib import Path
from rich import print

# Schema Version: 1.0

DB_OLD_PATH = Path("guardian_memory.db")
if DB_OLD_PATH.exists():
    print("[yellow]Warning: Detected old database 'guardian_memory.db'. Consider migrating to 'guardian.db'.[/yellow]")

app = typer.Typer()
DB_PATH = Path("guardian.db")

class GuardianDB:
    def __init__(self, db_path):
        self.db_path = db_path

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    display_name TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL DEFAULT 'default',
                    timestamp TEXT NOT NULL,
                    command TEXT NOT NULL,
                    tag TEXT,
                    type TEXT DEFAULT 'log',
                    parent_id INTEGER,
                    source TEXT,
                    related_to INTEGER,
                    priority INTEGER DEFAULT 1,
                    agent TEXT
                )
            """)
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    command,
                    tag,
                    agent,
                    content='memory',
                    content_rowid='id'
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS capsule_links (
                    user_id TEXT NOT NULL DEFAULT 'default',
                    capsule_id INTEGER,
                    child_id INTEGER,
                    PRIMARY KEY (user_id, capsule_id, child_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            cursor.execute("""
                INSERT OR IGNORE INTO schema_meta (key, value) VALUES ('version', '1.0')
            """)
            conn.commit()
        print("[green]Memory tables have been created or verified.[/green]")

    def insert_memory(self, command: str, tag: Optional[str], type_: str, source: Optional[str], parent_id: Optional[int], priority: int, agent: str, user_id: str):
        timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO memory (user_id, timestamp, command, tag, type, parent_id, source, priority, agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, timestamp, command, tag, type_, parent_id, source, priority, agent)
            )
            cursor.execute(
                """
                INSERT INTO memory_fts (rowid, command, tag, agent)
                VALUES (last_insert_rowid(), ?, ?, ?)
                """,
                (command, tag, agent)
            )
            conn.commit()
        return timestamp

    def search_memory(self, query: str, limit: int, user_id: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT memory.timestamp, memory.command, memory.tag, memory.agent
                FROM memory_fts
                JOIN memory ON memory_fts.rowid = memory.id
                WHERE memory_fts MATCH ? AND memory.user_id = ?
                ORDER BY memory.id DESC LIMIT ?
                """,
                (query, user_id, limit)
            )
            rows = cursor.fetchall()
        return rows

    def history_entries(self, limit: int, tag: Optional[str], user_id: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if tag:
                cursor.execute(
                    "SELECT timestamp, command, tag, agent FROM memory WHERE tag = ? AND user_id = ? ORDER BY id DESC LIMIT ?",
                    (tag, user_id, limit)
                )
            else:
                cursor.execute(
                    "SELECT timestamp, command, tag, agent FROM memory WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                    (user_id, limit)
                )
            rows = cursor.fetchall()
        return rows

    def summarize_entry(self, parent_id: int, summary: str, tag: Optional[str], source: Optional[str], priority: int, agent: str, user_id: str):
        timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO memory (user_id, timestamp, command, tag, type, parent_id, source, priority, agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, timestamp, summary, tag, "summary", parent_id, source, priority, agent)
            )
            cursor.execute(
                """
                INSERT INTO memory_fts (rowid, command, tag, agent)
                VALUES (last_insert_rowid(), ?, ?, ?)
                """,
                (summary, tag, agent)
            )
            conn.commit()
        return timestamp

    

    def migrate_agent_profiles(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_profiles (
                agent_id TEXT PRIMARY KEY,
                user_id TEXT,
                display_name TEXT,
                role TEXT,
                archetype TEXT,
                profile TEXT,
                identity_summary TEXT,
                personality_mode TEXT,
                requested_by_user INTEGER,
                evolution_log TEXT,
                recursion_count INTEGER,
                last_reflected TEXT,
                created_at TEXT,
                last_active TEXT,
                summarization_frequency TEXT DEFAULT 'daily',
                last_summarized TEXT,
                human_summary_count_today INTEGER DEFAULT 0,
                ai_summary_count_today INTEGER DEFAULT 0
            )
            """)
            conn.commit()

    def upsert_agent_profile(self, agent_id, **fields):
        # Only update supplied fields
        cols = []
        vals = []
        for k, v in fields.items():
            cols.append(f"{k} = ?")
            vals.append(json.dumps(v) if isinstance(v, (dict, list)) else v)
        sql = f"UPDATE agent_profiles SET {', '.join(cols)} WHERE agent_id = ?"
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            updated = cursor.execute(sql, vals + [agent_id]).rowcount
            if not updated:
                all_fields = fields.copy()
                all_fields['agent_id'] = agent_id
                col_names = ','.join(all_fields.keys())
                qmarks = ','.join(['?']*len(all_fields))
                vals2 = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in all_fields.values()]
                cursor.execute(f"INSERT INTO agent_profiles ({col_names}) VALUES ({qmarks})", vals2)
            conn.commit()

    def get_agent_profile(self, agent_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agent_profiles WHERE agent_id = ?", (agent_id,))
            row = cursor.fetchone()
            if not row:
                return None
            columns = [desc[0] for desc in cursor.description]
            profile = dict(zip(columns, row))
            # Decode JSON fields if present
            for k in ("evolution_log",):
                if profile.get(k):
                    try:
                        profile[k] = json.loads(profile[k])
                    except Exception:
                        pass
            return profile

    def check_summarization_allowed(self, agent_id, requested_by="ai", force=False):
        profile = self.get_agent_profile(agent_id)
        if not profile:
            return False, "Profile not found."

        freq = profile.get('summarization_frequency') or 'daily'
        now = datetime.now(datetime.UTC)
        last = None
        if profile.get('last_summarized'):
            try:
                last = datetime.fromisoformat(profile['last_summarized'])
            except Exception:
                last = None

        # Set min_delta (days) based on frequency
        min_delta = {'daily': 1, 'weekly': 7, 'monthly': 30}.get(freq, 1)
        limit_map = {'ai': 1, 'human': 1}  # Change quota here if you want more/less per day

        if force:
            return True, "Force override."

        # Check cooldown period
        if last:
            delta_days = (now - last).days
            if delta_days < min_delta:
                return False, f"Must wait {min_delta - delta_days} more day(s) for next summary ({freq} mode)."

        if requested_by == "human":
            count = profile.get('human_summary_count_today') or 0
            if count >= limit_map['human']:
                return False, "Human summary quota reached for today."
        elif requested_by == "ai":
            count = profile.get('ai_summary_count_today') or 0
            if count >= limit_map['ai']:
                return False, "AI summary quota reached for today."

        return True, "Summarization allowed."

    def increment_summarization_count(self, agent_id, requested_by="ai"):
        profile = self.get_agent_profile(agent_id)
        if not profile:
            return
        field = "ai_summary_count_today" if requested_by == "ai" else "human_summary_count_today"
        count = (profile.get(field) or 0) + 1
        now = datetime.now(datetime.UTC).isoformat()
        self.upsert_agent_profile(agent_id, **{
            field: count,
            "last_summarized": now
        })

    def reset_summarization_counts(self, agent_id):
        self.upsert_agent_profile(
            agent_id,
            ai_summary_count_today=0,
            human_summary_count_today=0
        )

@app.command()
def log(
    command: str = typer.Argument(..., help="Log message or command to store."),
    tag: Optional[str] = typer.Option(None, help="Optional tag for this log entry."),
    type_: str = typer.Option("log", "--type", help="Type of memory entry."),
    source: Optional[str] = typer.Option(None, help="Origin/source of the memory."),
    parent_id: Optional[int] = typer.Option(None, help="If this is a summary or child, set parent_id."),
    priority: int = typer.Option(1, help="Priority (higher means more important)."),
    agent: str = typer.Option("system", "--agent", help="Which agent/persona is logging this?"),
    user_id: str = typer.Option("default", "--user-id", help="User ID for multi-user support")
):
    """Store a memory entry in Guardian's database."""
    db = GuardianDB(DB_PATH)
    db.init_db()
    db.migrate_agent_profiles()
    timestamp = db.insert_memory(command, tag, type_, source, parent_id, priority, agent, user_id)
    tag_disp = f" [bold cyan]({tag})[/bold cyan]" if tag else ""
    print(f"[dim]{timestamp}[/dim] :: {command}{tag_disp} [green](agent: {agent})[/green]")

@app.command()
def search(
    query: str = typer.Argument(..., help="Search term in memory entries"),
    limit: int = typer.Option(10, help="Limit number of results."),
    user_id: str = typer.Option("default", "--user-id", help="User ID for multi-user support")
):
    """Search memory for a keyword in command text."""
    db = GuardianDB(DB_PATH)
    db.init_db()
    db.migrate_agent_profiles()
    rows = db.search_memory(query, limit, user_id)
    if not rows:
        print(f"[red]No results found for: '{query}'[/red]")
    else:
        for timestamp, command, tag, agent in rows:
            tag_display = f" [bold cyan]({tag})[/bold cyan]" if tag else ""
            print(f"[dim]{timestamp}[/dim] :: {command}{tag_display} [green](agent: {agent})[/green]")

@app.command()
def history(
    limit: int = typer.Option(10, help="Limit number of entries shown."),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag."),
    user_id: str = typer.Option("default", "--user-id", help="User ID for multi-user support")
):
    """Show recent memory entries."""
    db = GuardianDB(DB_PATH)
    db.init_db()
    db.migrate_agent_profiles()
    rows = db.history_entries(limit, tag, user_id)
    if not rows:
        print("[red]No entries found.[/red]")
    else:
        for timestamp, command, tag, agent in rows:
            tag_disp = f" [bold cyan]({tag})[/bold cyan]" if tag else ""
            print(f"[dim]{timestamp}[/dim] :: {command}{tag_disp} [green](agent: {agent})[/green]")

@app.command()
def summarize(
    parent_id: int = typer.Argument(..., help="ID of entry being summarized."),
    summary: str = typer.Argument(..., help="Summary text."),
    tag: Optional[str] = typer.Option(None, help="Optional tag for the summary."),
    source: Optional[str] = typer.Option(None, help="Summary source or method."),
    priority: int = typer.Option(1, help="Priority of the summary."),
    agent: str = typer.Option("system", "--agent", help="Which agent/persona is logging this?"),
    user_id: str = typer.Option("default", "--user-id", help="User ID for multi-user support")
):
    """Summarize a previous entry (recursive memory!)."""
    db = GuardianDB(DB_PATH)
    db.init_db()
    db.migrate_agent_profiles()
    timestamp = db.summarize_entry(parent_id, summary, tag, source, priority, agent, user_id)
    print(f"[green]Summary capsule created for parent_id {parent_id} by {agent}![green]")
