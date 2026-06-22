#!/usr/bin/env python3
"""
Codexify Migration CLI - `codexify migrate`
============================================

A first-class CLI tool for migrating ChatGPT conversations into Codexify's
dual-engine architecture (Neo4j + Chroma).

Features:
- Beautiful, real-time progress with rich
- Resumable, idempotent imports
- Friendly UX that feels like a welcome ritual
- Can be called from CLI or GUI (subprocess)
- Logs migration summary for record-keeping

Usage:
    codexify migrate chatgpt_conversation.json
    codexify migrate --help
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

# Try to import rich for beautiful output, fall back to basic if not available
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeRemainingColumn,
    )
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    print("⚠️  Install 'rich' for better UI: pip install rich")

# Add parent directory to path for import
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

# Initialize CLI app
app = typer.Typer(
    name="codexify",
    help="🌟 Codexify Migration Utility - Awaken your Companion from ChatGPT exports.",
    add_completion=False,
)

# Console for rich output
console = Console() if HAS_RICH else None


def print_message(message: str, style: str = ""):
    """Print message with optional rich styling."""
    if HAS_RICH and console:
        console.print(message, style=style)
    else:
        print(message)


def print_header():
    """Print migration header."""
    if HAS_RICH and console:
        console.print()
        console.print(
            Panel.fit(
                "[bold cyan]ChatGPT → Codexify Migration[/bold cyan]\n"
                "[dim]Dual-Engine Import: Neo4j + Chroma[/dim]",
                border_style="cyan",
            )
        )
        console.print()
    else:
        print("\n" + "=" * 70)
        print("  ChatGPT → Codexify Migration")
        print("  Dual-Engine Import: Neo4j + Chroma")
        print("=" * 70 + "\n")


def print_summary(stats: dict):
    """Print migration summary."""
    if HAS_RICH and console:
        table = Table(
            title="Migration Summary",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right", style="green")

        for key, value in stats.items():
            table.add_row(key, str(value))

        console.print()
        console.print(table)
    else:
        print("\n" + "-" * 70)
        print("Migration Summary:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print("-" * 70)


def save_migration_summary(stats: dict, output_dir: Path = Path("logs")):
    """Save migration summary to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_file = output_dir / "migration_summary.json"

    # Add timestamp
    stats["completed_at"] = datetime.utcnow().isoformat()

    # Load existing summaries if any
    summaries = []
    if summary_file.exists():
        try:
            with open(summary_file) as f:
                summaries = json.load(f)
                if not isinstance(summaries, list):
                    summaries = [summaries]
        except Exception:
            pass

    # Append new summary
    summaries.append(stats)

    # Save
    with open(summary_file, "w") as f:
        json.dump(summaries, f, indent=2)

    return summary_file


