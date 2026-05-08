#!/usr/bin/env python3
"""
Reset and validate packaged runtime script for Codexify.

This script automates the "blank machine rehearsal" for the packaged macOS app,
allowing operators to test first-run DMG behavior repeatedly without deleting
source code or unrelated developer files.

SAFETY: This script is safe by default:
- Requires explicit --confirm flag before destructive actions
- Prints every destructive action before executing it
- Never deletes the Git repo
- Never deletes arbitrary user files

Usage:
    # Dry run (print actions without executing)
    python3 scripts/ops/reset_and_validate_packaged_runtime.py

    # Execute with confirmation
    python3 scripts/ops/reset_and_validate_packaged_runtime.py --confirm

    # Full clean with Docker/Ollama cleanup
    python3 scripts/ops/reset_and_validate_packaged_runtime.py --confirm --prune-images --prune-volumes

    # Skip Docker/Ollama management, just launch app
    python3 scripts/ops/reset_and_validate_packaged_runtime.py --confirm --skip-docker --skip-ollama --launch-app

    # With Minimax observation prompt
    python3 scripts/ops/reset_and_validate_packaged_runtime.py --confirm --minimax-notes
"""
from __future__ import annotations

import argparse
import os
import platform
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Constants
REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILES = [
    REPO_ROOT / "docker-compose.yml",
    REPO_ROOT / "docker-compose.runtime.yml",
    REPO_ROOT / "docker-compose.compiled.yml",
]
COMPOSE_PROJECT_NAME = "codexify"

# Patterns for identifying Codexify-related Docker resources
# Conservative matching - only match clear Codexify identifiers
DOCKER_RESOURCE_PATTERNS = [
    "codexify",
    "guardian",
]

# macOS app bundle
DEFAULT_APP_PATH = "/Applications/Codexify.app"


@dataclass
class CommandResult:
    """Result of a command execution."""
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    success: bool = field(init=False)

    def __post_init__(self):
        self.success = self.returncode == 0


@dataclass
class SystemState:
    """Collected system state for validation."""
    docker_installed: bool = False
    docker_daemon_reachable: bool = False
    docker_skipped: bool = False
    ollama_installed: bool = False
    ollama_running: bool = False
    ollama_skipped: bool = False
    compose_files_present: list[Path] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Reset and validate Codexify packaged runtime for DMG testing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Safety:
  This script is safe by default. It requires --confirm before any destructive
  actions and prints all planned actions before executing them.

Examples:
  # Dry run - see what would be done
  %(prog)s

  # Execute with Docker/Ollama cleanup
  %(prog)s --confirm --prune-images --prune-volumes

  # Just launch the app without cleaning
  %(prog)s --confirm --skip-docker --skip-ollama --launch-app

  # Get Minimax observation prompt
  %(prog)s --confirm --minimax-notes
