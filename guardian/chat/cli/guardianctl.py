#!/usr/bin/env python3
"""
Guardian Control CLI
------------------
Command-line interface for managing Guardian system components.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone

from guardian.core.plugins import (
    get_runtime_plugin_loader,
    load_runtime_plugins,
)
from guardian.memory.logger import memory_logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
plugin_loader = get_runtime_plugin_loader()


def list_plugins(args: argparse.Namespace) -> None:
    """List available plugins and their status."""
    plugins = plugin_loader.plugins

    print("\nAvailable Plugins:")
    print("=" * 50)

    for name, plugin in plugins.items():
        status = "ENABLED" if plugin.enabled else "DISABLED"
        print(f"\n{name} ({status})")
        print("-" * len(name))
        print(f"Version: {plugin.metadata['version']}")
        print(f"Author: {plugin.metadata['author']}")
        print(f"Description: {plugin.metadata['description']}")
        if plugin.last_health_check:
            print(f"Health: {plugin.last_health_check['status']}")
        print(f"Error Count: {plugin.error_count}")


def run_plugin(args: argparse.Namespace) -> None:
    """Run a specific plugin."""
    plugin = plugin_loader.get_plugin(args.name)
    if not plugin:
        logger.error(f"Plugin {args.name} not found")
        sys.exit(1)

    if not plugin.enabled:
        logger.error(f"Plugin {args.name} is disabled")
        sys.exit(1)

    try:
        # Check if plugin has run method
        if not hasattr(plugin.module, "run"):
            logger.error(f"Plugin {args.name} does not implement run method")
            sys.exit(1)

        # Parse plugin args if provided
        plugin_args = {}
        if args.args:
            for arg in args.args:
                key, value = arg.split("=")
                plugin_args[key] = value

        result = plugin.module.run(**plugin_args)
        print(f"\nPlugin {args.name} execution result:")
        print(json.dumps(result, indent=2))

    except Exception as e:
        logger.error(f"Failed to run plugin {args.name}: {e}")
        sys.exit(1)


def query_memory(args: argparse.Namespace) -> None:
    """Query memory events."""
    # Parse time range
    start_time = None
    end_time = None

    if args.last:
        start_time = datetime.now(timezone.utc) - timedelta(hours=args.last)
    else:
        if args.start:
            start_time = datetime.fromisoformat(args.start)
        if args.end:
            end_time = datetime.fromisoformat(args.end)

    # Parse tags
    tags = args.tags.split(",") if args.tags else None

    events = memory_logger.query_events(
        backend=args.backend,
        source=args.source,
        event_type=args.type,
        tags=tags,
        start_time=start_time,
        end_time=end_time,
        limit=args.limit,
    )

    print(f"\nMemory Events ({len(events)} results):")
    print("=" * 50)

    for event in events:
        print(f"\nTimestamp: {event['timestamp']}")
        print(f"Source: {event['source']}")
        print(f"Type: {event['event_type']}")
        print(f"Tags: {', '.join(event['tags'])}")
        print("Payload:")
        print(json.dumps(event["payload"], indent=2))
        print("-" * 50)


def enable_plugin(args: argparse.Namespace) -> None:
    """Enable a plugin."""
    if plugin_loader.enable_plugin(args.name):
        print(f"Successfully enabled plugin {args.name}")
    else:
        logger.error(f"Failed to enable plugin {args.name}")
        sys.exit(1)


def disable_plugin(args: argparse.Namespace) -> None:
    """Disable a plugin."""
    if plugin_loader.disable_plugin(args.name):
        print(f"Successfully disabled plugin {args.name}")
    else:
        logger.error(f"Failed to disable plugin {args.name}")
        sys.exit(1)


def main() -> None:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Guardian Control CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Command to execute"
    )

    # List plugins command
    list_parser = subparsers.add_parser(
        "list-plugins", help="List available plugins"
    )

    # Add companion-related commands
    build_parser = subparsers.add_parser(
        "build-companion", help="Launch Imprint Zero companion creation flow"
    )

    list_companions_parser = subparsers.add_parser(
        "list-companions", help="List saved companions"
    )

    deploy_parser = subparsers.add_parser(
        "deploy-companion", help="Load and deploy a companion"
    )
    deploy_parser.add_argument("name", help="Companion name")

    delete_parser = subparsers.add_parser(
        "delete-companion", help="Delete a companion profile"
    )
    delete_parser.add_argument("name", help="Companion name")

    # Run plugin command
    run_parser = subparsers.add_parser(
        "run-plugin", help="Run a specific plugin"
    )
    run_parser.add_argument("name", help="Plugin name")
    run_parser.add_argument(
        "--args", nargs="*", help="Plugin arguments in key=value format"
    )

    # Query memory command
    query_parser = subparsers.add_parser(
        "query-memory", help="Query memory events"
    )
    query_parser.add_argument(
        "--backend",
        choices=["sqlite", "jsonl"],
        default="sqlite",
        help="Storage backend to query",
    )
    query_parser.add_argument("--source", help="Filter by source")
    query_parser.add_argument("--type", help="Filter by event type")
    query_parser.add_argument("--tags", help="Filter by tags (comma-separated)")
    query_parser.add_argument("--start", help="Start time (ISO format)")
    query_parser.add_argument("--end", help="End time (ISO format)")
    query_parser.add_argument(
        "--last", type=int, help="Query events from last N hours"
    )
    query_parser.add_argument(
        "--limit", type=int, default=100, help="Maximum number of results"
    )

    # Enable plugin command
    enable_parser = subparsers.add_parser(
        "enable-plugin", help="Enable a plugin"
    )
    enable_parser.add_argument("name", help="Plugin name")

    # Disable plugin command
    disable_parser = subparsers.add_parser(
        "disable-plugin", help="Disable a plugin"
    )
    disable_parser.add_argument("name", help="Plugin name")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize plugin system
    load_runtime_plugins()

    # Execute command
    if args.command == "list-plugins":
        list_plugins(args)
    elif args.command == "run-plugin":
        run_plugin(args)
    elif args.command == "query-memory":
        query_memory(args)
    elif args.command == "enable-plugin":
        enable_plugin(args)
    elif args.command == "disable-plugin":
        disable_plugin(args)
    elif args.command == "build-companion":
        import sys
        from pathlib import Path

        script_path = (
            Path(__file__).parent.parent.parent
            / "scripts"
            / "imprint_zero_flow.py"
        )

        if not script_path.exists():
            logger.error("Imprint Zero flow script not found")
            sys.exit(1)

        # Add scripts directory to Python path
        sys.path.append(str(script_path.parent))

        import imprint_zero_flow

        imprint_zero_flow.main()
    elif args.command == "list-companions":
        from guardian.profiles.manager import profile_manager

        companions = profile_manager.list_profiles()
        if companions:
            print("\nSaved Companions:")
            print("=" * 50)
            for comp in companions:
                status = "ACTIVE" if comp.get("active") else "INACTIVE"
                print(f"\nName: {comp['name']} ({status})")
                print(f"Path: {comp['path']}")
        else:
            print("\nNo companions found.")

    elif args.command == "deploy-companion":
        from guardian.profiles.manager import profile_manager

        if profile_manager.deploy_profile(args.name):
            profile = profile_manager.load_profile(args.name)
            if profile:
                print("\nDeployed companion profile:")
                print("=" * 50)
                print(json.dumps(profile, indent=2))
            else:
                logger.error(f"Failed to load companion '{args.name}'")
                sys.exit(1)
        else:
            logger.error(f"Failed to deploy companion '{args.name}'")
            sys.exit(1)

    elif args.command == "delete-companion":
        from guardian.profiles.manager import profile_manager

        if profile_manager.delete_profile(args.name):
            print(f"\nDeleted companion '{args.name}'")
        else:
            logger.error(f"Failed to delete companion '{args.name}'")
            sys.exit(1)


if __name__ == "__main__":
    main()
