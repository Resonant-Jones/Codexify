"""
guardian.cli.main
=================
Command‑line interface for Guardian.

This module wraps the GuardianDB core logic in a Typer‑based CLI so you can
initialise the database, log entries, and query history from the terminal.

Run with:
    python -m guardian.cli.main --help
"""

from datetime import datetime
from typing import Optional

import typer
from rich import print

from guardian.core.db import GuardianDB
from guardian.config import get_settings

# --------------------------------------------------------------------------- #
# Setup
# --------------------------------------------------------------------------- #

app = typer.Typer(help="Guardian command‑line interface")
settings = get_settings()
db = GuardianDB(settings.GUARDIAN_DB_PATH)


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

@app.command()
def init() -> None:
    """Initialise the SQLite database schema."""
    db.init_db()
    print("[bold green]Database initialised.[/bold green]")


@app.command()
def log(
    command: str = typer.Argument(..., help="Text to log into memory"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Optional tag label"),
    agent: Optional[str] = typer.Option(
        None, "--agent", "-a", help="Name of the calling agent"
    ),
    user_id: str = typer.Option(
        "default", "--user", "-u", help="User ID (defaults to 'default')"
    ),
) -> None:
    """Insert a new memory row."""
    timestamp = datetime.utcnow().isoformat()
    db.insert_log(
        user_id=user_id,
        command=command,
        tag=tag,
        agent=agent,
        timestamp=timestamp,
    )
    print(f"[green]Logged:[/green] {command!r} at {timestamp}")


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Rows to display"),
    user_id: str = typer.Option("default", "--user", "-u", help="User ID filter"),
) -> None:
    """Show the most recent memory entries."""
    rows = db.get_history(limit=limit, user_id=user_id)
    if not rows:
        print("[yellow]No history found.[/yellow]")
        return

    for row in rows:
        row_id, ts, cmd, tag, agent = row[:5]
        print(f"[cyan]{row_id:>4}[/cyan] {ts}  {cmd}  {tag or '-'}  {agent or '-'}")


@app.command("check-config")
def check_config():
    """Show current config status and highlight any missing/invalid values."""
    from pydantic import ValidationError
    try:
        from guardian.config import Settings
        current_settings = Settings()
        print("[bold green]✅ All required config variables are set![/bold green]\n")
        for key, value in current_settings.dict().items():
            # Mask secrets for display
            if "KEY" in key or "TOKEN" in key:
                display = "********" if value else "(Not set)"
            else:
                display = value or "(Not set)"
            print(f"[bold]{key}:[/bold] {display}")
    except ValidationError as e:
        print("[bold red]❌ Configuration error: Missing or invalid settings.[/bold red]\n")
        for err in e.errors():
            field = err["loc"][0]
            print(f" - {field}: {err['msg']}")
        print("\nTo fix, set these as environment variables or in your .env file.")
        raise typer.Exit(code=1)


# --------------------------------------------------------------------------- #
# Entrypoint
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    app()