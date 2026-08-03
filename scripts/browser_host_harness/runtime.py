"""Harness runtime: start/stop servers, write manifests, manage credentials.

Orchestrates the three loopback servers (Origin A, Origin B, Guardian stub)
and writes the safe runtime manifest and separate credential file.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .fixture_server import FixtureServer
from .fixtures import FIXTURE_VERSION, OriginRole
from .guardian_stub import GUARDIAN_STUB_VERSION, GuardianStub

HARNESS_VERSION = "0.1.0"

_SAFE_LOG_FIELDS: frozenset[str] = frozenset(
    {
        "runId",
        "component",
        "origin_role",
        "route",
        "status",
        "receipt_id",
        "failure_code",
        "content_length",
        "content_hash",
        "timestamp",
    }
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_log_message(**kwargs: Any) -> str:
    """Build a safe structured log message, dropping unsafe fields."""
    safe: dict[str, Any] = {}
    for k, v in kwargs.items():
        if k in _SAFE_LOG_FIELDS:
            safe[k] = v
    safe["timestamp"] = _iso_now()
    return json.dumps(safe, sort_keys=True)


def safe_logger(**kwargs: Any) -> None:
    """Write a safe structured log line to stderr."""
    print(_clean_log_message(**kwargs), file=sys.stderr)


class HarnessRuntime:
    """Manages the three-server Browser Host proof harness."""

    def __init__(self, runtime_dir: Path):
        self.runtime_dir = runtime_dir
        self.run_id: str = f"harness-{uuid.uuid4().hex[:8]}"
        self._started_at: str = ""
        self._origin_a: FixtureServer | None = None
        self._origin_b: FixtureServer | None = None
        self._guardian_stub: GuardianStub | None = None
        self._credential_file: Path | None = None
        self._servers_started: bool = False

    @property
    def origin_a_url(self) -> str:
        if self._origin_a:
            return self._origin_a.base_url
        return ""

    @property
    def origin_b_url(self) -> str:
        if self._origin_b:
            return self._origin_b.base_url
        return ""

    @property
    def guardian_url(self) -> str:
        if self._guardian_stub:
            return self._guardian_stub.base_url
        return ""

    def start(self) -> dict:
        """Start all three servers and write runtime artifacts."""
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self._started_at = _iso_now()

        # Create runtime directory
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        # Create sentinel credential FIRST so stub and file agree
        sentinel = _make_sentinel_credential()
        self._credential_file = self.runtime_dir / "guardian-sentinel.txt"
        _write_credential_file(self._credential_file, sentinel)

        # Start Guardian stub with the correct sentinel
        self._guardian_stub = GuardianStub(
            harness_version=HARNESS_VERSION,
            safe_logger=safe_logger,
        )
        # Override the auto-generated sentinel with ours
        self._guardian_stub._sentinel = sentinel
        self._guardian_stub.start()
        safe_logger(
            component="guardian_stub",
            route="startup",
            status="started",
            port=str(self._guardian_stub.port),
        )

        # Start Origin B first (so Origin A can reference it)
        self._origin_b = FixtureServer(OriginRole.ORIGIN_B, safe_logger=safe_logger)
        self._origin_b.start()
        safe_logger(
            component="fixture_server",
            origin_role="origin_b",
            status="started",
            port=str(self._origin_b.port),
        )

        # Start Origin A
        self._origin_a = FixtureServer(OriginRole.ORIGIN_A, safe_logger=safe_logger)
        self._origin_a.start(origin_b_base=self._origin_b.base_url)
        safe_logger(
            component="fixture_server",
            origin_role="origin_a",
            status="started",
            port=str(self._origin_a.port),
        )

        self._servers_started = True

        # Write manifest
        manifest = self._build_manifest(sentinel)
        manifest_path = self.runtime_dir / "runtime-manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        return manifest

    def stop(self) -> None:
        """Stop all servers and remove the credential file."""
        errors: list[str] = []

        if self._origin_a:
            try:
                self._origin_a.stop()
                safe_logger(component="fixture_server", origin_role="origin_a", status="stopped")
            except Exception as e:
                errors.append(f"origin_a stop: {e}")

        if self._origin_b:
            try:
                self._origin_b.stop()
                safe_logger(component="fixture_server", origin_role="origin_b", status="stopped")
            except Exception as e:
                errors.append(f"origin_b stop: {e}")

        if self._guardian_stub:
            try:
                self._guardian_stub.stop()
                safe_logger(component="guardian_stub", status="stopped")
            except Exception as e:
                errors.append(f"guardian_stub stop: {e}")

        # Remove credential file
        if self._credential_file and self._credential_file.exists():
            try:
                self._credential_file.unlink()
                safe_logger(component="runtime", status="credential_removed")
            except Exception as e:
                errors.append(f"credential removal: {e}")

        self._servers_started = False

        if errors:
            safe_logger(component="runtime", status="shutdown_errors", detail="; ".join(errors))

    def is_running(self) -> bool:
        return self._servers_started and all(
            s is not None and s.is_running()
            for s in [self._origin_a, self._origin_b, self._guardian_stub]
        )

    def verify_ports_closed(self) -> bool:
        """Verify no harness server port is still bound."""
        import socket

        ports = []
        for s in [self._origin_a, self._origin_b, self._guardian_stub]:
            if s is not None and s.port > 0:
                ports.append(s.port)

        for port in ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.5)
                    result = sock.connect_ex(("127.0.0.1", port))
                    if result == 0:
                        safe_logger(
                            component="runtime",
                            status="port_still_open",
                            port=str(port),
                        )
                        return False
            except Exception:
                pass
        return True

    def _build_manifest(self, sentinel: str) -> dict:
        return {
            "runId": self.run_id,
            "harnessVersion": HARNESS_VERSION,
            "fixtureVersion": FIXTURE_VERSION,
            "guardianStubVersion": GUARDIAN_STUB_VERSION,
            "originAUrl": self.origin_a_url,
            "originBUrl": self.origin_b_url,
            "guardianBaseUrl": self.guardian_url,
            "fixtureManifestUrl": f"{self.origin_a_url}/manifest.json",
            "startTimestamp": self._started_at,
            "runtimeDirectory": str(self.runtime_dir),
            "credentialFilePath": str(self._credential_file),
            "syntheticThreadId": f"synthetic-thread-{uuid.uuid4().hex[:8]}",
            "syntheticRequestId": f"synthetic-req-{uuid.uuid4().hex[:8]}",
        }


def _make_sentinel_credential() -> str:
    return f"CODEXIFY-HARNESS-SENTINEL-{uuid.uuid4().hex}-NOT-A-REAL-CREDENTIAL"


def _write_credential_file(path: Path, sentinel: str) -> None:
    """Write the sentinel credential with restrictive permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(sentinel + "\n", encoding="utf-8")

    # Restrict permissions on Unix
    if os.name != "nt":
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass  # best-effort


def read_credential(path: Path) -> str:
    """Read the sentinel credential from its file."""
    return path.read_text(encoding="utf-8").strip()
