#!/usr/bin/env python3

import typer
from typing import Optional
from datetime import datetime
import sqlite3
from pathlib import Path
from rich import print

DB_OLD_PATH = Path("guardian_memory.db")
if DB_OLD_PATH.exists():
    print("[yellow]Warning: Detected old database 'guardian_memory.db'. Consider migrating to 'guardian.db'.[/yellow]")

app = typer.Typer()
DB_PATH = Path("guardian.db")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Both 'memory' and 'memory_fts' tables are always created together
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        # Create capsule_links table for many-to-many relationships between capsules and memory/logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS capsule_links (
                capsule_id INTEGER,
                child_id INTEGER,
                PRIMARY KEY (capsule_id, child_id)
                -- (Add FOREIGN KEY constraints if you want)
            )
        """)
        conn.commit()
    print("[green]Memory tables have been created or verified.[/green]")

@app.command()
def log(
    command: str = typer.Argument(..., help="Log message or command to store."),
    tag: Optional[str] = typer.Option(None, help="Optional tag for this log entry."),
    type_: str = typer.Option("log", "--type", help="Type of memory entry."),
    source: Optional[str] = typer.Option(None, help="Origin/source of the memory."),
    parent_id: Optional[int] = typer.Option(None, help="If this is a summary or child, set parent_id."),
    priority: int = typer.Option(1, help="Priority (higher means more important)."),
    agent: str = typer.Option("system", "--agent", help="Which agent/persona is logging this?")
):
    """Store a memory entry in Guardian's database."""
    init_db()
    timestamp = datetime.now().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO memory (timestamp, command, tag, type, parent_id, source, priority, agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (timestamp, command, tag, type_, parent_id, source, priority, agent)
            )

        cursor.execute(
            """
            INSERT INTO memory_fts (rowid, command, tag, agent)
            VALUES (last_insert_rowid(), ?, ?, ?)
            """,
            (command, tag, agent)
        )

        conn.commit()
    tag_disp = f" [bold cyan]({tag})[/bold cyan]" if tag else ""
    print(f"[dim]{timestamp}[/dim] :: {command}{tag_disp}")

@app.command()
def search(
    query: str = typer.Argument(..., help="Search term in memory entries"),
    limit: int = typer.Option(10, help="Limit number of results.")
):
    """Search memory for a keyword in command text."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
"""
            SELECT memory.timestamp, memory.command, memory.tag, memory.agent
            FROM memory_fts
            JOIN memory ON memory_fts.rowid = memory.id
            WHERE memory_fts MATCH ?
            ORDER BY memory.id DESC LIMIT ?
            """,
	    (query, limit)
        )
        rows = cursor.fetchall()
    if not rows:
        print(f"[red]No results found for: '{query}'[/red]")
    else:
        for timestamp, command, tag, agent in rows:
            tag_display = f" [bold cyan]({tag})[/bold cyan]" if tag else ""
            print(f"[dim]{timestamp}[/dim] :: {command}{tag_display} [green](agent: {agent})[/green]")

@app.command()
def history(
    limit: int = typer.Option(10, help="Limit number of entries shown."),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag.")
):
    """Show recent memory entries."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        if tag:
            cursor.execute(
                "SELECT timestamp, command, tag, agent FROM memory WHERE tag = ? ORDER BY id DESC LIMIT ?",
                (tag, limit)
            )
        else:
            cursor.execute(
                "SELECT timestamp, command, tag, agent FROM memory ORDER BY id DESC LIMIT ?",
                (limit,)
            )
        rows = cursor.fetchall()
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
    agent: str = typer.Option("system", "--agent", help="Which agent/persona is logging this?")
):
    """Summarize a previous entry (recursive memory!)."""
    init_db()
    timestamp = datetime.now().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO memory (timestamp, command, tag, type, parent_id, source, priority, agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (timestamp, summary, tag, "summary", parent_id, source, priority, agent)
        )
        # Insert into FTS table for full-text search
        cursor.execute(
            """
            INSERT INTO memory_fts (rowid, command, tag, agent)
            VALUES (last_insert_rowid(), ?, ?, ?)
            """,
            (summary, tag, agent)
        )
        conn.commit()
    print(f"[green]Summary capsule created for parent_id {parent_id} by {agent}![green]")

if __name__ == "__main__":
    app()
