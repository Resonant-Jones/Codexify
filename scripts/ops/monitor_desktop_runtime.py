#!/usr/bin/env python3
"""
Codexify Desktop Runtime Monitor
================================
Read-only operator monitor for the supported local Docker Compose runtime and the
packaged desktop-launcher proof surfaces.

What this monitors
-------------------
Runtime HTTP surfaces (all on the configured BACKEND_BASE_URL):
  GET /health               → overall backend liveness
  GET /health/chat          → Redis/queue/worker health for chat completion
  GET /api/health/llm       → active-provider runtime state
  GET /api/health/retrieval  → retrieval/vector health
  GET /api/llm/catalog?include=all  → discovered model inventory

Desktop-launcher proof artifacts (on-disk, platform-specific app-support dir):
  ~/.codexify-launcher-startup-state.json  → setup-complete + backend handoff target
  ~/.codexify-runtime-manifest.json        → packaged runtime config snapshot
  ~/.codexify-packaged-runtime             → empty marker confirming materialization

What this does NOT do
----------------------
- Does NOT change code or config
- Does NOT restart services
- Does NOT run migrations
- Does NOT patch files
- Does NOT collapse multiple truth surfaces into one binary healthy/unhealthy flag

Exit codes
-----------
  0 → all surfaces reachable/ready (ready or degraded only — not unreachable or missing_artifact)
  1 → one or more surfaces degraded or not_ready
  2 → one or more surfaces unreachable or missing critical artifact

Usage
------
  python scripts/ops/monitor_desktop_runtime.py --once
  python scripts/ops/monitor_desktop_runtime.py --watch --interval 15
  python scripts/ops/monitor_desktop_runtime.py --once --json
  python scripts/ops/monitor_desktop_runtime.py --once --backend-url http://localhost:8888
"""

import argparse
import json
import os
import platform
import signal
import sys
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

try:
    import requests

    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False


# ---------------------------------------------------------------------------
# Bounded status vocabulary — matches chat-runtime-contract semantic precision
# ---------------------------------------------------------------------------


class HealthStatus(str, Enum):
    """Bounded status vocabulary for a single monitored surface."""

    READY = "ready"  # surface responded with a healthy/ok status
    DEGRADED = (
        "degraded"  # surface responded but with a degraded/warning indicator
    )
    NOT_READY = (
        "not_ready"  # surface responded but content indicates not yet ready
    )
    UNREACHABLE = "unreachable"  # transport-level failure (timeout, connection error, 5xx)
    MISSING_ARTIFACT = (
        "missing_artifact"  # expected on-disk file or directory is absent
    )


# ---------------------------------------------------------------------------
# Per-surface result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class HttpSurfaceResult:
    """Result from a single HTTP health endpoint probe."""

    url: str
    status: HealthStatus
    http_status_code: Optional[int] = None
    response_body: Optional[dict] = field(default=None)
    error: Optional[str] = None

    def is_healthy_enough(self) -> bool:
        """Return True when this surface does not block overall readiness.

        Rules:
        - UNREACHABLE or MISSING_ARTIFACT → False
        - READY or DEGRADED or NOT_READY → True  (degraded/not_ready are advisory)
        """
        return self.status not in (
            HealthStatus.UNREACHABLE,
            HealthStatus.MISSING_ARTIFACT,
        )


@dataclass
class LauncherArtifactResult:
    """Result from checking a single desktop-launcher on-disk artifact."""

    path: str
    status: HealthStatus
    detail: Optional[str] = None


# ---------------------------------------------------------------------------
# Platform-aware app-support root
# ---------------------------------------------------------------------------


def _codexify_app_support_root() -> Path:
    """Return the platform-specific Codexify Application Support root."""
    system = platform.system()
    if system == "Darwin":
        base = Path(os.path.expanduser("~/Library/Application Support"))
    elif system == "Windows":
        base = Path(
            os.environ.get(
                "LOCALAPPDATA", str(Path.home() / "AppData" / "Local")
            )
        )
    else:  # Linux and others
        base = Path(
            os.environ.get(
                "XDG_DATA_HOME", str(Path.home() / ".local" / "share")
            )
        )
    return base / "Codexify"