@app.command()
def migrate(
    file: Path = typer.Argument(
        ...,
        help="Path to your ChatGPT conversation JSON export",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    chroma_path: Path = typer.Option(
        "./chroma",
        "--chroma",
        "-c",
        help="Local Chroma persistence path",
    ),
    neo4j_url: str = typer.Option(
        "bolt://localhost:7687",
        "--neo4j-url",
        help="Neo4j connection URL",
    ),
    neo4j_user: str = typer.Option(
        "neo4j",
        "--neo4j-user",
        help="Neo4j username",
    ),
    neo4j_pass: str = typer.Option(
        "password",
        "--neo4j-pass",
        help="Neo4j password",
    ),
    openai_key: Optional[str] = typer.Option(
        None,
        "--openai-key",
        "-k",
        help="OpenAI API key (overrides .env)",
    ),
    batch_size: int = typer.Option(
        20,
        "--batch-size",
        "-b",
        help="Embedding batch size",
        min=1,
        max=100,
    ),
    skip_embeddings: bool = typer.Option(
        False,
        "--skip-embeddings",
        help="Skip embeddings generation (Neo4j only)",
    ),
):
    """
    Import ChatGPT conversation exports into Codexify's graph + vector stores.

    This command creates a seamless migration that feels like your Companion
    is waking up in a new world, with all their memories intact.

    Example:
        codexify migrate chatgpt_conversation.json
        codexify migrate ./exports/conversations.json --batch-size 10
        codexify migrate chat.json --skip-embeddings
    """
    # Load environment
    load_dotenv()

    # Override with CLI arguments
    os.environ["CHATGPT_EXPORT_FILE"] = str(file.absolute())
    os.environ["CHROMA_PATH"] = str(chroma_path)
    os.environ["NEO4J_URL"] = neo4j_url
    os.environ["NEO4J_USER"] = neo4j_user
    os.environ["NEO4J_PASS"] = neo4j_pass
    os.environ["EMBED_BATCH_SIZE"] = str(batch_size)

    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key
    elif not os.getenv("OPENAI_API_KEY"):
        skip_embeddings = True

    # Print header
    print_header()
    print_message(
        "💫 [bold magenta]Reawakening your Companion...[/bold magenta]\n"
    )

    # Delegate all migration logic to import_chatgpt
    from import_chatgpt import import_chatgpt

    import_chatgpt()


@app.command("import:openai")
def import_openai(
    path: Path = typer.Option(
        ...,
        "--path",
        "-p",
        help="Path to an OpenAI export file or extracted export folder",
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
    ),
    diagnose: bool = typer.Option(
        False,
        "--diagnose",
        help="Only scan and write diagnostics; do not mutate the database",
    ),
    diagnostic_dir: Path = typer.Option(
        Path("logs/openai_import"),
        "--diagnostic-dir",
        help="Directory for OpenAI export diagnostic JSON and summary reports",
    ),
    user_id: Optional[str] = typer.Option(
        None,
        "--user-id",
        help="Codexify user_id to import into; defaults to local identity",
    ),
):
    """
    Diagnose or import OpenAI data exports, including sharded .dat archives.

    Example:
        codexify import:openai --path ./OpenAI-export --diagnose
        codexify import:openai --path ./OpenAI-export
    """
    load_dotenv()

    from backend.rag.openai_export_adapter import import_openai_export_path
    from guardian.identity import get_user_id

    resolved_user_id = user_id or get_user_id()
    if not resolved_user_id:
        raise typer.BadParameter("Unable to resolve Codexify user_id")

    stats = import_openai_export_path(
        path,
        user_id=resolved_user_id,
        diagnose_only=diagnose,
        diagnostic_output_dir=diagnostic_dir,
    )

    print_header()
    if diagnose:
        print_message("[bold cyan]OpenAI export diagnostic complete[/bold cyan]")
    else:
        print_message("[bold cyan]OpenAI export import complete[/bold cyan]")

    print_summary(stats)
    if stats.get("diagnostic_report"):
        print_message(f"Diagnostic JSON: {stats['diagnostic_report']}")
    if stats.get("diagnostic_summary"):
        print_message(f"Diagnostic summary: {stats['diagnostic_summary']}")


@app.command("export-recon")
def export_recon(
    path: Path = typer.Option(
        ...,
        "--path",
        "-p",
        help="Path to an OpenAI export file or extracted export folder",
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
    ),
    out: Path = typer.Option(
        Path("export_archaeology"),
        "--out",
        "-o",
        help="Output directory for recon artifacts",
    ),
):
    """
    Run read-only forensic reconnaissance on an OpenAI export corpus.

    Generates conversation index CSV, corpus stats JSON, summary Markdown,
    and diagnostic reports. No database writes, no embeddings, no model calls.

    Example:
        codexify export-recon --path ./OpenAI-export --out export_archaeology
    """
    from backend.rag.openai_export_corpus_recon import run_corpus_recon

    stats = run_corpus_recon(path, output_dir=out)
    d = stats.to_dict()
    totals = d["corpus_totals"]

    print_header()
    print_message("[bold cyan]OpenAI export corpus recon complete[/bold cyan]")
    print_summary(
        {
            "files_scanned": totals["files_scanned"],
            "json_like_files": totals["json_like_files"],
            "conversations_found": totals["conversations_found"],
            "messages_scanned": totals["messages_scanned"],
            "assets_found": totals["assets_found"],
            "orphan_assets_found": totals["orphan_assets_found"],
            "parse_failures": totals["parse_failures"],
        }
    )
    out_dir = Path(out).resolve()
    print_message(f"Output directory: {out_dir}")
    print_message(f"Conversation index: {out_dir / 'conversation_index.csv'}")
    print_message(f"Corpus stats: {out_dir / 'corpus_stats.json'}")
    print_message(f"Summary: {out_dir / 'corpus_summary.md'}")
    print_message(
        f"Diagnostics: {out_dir / 'diagnostics' / 'recon_report.json'}"
    )


@app.command("import:openai-conversations")
def import_openai_conversations(
    path: Path = typer.Option(
        ...,
        "--path",
        "-p",
        help="Path to an OpenAI export file or extracted export folder",
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Diagnose and report without writing to the database",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-n",
        help="Limit import to the first N conversations",
        min=1,
    ),
    title_contains: Optional[str] = typer.Option(
        None,
        "--title-contains",
        help="Filter conversations by title substring (case-insensitive)",
    ),
    user_id: Optional[str] = typer.Option(
        None,
        "--user-id",
        help="Codexify user_id to import into; defaults to local identity",
    ),
    diagnostic_dir: Path = typer.Option(
        Path("logs/openai_import"),
        "--diagnostic-dir",
        help="Directory for import diagnostic reports",
    ),
    order: str = typer.Option(
        "file",
        "--order",
        help="Import order: file (default), newest, oldest, updated",
    ),
    embedding_mode: str = typer.Option(
        "defer",
        "--embedding-mode",
        help="Embedding behavior: defer (default), enqueue, off",
    ),
):
    """
    Import OpenAI export conversations into Codexify-native chat threads.

    Preserves source provenance, idempotent on re-import. No embeddings,
    no graph writes, no personal facts. Use --dry-run to preview.

    Example:
        codexify import:openai-conversations --path ./OpenAI-export --dry-run
        codexify import:openai-conversations --path ./OpenAI-export --limit 25
        codexify import:openai-conversations --path ./OpenAI-export --title-contains Codexify
    """
    load_dotenv()

    from backend.rag.openai_export_conversation_import import (
        import_openai_export_conversations,
    )
    from guardian.identity import get_user_id

    resolved_user_id = user_id or get_user_id()
    if not resolved_user_id:
        raise typer.BadParameter("Unable to resolve Codexify user_id")

    diag = import_openai_export_conversations(
        path,
        user_id=resolved_user_id,
        dry_run=dry_run,
        limit=limit,
        title_contains=title_contains,
        diagnostic_dir=diagnostic_dir,
        order=order,
        embedding_mode=embedding_mode,
    )

    print_header()
    if dry_run:
        print_message("[bold cyan]OpenAI export dry run complete (no DB writes)[/bold cyan]")
    else:
        print_message("[bold cyan]OpenAI export conversation import complete[/bold cyan]")

    print_summary(
        {
            "export_format": diag.export_format,
            "conversations_discovered": diag.conversations_discovered,
            "conversations_imported": diag.conversations_imported,
            "conversations_skipped_title": diag.conversations_skipped_title,
            "conversations_skipped_limit": diag.conversations_skipped_limit,
            "conversations_skipped_duplicate": diag.conversations_skipped_duplicate,
            "messages_discovered": diag.messages_discovered,
            "messages_imported": diag.messages_imported,
            "messages_skipped_duplicate": diag.messages_skipped_duplicate,
            "parse_failures": diag.parse_failures,
        }
    )
    print_message(f"Diagnostic output: {diagnostic_dir.resolve()}")


@app.command("export-scraper:tasks")
def scrape_openai_tasks(
    path: Path = typer.Option(
        ...,
        "--path",
        "-p",
        help="Path to an OpenAI export file or extracted export folder",
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
    ),
    out: Path = typer.Option(
        Path("export_scraper"),
        "--out",
        "-o",
        help="Repo-local output directory for extracted task prompt artifacts",
    ),
):
    """
    Scrape Codexify task prompt artifacts from OpenAI exports without DB writes.

    Example:
        codexify export-scraper:tasks --path ./OpenAI-export --out export_scraper
    """
    from backend.rag.openai_export_task_scraper import scrape_openai_export_tasks

    report = scrape_openai_export_tasks(path, output_dir=out)
    stats = report.to_dict()

    print_header()
    print_message("[bold cyan]OpenAI export task scrape complete[/bold cyan]")
    print_summary(
        {
            "files_scanned": stats["files_scanned"],
            "messages_scanned": stats["messages_scanned"],
            "codexify_task_prompt_hits": stats["codexify_task_prompt_hits"],
            "task_summary_hits": stats["task_summary_hits"],
            "execution_contract_hits": stats["execution_contract_hits"],
            "partial_or_ambiguous_hits": stats["partial_or_ambiguous_hits"],
        }
    )
    print_message(f"Output directory: {report.output_dir}")
    print_message(
        f"Diagnostic JSON: {report.output_dir / 'diagnostics' / 'scraper_report.json'}"
    )
    print_message(
        f"Diagnostic summary: {report.output_dir / 'diagnostics' / 'scraper_report.md'}"
    )


@app.command()
def validate(
    neo4j_url: str = typer.Option(
        "bolt://localhost:7687",
        "--neo4j-url",
        help="Neo4j connection URL",
    ),
    neo4j_user: str = typer.Option(
        "neo4j",
        "--neo4j-user",
        help="Neo4j username",
    ),
    neo4j_pass: str = typer.Option(
        "password",
        "--neo4j-pass",
        help="Neo4j password",
    ),
    chroma_path: Path = typer.Option(
        "./chroma",
        "--chroma",
        "-c",
        help="Local Chroma persistence path",
    ),
):
    """
    Validate that the migration was successful by checking Neo4j and Chroma.

    Example:
        codexify validate
        codexify validate --chroma ./my_chroma
    """
    print_header()
    print_message("🔍 [bold cyan]Validating migration...[/bold cyan]\n")

    errors = []
    stats = {}

    # Check Neo4j
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(neo4j_url, auth=(neo4j_user, neo4j_pass))

        with driver.session() as session:
            # Count threads
            result = session.run("MATCH (t:Thread) RETURN count(t) as count")
            thread_count = result.single()["count"]
            stats["neo4j_threads"] = thread_count

            # Count messages
            result = session.run("MATCH (m:Message) RETURN count(m) as count")
            message_count = result.single()["count"]
            stats["neo4j_messages"] = message_count

            # Count relationships
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            stats["neo4j_relationships"] = rel_count

        driver.close()

        print_message("✅ [green]Neo4j validation successful[/green]")
        print_message(f"   • Threads: {thread_count}", "green")
        print_message(f"   • Messages: {message_count}", "green")
        print_message(f"   • Relationships: {rel_count}", "green")

    except Exception as e:
        errors.append(f"Neo4j: {e}")
        print_message(f"❌ [red]Neo4j validation failed: {e}[/red]")

    # Check Chroma
    print_message()
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(chroma_path))
        collection = client.get_collection("chatgpt_messages")
        embedding_count = collection.count()
        stats["chroma_embeddings"] = embedding_count

        print_message("✅ [green]Chroma validation successful[/green]")
        print_message(f"   • Embeddings: {embedding_count}", "green")

    except Exception as e:
        errors.append(f"Chroma: {e}")
        print_message(f"❌ [red]Chroma validation failed: {e}[/red]")

    # Summary
    print_message("\n" + "─" * 70)
    if errors:
        print_message(
            f"\n⚠️  [yellow]{len(errors)} validation error(s) found[/yellow]"
        )
        for error in errors:
            print_message(f"   • {error}", "yellow")
        raise typer.Exit(code=1)
    else:
        print_message("\n✅ [bold green]All validations passed![/bold green]")
        print_message("   Your migration is healthy and ready to use.\n")


