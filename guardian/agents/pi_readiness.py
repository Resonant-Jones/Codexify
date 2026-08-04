"""Canonical readiness contract for the Guardian Pi coding-worker lane.

This module inspects prerequisites and asks the Node wrapper to perform a
non-executing SDK/model/auth initialization. It never submits a prompt and
never includes credential values or subprocess error text in its report.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Mapping

PI_READINESS_STATES = frozenset({"ready", "blocked", "degraded"})
PI_READINESS_REASONS = frozenset(
    {
        "node_missing",
        "wrapper_missing",
        "pi_sdk_build_missing",
        "worker_home_unavailable",
        "worker_home_read_only",
        "pi_auth_missing",
        "pi_auth_unreadable",
        "pi_auth_permissions_open",
        "provider_unresolved",
        "provider_credential_missing",
        "adapter_initialization_failed",
    }
)

DEFAULT_WRAPPER_PATH = "/app/codex_runner/src/agent-wrapper.js"
DEFAULT_PI_PACKAGE_ROOT = (
    "/opt/codexify/pi-sdk/node_modules/@mariozechner/pi-coding-agent"
)
DEFAULT_PI_NODE_MODULES = "/opt/codexify/pi-sdk/node_modules"
DEFAULT_PI_PROVIDER = "anthropic"
DEFAULT_PI_MODEL = "claude-sonnet-4-20250514"


@dataclass(frozen=True)
class PiReadinessCheck:
    name: str
    state: str
    reason: str | None = None


@dataclass(frozen=True)
class PiReadinessReport:
    status: str
    effective_provider: str
    effective_model: str
    checks: tuple[PiReadinessCheck, ...]
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    credential_validity: str = "unproven"
    schema_version: int = 1

    @property
    def can_consume_tasks(self) -> bool:
        return self.status != "blocked"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "can_consume_tasks": self.can_consume_tasks,
            "effective_provider": self.effective_provider,
            "effective_model": self.effective_model,
            "credential_validity": self.credential_validity,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "checks": [asdict(check) for check in self.checks],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def to_human(self) -> str:
        lines = [
            f"Pi coding-worker readiness: {self.status}",
            f"Effective provider: {self.effective_provider}",
            f"Effective model: {self.effective_model}",
            "Credential validity: unproven (presence only)",
        ]
        for check in self.checks:
            suffix = f" ({check.reason})" if check.reason else ""
            lines.append(f"- {check.name}: {check.state}{suffix}")
        return "\n".join(lines)


AdapterProbe = Callable[[str, Path, Mapping[str, str]], Mapping[str, object]]


def _default_adapter_probe(
    node_executable: str,
    wrapper_path: Path,
    environment: Mapping[str, str],
) -> Mapping[str, object]:
    try:
        completed = subprocess.run(
            [node_executable, str(wrapper_path), "readiness"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
            env=dict(environment),
        )
        if completed.returncode != 0:
            return {"adapter_initialized": False}
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            return {"adapter_initialized": False}
        payload = json.loads(lines[-1])
        if not isinstance(payload, dict):
            return {"adapter_initialized": False}
        return payload
    except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError):
        return {"adapter_initialized": False}


def _auth_file_state(path: Path) -> str:
    if not path.is_file():
        return "missing"
    try:
        with path.open("rb") as handle:
            handle.read(1)
    except OSError:
        return "unreadable"
    return "present"


def evaluate_pi_readiness(
    *,
    environ: Mapping[str, str] | None = None,
    adapter_probe: AdapterProbe | None = None,
) -> PiReadinessReport:
    """Return the complete, secret-free Pi prerequisite posture."""

    environment = dict(os.environ if environ is None else environ)
    probe_adapter = adapter_probe or _default_adapter_probe
    checks: list[PiReadinessCheck] = []
    reasons: list[str] = []
    warnings: list[str] = []

    def record(
        name: str,
        state: str,
        reason: str | None = None,
        *,
        warning: bool = False,
    ) -> None:
        checks.append(PiReadinessCheck(name=name, state=state, reason=reason))
        if reason:
            (warnings if warning else reasons).append(reason)

    node_executable = shutil.which("node", path=environment.get("PATH"))
    record(
        "node_executable",
        "available" if node_executable else "blocked",
        None if node_executable else "node_missing",
    )

    wrapper_path = Path(environment.get("PI_WRAPPER_PATH", DEFAULT_WRAPPER_PATH))
    wrapper_available = wrapper_path.is_file()
    record(
        "guardian_pi_wrapper",
        "available" if wrapper_available else "blocked",
        None if wrapper_available else "wrapper_missing",
    )

    package_root = Path(
        environment.get("PI_CODING_AGENT_PACKAGE_ROOT", DEFAULT_PI_PACKAGE_ROOT)
    )
    node_modules_root = Path(
        environment.get("PI_CODING_AGENT_NODE_MODULES", DEFAULT_PI_NODE_MODULES)
    )
    sdk_available = (package_root / "dist/index.js").is_file() and (
        node_modules_root / "@mariozechner/pi-ai/dist/index.js"
    ).is_file()
    record(
        "pi_sdk_runtime",
        "available" if sdk_available else "blocked",
        None if sdk_available else "pi_sdk_build_missing",
    )

    home_value = environment.get("HOME", "").strip()
    worker_home = Path(home_value) if home_value else None
    home_usable = bool(
        worker_home
        and worker_home.is_dir()
        and os.access(worker_home, os.R_OK | os.X_OK)
    )
    home_writable = bool(home_usable and os.access(worker_home, os.W_OK))
    if not home_usable:
        record("worker_home", "blocked", "worker_home_unavailable")
    elif not home_writable:
        record("worker_home", "blocked", "worker_home_read_only")
    else:
        record("worker_home", "available")

    auth_path = (
        worker_home / ".pi/agent/auth.json" if worker_home else Path("/nonexistent")
    )
    auth_state = _auth_file_state(auth_path) if home_usable else "missing"
    if auth_state == "missing":
        record("pi_auth_material", "blocked", "pi_auth_missing")
    elif auth_state == "unreadable":
        record("pi_auth_material", "blocked", "pi_auth_unreadable")
    else:
        record("pi_auth_material", "available")

    if auth_state == "present":
        permissions_open = bool(stat.S_IMODE(auth_path.stat().st_mode) & 0o077)
        record(
            "pi_auth_permissions",
            "degraded" if permissions_open else "restricted",
            "pi_auth_permissions_open" if permissions_open else None,
            warning=permissions_open,
        )
    else:
        record("pi_auth_permissions", "not_checked")

    effective_provider = environment.get("PI_PROVIDER", DEFAULT_PI_PROVIDER).strip()
    effective_model = environment.get("PI_MODEL", DEFAULT_PI_MODEL).strip()
    provider_configured = bool(effective_provider and effective_model)
    provider_check_index = len(checks)
    if not provider_configured:
        record("effective_provider", "blocked", "provider_unresolved")
    else:
        record("effective_provider", "configured")

    can_probe = bool(
        node_executable
        and wrapper_available
        and sdk_available
        and home_writable
        and auth_state == "present"
        and provider_configured
    )
    if can_probe:
        probe = probe_adapter(node_executable, wrapper_path, environment)
        adapter_initialized = probe.get("adapter_initialized") is True
        if not adapter_initialized:
            record("adapter_initialization", "blocked", "adapter_initialization_failed")
            record("provider_credential", "not_checked")
        else:
            record("adapter_initialization", "available")
            provider_resolved = probe.get("provider_resolved") is True
            if not provider_resolved:
                if "provider_unresolved" not in reasons:
                    reasons.append("provider_unresolved")
                checks[provider_check_index] = PiReadinessCheck(
                    name="effective_provider",
                    state="blocked",
                    reason="provider_unresolved",
                )
                record("provider_credential", "not_checked")
            else:
                effective_provider = str(
                    probe.get("effective_provider") or effective_provider
                )
                effective_model = str(probe.get("effective_model") or effective_model)
                credential_available = (
                    probe.get("provider_credential_available") is True
                )
                record(
                    "provider_credential",
                    "available" if credential_available else "blocked",
                    None if credential_available else "provider_credential_missing",
                )
    else:
        record("adapter_initialization", "not_checked")
        record("provider_credential", "not_checked")

    unique_reasons = tuple(dict.fromkeys(reasons))
    unique_warnings = tuple(dict.fromkeys(warnings))
    status = (
        "blocked" if unique_reasons else ("degraded" if unique_warnings else "ready")
    )
    return PiReadinessReport(
        status=status,
        effective_provider=effective_provider or "unresolved",
        effective_model=effective_model or "unresolved",
        checks=tuple(checks),
        reasons=unique_reasons,
        warnings=unique_warnings,
    )