# ---------------------------------------------------------------------------
# HTTP surface probing
# ---------------------------------------------------------------------------


def _probe_http_surface(url: str, timeout: float = 5.0) -> HttpSurfaceResult:
    """Probe a single HTTP endpoint and classify its response."""
    if not _HAS_REQUESTS:
        return HttpSurfaceResult(
            url=url,
            status=HealthStatus.UNREACHABLE,
            error="requests library not available — install with: pip install requests",
        )

    try:
        response = requests.get(url, timeout=timeout)
        http_status_code = response.status_code

        # Try to parse JSON body
        try:
            body = response.json()
        except Exception:
            body = None

        # 5xx or network-level errors → unreachable
        if http_status_code >= 500:
            return HttpSurfaceResult(
                url=url,
                status=HealthStatus.UNREACHABLE,
                http_status_code=http_status_code,
                response_body=body,
                error=f"HTTP {http_status_code}",
            )

        # 4xx without a successful sub-range → treat as degraded/unreachable depending on which endpoint
        if http_status_code >= 400:
            return HttpSurfaceResult(
                url=url,
                status=HealthStatus.DEGRADED,
                http_status_code=http_status_code,
                response_body=body,
                error=f"HTTP {http_status_code}",
            )

        # Inspect body for semantic health indicators
        if body is not None:
            status_val = _classify_health_body(url, body)
            return HttpSurfaceResult(
                url=url,
                status=status_val,
                http_status_code=http_status_code,
                response_body=body,
            )

        # No body — treat 2xx as ready by default
        return HttpSurfaceResult(
            url=url,
            status=HealthStatus.READY,
            http_status_code=http_status_code,
        )

    except requests.exceptions.Timeout:
        return HttpSurfaceResult(
            url=url, status=HealthStatus.UNREACHABLE, error="connection timeout"
        )
    except requests.exceptions.ConnectionError as exc:
        return HttpSurfaceResult(
            url=url,
            status=HealthStatus.UNREACHABLE,
            error=f"connection error: {exc}",
        )
    except Exception as exc:  # noqa: BLE001
        return HttpSurfaceResult(
            url=url, status=HealthStatus.UNREACHABLE, error=str(exc)
        )


def _classify_health_body(url: str, body: dict) -> HealthStatus:
    """Classify the semantic health of an endpoint response body.

    This implements the bounded status vocabulary by inspecting known health fields.
    """
    # /health  — {"status": "ok", ...} or {"status": "degraded", ...}
    if "status" in body:
        val = str(body["status"]).lower()
        if val in ("ok", "ready", "healthy", "available"):
            return HealthStatus.READY
        if val in ("degraded", "warning"):
            return HealthStatus.DEGRADED
        if val in ("error", "unhealthy", "down"):
            return HealthStatus.UNREACHABLE
        if val in ("starting", "initializing", "not_ready", "booting"):
            return HealthStatus.NOT_READY

    # /health/chat — {"queue_health": "healthy", ...} or {"workers_alive": false, ...}
    if (
        "queue_health" in body
        or "workers_alive" in body
        or "chat_service" in body
    ):
        queue_val = str(body.get("queue_health", "")).lower()
        workers_val = body.get("workers_alive")
        chat_status = str(body.get("chat_service", "")).lower()

        if workers_val is False:
            return HealthStatus.DEGRADED
        if queue_val in ("healthy", "ok"):
            return HealthStatus.READY
        if queue_val in ("degraded", "warning"):
            return HealthStatus.DEGRADED
        if queue_val in ("unhealthy", "down"):
            return HealthStatus.UNREACHABLE
        if chat_status in ("ready", "ok"):
            return HealthStatus.READY
        if chat_status in ("degraded", "warning"):
            return HealthStatus.DEGRADED
        if chat_status in ("unavailable", "down"):
            return HealthStatus.UNREACHABLE

    # /api/health/llm — {"provider": "...", "provider_runtime": "...", ...}
    if "provider_runtime" in body or "provider_status" in body:
        prov_status = str(
            body.get("provider_runtime", body.get("provider_status", ""))
        ).lower()
        if prov_status in ("ready", "runtime_available"):
            return HealthStatus.READY
        if prov_status in ("model_warming", "warming"):
            return HealthStatus.NOT_READY
        if prov_status in ("degraded", "slow"):
            return HealthStatus.DEGRADED
        if prov_status in ("offline", "error", "unavailable"):
            return HealthStatus.UNREACHABLE

    # /api/health/retrieval — {"status": "ok", ...} or {"vector_health": ...}
    if "vector_health" in body or "retrieval_status" in body:
        vec_val = str(
            body.get("vector_health", body.get("retrieval_status", ""))
        ).lower()
        if vec_val in ("ok", "ready", "healthy", "available"):
            return HealthStatus.READY
        if vec_val in ("degraded", "warning", "limited"):
            return HealthStatus.DEGRADED
        if vec_val in ("unavailable", "down", "error"):
            return HealthStatus.UNREACHABLE

    # /api/llm/catalog — {"models": [...], ...}
    if "models" in body or "catalog" in body:
        return HealthStatus.READY

    # Generic fallback: if we got a 2xx with a body dict, call it ready
    return HealthStatus.READY


