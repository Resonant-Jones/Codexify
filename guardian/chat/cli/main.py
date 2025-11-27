from memoryos.embedders.local_embedder import LocalEmbedder
from memoryos.memoryos import Memoryos

embedder = LocalEmbedder()
memory = Memoryos(
    user_id="default",
    data_storage_path="./data",
    embedder=embedder,
)
import json

import typer

from guardian.cli.imprint_zero_cli import ImprintZero
from guardian.core.orchestrator.pulse_orchestrator import orchestrate

# Vision helpers
from guardian.utils.groq_helpers import (
    run_groq_vision_file,
    run_groq_vision_url,
)

app = typer.Typer()

app.add_typer(ImprintZero, name="imprint-zero")


# Add a new CLI command for orchestrate
@app.command("orchestrate")
def orchestrate_command(
    json_input: str = typer.Argument(
        ...,
        help="JSON string representing the command for Gemma to orchestrate.",
    )
):
    """Send a structured command to Gemma's orchestrator engine."""
    try:
        command_dict = json.loads(json_input)
    except json.JSONDecodeError:
        print("[red]Invalid JSON input.[/red]")
        raise typer.Exit(code=1)
    result = orchestrate(command_dict)
    print("[bold green]Orchestration Result:[/bold green]")
    print(json.dumps(result, indent=2))


# --------------------------------------------------------------------------- #
# Research Agent Command
# --------------------------------------------------------------------------- #
from datetime import timezone


@app.command("research")
def research(
    query: str = typer.Argument(..., help="What do you want to research?"),
    mode: str = typer.Option(
        "web", "--mode", "-m", help="'web', 'codex', or 'hybrid' (default: web)"
    ),
):
    """Run the research agent (web, codex, or hybrid)."""
    import asyncio

    from guardian.core.research.Modules.agent import Agent, Planner
    from guardian.core.research.Modules.main import generate_report, read_config

    config = read_config()
    planner = Planner(**config.get("planner", {}))
    agents = [Agent(**a) for a in config.get("agents", [])]

    # You could allow different agent setups for 'web' or 'codex' modes in future
    print(f"[bold green]Running research agent in {mode} mode...[/bold green]")
    report = asyncio.run(generate_report(query, planner, agents))
    print("[bold magenta]Research Report:[/bold magenta]\n")
    print(report)


"""
guardian.cli.main
=================
Command‑line interface for Guardian.

This module wraps the GuardianDB core logic in a Typer‑based CLI so you can
initialise the database, log entries, and query history from the terminal.

Run with:
    python -m guardian.cli.main --help
"""

import os
from datetime import datetime, timezone
from typing import Optional

from rich import print

from guardian.config import get_settings
from guardian.core.db import GuardianDB
from guardian.core.utils.hybrid_router import HybridRouter

# --------------------------------------------------------------------------- #
# Setup
# --------------------------------------------------------------------------- #


settings = get_settings()
_db_url = getattr(settings, "GUARDIAN_DATABASE_URL", None) or os.getenv(
    "DATABASE_URL"
)
if not _db_url:
    raise RuntimeError(
        "DATABASE_URL or GUARDIAN_DATABASE_URL is required for guardian CLI commands."
    )
db = GuardianDB(_db_url)


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


@app.command()
def init() -> None:
    """Verify Postgres connectivity (schema is managed via Alembic)."""
    try:
        db.count_chat_threads()
        print("[bold green]Database connection verified.[/bold green]")
    except Exception as exc:  # pragma: no cover - CLI guard
        print(f"[red]Database check failed:[/red] {exc}")


@app.command()
def log(
    command: str = typer.Argument(..., help="Text to log into memory"),
    tag: Optional[str] = typer.Option(
        None, "--tag", "-t", help="Optional tag label"
    ),
    agent: Optional[str] = typer.Option(
        None, "--agent", "-a", help="Name of the calling agent"
    ),
    user_id: str = typer.Option(
        "default", "--user", "-u", help="User ID (defaults to 'default')"
    ),
) -> None:
    """Insert a new memory row."""
    timestamp = datetime.now(timezone.utc).isoformat()
    db.insert_log(
        user_id=user_id,
        command=command,
        tag=tag,
        agent=agent,
        timestamp=timestamp,
    )
    print(f"[green]Logged:[/green] {command!r} at {timestamp}")
    memory.log_event(
        user_id=user_id,
        agent=agent,
        data={
            "type": "log",
            "content": command,
            "tag": tag,
            "timestamp": timestamp,
        },
    )


# --------------------------------------------------------------------------- #
# MemoryOS Memory History Command
# --------------------------------------------------------------------------- #