"""
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm destructive actions. Without this flag, only prints planned actions."
    )
    parser.add_argument(
        "--prune-images",
        action="store_true",
        help="Remove Codexify-related Docker images (requires --confirm)."
    )
    parser.add_argument(
        "--prune-volumes",
        action="store_true",
        help="Remove Codexify-related Docker volumes (requires --confirm)."
    )
    parser.add_argument(
        "--skip-docker",
        action="store_true",
        help="Skip Docker Compose management."
    )
    parser.add_argument(
        "--skip-ollama",
        action="store_true",
        help="Skip Ollama management."
    )
    parser.add_argument(
        "--launch-app",
        action="store_true",
        help="Launch the packaged app after reset."
    )
    parser.add_argument(
        "--app-path",
        type=str,
        default=DEFAULT_APP_PATH,
        help=f"Path to the app bundle (default: {DEFAULT_APP_PATH})."
    )
    parser.add_argument(
        "--minimax-notes",
        action="store_true",
        help="Print a Minimax prompt for observing and summarizing validation from screenshots/logs."
    )
    return parser.parse_args()


def run_command(
    command: list[str],
    cwd: Optional[Path] = None,
    capture: bool = True,
    check: bool = False,
) -> CommandResult:
    """
    Run a command and return the result.

    Args:
        command: Command and arguments as list
        cwd: Working directory (defaults to REPO_ROOT)
        capture: Whether to capture stdout/stderr
        check: Whether to raise exception on non-zero exit

    Returns:
        CommandResult with execution details
    """
    if cwd is None:
        cwd = REPO_ROOT

    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=capture,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=check,
        )
        return CommandResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout if capture else "",
            stderr=completed.stderr if capture else "",
        )
    except OSError as exc:
        return CommandResult(
            command=command,
            returncode=-1,
            stdout="",
            stderr=str(exc),
        )


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print('=' * 60)


def print_status(prefix: str, message: str) -> None:
    """Print a status message with prefix."""
    print(f"[{prefix}] {message}")


def info(message: str) -> None:
    """Print INFO message."""
    print_status("INFO", message)


def warn(message: str) -> None:
    """Print WARN message."""
    print_status("WARN", message)


def pass_msg(message: str) -> None:
    """Print PASS message."""
    print_status("PASS", message)


def check_docker_installed() -> bool:
    """Check if Docker is installed."""
    result = run_command(["docker", "--version"])
    return result.success


def check_docker_daemon() -> bool:
    """Check if Docker daemon is reachable."""
    result = run_command(["docker", "info"])
    return result.success


def check_ollama_installed() -> bool:
    """Check if Ollama is installed."""
    result = run_command(["ollama", "--version"])
    return result.success


def check_ollama_running() -> bool:
    """Check if Ollama process is running (macOS)."""
    if platform.system() != "Darwin":
        return False

    # Try pgrep for Ollama process
    result = run_command(["pgrep", "-x", "Ollama"])
    if result.success:
        return True

    # Fall back to pgrep -f for ollama binary
    result = run_command(["pgrep", "-f", "ollama"])
    return result.success


def collect_system_state(args: argparse.Namespace) -> SystemState:
    """Collect current system state for reporting."""
    state = SystemState()

    # Check Docker
    if args.skip_docker:
        state.docker_skipped = True
    else:
        state.docker_installed = check_docker_installed()
        if state.docker_installed:
            state.docker_daemon_reachable = check_docker_daemon()
        else:
            state.docker_daemon_reachable = False

    # Check Ollama
    if args.skip_ollama:
        state.ollama_skipped = True
    else:
        state.ollama_installed = check_ollama_installed()
        if state.ollama_installed:
            state.ollama_running = check_ollama_running()
        else:
            state.ollama_running = False

    # Check compose files
    for compose_file in COMPOSE_FILES:
        if compose_file.exists():
            state.compose_files_present.append(compose_file)

    return state


def report_system_state(state: SystemState) -> None:
    """Report collected system state."""
    print_section("System State Report")

    # Docker status
    if state.docker_skipped:
        info("Docker management skipped (--skip-docker)")
    elif state.docker_installed:
        pass_msg("Docker is installed")
        if state.docker_daemon_reachable:
            pass_msg("Docker daemon is reachable")
        else:
            warn("Docker is installed but daemon is not reachable")
    else:
        info("Docker is not installed")

    # Ollama status
    if state.ollama_skipped:
        info("Ollama management skipped (--skip-ollama)")
    elif state.ollama_installed:
        pass_msg("Ollama is installed")
        if state.ollama_running:
            pass_msg("Ollama is running")
        else:
            info("Ollama is installed but not running")
    else:
        info("Ollama is not installed")

    # Compose files
    if state.compose_files_present:
        info(f"Found {len(state.compose_files_present)} compose file(s):")
        for cf in state.compose_files_present:
            print(f"  - {cf.relative_to(REPO_ROOT)}")


def get_compose_down_command(compose_file: Path) -> list[str]:
    """Get the docker compose down command for a compose file."""
    return [
        "docker", "compose",
        "-f", str(compose_file),
        "-p", COMPOSE_PROJECT_NAME,
        "down"
    ]


def get_compose_files_for_cleanup() -> list[Path]:
    """Get list of compose files that exist and should be cleaned up."""
    return [cf for cf in COMPOSE_FILES if cf.exists()]


def plan_docker_compose_down(confirm: bool) -> None:
    """Plan and optionally execute Docker Compose down."""
    compose_files = get_compose_files_for_cleanup()

    if not compose_files:
        info("No Docker Compose files found - skipping compose down")
        return

    for compose_file in compose_files:
        rel_path = compose_file.relative_to(REPO_ROOT)
        cmd = get_compose_down_command(compose_file)
        cmd_str = shlex.join(cmd)

        info(f"Would execute: {cmd_str}")

        if confirm:
            print(f"  Executing compose down for {rel_path}...")
            result = run_command(cmd)
            if result.success:
                pass_msg(f"Compose down completed for {rel_path}")
            else:
                warn(f"Compose down failed for {rel_path}: {result.stderr.strip() or 'unknown error'}")


def get_codexify_containers() -> list[str]:
    """Get list of Codexify-related containers."""
    result = run_command([
        "docker", "ps", "-a",
        "--filter", f"name={COMPOSE_PROJECT_NAME}",
        "--format", "{{.Names}}"
    ])

    if not result.success:
        return []

    containers = [c.strip() for c in result.stdout.strip().split("\n") if c.strip()]
    return containers


def get_codexify_volumes() -> list[str]:
    """Get list of Codexify-related volumes."""
    result = run_command([
        "docker", "volume", "ls",
        "--filter", f"name={COMPOSE_PROJECT_NAME}",
        "--format", "{{.Name}}"
    ])

    if not result.success:
        return []

    volumes = [v.strip() for v in result.stdout.strip().split("\n") if v.strip()]
    return volumes


def get_codexify_images() -> list[str]:
    """Get list of Codexify-related images."""
    # Conservative pattern matching for Codexify images
    all_images_result = run_command([
        "docker", "images",
        "--format", "{{.Repository}}:{{.Tag}}"
    ])

    if not all_images_result.success:
        return []

    codexify_images = []
    for line in all_images_result.stdout.strip().split("\n"):
        image = line.strip()
        if not image or image == "<none>:<none>":
            continue

        # Check if image matches any Codexify pattern
        image_lower = image.lower()
        for pattern in DOCKER_RESOURCE_PATTERNS:
            if pattern in image_lower:
                codexify_images.append(image)
                break

    return codexify_images


def plan_container_removal(confirm: bool) -> None:
    """Plan and optionally execute container removal."""
    containers = get_codexify_containers()

    if not containers:
        info("No Codexify containers found")
        return

    info(f"Found {len(containers)} Codexify container(s):")
    for container in containers:
        print(f"  - {container}")

    if confirm:
        for container in containers:
            info(f"Removing container: {container}")
            result = run_command(["docker", "rm", "-f", container])
            if result.success:
                pass_msg(f"Removed container: {container}")
            else:
                warn(f"Failed to remove container {container}: {result.stderr.strip() or 'unknown error'}")


def plan_volume_removal(confirm: bool, prune_volumes: bool) -> None:
    """Plan and optionally execute volume removal."""
    if not prune_volumes:
        info("Volume pruning disabled - skipping volume removal")
        return

    volumes = get_codexify_volumes()

    if not volumes:
        info("No Codexify volumes found")
        return

    info(f"Found {len(volumes)} Codexify volume(s):")
    for volume in volumes:
        print(f"  - {volume}")

    if confirm:
        for volume in volumes:
            info(f"Removing volume: {volume}")
            result = run_command(["docker", "volume", "rm", volume])
            if result.success:
                pass_msg(f"Removed volume: {volume}")
            else:
                warn(f"Failed to remove volume {volume}: {result.stderr.strip() or 'unknown error'}")


def plan_image_removal(confirm: bool, prune_images: bool) -> None:
    """Plan and optionally execute image removal."""
    if not prune_images:
        info("Image pruning disabled - skipping image removal")
        return

    images = get_codexify_images()

    if not images:
        info("No Codexify images found")
        return

    info(f"Found {len(images)} Codexify image(s):")
    for image in images:
        print(f"  - {image}")

    if confirm:
        for image in images:
            info(f"Removing image: {image}")
            result = run_command(["docker", "rmi", image])
            if result.success:
                pass_msg(f"Removed image: {image}")
            else:
                warn(f"Failed to remove image {image}: {result.stderr.strip() or 'unknown error'}")


def stop_ollama_macos(confirm: bool) -> None:
    """Stop Ollama on macOS using osascript."""
    if platform.system() != "Darwin":
        info("Ollama stop not supported on this platform")
        return

    # Check if Ollama is actually running first
    if not check_ollama_running():
        info("Ollama is not running - skipping stop")
        return

    info("Ollama is running - preparing stop command")

    # Use osascript to gracefully quit the Ollama app
    cmd = ["osascript", "-e", 'quit app "Ollama"']
    cmd_str = shlex.join(cmd)

    info(f"Would execute: {cmd_str}")

    if confirm:
        print("  Sending quit to Ollama app...")
        result = run_command(cmd)
        if result.success:
            pass_msg("Quit signal sent to Ollama")
            info("Note: If Ollama has background processes, you may need to manually force quit")
        else:
            warn(f"Failed to quit Ollama gracefully: {result.stderr.strip() or 'unknown error'}")
            warn("Consider manually quitting Ollama before testing if issues persist")


def launch_app(app_path: str, confirm: bool) -> None:
    """Launch the packaged app using open command."""
    if not confirm:
        info(f"Would launch app: open {shlex.quote(app_path)}")
        return

    path = Path(app_path)
    if not path.exists():
        warn(f"App path does not exist: {app_path}")
        info("Please verify the app is installed at the specified path")
        return

    info(f"Launching app: {app_path}")
    result = run_command(["open", app_path])
    if result.success:
        pass_msg(f"Launched: {app_path}")
    else:
        warn(f"Failed to launch app: {result.stderr.strip() or 'unknown error'}")


def print_validation_observations() -> None:
    """Print expected manual observations after launching the app."""
    print_section("Post-Launch Validation Observations")

    info("After launching the app, observe the following:")

    observations = [
        ("Docker Status", [
            "If Docker is missing: App should display clear message about Docker requirement",
            "If Docker is offline: App should show legible offline/unreachable state",
            "If Docker is available: Runtime pull/startup should begin automatically",
        ]),
        ("Ollama Status", [
            "If Ollama is missing: App should display clear message about Ollama requirement",
            "If Ollama is offline: App should show legible offline/unreachable state",
            "If Ollama is available: Model warming should begin automatically",
        ]),
        ("Health Recovery", [
            "Health surfaces should eventually recover to ready/degraded states",
            "Check /health, /health/chat, /api/health/llm, /api/health/retrieval",
        ]),
        ("First Chat", [
            "First chat send should either:",
            "  - Complete successfully with response",
            "  - Report clear blocked/degraded state with actionable message",
        ]),
    ]

    for category, items in observations:
        print(f"\n  {category}:")
        for item in items:
            print(f"    - {item}")


def print_minimax_prompt() -> None:
    """Print a suggested Minimax prompt for observing validation runs."""
    print_section("Minimax Observation Prompt")

    prompt = """Use this prompt with Minimax to observe and summarize your validation run:

