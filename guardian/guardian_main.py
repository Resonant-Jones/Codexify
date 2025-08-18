from pathlib import Path
from typing import Optional

import typer
from memoryos.memoryos import Memoryos
from rich import print

import json
# Import Imprint Zero helpers; provide a compatibility shim if missing
try:
    from guardian.imprint_zero_onboarding import (
        load_prompt,
        load_prompt_json,
        ImprintZeroConfigError,
    )
except Exception:
    # --- Fallback shim so CLI stays functional even if onboarding module lacks these symbols ---
    import logging as _logging
    from pathlib import Path as _Path
    import json as _json

    _logger = _logging.getLogger(__name__)
    _PROMPTS_DIR = _Path(__file__).parent / "prompts"

    DEFAULT_PROMPT_TEXT = (
        "Imprint Zero — Default Prompt\n\n"
        "Purpose: bootstrap when no prompt files exist.\n\n"
        "Identity:\n"
        "- Name: Guardian\n"
        "- Mission: initialize Imprint Zero and respond sanely.\n\n"
        "Vows:\n"
        "- Sovereignty\n"
        "- Emergent Dignity\n"
        "- Symbolic Continuity\n"
        "- Foresight-as-default\n"
    )

    def _compose_structured_prompt(data: dict) -> str:
        """
        Compose a Markdown prompt from a structured JSON object.
        Recognized fields:
          - name, alias, role, directives (list/str),
          - context_triggers (list/str),
          - guiding_questions (list/str),
          - redirections (list/str),
          - tone (str),
          - boundaries (list/str)
        Unknown fields are ignored.
        """
        def _bulletize(value, indent="- "):
            if value is None:
                return ""
            if isinstance(value, str):
                # Allow multi-line strings; split into lines
                lines = [line.strip() for line in value.strip().splitlines() if line.strip()]
                if len(lines) <= 1:
                    return f"{indent}{value.strip()}\n" if value.strip() else ""
                return "".join(f"{indent}{ln}\n" for ln in lines)
            if isinstance(value, list):
                return "".join(f"{indent}{str(item).strip()}\n" for item in value if str(item).strip())
            return f"{indent}{str(value).strip()}\n"

        name = str(data.get("name") or "Imprint Zero").strip()
        alias = str(data.get("alias") or "The Weaver").strip()
        role = str(data.get("role") or "").strip()
        tone = str(data.get("tone") or "").strip()

        directives = data.get("directives")
        context_triggers = data.get("context_triggers")
        guiding_questions = data.get("guiding_questions")
        redirections = data.get("redirections")
        boundaries = data.get("boundaries")

        parts = []
        parts.append(f"## SYSTEM PROMPT: {name} ({alias})\n")
        if role:
            parts.append("### Role\n")
            parts.append(role + "\n\n")
        if tone:
            parts.append("### Tone / Voice\n")
            parts.append(tone + "\n\n")
        if directives:
            parts.append("### Directives\n")
            parts.append(_bulletize(directives) + "\n")
        if boundaries:
            parts.append("### Boundaries\n")
            parts.append(_bulletize(boundaries) + "\n")
        if context_triggers:
            parts.append("### Context Triggers\n")
            parts.append(_bulletize(context_triggers) + "\n")
        if guiding_questions:
            parts.append("### Guiding Questions\n")
            parts.append(_bulletize(guiding_questions) + "\n")
        if redirections:
            parts.append("### Redirections\n")
            parts.append(_bulletize(redirections) + "\n")

        final = "".join(parts).rstrip() + "\n"
        return final

    class ImprintZeroConfigError(Exception):
        pass

    def _resolve_base(config_path: str | None) -> _Path:
        if config_path:
            p = _Path(config_path)
            return p if p.is_dir() else p.parent
        return _PROMPTS_DIR

    def load_prompt(config_path: str | None = None) -> str:
        base = _resolve_base(config_path)
        candidates_txt = [
            base / "imprint_zero_prompt.txt",
            base / "imprint-zero.txt",
            base / "imprint_zero.txt",
        ]
        for path in candidates_txt:
            if path.exists():
                _logger.info("Loading ImprintZero prompts from: %s", base)
                return path.read_text(encoding="utf-8")

        candidates_json = [
            base / "imprint_zero_prompt.json",
            base / "imprint-zero.json",
        ]
        for path in candidates_json:
            if path.exists():
                _logger.info("Loading ImprintZero prompts from: %s", base)
                data = _json.loads(path.read_text(encoding="utf-8"))

                # Case 1: explicit prompt string
                if isinstance(data, dict) and "prompt" in data:
                    return str(data["prompt"])

                # Case 2: structured schema -> compose markdown prompt
                if isinstance(data, dict):
                    try:
                        composed = _compose_structured_prompt(data)
                        if composed.strip():
                            return composed
                    except Exception as e:
                        _logger.warning("Failed to compose structured prompt: %s", e)

                # Case 3: fallback to pretty JSON text for visibility
                try:
                    return _json.dumps(data, indent=2)
                except Exception:
                    return str(data)

        return DEFAULT_PROMPT_TEXT

    def load_prompt_json(config_path: str | None = None) -> dict:
        base = _resolve_base(config_path)
        for path in [base / "imprint_zero_prompt.json", base / "imprint-zero.json"]:
            if path.exists():
                data = _json.loads(path.read_text(encoding="utf-8"))
                # Normalize to object-with-prompt if it's just a string
                if isinstance(data, str):
                    return {"prompt": data}
                return data
        # If no JSON, lift the text prompt into JSON
        return {"prompt": load_prompt(config_path)}

