"""Whoosh'd managed sidecar provider for Codexify.

Detects, optionally launches, monitors, and safely stops a Whoosh'd
sidecar process.  Communicates with Whoosh'd exclusively over HTTP.

Ownership rules:
  - Already-running Whoosh'd is treated as external/user-managed.
  - Codexify-launched Whoosh'd is tracked by PID + session_id.
  - Codexify stops ONLY processes it started.
  - Session/PID mismatch revokes ownership.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import httpx

from guardian.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


# ── State enums ────────────────────────────────────────────────────────────


class WhooshdState(Enum):
    OFFLINE = "offline"
    STARTING = "starting"
    RUNTIME_AVAILABLE = "runtime_available"
    MODEL_WARMING = "model_warming"
    READY = "ready"
    GENERATING = "generating"
    DEGRADED = "degraded"
    ERROR = "error"


class Ownership(Enum):
    NONE = "none"
    EXTERNAL = "external"
    MANAGED = "managed"


# ── Status record ──────────────────────────────────────────────────────────


@dataclass
class WhooshdStatus:
    base_url: str
    state: WhooshdState = WhooshdState.OFFLINE
    ownership: Ownership = Ownership.NONE
    session_id: str = ""
    pid: int | None = None
    runtime_kinds: list[str] = field(default_factory=list)
    active_model: str = ""
    configured_model: str = ""
    models: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    detail: str = ""
    started_at: str = ""


# ── Sidecar manager ────────────────────────────────────────────────────────


class WhooshdSidecar:
    """Manages detection, launch, health polling, and shutdown of Whoosh'd."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._process: subprocess.Popen | None = None
        self._launched_pid: int | None = None
        self._launched_session_id: str = ""
        self._started_at: float = 0.0

    @property
    def base_url(self) -> str:
        host = self._settings.WHOOSHD_HOST
        port = self._settings.WHOOSHD_PORT
        return f"http://{host}:{port}"

    @property
    def is_managed_enabled(self) -> bool:
        return bool(self._settings.WHOOSHD_MANAGED)

    @property
    def is_whooshd_configured(self) -> bool:
        vendor = str(getattr(self._settings, "LOCAL_PROVIDER_VENDOR", "") or "").strip().lower()
        return vendor == "whooshd"

    # ── Detection ───────────────────────────────────────────────────────

    async def detect(self) -> WhooshdStatus:
        """Detect whether Whoosh'd is reachable and collect status."""
        status = WhooshdStatus(base_url=self.base_url)

        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try /health first.
            try:
                resp = await client.get(f"{self.base_url}/health")
                if resp.status_code != 200:
                    status.state = WhooshdState.ERROR
                    status.detail = f"/health returned {resp.status_code}"
                    return status
            except Exception:
                status.state = WhooshdState.OFFLINE
                status.detail = "Whoosh'd not reachable"
                return status

            # Try /health/runtime.
            try:
                resp = await client.get(f"{self.base_url}/health/runtime")
                if resp.status_code == 200:
                    body = resp.json()
                    session = body.get("session", {})
                    status.session_id = session.get("session_id", "")
                    status.pid = session.get("pid")
                    status.started_at = session.get("started_at", "")
                    status.runtime_kinds = session.get("registered_runtime_kinds", [])

                    runtimes = body.get("runtimes", {})
                    non_stub = {k: v for k, v in runtimes.items() if k != "stub"}
                    if non_stub:
                        for kind, rt in non_stub.items():
                            status.state = _map_runtime_state(rt.get("state", ""))
                            status.active_model = rt.get("active_model", "") or ""
                            status.configured_model = rt.get("configured_model", "") or ""
                            break
                    else:
                        # Only stub registered — process is alive but no real runtime loaded.
                        status.state = WhooshdState.RUNTIME_AVAILABLE
                        status.active_model = "stub-model"
            except Exception:
                pass

            # Try /v1/models.
            try:
                resp = await client.get(f"{self.base_url}/v1/models")
                if resp.status_code == 200:
                    status.models = [m["id"] for m in resp.json().get("data", [])]
            except Exception:
                pass

            # Try /api/tags.
            try:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    status.tags = [m["name"] for m in resp.json().get("models", [])]
            except Exception:
                pass

        return status

    # ── Ownership ───────────────────────────────────────────────────────

    def determine_ownership(self, status: WhooshdStatus) -> Ownership:
        """Determine whether the running Whoosh'd is ours.

        The process is considered reachable if /health returned 200,
        regardless of whether non-stub runtimes are registered.
        """
        # Process is unreachable (transport failure).
        if status.state == WhooshdState.OFFLINE and not status.session_id:
            return Ownership.NONE
        if self._launched_pid is not None and status.pid == self._launched_pid:
            if self._launched_session_id and status.session_id != self._launched_session_id:
                logger.warning("Whoosh'd session changed — revoking ownership")
                return Ownership.EXTERNAL
            return Ownership.MANAGED
        return Ownership.EXTERNAL

    # ── Launch ──────────────────────────────────────────────────────────

    async def launch(self) -> WhooshdStatus:
        """Launch Whoosh'd as a managed sidecar process.

        Returns the status after startup polling.
        """
        if not self.is_managed_enabled:
            raise RuntimeError("Whoosh'd managed mode is not enabled")
        if not self.is_whooshd_configured:
            raise RuntimeError("LOCAL_PROVIDER_VENDOR is not whooshd")

        # Check if already running.
        status = await self.detect()
        if status.state not in (WhooshdState.OFFLINE, WhooshdState.ERROR):
            status.ownership = Ownership.EXTERNAL
            return status

        # Build launch environment.
        env = os.environ.copy()
        env["WHOOSHD_MLX_ENABLED"] = "true"
        if self._settings.WHOOSHD_MODEL_REGISTRY_PATH:
            env["WHOOSHD_MODEL_REGISTRY_PATH"] = self._settings.WHOOSHD_MODEL_REGISTRY_PATH

        # Build command.
        cmd = self._settings.WHOOSHD_COMMAND.split()
        cmd.extend(["--host", self._settings.WHOOSHD_HOST])
        cmd.extend(["--port", str(self._settings.WHOOSHD_PORT)])

        cwd = self._settings.WHOOSHD_WORKING_DIR or os.getcwd()

        logger.info("whooshd_sidecar.launch cmd=%s cwd=%s", cmd, cwd)

        try:
            self._process = subprocess.Popen(
                cmd,
                env=env,
                cwd=cwd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            status = WhooshdStatus(base_url=self.base_url)
            status.state = WhooshdState.ERROR
            status.detail = f"Failed to launch Whoosh'd: {exc}"
            return status

        self._launched_pid = self._process.pid
        self._started_at = time.time()

        # Poll until ready.
        return await self._poll_ready()

    async def _poll_ready(self) -> WhooshdStatus:
        """Poll Whoosh'd health until ready or timeout."""
        deadline = time.time() + self._settings.WHOOSHD_STARTUP_TIMEOUT_SECONDS
        interval = self._settings.WHOOSHD_HEALTH_POLL_INTERVAL_SECONDS

        while time.time() < deadline:
            status = await self.detect()
            if status.state == WhooshdState.READY:
                self._launched_session_id = status.session_id
                status.ownership = Ownership.MANAGED
                return status
            if status.state == WhooshdState.ERROR:
                return status
            await asyncio.sleep(interval)

        status = await self.detect()
        status.detail = f"Startup timed out after {self._settings.WHOOSHD_STARTUP_TIMEOUT_SECONDS}s"
        return status

    # ── Shutdown ────────────────────────────────────────────────────────

    async def stop(self) -> bool:
        """Stop Whoosh'd only if Codexify launched it and ownership is still valid.

        Returns True if the process was stopped.
        """
        if self._process is None:
            return False

        # Re-verify ownership.
        status = await self.detect()
        ownership = self.determine_ownership(status)
        if ownership != Ownership.MANAGED:
            logger.warning("whooshd_sidecar.stop: ownership revoked, not stopping")
            return False

        pid = self._launched_pid
        if pid is None:
            return False

        logger.info("whooshd_sidecar.stop pid=%s", pid)
        try:
            os.kill(pid, signal.SIGTERM)
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.kill(pid, signal.SIGKILL)
                self._process.wait(timeout=5)
        except ProcessLookupError:
            pass
        except Exception as exc:
            logger.error("whooshd_sidecar.stop error: %s", exc)

        self._process = None
        self._launched_pid = None
        self._launched_session_id = ""
        return True

    # ── Status for provider truth ──────────────────────────────────────

    async def status_dict(self) -> dict:
        """Return a dict suitable for provider truth/health surfaces."""
        status = await self.detect()
        status.ownership = self.determine_ownership(status)
        return {
            "base_url": self.base_url,
            "state": status.state.value,
            "ownership": status.ownership.value,
            "managed_enabled": self.is_managed_enabled,
            "session_id": status.session_id,
            "pid": status.pid,
            "runtime_kinds": status.runtime_kinds,
            "active_model": status.active_model,
            "configured_model": status.configured_model,
            "models": status.models,
            "tags": status.tags,
            "detail": status.detail,
            "started_at": status.started_at,
        }


# ── Helpers ────────────────────────────────────────────────────────────────


def _map_runtime_state(whooshd_state: str) -> WhooshdState:
    """Map Whoosh'd runtime state strings to WhooshdState enum.

    Never maps warmup to offline.
    """
    state = str(whooshd_state or "").strip().lower()
    mapping = {
        "offline": WhooshdState.OFFLINE,
        "starting": WhooshdState.STARTING,
        "runtime_available": WhooshdState.RUNTIME_AVAILABLE,
        "model_warming": WhooshdState.MODEL_WARMING,
        "ready": WhooshdState.READY,
        "generating": WhooshdState.GENERATING,
        "degraded": WhooshdState.DEGRADED,
        "error": WhooshdState.ERROR,
    }
    return mapping.get(state, WhooshdState.DEGRADED)


# ── Module-level convenience ───────────────────────────────────────────────

_sidecar: WhooshdSidecar | None = None


def get_sidecar(settings: Settings | None = None) -> WhooshdSidecar:
    global _sidecar
    if _sidecar is None:
        _sidecar = WhooshdSidecar(settings)
    return _sidecar
