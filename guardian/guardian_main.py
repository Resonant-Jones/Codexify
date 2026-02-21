"""guardian_main

Entry point for the Guardian backend CLI.

This module provides a Typer‑based command‑line interface that aggregates
various sub‑commands for project management, thread handling, codemap
generation, and Imprint Zero onboarding. It imports helper functions from
the `guardian` package and defines commands such as:

- `create-project` / `list-projects` – manage project records.
- `init-db` – initialise the SQLite database schema.
- `init-threads-table-cmd` – create the legacy `threads` table.
- `generate-codemap` – produce a `codemap.json` describing the repository.
- `dump-imprint-zero-prompt-*` – expose the onboarding prompt.

The file also contains utility functions for normalising codemap data
and for interfacing with the optional web‑crawling module. The CLI is
registered via `typer.Typer()` and can be invoked with `python -m
guardian.guardian_main` or via the console script defined in
`pyproject.toml`.
"""

# Import Imprint Zero helpers; provide a compatibility shim if missing
import json
import json as _json
import logging as _logging
import os
from pathlib import Path
from pathlib import Path as _Path
from typing import Any, Dict, List, Optional, Tuple  # added for type hints

import typer
from rich import print

logger = _logging.getLogger(__name__)
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
            lines = [
                line.strip()
                for line in value.strip().splitlines()
                if line.strip()
            ]
            if len(lines) <= 1:
                return f"{indent}{value.strip()}\n" if value.strip() else ""
            return "".join(f"{indent}{ln}\n" for ln in lines)
        if isinstance(value, list):
            return "".join(
                f"{indent}{str(item).strip()}\n"
                for item in value
                if str(item).strip()
            )
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
                    _logger.warning(
                        "Failed to compose structured prompt: %s", e
                    )

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


from guardian.codemap import generate_codemap as codemap_module
from guardian.conversations import conversations as conversations_module

# from guardian.mcp import mcp as mcp_module
from guardian.projects import projects as projects_module

try:
    from guardian.web import crawl as crawl_module
except ImportError:
    crawl_module = None

#
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
    description: Optional[str] = typer.Option(
        None, help="Project description."
    ),
):
    """Create a new project folder."""
    try:
        projects_module.create_project(name, description)
        logger.info(f"Project '%s' created successfully.", name)
    except Exception as e:
        logger.error(f"Failed to create project: %s", e)


@app.command()
def list_projects():
    """List all existing projects."""
    try:
        projects = projects_module.list_projects()
        if not projects:
            logger.warning("No projects found.")
        else:
            for proj in projects:
                id, name, desc, created = proj
                logger.info(
                    f"%s: %s - %s (%s)",
                    id,
                    name,
                    desc or "[no description]",
                    created,
                )
    except Exception as e:
        logger.error(f"Failed to list projects: %s", e)


@app.command()
def init_db():
    """
    Initialize all Guardian DB tables: memory, chat, agent_profiles, projects, etc.
    """
    import sqlite3

    from guardian.core.db import GuardianDB
    from guardian.projects import projects as projects_module

    # Initialize memory, agent_profiles, etc.
    db = GuardianDB(DB_PATH)
    db.init_db()
    # Older GuardianDB may not have migrate_agent_profiles; skip gracefully
    if hasattr(db, "migrate_agent_profiles"):
        db.migrate_agent_profiles()
    else:
        logger.warning(
            "GuardianDB.migrate_agent_profiles() not available; skipping."
        )
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
        logger.info("All Guardian DB tables initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize projects table: %s", e)


# ---- THREADS MANAGEMENT CLI COMMANDS ----

from guardian.threads_structure import threads as threads_module


@app.command()
def init_threads_table_cmd():
    """Initialize the threads table in the database."""
    try:
        threads_module.init_threads_table()
        logger.info("Threads table initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize threads table: %s", e)


@app.command()
def create_thread_cmd(
    project: str = typer.Argument(..., help="Project name."),
    title: str = typer.Argument(..., help="Thread title."),
    user_id: Optional[str] = typer.Option(
        None, help="User ID creating the thread."
    ),
):
    """Create a new thread in a project."""
    try:
        thread_id = threads_module.create_thread(project, title, user_id)
        logger.info(
            f"Thread '%s' created successfully with ID %s.", title, thread_id
        )
    except Exception as e:
        logger.error(f"Failed to create thread: %s", e)


