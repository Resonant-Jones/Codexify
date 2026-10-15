"""Readiness checks for the invocation-scoped Guardian Pi coding worker.

Worker startup verifies only that the pinned Pi runtime can load. It does not
select a provider/model or inspect credential material; Guardian resolves and
authorizes those separately for each invocation.
"""

from __future__ import annotations

import json
import os
import shutil
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
        "adapter_initialization_failed",
    }
)

DEFAULT_WRAPPER_PATH = "/app/codex_runner/src/agent-wrapper.js"
DEFAULT_PI_PACKAGE_ROOT = (
    "/opt/codexify/pi-sdk/node_modules/@earendil-works/pi-coding-agent"
)
DEFAULT_PI_NODE_MODULES = "/opt/codexify/pi-sdk/node_modules"


@dataclass(frozen=True)
class PiReadinessCheck:
    name: str
    state: str
    reason: str | None = None


@dataclass(frozen=True)
class PiReadinessReport:
    status: str
    checks: tuple[PiReadinessCheck, ...]
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    harness_id: str | None = None
    harness_version: str | None = None
    credential_validity: str = "checked_by_guardian_per_invocation"
    schema_version: int = 2

    @property
    def can_consume_tasks(self) -> bool:
        return self.status != "blocked"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "can_consume_tasks": self.can_consume_tasks,
            "harness_id": self.harness_id,
            "harness_version": self.harness_version,
            "provider_model_authority": "invocation_scoped_guardian_binding",
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
            "Provider/model identity: resolved by Guardian for each invocation",
            "Credential validity: checked by Guardian at invocation dispatch",
        ]
        if self.harness_id:
            lines.append(f"Pi runtime: {self.harness_id} {self.harness_version or ''}".strip())
        for check in self.checks:
            suffix = f" ({check.reason})" if check.reason else ""
            lines.append(f"- {check.name}: {check.state}{suffix}")
        return "\n".join(lines)


AdapterProbe = Callable[[str, Path, Mapping[str, str]], Mapping[str, object]]


def _probe_environment(environment: Mapping[str, str]) -> dict[str, str]:
    """Pass runtime paths only; never forward model identity or credentials."""
    allowed = (
        "PATH",
        "LANG",
        "LC_ALL",
        "PI_CODING_AGENT_PACKAGE_ROOT",
        "PI_CODING_AGENT_NODE_MODULES",
    )
    return {key: environment[key] for key in allowed if environment.get(key)}


def _default_adapter_probe(
    node_executable: str,
    wrapper_path: Path,
    environment: Mapping[str, str],
) -> Mapping[str, object]:
    try:
        completed = subprocess.run(
            [node_executable, str(wrapper_path), "coding-worker-readiness"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
            env=_probe_environment(environment),
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


def evaluate_pi_readiness(
    *,
    environ: Mapping[str, str] | None = None,
    adapter_probe: AdapterProbe | None = None,
) -> PiReadinessReport:
    """Verify Pi runtime prerequisites without reading ambient auth state."""

    environment = dict(os.environ if environ is None else environ)
    probe_adapter = adapter_probe or _default_adapter_probe
    checks: list[PiReadinessCheck] = []
    reasons: list[str] = []

    def record(name: str, state: str, reason: str | None = None) -> None:
        checks.append(PiReadinessCheck(name=name, state=state, reason=reason))
        if reason:
            reasons.append(reason)

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
        node_modules_root / "@earendil-works/pi-ai/dist/index.js"
    ).is_file()
    record(
        "pi_sdk_runtime",
        "available" if sdk_available else "blocked",
        None if sdk_available else "pi_sdk_build_missing",
    )

    harness_id = None
    harness_version = None
    can_probe = bool(node_executable and wrapper_available and sdk_available)
    if can_probe:
        probe = probe_adapter(
            node_executable,
            wrapper_path,
            _probe_environment(environment),
        )
        if probe.get("adapter_initialized") is True and probe.get(
            "credential_authority"
        ) == "invocation_scoped":
            record("adapter_initialization", "available")
            harness_id = str(probe.get("harness_id") or "") or None
            harness_version = str(probe.get("harness_version") or "") or None
        else:
            record("adapter_initialization", "blocked", "adapter_initialization_failed")
    else:
        record("adapter_initialization", "not_checked")

    unique_reasons = tuple(dict.fromkeys(reasons))
    status = "blocked" if unique_reasons else "ready"
    return PiReadinessReport(
        status=status,
        checks=tuple(checks),
        reasons=unique_reasons,
        warnings=(),
        harness_id=harness_id,
        harness_version=harness_version,
    )