@app.command("memory-history")
def memory_history(
    user_id: str = typer.Option("default", "--user", "-u"),
    limit: int = typer.Option(10, "--limit", "-n"),
):
    logs = memory.fetch_memory(user_id=user_id, limit=limit)
    if not logs:
        print("[yellow]No memoryOS history found.[/yellow]")
        return
    for item in logs:
        ts = item.get("timestamp", "(no timestamp)")
        content = item.get("data", {}).get("content", "(no content)")
        print(f"[cyan]{ts}[/cyan] {content}")


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Rows to display"),
    user_id: str = typer.Option(
        "default", "--user", "-u", help="User ID filter"
    ),
) -> None:
    """Show the most recent memory entries."""
    rows = db.get_history(limit=limit, user_id=user_id)
    if not rows:
        print("[yellow]No history found.[/yellow]")
        return

    for row in rows:
        row_id, ts, cmd, tag, agent = row[:5]
        print(
            f"[cyan]{row_id:>4}[/cyan] {ts}  {cmd}  {tag or '-'}  {agent or '-'}"
        )


@app.command("check-config")
def check_config():
    """Show current config status and highlight any missing/invalid values."""
    from pydantic import ValidationError

    try:
        from guardian.config import Settings

        current_settings = Settings()
        print(
            "[bold green]✅ All required config variables are set![/bold green]\n"
        )
        for key, value in current_settings.dict().items():
            # Mask secrets for display
            if "KEY" in key or "TOKEN" in key:
                display = "********" if value else "(Not set)"
            else:
                display = value or "(Not set)"
            print(f"[bold]{key}:[/bold] {display}")
    except ValidationError as e:
        print(
            "[bold red]❌ Configuration error: Missing or invalid settings.[/bold red]\n"
        )
        for err in e.errors():
            field = err["loc"][0]
            print(f" - {field}: {err['msg']}")
        print(
            "\nTo fix, set these as environment variables or in your .env file."
        )
        raise typer.Exit(code=1)


# --------------------------------------------------------------------------- #
# Config Status Command
# --------------------------------------------------------------------------- #


@app.command("config-status")
def config_status():
    """Print a summary of the active config and warn if anything is missing."""
    from guardian.config import print_config_status

    print_config_status()


# --------------------------------------------------------------------------- #
# Set AI Backend Command
# --------------------------------------------------------------------------- #


@app.command("set-backend")
def set_backend(
    backend: str = typer.Argument(
        ...,
        help="AI backend to use (e.g., ollama, openai, gemini, nebius, groq)",
    )
):
    """Update the AI_BACKEND setting in the .env file."""
    from pathlib import Path

    env_path = Path(".env")
    if not env_path.exists():
        print("[red]No .env file found in this directory.[/red]")
        raise typer.Exit(code=1)

    lines = env_path.read_text().splitlines()
    updated = False
    for idx, line in enumerate(lines):
        if line.startswith("AI_BACKEND="):
            lines[idx] = f"AI_BACKEND={backend}"
            updated = True
            break
    if not updated:
        lines.append(f"AI_BACKEND={backend}")

    env_path.write_text("\n".join(lines) + "\n")
    print(f"[bold green]✅ AI_BACKEND updated to:[/bold green] {backend}")


# --------------------------------------------------------------------------- #
# Chat History and Summarize Commands
# --------------------------------------------------------------------------- #