@app.command()
def list_threads_by_project(
    project: str = typer.Argument(..., help="Project name."),
):
    """List all threads for a given project."""
    try:
        threads = threads_module.list_threads_by_project(project)
        if not threads:
            logger.warning("No threads found for this project.")
        else:
            for thread in threads:
                id, title, user_id, created_at = thread
                logger.info(
                    f"%s: %s by %s (%s)",
                    id,
                    title,
                    user_id or "unknown",
                    created_at,
                )
    except Exception as e:
        logger.error(f"Failed to list threads: %s", e)


@app.command()
def list_child_threads(
    parent_thread_id: int = typer.Argument(..., help="Parent thread ID."),
):
    """List child threads of a given parent thread."""
    try:
        child_threads = threads_module.list_child_threads(parent_thread_id)
        if not child_threads:
            logger.warning("No child threads found for this parent thread.")
        else:
            for thread in child_threads:
                id, title, user_id, created_at = thread
                logger.info(
                    f"%s: %s by %s (%s)",
                    id,
                    title,
                    user_id or "unknown",
                    created_at,
                )
    except Exception as e:
        logger.error(f"Failed to list child threads: %s", e)


@app.command()
def show_thread_lineage(
    thread_id: int = typer.Argument(..., help="Thread ID."),
):
    """Show the lineage (parent chain) of a given thread."""
    try:
        lineage = threads_module.show_thread_lineage(thread_id)
        if not lineage:
            logger.warning("No lineage found for this thread.")
        else:
            logger.info("Thread lineage:")
            for thread in lineage:
                id, title, user_id, created_at = thread
                logger.info(
                    f"%s: %s by %s (%s)",
                    id,
                    title,
                    user_id or "unknown",
                    created_at,
                )
    except Exception as e:
        logger.error(f"Failed to show thread lineage: %s", e)


@app.command()
def show_mcp_map(base_path: str = "guardian"):
    """MCP integration not available."""
    logger.warning(
        "MCP module not found. Install or configure guardian.mcp to enable this command."
    )


# ---- Providers diagnostics ----
try:
    from guardian.providers.registry import ProviderRegistry  # type: ignore
except Exception:
    ProviderRegistry = None  # type: ignore


@app.command("providers:capabilities")
def providers_capabilities():
    """Print available chat and embeddings providers based on current env + installs."""
    if ProviderRegistry is None:
        logger.info('{"chat": [], "embeddings": []}')
        return
    reg = ProviderRegistry()
    logger.info(reg.capabilities())


# ---- CODEMAP GENERATION CLI COMMAND ----


# --- Codemap normalization helpers (ensure dict shape expected by MemoryOS) ---
def _normalize_codemap_mapping(obj):
    """
    MemoryOS expects a mapping for the codemap (path -> metadata).
    Some generators produce a list. Convert list -> dict keyed by path/file.
    """
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, list):
        fixed = {}
        for i, entry in enumerate(obj):
            if isinstance(entry, dict):
                key = entry.get("path") or entry.get("file") or f"__entry_{i}"
                fixed[key] = entry
        return fixed
    return obj


def _normalize_codemap(obj):
    # simple alias so other code can call a stable name
    return _normalize_codemap_mapping(obj)


def _normalize_codemap_file(path: Path) -> dict | None:
    try:
        if path.exists():
            raw = path.read_text(encoding="utf-8")
            import json as _json

            data = _json.loads(raw)
            fixed = _normalize_codemap_mapping(data)
            if fixed is not data:
                path.write_text(_json.dumps(fixed, indent=2), encoding="utf-8")
                logger.warning(f"Normalized codemap at %s", path)
            return fixed
    except Exception as e:
        logger.warning(f"Codemap normalization skipped: %s", e)
    return None


@app.command()
def generate_codemap():
    """Generate a codemap.json file of the project structure."""
    try:
        codemap_module.generate_codemap()
        # Normalize codemap on disk to dict shape
        codemap_path = Path(__file__).parent / "codemap" / "codemap.json"
        _normalize_codemap_file(codemap_path)
        logger.info("Codemap generated successfully.")
    except Exception as e:
        logger.error(f"Failed to generate codemap: %s", e)


