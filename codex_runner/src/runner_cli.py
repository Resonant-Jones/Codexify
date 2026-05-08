#!/usr/bin/env python3
"""
Campaign Runner - Unified CLI with Pi Integration

This module provides:
- Profile management (list, create, edit, delete)
- Natural language command processing
- Pi SDK integration for agent execution

Usage:
    python runner_cli.py profile list
    python runner_cli.py profile create my-profile
    python runner_cli.py run --profile fast
    python runner_cli.py run "Analyze and fix security issues"
    python runner_cli.py audit "Look for bugs"
    python runner_cli.py compile "Generate campaigns from audit"
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Import profile management
from profile import Profile, ProfileManager
from typing import Any

# Configuration
SCRIPT_DIR = Path(__file__).resolve().parent
PI_WRAPPER = SCRIPT_DIR / "agent-wrapper.js"


@dataclass
class CommandResult:
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0


def get_git_info(repo_root: Path) -> dict[str, str]:
    """Get current git branch and commit."""
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return {"branch": branch, "commit": commit}
    except Exception:
        return {"branch": "unknown", "commit": "unknown"}


def generate_audit_id() -> str:
    """Generate a deterministic audit ID."""
    import hashlib
    import time

    payload = {
        "timestamp": str(time.time()),
        "random": os.urandom(16).hex(),
    }
    hash_input = json.dumps(payload, sort_keys=True)
    short_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
    return f"AUDIT_{short_hash}"


def run_pi_agent(
    mode: str, prompt: str, options: dict[str, Any]
) -> CommandResult:
    """Run the Pi agent wrapper with given mode and prompt."""

    # Build environment
    env = os.environ.copy()
    env["PI_MODEL"] = options.get("model", "claude-sonnet-4-20250514")
    env["PI_THINKING"] = options.get("thinking", "medium")
    if options.get("verbose"):
        env["PI_VERBOSE"] = "1"

    # Build command
    cmd = ["node", str(PI_WRAPPER), mode, prompt]

    try:
        result = subprocess.run(
            cmd,
            cwd=options.get("cwd", os.getcwd()),
            env=env,
            capture_output=True,
            text=True,
            timeout=options.get("timeout", 300),
        )
        return CommandResult(
            success=result.returncode == 0,
            output=result.stdout,
            error=result.stderr,
            exit_code=result.returncode,
        )
    except subprocess.TimeoutExpired:
        return CommandResult(
            success=False,
            error=f"Timeout after {options.get('timeout', 300)}s",
            exit_code=124,
        )
    except FileNotFoundError:
        return CommandResult(
            success=False,
            error=f"Node.js not found. Ensure Node.js is installed.",
            exit_code=127,
        )
    except Exception as exc:
        return CommandResult(
            success=False,
            error=str(exc),
            exit_code=1,
        )


def cmd_profile(args: list[str]) -> CommandResult:
    """Handle profile subcommand."""
    pm = ProfileManager().load()

    if not args:
        return CommandResult(success=True, output=pm.render())

    subcmd = args[0]

    if subcmd == "list":
        return CommandResult(success=True, output=pm.render())

    elif subcmd == "show":
        if len(args) < 2:
            return CommandResult(
                success=False, error="Usage: profile show <name>", exit_code=1
            )
        profile = pm.get(args[1])
        if profile:
            return CommandResult(
                success=True, output=json.dumps(profile.to_dict(), indent=2)
            )
        return CommandResult(
            success=False, error=f"Profile '{args[1]}' not found", exit_code=1
        )

    elif subcmd == "create":
        if len(args) < 2:
            return CommandResult(
                success=False,
                error="Usage: profile create <name> [key=val...]",
                exit_code=1,
            )
        name = args[1]
        kwargs = {}
        for arg in args[2:]:
            if "=" in arg:
                key, val = arg.split("=", 1)
                if key in {"passes"}:
                    kwargs[key] = int(val)
                elif key in {"verify", "execute"}:
                    kwargs[key] = val.lower() in {"1", "true", "yes", "on"}
                else:
                    kwargs[key] = val
        profile = pm.create(name, **kwargs)
        return CommandResult(
            success=True, output=f"Created profile: {profile.name}"
        )

    elif subcmd == "delete":
        if len(args) < 2:
            return CommandResult(
                success=False, error="Usage: profile delete <name>", exit_code=1
            )
        if pm.delete(args[1]):
            return CommandResult(
                success=True, output=f"Deleted profile: {args[1]}"
            )
        return CommandResult(
            success=False, error=f"Profile '{args[1]}' not found", exit_code=1
        )

    elif subcmd == "activate":
        if len(args) < 2:
            return CommandResult(
                success=False,
                error="Usage: profile activate <name>",
                exit_code=1,
            )
        if pm.set_active(args[1]):
            pm.save()
            return CommandResult(
                success=True, output=f"Activated profile: {args[1]}"
            )
        return CommandResult(
            success=False, error=f"Profile '{args[1]}' not found", exit_code=1
        )

    else:
        return CommandResult(
            success=False,
            error=f"Unknown profile command: {subcmd}",
            exit_code=1,
        )


def cmd_audit(args: list[str], options: dict[str, Any]) -> CommandResult:
    """Run an audit using the agent."""
    pm = ProfileManager().load()
    profile = pm.get(options.get("profile", pm.active_profile))

    if not args:
        return CommandResult(
            success=False,
            error="Usage: audit <prompt>\nExample: audit Analyze this repo for security issues",
            exit_code=1,
        )

    prompt = " ".join(args)

    # Get repo info
    repo_root = Path(options.get("cwd", os.getcwd()))
    git_info = get_git_info(repo_root)

    # Build context prompt
    context = f"""Repository: {repo_root}
