from memoryos.embedders.local_embedder import LocalEmbedder
from memoryos.memoryos import Memoryos

embedder = LocalEmbedder()
memory = Memoryos(
    user_id="default",
    data_storage_path="./data",
    embedder=embedder,
)
import json
import logging

import typer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

from guardian.cli.imprint_zero_cli import ImprintZero
from guardian.core.orchestrator.pulse_orchestrator import orchestrate

# Vision helpers
from guardian.utils.groq_helpers import (
    run_groq_vision_file,
    run_groq_vision_url,
)

app = typer.Typer()

# Keep the imprint-zero group wired to the shared Typer app in guardian.cli.imprint_zero_cli.
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
        logger.error("Invalid JSON input.")
        raise typer.Exit(code=1)
    result = orchestrate(command_dict)
    logger.info("Orchestration Result:")
    logger.info(json.dumps(result, indent=2))


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
    logger.info(f"Running research agent in {mode} mode...")
    report = asyncio.run(generate_report(query, planner, agents))
    logger.info("Research Report:")
    logger.info(report)


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
        logger.info("Database connection verified.")
    except Exception as exc:  # pragma: no cover - CLI guard
        logger.error(f"Database check failed: {exc}")


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
    logger.info(f"Logged: {command!r} at {timestamp}")
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
        logger.warning("No memoryOS history found.")
        return
    for item in logs:
        ts = item.get("timestamp", "(no timestamp)")
        content = item.get("data", {}).get("content", "(no content)")
        logger.info(f"{ts} {content}")


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
        logger.warning("No history found.")
        return

    for row in rows:
        row_id, ts, cmd, tag, agent = row[:5]
        logger.info(f"{row_id:>4} {ts}  {cmd}  {tag or '-'}  {agent or '-'}")


@app.command("check-config")
def check_config():
    """Show current config status and highlight any missing/invalid values."""
    from pydantic import ValidationError

    try:
        from guardian.config import Settings

        current_settings = Settings()
        logger.info("All required config variables are set!")
        for key, value in current_settings.dict().items():
            # Mask secrets for display
            if "KEY" in key or "TOKEN" in key:
                display = "********" if value else "(Not set)"
            else:
                display = value or "(Not set)"
            logger.info(f"{key}: {display}")
    except ValidationError as e:
        logger.error("Configuration error: Missing or invalid settings.")
        for err in e.errors():
            field = err["loc"][0]
            logger.error(f" - {field}: {err['msg']}")
        logger.error(
            "To fix, set these as environment variables or in your .env file."
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
        logger.error("No .env file found in this directory.")
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
    logger.info(f"AI_BACKEND updated to: {backend}")


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
        logger.warning("No chat history found.")
        return
    for row in rows:
        # row: id, timestamp, session_id, user_id, role, message, response, backend, model, agent, tag, extra
        content = row[5] if row[4] == "user" else row[6]
        logger.info(f"{row[1]} {row[4]}: {content}")


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
        logger.warning("No chat history found.")
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
    logger.info(f"Summary:\n{summary}")


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
        logger.warning("No threads found.")
        return
    for row in rows:
        logger.info(
            f"Thread {row['id']} | Parent: {row.get('parent_id') or '-'} | "
            f"User: {row.get('user_id') or '-'} | "
            f"Project: {row.get('project_id') or '-'}"
        )
        logger.info(f"Summary: {row.get('summary') or '(None)'}")
        logger.info(f"Created: {row.get('created_at')}")


@app.command("show-thread")
def show_thread(thread_id: int = typer.Argument(..., help="Thread ID to show")):
    """Show details for a single thread (summary, parent, children)."""
    thread = db.get_thread(thread_id)
    if not thread:
        logger.error(f"Thread {thread_id} not found.")
        return
    logger.info(f"Thread {thread[0]}")
    logger.info(
        f"Parent: {thread[1] or '-'} | Session: {thread[2] or '-'} | User: {thread[5] or '-'} | Project: {thread[6] or '-'}"
    )
    logger.info(f"Summary: {thread[3] or '(None)'}")
    logger.info(f"Created: {thread[4]}")

    # Show children
    children = db.get_child_threads(thread_id)
    if children:
        logger.info("Children:")
        for child in children:
            logger.info(
                f"Thread {child[0]} (Session: {child[1]}, Summary: {child[2]})"
            )
    else:
        logger.info("No children.")


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
    logger.info(f"Branched new thread {new_id} from parent {parent_thread_id}.")


@app.command("show-children")
def show_children(
    parent_thread_id: int = typer.Argument(..., help="Parent thread ID")
):
    """List all child threads for a given parent."""
    children = db.get_child_threads(parent_thread_id)
    if not children:
        logger.warning("No child threads found.")
        return
    logger.info(f"Children of thread {parent_thread_id}:")
    for child in children:
        logger.info(
            f"Thread {child[0]} (Session: {child[1]}, Summary: {child[2]})"
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
        logger.error("Please specify either --image-url or --image-file")
        raise typer.Exit(code=1)

    logger.info("Groq Vision Result:")
    logger.info(result)


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
        logger.warning(
            "CLOUD ONLY MODE ENABLED: All LLM tasks routed to cloud."
        )
    elif hybrid:
        HybridRouter.set_hybrid_enabled(True)
        logger.info("Hybrid mode enabled: cloud for research, local for chat.")


if __name__ == "__main__":
    app()