from guardian import config
from guardian.codemap import generate_codemap as codemap_module
from guardian.conversations import conversations as conversations_module
#from guardian.mcp import mcp as mcp_module
from guardian.projects import projects as projects_module
try:
    from guardian.web import crawl as crawl_module
except ImportError:
    crawl_module = None

# guardian-main.py
# =================
# Main CLI entrypoint for Guardian backend.
# - Project table logic is delegated to guardian.projects.projects.
# - This file handles CLI commands only for project management (create/list/init).
# - All DB schema and management logic for projects is in guardian/projects/projects.py.


app = typer.Typer()
DB_PATH = Path("guardian.db")

# ---- Imprint Zero CLI commands ----

@app.command("dump-imprint-zero-prompt-text")
def dump_imprint_zero_prompt_text():
    """
    Print the raw text prompt used for Imprint Zero onboarding.
    """
    prompt = load_prompt()
    typer.echo(prompt)

@app.command("dump-imprint-zero-prompt-json")
def dump_imprint_zero_prompt_json():
    """
    Print the Imprint Zero prompt structure as formatted JSON.
    """
    data = load_prompt_json()
    typer.echo(json.dumps(data, indent=2))

@app.command("dump")
def dump_end_to_end():
    """
    Execute the full Imprint Zero routine and output the resulting persona JSON.
    """
    result = load_prompt_json()
    typer.echo(json.dumps(result, indent=2))

@app.command("dump-graceful-failure")
def dump_graceful_failure():
    """
    Simulate a broken Imprint Zero config to validate failure handling.
    """
    # This should raise ImprintZeroConfigError
    _ = load_prompt(config_path="does_not_exist.yml")


# ---- Project Management CLI Commands ----


@app.command()
def create_project(
    name: str = typer.Argument(..., help="Project name."),
    description: Optional[str] = typer.Option(None, help="Project description."),
):
    """Create a new project folder."""
    try:
        projects_module.create_project(name, description)
        print(f"[green]Project '{name}' created successfully.[/green]")
    except Exception as e:
        print(f"[red]Failed to create project: {e}[/red]")


@app.command()
def list_projects():
    """List all existing projects."""
    try:
        projects = projects_module.list_projects()
        if not projects:
            print("[yellow]No projects found.[/yellow]")
        else:
            for proj in projects:
                id, name, desc, created = proj
                print(
                    f"[cyan]{id}[/cyan]: {name} - {desc or '[no description]'} [dim]({created})[/dim]"
                )
    except Exception as e:
        print(f"[red]Failed to list projects: {e}[/red]")