# ---------------------------------------------------------------------------
# Launcher artifact probing
# ---------------------------------------------------------------------------


def _probe_launcher_artifact(
    path: Path, is_file: bool = True
) -> LauncherArtifactResult:
    """Check for the presence (and basic readability) of a single launcher artifact."""
    try:
        if is_file:
            if path.is_file():
                # For JSON files, validate basic parseability
                if path.suffix == ".json":
                    try:
                        with open(path, encoding="utf-8") as fh:
                            json.load(fh)
                    except json.JSONDecodeError as exc:
                        return LauncherArtifactResult(
                            path=str(path),
                            status=HealthStatus.DEGRADED,
                            detail=f"present but not valid JSON: {exc}",
                        )
                return LauncherArtifactResult(
                    path=str(path), status=HealthStatus.READY, detail="present"
                )
            elif path.is_dir():
                return LauncherArtifactResult(
                    path=str(path),
                    status=HealthStatus.DEGRADED,
                    detail="expected file but found directory",
                )
            else:
                return LauncherArtifactResult(
                    path=str(path),
                    status=HealthStatus.MISSING_ARTIFACT,
                    detail="artifact not found",
                )
        else:
            # Directory marker
            if path.is_dir():
                return LauncherArtifactResult(
                    path=str(path),
                    status=HealthStatus.READY,
                    detail="directory present",
                )
            else:
                return LauncherArtifactResult(
                    path=str(path),
                    status=HealthStatus.MISSING_ARTIFACT,
                    detail="directory not found",
                )
    except PermissionError:
        return LauncherArtifactResult(
            path=str(path),
            status=HealthStatus.DEGRADED,
            detail="permission denied",
        )
    except OSError as exc:
        return LauncherArtifactResult(
            path=str(path),
            status=HealthStatus.DEGRADED,
            detail=f"OS error: {exc}",
        )


# ---------------------------------------------------------------------------
# Monitor
# ---------------------------------------------------------------------------


@dataclass
class MonitorSummary:
    """Aggregated result from a full monitor pass."""

    runtime: dict[str, HttpSurfaceResult]
    launcher_artifacts: dict[str, LauncherArtifactResult]
    overall_status: HealthStatus = HealthStatus.READY
    next_actions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        result = {
            "overall_status": self.overall_status.value,
            "runtime": {
                name: {
                    "url": r.url,
                    "status": r.status.value,
                    "http_status_code": r.http_status_code,
                    "error": r.error,
                }
                for name, r in self.runtime.items()
            },
            "launcher_artifacts": {
                name: {
                    "path": r.path,
                    "status": r.status.value,
                    "detail": r.detail,
                }
                for name, r in self.launcher_artifacts.items()
            },
            "next_actions": self.next_actions,
        }
        return result