Branch: {git_info['branch']}
Commit: {git_info['commit']}

{prompt}

Respond with JSON only. Format:
{{
  "audit_id": "{generate_audit_id()}",
  "repo": {{"path": "{repo_root}", "branch": "{git_info['branch']}", "commit": "{git_info['commit']}"}},
  "generated_at": "<ISO-8601>",
  "reports": [],
  "runner_ready_findings": [],
  "derived_campaigns": []
}}
"""

    agent_options = {
        "model": profile.model if profile else "claude-sonnet-4-20250514",
        "thinking": profile.thinking if profile else "medium",
        "verbose": options.get("verbose", False),
        "cwd": str(repo_root),
    }

    return run_pi_agent("audit", context, agent_options)


def cmd_compile(args: list[str], options: dict[str, Any]) -> CommandResult:
    """Compile audit results into campaign set."""
    pm = ProfileManager().load()
    profile = pm.get(options.get("profile", pm.active_profile))

    if not args:
        return CommandResult(
            success=False,
            error="Usage: compile <prompt>\nExample: compile Generate campaigns from audit findings",
            exit_code=1,
        )

    prompt = " ".join(args)

    repo_root = Path(options.get("cwd", os.getcwd()))
    git_info = get_git_info(repo_root)

    context = f"""Repository: {repo_root}
Branch: {git_info['branch']}

{prompt}

Output a JSON campaign set:
{{
  "audit_id": "<use existing or create new>",
  "generated_at": "<ISO-8601>",
  "campaigns": []
}}
"""

    agent_options = {
        "model": profile.model if profile else "claude-opus-4-5",
        "thinking": profile.thinking if profile else "high",
        "verbose": options.get("verbose", False),
        "cwd": str(repo_root),
    }

    return run_pi_agent("compile", context, agent_options)


def cmd_run(args: list[str], options: dict[str, Any]) -> CommandResult:
    """Run a natural language command through the agent."""
    pm = ProfileManager().load()
    profile = pm.get(options.get("profile", pm.active_profile))

    if not args:
        return CommandResult(
            success=False,
            error="Usage: run <prompt>\nExample: run Analyze and fix all security issues",
            exit_code=1,
        )

    prompt = " ".join(args)
    repo_root = Path(options.get("cwd", os.getcwd()))
    git_info = get_git_info(repo_root)

    context = f"""You are working in repository: {repo_root}
Branch: {git_info['branch']}

Command: {prompt}

Execute this command. You have full access to read, write, edit, and bash tools.
Report your findings and actions as JSON.
"""

    agent_options = {
        "model": profile.model if profile else "claude-sonnet-4-20250514",
        "thinking": profile.thinking if profile else "medium",
        "verbose": options.get("verbose", False),
        "cwd": str(repo_root),
    }

    return run_pi_agent("audit", context, agent_options)


def cmd_help() -> CommandResult:
    """Show help."""
    help_text = """
Campaign Runner - Pi-Powered AI Agent
=======================================

Usage:
    python runner_cli.py <command> [options] [args...]

Commands:
    profile <subcommand>   - Manage profiles (list, show, create, delete, activate)
    audit <prompt>         - Run audit analysis
    compile <prompt>       - Compile audit results into campaigns
    run <prompt>           - Execute natural language command
    help                   - Show this help

Profile Management:
    profile list                    - List all profiles
    profile show <name>            - Show profile details
    profile create <name> [k=v...] - Create profile with options
    profile delete <name>           - Delete a profile
    profile activate <name>        - Set active profile

Options:
    --profile <name>    - Use specific profile (default: active)
    --verbose           - Enable verbose output
    --cwd <path>        - Set working directory
    --model <id>        - Override model
    --thinking <level>  - Override thinking level

Examples:
    # List profiles
    python runner_cli.py profile list

    # Run audit with default profile
    python runner_cli.py audit "Find security issues"

    # Run with specific profile
    python runner_cli.py --profile thorough audit "Thorough security review"

    # Natural language command
    python runner_cli.py run "Analyze code quality and suggest improvements"

    # Compile campaigns
    python runner_cli.py compile "Generate campaign set from findings"
"""
    return CommandResult(success=True, output=help_text)


def main():
    args = sys.argv[1:]

    # Parse global options
    options: dict[str, Any] = {}
    filtered_args = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--profile" and i + 1 < len(args):
            options["profile"] = args[i + 1]
            i += 2
        elif arg == "--verbose" or arg == "-v":
            options["verbose"] = True
            i += 1
        elif arg == "--cwd" and i + 1 < len(args):
            options["cwd"] = args[i + 1]
            i += 2
        elif arg == "--model" and i + 1 < len(args):
            options["model"] = args[i + 1]
            i += 2
        elif arg == "--thinking" and i + 1 < len(args):
            options["thinking"] = args[i + 1]
            i += 2
        else:
            filtered_args.append(arg)
            i += 1

    if not filtered_args:
        print(cmd_help().output)
        return 0

    cmd = filtered_args[0]
    cmd_args = filtered_args[1:]

    result: CommandResult

    if cmd == "profile":
        result = cmd_profile(cmd_args)
    elif cmd == "audit":
        result = cmd_audit(cmd_args, options)
    elif cmd == "compile":
        result = cmd_compile(cmd_args, options)
    elif cmd == "run":
        result = cmd_run(cmd_args, options)
    elif cmd == "help" or cmd == "--help" or cmd == "-h":
        result = cmd_help()
    else:
        # Treat as natural language command
        result = cmd_run([cmd] + cmd_args, options)

    if result.output:
        print(result.output)
    if result.error and not result.success:
        print(result.error, file=sys.stderr)

    return 0 if result.success else result.exit_code


if __name__ == "__main__":
    sys.exit(main())