@app.command("codemap:summary")
def codemap_summary():
    """Print a quick summary of the current codemap.json (after normalizing)."""
    codemap_path = Path(__file__).parent / "codemap" / "codemap.json"

    # Normalize on-disk file first (if present)
    fixed = _normalize_codemap_file(codemap_path)

    # If normalization didn't load content, read it raw (best-effort)
    import json as _json

    if fixed is None and codemap_path.exists():
        try:
            fixed = _json.loads(codemap_path.read_text(encoding="utf-8"))
            fixed = _normalize_codemap(fixed)
        except Exception:
            fixed = {}

    # Print a compact summary
    if isinstance(fixed, dict) and fixed:
        keys = list(fixed.keys())
        logger.info(f"Codemap entries: %s", len(keys))
        for k in keys[:10]:
            logger.debug(f" - %s", k)
        if len(keys) > 10:
            logger.info(f"... (+%s more)", len(keys) - 10)
    elif isinstance(fixed, dict) and not fixed:
        logger.warning("Codemap is present but empty after normalization.")
    else:
        logger.warning(
            "Codemap not found or unreadable. Run `generate-codemap` first."
        )


@app.command("codemap:query")
def codemap_query(
    query: str = typer.Argument(
        ..., help="Natural language query against the codemap."
    ),
    provider: str = typer.Option(
        "openai",
        "--provider",
        "-p",
        help="LLM provider for answering the query (e.g., openai, groq, local).",
    ),
    embedder: str = typer.Option(
        "openai",
        "--embedder",
        "-e",
        help="Embedding backend required by MemoryOS (e.g., openai, local).",
    ),
    user_id: str = typer.Option(
        "default_user",
        "--user-id",
        "-u",
        help="User ID for the MemoryOS session.",
    ),
    api_key: str = typer.Option(
        "your-api-key",
        "--api-key",
        "-k",
        help="API key for the chosen provider/embedder.",
    ),
    data_storage_path: str = typer.Option(
        "data", "--data-path", "-d", help="Path to MemoryOS data directory."
    ),
):
    # Ensure MemoryOS will always see a dict-shaped codemap
    # 1) Normalize on-disk JSON (helps any consumer that reads the file)
    CODEMAP_PATH = Path(__file__).parent / "codemap" / "codemap.json"
    _normalize_codemap_file(CODEMAP_PATH)

    # 2) Monkey-patch the provider module that MemoryOS imports so its
    #    generate_codemap() returns a dict (list -> dict)
    try:
        import importlib

        gen = importlib.import_module("guardian.codemap.generate_codemap")
        _orig_generate = getattr(gen, "generate_codemap", None)
        if callable(_orig_generate):

            def _wrapped_generate(*args, **kwargs):
                result = _orig_generate(*args, **kwargs)
                try:
                    return _normalize_codemap(result)
                except Exception:
                    return result

            setattr(gen, "generate_codemap", _wrapped_generate)
    except Exception:
        # Non-fatal; downstream guards handle list->dict too
        pass

    # 3) Now import MemoryOS (after patching)
    try:
        from memoryos.memoryos import Memoryos
    except Exception as e:
        logger.error(f"MemoryOS import failed: %s", e)
        logger.warning(
            "Tip: install it with `pip install memoryos` or disable this command."
        )
        raise typer.Exit(code=1)

    # Wire API keys into env for backends that expect them
    try:
        if api_key:
            # Embedding backend expects its own key (e.g., OpenAI embeddings)
            if isinstance(embedder, str) and embedder.lower() == "openai":
                os.environ.setdefault("OPENAI_API_KEY", api_key)
            # LLM provider (e.g., Groq) may expect its own key
            if isinstance(provider, str) and provider.lower() == "groq":
                os.environ.setdefault("GROQ_API_KEY", api_key)
    except Exception:
        # Non-fatal: continue; MemoryOS may also read keys from its own config
        pass

    try:
        # Prefer newer signature including provider
        try:
            memos = Memoryos(
                user_id=user_id,
                data_storage_path=data_storage_path,
                embedder=embedder,
                provider=provider,
            )
        except TypeError:
            # Fallback for older MemoryOS without `provider` arg
            memos = Memoryos(
                user_id=user_id,
                data_storage_path=data_storage_path,
                embedder=embedder,
            )
    except TypeError as e:
        logger.error(f"MemoryOS init error: %s", e)
        logger.warning(
            "Tip: pass a supported --embedder (e.g., openai or local). "
            "If using OpenAI embeddings, provide an API key via --api-key or OPENAI_API_KEY. "
            "If using Groq for the LLM, set GROQ_API_KEY or pass --api-key with --provider groq."
        )
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"MemoryOS initialization failed: %s", e)
        raise typer.Exit(code=1)

    # Normalize in-memory codemap if MemoryOS exposed a list
    try:
        cm = getattr(memos, "codemap", None)
        if isinstance(cm, list):
            memos.codemap = _normalize_codemap(cm)
    except Exception:
        # Non-fatal; continue to query
        pass

    try:
        result = memos.query_codemap(query)
        logger.info(result)
    except Exception as e:
        logger.error(f"Codemap query failed: {e}")
        raise typer.Exit(code=1)