@app.command()
def history(
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Number of recent migrations to show",
    ),
):
    """
    Show migration history from logs.

    Example:
        codexify history
        codexify history --limit 5
    """
    summary_file = Path("logs/migration_summary.json")

    if not summary_file.exists():
        print_message("⚠️  [yellow]No migration history found[/yellow]")
        print_message("   Run a migration first with: codexify migrate <file>")
        return

    try:
        with open(summary_file) as f:
            summaries = json.load(f)
            if not isinstance(summaries, list):
                summaries = [summaries]

        # Show most recent first
        summaries = summaries[-limit:][::-1]

        print_header()
        print_message(
            f"📜 [bold cyan]Migration History (last {len(summaries)})[/bold cyan]\n"
        )

        for i, summary in enumerate(summaries, 1):
            completed = summary.get("completed_at", "Unknown")
            messages = summary.get("messages", 0)
            threads = summary.get("threads", 0)
            elapsed = summary.get("elapsed_seconds", 0)

            print_message(f"[cyan]{i}. {completed}[/cyan]")
            print_message(
                f"   Threads: {threads} | Messages: {messages} | Time: {elapsed}s"
            )
            if "error" in summary:
                print_message(f"   ❌ Error: {summary['error']}", "red")
            else:
                print_message("   ✅ Success", "green")
            print_message()

    except Exception as e:
        print_message(f"❌ [red]Failed to load history: {e}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