@app.command("chat-history")
def chat_history(
    session_id: str = typer.Option(
        ..., "--session-id", "-s", help="Session ID to fetch"
    ),
    user_id: str = typer.Option("default", "--user", "-u", help="User ID"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of messages"),
) -> None:
    """Show recent chat log entries from the chat_log table."""
    rows = db.get_chat_history(
        session_id=session_id, user_id=user_id, limit=limit
    )
    if not rows:
        print("[yellow]No chat history found.[/yellow]")
        return
    for row in rows:
        # row: id, timestamp, session_id, user_id, role, message, response, backend, model, agent, tag, extra
        content = row[5] if row[4] == "user" else row[6]
        print(f"[magenta]{row[1]}[/magenta] [bold]{row[4]}[/bold]: {content}")


@app.command("summarize-chat")
def summarize_chat(
    session_id: str = typer.Option(
        ..., "--session-id", "-s", help="Session ID to summarize"
    ),
    user_id: str = typer.Option("default", "--user", "-u", help="User ID"),
    limit: int = typer.Option(
        20, "--limit", "-n", help="How many messages to summarize"
    ),
):
    """Summarize the chat log for a session using the active LLM backend."""
    from guardian.core.ai_router import (  # Import here to avoid CLI boot issues if backend changes
        chat_with_ai,
    )

    rows = db.get_chat_history(
        session_id=session_id, user_id=user_id, limit=limit
    )
    if not rows:
        print("[yellow]No chat history found.[/yellow]")
        return
    messages = []
    for row in reversed(rows):
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
    summary = chat_with_ai(summary_prompt)
    print("[bold green]Summary:[/bold green]\n" + summary)


# --------------------------------------------------------------------------- #
# Thread Lineage Commands
# --------------------------------------------------------------------------- #


@app.command("list-threads")
def list_threads(
    user_id: str = typer.Option(
        None, "--user", "-u", help="User ID (optional)"
    ),
    project_id: str = typer.Option(
        None, "--project", "-p", help="Project ID (optional)"
    ),
):
    """List all threads (optionally filtered by user or project)."""
    rows = db.list_threads(user_id=user_id, project_id=project_id)
    if not rows:
        print("[yellow]No threads found.[/yellow]")
        return
    for row in rows:
        print(
            f"[cyan]Thread {row['id']}[/cyan] | Parent: {row.get('parent_id') or '-'} | "
            f"[magenta]User:[/magenta] {row.get('user_id') or '-'} | "
            f"[magenta]Project:[/magenta] {row.get('project_id') or '-'}"
        )
        print(f"  [green]Summary:[/green] {row.get('summary') or '(None)'}")
        print(f"  Created: {row.get('created_at')}")
        print("")


@app.command("show-thread")
def show_thread(thread_id: int = typer.Argument(..., help="Thread ID to show")):
    """Show details for a single thread (summary, parent, children)."""
    thread = db.get_thread(thread_id)
    if not thread:
        print(f"[red]Thread {thread_id} not found.[/red]")
        return
    print(f"[bold cyan]Thread {thread[0]}[/bold cyan]")
    print(
        f"Parent: {thread[1] or '-'} | Session: {thread[2] or '-'} | User: {thread[5] or '-'} | Project: {thread[6] or '-'}"
    )
    print(f"[green]Summary:[/green] {thread[3] or '(None)'}")
    print(f"Created: {thread[4]}\n")

    # Show children
    children = db.get_child_threads(thread_id)
    if children:
        print("[blue]Children:[/blue]")
        for child in children:
            print(
                f" - [cyan]Thread {child[0]}[/cyan] (Session: {child[1]}, Summary: {child[2]})"
            )
    else:
        print("[blue]No children.[/blue]")


@app.command("branch-thread")
def branch_thread(
    parent_thread_id: int = typer.Argument(..., help="Parent thread ID"),
    session_id: str = typer.Option(
        None, "--session-id", "-s", help="Session ID for new thread"
    ),
    summary: str = typer.Option(
        "", "--summary", "-m", help="Initial summary for child thread"
    ),
    user_id: str = typer.Option("default", "--user", "-u", help="User ID"),
    project_id: str = typer.Option(None, "--project", "-p", help="Project ID"),
):
    """Create a new child thread branching from a parent."""
    new_id = db.create_thread(
        parent_thread_id, session_id, summary, user_id, project_id
    )
    print(
        f"[green]Branched new thread {new_id} from parent {parent_thread_id}.[/green]"
    )


@app.command("show-children")
def show_children(
    parent_thread_id: int = typer.Argument(..., help="Parent thread ID")
):
    """List all child threads for a given parent."""
    children = db.get_child_threads(parent_thread_id)
    if not children:
        print("[yellow]No child threads found.[/yellow]")
        return
    print(f"[blue]Children of thread {parent_thread_id}:[/blue]")
    for child in children:
        print(
            f" - [cyan]Thread {child[0]}[/cyan] (Session: {child[1]}, Summary: {child[2]})"
        )


# --------------------------------------------------------------------------- #
# Entrypoint
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# Groq Vision Command
# --------------------------------------------------------------------------- #


@app.command("vision")
def vision(
    image_url: str = typer.Option(None, "--image-url", help="URL to the image"),
    image_file: str = typer.Option(
        None, "--image-file", help="Path to a local image file"
    ),
    text: str = typer.Option(
        "What's in this image?",
        "--text",
        "-t",
        help="Prompt text for vision model",
    ),
):
    """Run Groq vision model on a URL or local image."""
    if image_url:
        result = run_groq_vision_url(image_url, text)
    elif image_file:
        result = run_groq_vision_file(image_file, text)
    else:
        print("[red]❌ Please specify either --image-url or --image-file[/red]")
        raise typer.Exit(code=1)

    print("[bold green]Groq Vision Result:[/bold green]")
    print(result)


# CLI root callback to set LLM routing mode via CLI flags
@app.callback()
def main(
    cloud_only: bool = typer.Option(
        False,
        "--cloud-only",
        help="Force all LLM calls to cloud (sovereignty warning!)",
    ),
    hybrid: bool = typer.Option(
        False,
        "--hybrid",
        help="Enable hybrid mode: cloud for research, local for chat",
    ),
):
    """
    Guardian CLI root callback: set LLM routing mode via CLI flags.
    """
    if cloud_only:
        HybridRouter.set_cloud_only(True)
        print(
            "[bold yellow]⚠️  CLOUD ONLY MODE ENABLED: All LLM tasks routed to cloud.[/bold yellow]"
        )
    elif hybrid:
        HybridRouter.set_hybrid_enabled(True)
        print(
            "[cyan]Hybrid mode enabled: cloud for research, local for chat.[/cyan]"
        )


if __name__ == "__main__":
    app()