class DesktopRuntimeMonitor:
    """Read-only operator monitor for Codexify runtime health surfaces."""

    # Canonical HTTP surfaces to probe
    DEFAULT_HTTP_SURFACES = [
        ("health", "/health"),
        ("health_chat", "/health/chat"),
        ("health_llm", "/api/health/llm"),
        ("health_retrieval", "/api/health/retrieval"),
        ("llm_catalog", "/api/llm/catalog?include=all"),
    ]

    # Canonical desktop-launcher artifact names and paths
    LAUNCHER_ARTIFACTS = [
        (".codexify-launcher-startup-state.json", True),
        (".codexify-runtime-manifest.json", True),
        (".codexify-packaged-runtime", False),
    ]

    def __init__(
        self,
        backend_base_url: str = "http://localhost:8888",
        http_timeout: float = 5.0,
        app_support_root: Optional[Path] = None,
    ):
        self.backend_base_url = backend_base_url.rstrip("/")
        self.http_timeout = http_timeout
        self.app_support_root = app_support_root or _codexify_app_support_root()

    def _http_url(self, path: str) -> str:
        return f"{self.backend_base_url}{path}"

    def probe_runtime_surfaces(self) -> dict[str, HttpSurfaceResult]:
        """Probe all configured HTTP health surfaces."""
        results: dict[str, HttpSurfaceResult] = {}
        for name, path in self.DEFAULT_HTTP_SURFACES:
            results[name] = _probe_http_surface(
                self._http_url(path), self.http_timeout
            )
        return results

    def probe_launcher_artifacts(self) -> dict[str, LauncherArtifactResult]:
        """Probe all configured desktop-launcher proof artifacts."""
        results: dict[str, LauncherArtifactResult] = {}
        for filename, is_file in self.LAUNCHER_ARTIFACTS:
            artifact_path = self.app_support_root / filename
            results[filename] = _probe_launcher_artifact(
                artifact_path, is_file=is_file
            )
        return results

    def _derive_next_actions(
        self,
        runtime: dict[str, HttpSurfaceResult],
        artifacts: dict[str, LauncherArtifactResult],
    ) -> list[str]:
        """Derive advisory next_action suggestions from current surface states.

        These are read-only hints. The monitor never auto-remediates.
        """
        actions: list[str] = []

        # Check runtime surfaces
        unreachable = [
            name
            for name, r in runtime.items()
            if r.status == HealthStatus.UNREACHABLE
        ]
        if unreachable:
            actions.append(
                f"Runtime surface(s) {unreachable} unreachable — verify the "
                "Docker Compose stack is running and the backend is accessible at "
                f"{self.backend_base_url}."
            )

        degraded_runtime = [
            name
            for name, r in runtime.items()
            if r.status in (HealthStatus.DEGRADED, HealthStatus.NOT_READY)
        ]
        if degraded_runtime:
            actions.append(
                f"Runtime surface(s) {degraded_runtime} returned degraded or not_ready "
                "status — check provider warmth, Redis connectivity, and worker heartbeats."
            )

        missing_artifacts = [
            name
            for name, r in artifacts.items()
            if r.status == HealthStatus.MISSING_ARTIFACT
        ]
        if missing_artifacts:
            actions.append(
                f"Launcher artifact(s) {missing_artifacts} not found under "
                f"{self.app_support_root} — verify desktop setup completed successfully "
                "and the Application Support directory is accessible."
            )

        degraded_artifacts = [
            name
            for name, r in artifacts.items()
            if r.status == HealthStatus.DEGRADED
        ]
        if degraded_artifacts:
            actions.append(
                f"Launcher artifact(s) {degraded_artifacts} present but degraded — "
                "check file permissions and JSON validity."
            )

        if not actions:
            actions.append(
                "All monitored surfaces are reachable and healthy. "
                "No immediate action required."
            )

        return actions

    def _derive_overall_status(
        self,
        runtime: dict[str, HttpSurfaceResult],
        artifacts: dict[str, LauncherArtifactResult],
    ) -> HealthStatus:
        """Derive an overall bounded status from all surface results.

        Priority order (highest wins):
          UNREACHABLE > MISSING_ARTIFACT > NOT_READY > DEGRADED > READY
        """
        worst = HealthStatus.READY
        priority = {
            HealthStatus.UNREACHABLE: 5,
            HealthStatus.MISSING_ARTIFACT: 4,
            HealthStatus.NOT_READY: 3,
            HealthStatus.DEGRADED: 2,
            HealthStatus.READY: 1,
        }

        for r in list(runtime.values()) + list(artifacts.values()):
            if priority.get(r.status, 0) > priority.get(worst, 0):
                worst = r.status

        return worst

    def run_once(self) -> MonitorSummary:
        """Run a single monitor pass and return the aggregated summary."""
        runtime = self.probe_runtime_surfaces()
        artifacts = self.probe_launcher_artifacts()
        overall = self._derive_overall_status(runtime, artifacts)
        next_actions = self._derive_next_actions(runtime, artifacts)
        return MonitorSummary(
            runtime=runtime,
            launcher_artifacts=artifacts,
            overall_status=overall,
            next_actions=next_actions,
        )


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def _format_human(summary: MonitorSummary) -> str:
    """Format summary as human-readable output."""
    lines = [
        "=== Codexify Runtime Monitor ===",
        "",
        f"Overall status: {summary.overall_status.value}",
        "",
        "-- Runtime HTTP surfaces --",
    ]
    for name, result in summary.runtime.items():
        icon = {
            HealthStatus.READY: "✓",
            HealthStatus.DEGRADED: "⚠",
            HealthStatus.NOT_READY: "○",
            HealthStatus.UNREACHABLE: "✗",
            HealthStatus.MISSING_ARTIFACT: "?",
        }.get(result.status, "?")
        lines.append(f"  {icon} [{result.status.value}] {name} → {result.url}")
        if result.error:
            lines.append(f"       error: {result.error}")
        elif result.http_status_code:
            lines.append(f"       HTTP {result.http_status_code}")

    lines.append("")
    lines.append("-- Desktop launcher artifacts --")
    for name, result in summary.launcher_artifacts.items():
        icon = {
            HealthStatus.READY: "✓",
            HealthStatus.DEGRADED: "⚠",
            HealthStatus.NOT_READY: "○",
            HealthStatus.UNREACHABLE: "✗",
            HealthStatus.MISSING_ARTIFACT: "?",
        }.get(result.status, "?")
        lines.append(f"  {icon} [{result.status.value}] {name}")
        if result.detail:
            lines.append(f"       {result.detail} ({result.path})")
        else:
            lines.append(f"       {result.path}")

    lines.append("")
    lines.append("-- Next actions (advisory only) --")
    for action in summary.next_actions:
        lines.append(f"  • {action}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="monitor_desktop_runtime.py",
        description="Read-only Codexify runtime and desktop-launcher monitor.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--once",
        action="store_true",
        help="Run one monitor pass and exit",
    )
    mode_group.add_argument(
        "--watch",
        action="store_true",
        help="Run monitor continuously until interrupted",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=15.0,
        help="Seconds between watch-mode passes (default: 15)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output instead of human-readable output",
    )
    parser.add_argument(
        "--backend-url",
        default=os.environ.get(
            "CODEXIFY_MONITOR_BACKEND_URL", "http://localhost:8888"
        ),
        help="Base URL for the Codexify backend (default: http://localhost:8888 or "
        "CODEXIFY_MONITOR_BACKEND_URL env var)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="HTTP request timeout in seconds (default: 5.0)",
    )
    return parser


def _exit_code_for_status(status: HealthStatus) -> int:
    """Map overall monitor status to process exit code."""
    if status == HealthStatus.READY:
        return 0
    if status in (HealthStatus.DEGRADED, HealthStatus.NOT_READY):
        return 1
    # UNREACHABLE or MISSING_ARTIFACT
    return 2


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    monitor = DesktopRuntimeMonitor(
        backend_base_url=args.backend_url,
        http_timeout=args.timeout,
    )

    if args.once:
        summary = monitor.run_once()
        if args.json:
            print(json.dumps(summary.as_dict(), indent=2))
        else:
            print(_format_human(summary))
        sys.exit(_exit_code_for_status(summary.overall_status))

    # --watch mode
    running = True

    def _handle_signal(signum, frame):  # type: ignore[unused-var]
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    while running:
        summary = monitor.run_once()
        if args.json:
            print(json.dumps(summary.as_dict(), indent=2))
        else:
            print(_format_human(summary))
        if not running:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