# ---- CONVERSATIONS MANAGEMENT CLI COMMANDS ----


@app.command()
def create_conversation(
    thread_id: int = typer.Argument(
        ..., help="Thread ID the conversation belongs to."
    ),
    user_id: str = typer.Argument(
        ..., help="User ID initiating the conversation."
    ),
    title: str = typer.Option(
        None, help="Optional title for the conversation."
    ),
    parent_id: int = typer.Option(
        None, help="Optional parent conversation ID (for threaded lineage)."
    ),
):
    """Create a new conversation entry under a thread."""
    try:
        convo_id = conversations_module.create_conversation(
            thread_id, user_id, title, parent_id
        )
        logger.info(f"Conversation created successfully with ID {convo_id}.")
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}")


@app.command()
def list_conversations_by_thread(
    thread_id: int = typer.Argument(..., help="Thread ID."),
):
    """List all conversations within a given thread."""
    try:
        conversations = conversations_module.list_conversations_by_thread(
            thread_id
        )
        if not conversations:
            logger.info("No conversations found in this thread.")
        else:
            for convo in conversations:
                id, user_id, title, parent_id, created_at = convo
                lineage = f" <- parent {parent_id}" if parent_id else ""
                logger.info(
                    f"{id}: {title or '[untitled]'} by {user_id}{lineage} ({created_at})"
                )
    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")


@app.command()
def show_conversation_lineage(
    conversation_id: int = typer.Argument(..., help="Conversation ID."),
):
    """Show the parent lineage of a given conversation."""
    try:
        lineage = conversations_module.show_conversation_lineage(
            conversation_id
        )
        if not lineage:
            logger.info("No lineage found for this conversation.")
        else:
            logger.info("Conversation lineage:")
            for convo in lineage:
                id, user_id, title, parent_id, created_at = convo
                logger.info(
                    f"{id}: {title or '[untitled]'} by {user_id} ({created_at})"
                )
    except Exception as e:
        logger.error(f"Failed to retrieve lineage: {e}")


@app.command()
def crawl_url(
    base_url: str = typer.Argument(..., help="Starting URL to crawl."),
    query: str = typer.Argument(..., help="Semantic query to guide crawl."),
    max_pages: int = typer.Option(5, help="Maximum pages to crawl."),
):
    """Crawl the web starting from a URL using a semantic query."""
    if crawl_module is None:
        logger.warning(
            "Web crawl module not available. Install or configure guardian.web to enable this command."
        )
        return
    try:
        result = crawl_module.crawl_url(base_url, query, max_pages)
        logger.info(result)
    except Exception as e:
        logger.error(f"Failed to crawl URL: {e}")


@app.command()
def crawl_summary(
    urls: str = typer.Argument(..., help="Comma-separated list of URLs."),
    query: str = typer.Argument(..., help="Semantic summary query."),
):
    """Summarize multiple pages from URLs using a focused query."""
    if crawl_module is None:
        logger.warning(
            "Web crawl module not available. Install or configure guardian.web to enable this command."
        )
        return
    try:
        url_list = [url.strip() for url in urls.split(",")]
        result = crawl_module.crawl_summary(url_list, query)
        logger.info(result)
    except Exception as e:
        logger.error(f"Failed to summarize URLs: {e}")


@app.command()
def crawl_table(
    url: str = typer.Argument(..., help="Page URL to extract a table from."),
    query: str = typer.Argument(..., help="Semantic table extraction query."),
):
    """Extract tabular data from a page matching a query."""
    if crawl_module is None:
        logger.warning(
            "Web crawl module not available. Install or configure guardian.web to enable this command."
        )
        return
    try:
        result = crawl_module.crawl_table(url, query)
        logger.info(result)
    except Exception as e:
        logger.error(f"Failed to extract table: {e}")


# ---- Modular CLI Integration ----
try:
    from guardian.cli.guardian_cli import register_cli_commands
except Exception:
    register_cli_commands = lambda app: None  # no-op if plugin missing
register_cli_commands(app)