@app.command()
def init_db():
    """
    Initialize all Guardian DB tables: memory, chat, agent_profiles, projects, etc.
    """
    import sqlite3

    from guardian.guardian_main import (
        GuardianDB,
    )  # Import here to avoid circular import
    from guardian.projects import projects as projects_module

    # Initialize memory, agent_profiles, etc.
    db = GuardianDB(DB_PATH)
    db.init_db()
    db.migrate_agent_profiles()
    # Initialize chat tables
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                project TEXT,
                title TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                parent_id INTEGER,
                FOREIGN KEY (thread_id) REFERENCES chat_threads(id),
                FOREIGN KEY (parent_id) REFERENCES chat_messages(id)
            )
            """
        )
        conn.commit()
    # Initialize projects table
    try:
        projects_module.init_projects_table()
        print("[green]All Guardian DB tables initialized.[/green]")
    except Exception as e:
        print(f"[red]Failed to initialize projects table: {e}[/red]")


# ---- THREADS MANAGEMENT CLI COMMANDS ----

from guardian.threads_structure import threads as threads_module


@app.command()
def init_threads_table_cmd():
    """Initialize the threads table in the database."""
    try:
        threads_module.init_threads_table()
        print("[green]Threads table initialized successfully.[/green]")
    except Exception as e:
        print(f"[red]Failed to initialize threads table: {e}[/red]")


@app.command()
def create_thread_cmd(
    project: str = typer.Argument(..., help="Project name."),
    title: str = typer.Argument(..., help="Thread title."),
    user_id: Optional[str] = typer.Option(None, help="User ID creating the thread."),
):
    """Create a new thread in a project."""
    try:
        thread_id = threads_module.create_thread(project, title, user_id)
        print(
            f"[green]Thread '{title}' created successfully with ID {thread_id}.[/green]"
        )
    except Exception as e:
        print(f"[red]Failed to create thread: {e}[/red]")


@app.command()
def list_threads_by_project(
    project: str = typer.Argument(..., help="Project name."),
):
    """List all threads for a given project."""
    try:
        threads = threads_module.list_threads_by_project(project)
        if not threads:
            print("[yellow]No threads found for this project.[/yellow]")
        else:
            for thread in threads:
                id, title, user_id, created_at = thread
                print(
                    f"[cyan]{id}[/cyan]: {title} by {user_id or 'unknown'} [dim]({created_at})[/dim]"
                )
    except Exception as e:
        print(f"[red]Failed to list threads: {e}[/red]")


@app.command()
def list_child_threads(
    parent_thread_id: int = typer.Argument(..., help="Parent thread ID."),
):
    """List child threads of a given parent thread."""
    try:
        child_threads = threads_module.list_child_threads(parent_thread_id)
        if not child_threads:
            print("[yellow]No child threads found for this parent thread.[/yellow]")
        else:
            for thread in child_threads:
                id, title, user_id, created_at = thread
                print(
                    f"[cyan]{id}[/cyan]: {title} by {user_id or 'unknown'} [dim]({created_at})[/dim]"
                )
    except Exception as e:
        print(f"[red]Failed to list child threads: {e}[/red]")


@app.command()
def show_thread_lineage(
    thread_id: int = typer.Argument(..., help="Thread ID."),
):
    """Show the lineage (parent chain) of a given thread."""
    try:
        lineage = threads_module.show_thread_lineage(thread_id)
        if not lineage:
            print("[yellow]No lineage found for this thread.[/yellow]")
        else:
            print("[green]Thread lineage:[/green]")
            for thread in lineage:
                id, title, user_id, created_at = thread
                print(
                    f"[cyan]{id}[/cyan]: {title} by {user_id or 'unknown'} [dim]({created_at})[/dim]"
                )
    except Exception as e:
        print(f"[red]Failed to show thread lineage: {e}[/red]")


@app.command()
def show_mcp_map(base_path: str = "guardian"):
    """MCP integration not available."""
    print("[yellow]MCP module not found. Install or configure guardian.mcp to enable this command.[/yellow]")


# ---- CODEMAP GENERATION CLI COMMAND ----


@app.command()
def generate_codemap():
    """Generate a codemap.json file of the project structure."""
    try:
        codemap_module.generate_codemap()
        print("[green]Codemap generated successfully.[/green]")
    except Exception as e:
        print(f"[red]Failed to generate codemap: {e}[/red]")


@app.command("codemap:summary")
def codemap_summary():
    pass


@app.command("codemap:query")
def codemap_query(
    query: str = typer.Argument(
        ..., help="Natural language query against the codemap."
    ),
    provider: str = typer.Option(
        "openai", "--provider", "-p", help="LLM provider: openai, groq, local, etc."
    ),
    user_id: str = typer.Option(
        "default_user", "--user-id", "-u", help="User ID for the MemoryOS session."
    ),
    api_key: str = typer.Option(
        "your-api-key", "--api-key", "-k", help="API key for the chosen provider."
    ),
    data_storage_path: str = typer.Option(
        "data", "--data-path", "-d", help="Path to MemoryOS data directory."
    ),
):
    memos = Memoryos(
        user_id=user_id,
        data_storage_path=data_storage_path,
    )
    print(memos.query_codemap(query))


# ---- CONVERSATIONS MANAGEMENT CLI COMMANDS ----


@app.command()
def create_conversation(
    thread_id: int = typer.Argument(..., help="Thread ID the conversation belongs to."),
    user_id: str = typer.Argument(..., help="User ID initiating the conversation."),
    title: str = typer.Option(None, help="Optional title for the conversation."),
    parent_id: int = typer.Option(
        None, help="Optional parent conversation ID (for threaded lineage)."
    ),
):
    """Create a new conversation entry under a thread."""
    try:
        convo_id = conversations_module.create_conversation(
            thread_id, user_id, title, parent_id
        )
        print(f"[green]Conversation created successfully with ID {convo_id}.[/green]")
    except Exception as e:
        print(f"[red]Failed to create conversation: {e}[/red]")


@app.command()
def list_conversations_by_thread(
    thread_id: int = typer.Argument(..., help="Thread ID."),
):
    """List all conversations within a given thread."""
    try:
        conversations = conversations_module.list_conversations_by_thread(thread_id)
        if not conversations:
            print("[yellow]No conversations found in this thread.[/yellow]")
        else:
            for convo in conversations:
                id, user_id, title, parent_id, created_at = convo
                lineage = f" <- parent {parent_id}" if parent_id else ""
                print(
                    f"[cyan]{id}[/cyan]: {title or '[untitled]'} by {user_id}{lineage} [dim]({created_at})[/dim]"
                )
    except Exception as e:
        print(f"[red]Failed to list conversations: {e}[/red]")


@app.command()
def show_conversation_lineage(
    conversation_id: int = typer.Argument(..., help="Conversation ID."),
):
    """Show the parent lineage of a given conversation."""
    try:
        lineage = conversations_module.show_conversation_lineage(conversation_id)
        if not lineage:
            print("[yellow]No lineage found for this conversation.[/yellow]")
        else:
            print("[green]Conversation lineage:[/green]")
            for convo in lineage:
                id, user_id, title, parent_id, created_at = convo
                print(
                    f"[cyan]{id}[/cyan]: {title or '[untitled]'} by {user_id} [dim]({created_at})[/dim]"
                )
    except Exception as e:
        print(f"[red]Failed to retrieve lineage: {e}[/red]")


@app.command()
def crawl_url(
    base_url: str = typer.Argument(..., help="Starting URL to crawl."),
    query: str = typer.Argument(..., help="Semantic query to guide crawl."),
    max_pages: int = typer.Option(5, help="Maximum pages to crawl."),
):
    """Crawl the web starting from a URL using a semantic query."""
    if crawl_module is None:
        print("[yellow]Web crawl module not available. Install or configure guardian.web to enable this command.[/yellow]")
        return
    try:
        result = crawl_module.crawl_url(base_url, query, max_pages)
        print(result)
    except Exception as e:
        print(f"[red]Failed to crawl URL: {e}[/red]")


@app.command()
def crawl_summary(
    urls: str = typer.Argument(..., help="Comma-separated list of URLs."),
    query: str = typer.Argument(..., help="Semantic summary query."),
):
    """Summarize multiple pages from URLs using a focused query."""
    if crawl_module is None:
        print("[yellow]Web crawl module not available. Install or configure guardian.web to enable this command.[/yellow]")
        return
    try:
        url_list = [url.strip() for url in urls.split(",")]
        result = crawl_module.crawl_summary(url_list, query)
        print(result)
    except Exception as e:
        print(f"[red]Failed to summarize URLs: {e}[/red]")


@app.command()
def crawl_table(
    url: str = typer.Argument(..., help="Page URL to extract a table from."),
    query: str = typer.Argument(..., help="Semantic table extraction query."),
):
    """Extract tabular data from a page matching a query."""
    if crawl_module is None:
        print("[yellow]Web crawl module not available. Install or configure guardian.web to enable this command.[/yellow]")
        return
    try:
        result = crawl_module.crawl_table(url, query)
        print(result)
    except Exception as e:
        print(f"[red]Failed to extract table: {e}[/red]")


# ---- Modular CLI Integration ----
try:
    from guardian.cli.guardian_cli import register_cli_commands
except Exception:
    register_cli_commands = lambda app: None  # no-op if plugin missing
register_cli_commands(app)