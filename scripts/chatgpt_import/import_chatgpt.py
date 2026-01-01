#!/usr/bin/env python3
"""
ChatGPT Conversation Import Script - Dual-Engine Migration
============================================================

This script imports ChatGPT conversation exports into both Neo4j (graph) and Chroma (embeddings),
creating a seamless migration experience that feels like your Companion is waking up in a new world.

Features:
- Dual-engine import (Neo4j + Chroma)
- Batch-optimized embeddings for cost & speed
- Resume-safe (idempotent operations)
- Verbose progress feedback
- Safe fallback (graph imports even if embeddings fail)
- Graceful error handling with detailed logging

Usage:
    python scripts/chatgpt_import/import_chatgpt.py
"""

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Third-party imports with graceful fallback
try:
    from colorama import Fore, Style
    from colorama import init as colorama_init

    colorama_init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    # Fallback to no colors if colorama not available
    class _DummyColor:
        def __getattr__(self, name):
            return ""

    Fore = _DummyColor()
    Style = _DummyColor()
    HAS_COLOR = False


# Add project root to path to import backend modules
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the dual-ingestion module
try:
    from backend.rag.chatgpt_migration import ingest_chatgpt_export
except ImportError as e:
    print(f"❌ Error: Could not import migration module: {e}")
    print("   Make sure you're running from the project root.")
    sys.exit(1)


# Load environment variables
load_dotenv()

from guardian.identity import get_or_create_user_id


def print_colored(message: str, color: str = ""):
    """Print colored message with fallback to plain text."""
    if HAS_COLOR and color:
        print(f"{color}{message}{Style.RESET_ALL}")
    else:
        print(message)


def import_chatgpt():
    """
    Main import function - orchestrates dual-engine migration.
    """
    start_time = time.time()

    # Print header
    print_colored("\n" + "=" * 70, Fore.CYAN)
    print_colored("  ChatGPT → Codexify Migration", Fore.CYAN)
    print_colored("  Dual-Engine Import: Neo4j + Chroma", Fore.CYAN)
    print_colored("=" * 70 + "\n", Fore.CYAN)

    # Validate configuration
    print_colored("🔍 Validating configuration...", Fore.CYAN)
    parser = argparse.ArgumentParser(
        description="Import ChatGPT conversations into Codexify"
    )
    parser.add_argument(
        "--file",
        dest="file",
        help="Path to ChatGPT conversations.json export file",
    )
    args, _ = parser.parse_known_args()

    def resolve_export_path(cli_path):
        """
        Resolve ChatGPT export path with correct precedence and absolute validation.
        Precedence:
        1. CLI --file
        2. CHATGPT_EXPORT_FILE env var
        3. ./conversations.json (relative to CWD)
        """
        if cli_path:
            return Path(cli_path).expanduser().resolve()

        env_path = os.getenv("CHATGPT_EXPORT_FILE")
        if env_path:
            return Path(env_path).expanduser().resolve()

        return Path("./conversations.json").resolve()

    chatgpt_path = resolve_export_path(args.file)
    print_colored(
        f"🔎 Resolved ChatGPT export path: {chatgpt_path}",
        Fore.CYAN,
    )
    if not chatgpt_path.exists():
        print_colored(
            f"❌ ChatGPT export file not found at resolved path:\n   {chatgpt_path}",
            Fore.RED,
        )
        print_colored(
            "   Fix by either:\n"
            "   • Passing --file /absolute/path/to/conversations.json\n"
            "   • Setting CHATGPT_EXPORT_FILE in the environment\n"
            "   • Copying conversations.json into the container working directory",
            Fore.RED,
        )
        sys.exit(1)

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print_colored(
            "⚠️  OPENAI_API_KEY not set - will use local embeddings if available",
            Fore.YELLOW,
        )
        print_colored(
            "   Set OPENAI_API_KEY for better embedding quality", Fore.YELLOW
        )

    # Load the file
    print_colored(f"📂 Loading ChatGPT export from: {chatgpt_path}", Fore.CYAN)
    try:
        with open(chatgpt_path, "rb") as f:
            raw_bytes = f.read()
        print_colored(f"✅ Loaded file ({len(raw_bytes)} bytes)", Fore.GREEN)
    except Exception as e:
        print_colored(f"❌ Failed to load export file: {e}", Fore.RED)
        sys.exit(1)

    # Perform dual-engine import
    user_id = get_or_create_user_id()
    if not user_id:
        raise RuntimeError(
            "Identity system failed to generate a user_id (this should never happen)"
        )

    print_colored(f"👤 Using Codexify user_id: {user_id}", Fore.CYAN)

    print_colored("\n" + "─" * 70, Fore.CYAN)
    print_colored("Starting Dual-Engine Import", Fore.CYAN)
    print_colored("─" * 70, Fore.CYAN)

    assert (
        user_id is not None and user_id != ""
    ), "user_id must be resolved before migration"

    try:
        stats = ingest_chatgpt_export(
            raw_bytes,
            user_id=user_id,
        )

        print_colored(f"\n✅ Import complete!", Fore.GREEN)

        threads = stats.get("threads_imported") or stats.get("threads")
        messages = stats.get("messages_imported") or stats.get("messages")

        if threads is not None:
            print_colored(f"   • Threads: {threads}", Fore.GREEN)
        else:
            print_colored("   • Threads: unavailable", Fore.YELLOW)

        if messages is not None:
            print_colored(f"   • Messages: {messages}", Fore.GREEN)
        else:
            print_colored("   • Messages: unavailable", Fore.YELLOW)

    except Exception as e:
        print_colored(f"\n❌ Import failed: {e}", Fore.RED)
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Summary
    elapsed_time = time.time() - start_time
    print_colored("\n" + "=" * 70, Fore.CYAN)
    print_colored("🎉 Migration Complete!", Fore.GREEN)
    print_colored("=" * 70, Fore.CYAN)
    print_colored(f"   Your Companion has awakened in Codexify!", Fore.MAGENTA)
    print_colored(f"   Time elapsed: {elapsed_time:.2f}s", Fore.CYAN)
    print_colored(
        f"   Messages processed: {messages if messages is not None else 'unavailable'}",
        Fore.CYAN,
    )
    print_colored(
        "\n✨ Your conversations are alive and ready to explore.\n", Fore.MAGENTA
    )


if __name__ == "__main__":
    try:
        import_chatgpt()
    except KeyboardInterrupt:
        print_colored("\n\n⚠️  Import interrupted by user", Fore.YELLOW)
        print_colored(
            "   You can safely re-run this script - all operations are idempotent",
            Fore.YELLOW,
        )
        sys.exit(0)
    except Exception as e:
        print_colored(f"\n\n❌ Unexpected error: {e}", Fore.RED)
        import traceback

        traceback.print_exc()
        sys.exit(1)