---
Please analyze the screenshots and logs from my Codexify packaged app validation run.

Context:
- Testing first-run DMG behavior on a clean environment
- Checking how the app handles missing/available Docker and Ollama
- Looking for clear error states and recovery behavior

Please summarize:
1. What dependencies are detected as missing/offline?
2. Are the error messages clear and actionable for beta testers?
3. Does the runtime recovery behavior make sense?
4. Any UI/UX issues that would confuse a new user?

Provide specific observations with references to the screenshots/logs.
---

This script does NOT call any external API. Save this prompt and the
screenshots/logs for later analysis.
"""
    print(prompt)


def main() -> int:
    """Main entry point."""
    args = parse_args()

    print_section("Codexify Packaged Runtime Reset & Validation")
    print(f"Repository root: {REPO_ROOT}")
    print(f"Target app: {args.app_path}")

    # Collect system state
    state = collect_system_state(args)

    # Report current state
    report_system_state(state)

    # Planning phase - always runs to show what would happen
    print_section("Planned Actions")

    if not args.skip_docker:
        # Docker Compose down
        print("\n[DOCKER COMPOSE MANAGEMENT]")
        plan_docker_compose_down(args.confirm)

        # Container removal
        print("\n[CONTAINER REMOVAL]")
        plan_container_removal(args.confirm)

        # Volume removal
        print("\n[VOLUME REMOVAL]")
        plan_volume_removal(args.confirm, args.prune_volumes)

        # Image removal
        print("\n[IMAGE REMOVAL]")
        plan_image_removal(args.confirm, args.prune_images)
    else:
        info("Docker management skipped (--skip-docker)")

    if not args.skip_ollama:
        print("\n[OLLAMA MANAGEMENT]")
        stop_ollama_macos(args.confirm)
    else:
        info("Ollama management skipped (--skip-ollama)")

    if args.launch_app:
        print("\n[APP LAUNCH]")
        launch_app(args.app_path, args.confirm)
    else:
        info("App launch disabled (no --launch-app flag)")

    # Validation observations
    print_validation_observations()

    # Minimax prompt
    if args.minimax_notes:
        print_minimax_prompt()

    # Summary
    print_section("Execution Summary")

    if args.confirm:
        pass_msg("All destructive actions have been executed")
        if args.launch_app:
            info("App launch was requested - verify the app opened successfully")
    else:
        warn("DRY RUN - No actions were executed")
        info("Run with --confirm to execute the planned actions")
        info("Example: python3 scripts/ops/reset_and_validate_packaged_runtime.py --confirm")

    return 0


if __name__ == "__main__":
    sys.exit(main())
