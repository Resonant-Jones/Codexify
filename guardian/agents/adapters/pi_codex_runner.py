"""Pi-powered Codex Runner adapter implementing AgentAdapter protocol."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from guardian.agents.adapters.base import (
    AgentAdapter,
    AgentExecutionIdentity,
    AgentExecutionRequest,
    AgentRunEnvelope,
)


def _get_pi_wrapper_path() -> Path:
    """Get absolute path to Pi agent wrapper."""
    # Go up: pi_codex_runner.py -> adapters -> agents -> guardian -> repo_root
    repo_root = Path(__file__).parent.parent.parent.parent
    return repo_root / "codex_runner" / "src" / "agent-wrapper.js"


class PiCodexRunnerAdapter:
    """Adapter that invokes Codex Runner through the Pi agent wrapper.

    Implements AgentAdapter protocol for Guardian orchestration.
    Uses the Pi SDK wrapper to execute tasks via the configured model.
    `pi_codex_runner` is a legacy-compatible adapter name and does not mean
    direct Codex CLI execution.
    """

    name = "pi_codex_runner"

    def execute(self, request: AgentExecutionRequest) -> AgentRunEnvelope:
        """Execute a coding task through Pi agent wrapper.

        Args:
            request: AgentExecutionRequest with prompt and execution context

        Returns:
            AgentRunEnvelope with execution results
        """
        wrapper_path = _get_pi_wrapper_path()

        # Build execution environment
        env = os.environ.copy()

        # Set model and thinking from environment or defaults
        env["PI_MODEL"] = env.get("PI_MODEL", "claude-sonnet-4-20250514")
        env["PI_THINKING"] = env.get("PI_THINKING", "medium")

        # Build the command
        cmd = ["node", str(wrapper_path), "task", request.prompt]

        try:
            result = subprocess.run(
                cmd,
                cwd=request.cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
            )
            return self._parse_result(result)

        except subprocess.TimeoutExpired:
            return AgentRunEnvelope(
                status="error",
                summary=f"Execution timed out after {request.timeout_seconds}s",
                artifacts=[],
                next_actions=[],
                errors=["timeout_expired"],
                metrics={"timeout_seconds": request.timeout_seconds},
            )
        except FileNotFoundError as exc:
            return AgentRunEnvelope(
                status="error",
                summary="Pi agent wrapper not found (Node.js or wrapper.js missing)",
                artifacts=[],
                next_actions=[],
                errors=["pi_wrapper_not_found", str(exc)],
                metrics={},
            )

    def execute_authorized(
        self,
        request: AgentExecutionRequest,
        identity: AgentExecutionIdentity,
        *,
        read_only: bool,
    ) -> AgentRunEnvelope:
        """Execute exactly one Guardian-authorized Pi task.

        This opt-in path never falls back to the legacy provider/model defaults.
        Its local subprocess environment is the only configuration surface it
        changes; global process environment remains untouched.
        """
        if not all(
            (
                identity.provider_id,
                identity.model_id,
                identity.harness_id,
                identity.harness_version,
            )
        ):
            return AgentRunEnvelope(
                status="error",
                summary="Guardian-authorized Pi identity is incomplete",
                errors=["authorized_identity_missing"],
            )

        wrapper_path = _get_pi_wrapper_path()
        env = os.environ.copy()
        env.update(
            {
                "PI_PROVIDER": identity.provider_id,
                "PI_MODEL": identity.model_id,
                "PI_GUARDIAN_AUTHORIZED": "1",
                "PI_GUARDIAN_HARNESS_ID": identity.harness_id,
                "PI_GUARDIAN_HARNESS_VERSION": identity.harness_version,
                "PI_DISABLE_TOOLS": "1" if read_only else "0",
            }
        )
        cmd = ["node", str(wrapper_path), "guardian-authorized-task", request.prompt]

        try:
            result = subprocess.run(
                cmd,
                cwd=request.cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
            )
            return self._parse_result(result, require_runtime_identity=True)
        except subprocess.TimeoutExpired:
            return AgentRunEnvelope(
                status="error",
                summary=f"Execution timed out after {request.timeout_seconds}s",
                errors=["timeout_expired"],
                metrics={"timeout_seconds": request.timeout_seconds},
            )
        except FileNotFoundError:
            return AgentRunEnvelope(
                status="error",
                summary="Pi agent wrapper not found",
                errors=["pi_wrapper_not_found"],
            )

    def _parse_result(
        self,
        result: subprocess.CompletedProcess[str],
        *,
        require_runtime_identity: bool = False,
    ) -> AgentRunEnvelope:
        """Parse subprocess result into AgentRunEnvelope."""
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        if result.returncode != 0:
            return AgentRunEnvelope(
                status="error",
                summary="Pi agent execution failed",
                artifacts=[],
                next_actions=[],
                errors=[stderr or f"exit_code={result.returncode}"],
                metrics={"returncode": result.returncode},
            )

        if stdout:
            try:
                data = json.loads(stdout)
                runtime_identity = data.get("actual_runtime_identity")
                if require_runtime_identity and not isinstance(runtime_identity, dict):
                    return AgentRunEnvelope(
                        status="error",
                        summary="Pi wrapper omitted runtime identity attestation",
                        errors=["actual_identity_missing"],
                    )
                return AgentRunEnvelope(
                    status=data.get("status", "ok"),
                    summary=data.get(
                        "summary", data.get("text", "Task completed")
                    ),
                    artifacts=data.get("artifacts", []),
                    next_actions=data.get("next_actions", []),
                    errors=data.get("errors", []),
                    metrics=data.get("metrics", {}),
                    actual_provider_id=(
                        runtime_identity.get("actual_provider_id")
                        if isinstance(runtime_identity, dict)
                        else None
                    ),
                    actual_model_id=(
                        runtime_identity.get("actual_model_id")
                        if isinstance(runtime_identity, dict)
                        else None
                    ),
                    actual_harness_id=(
                        runtime_identity.get("actual_harness_id")
                        if isinstance(runtime_identity, dict)
                        else None
                    ),
                    actual_harness_version=(
                        runtime_identity.get("actual_harness_version")
                        if isinstance(runtime_identity, dict)
                        else None
                    ),
                )
            except json.JSONDecodeError:
                if require_runtime_identity:
                    return AgentRunEnvelope(
                        status="error",
                        summary="Pi wrapper returned a non-attested result",
                        errors=["actual_identity_missing"],
                    )
                # Non-JSON output - wrap as text summary
                return AgentRunEnvelope(
                    status="ok",
                    summary=stdout[:500] if stdout else "Task completed",
                    artifacts=[],
                    next_actions=[],
                    errors=[],
                    metrics={},
                )

        return AgentRunEnvelope(
            status="ok",
            summary=(
                "Pi wrapper omitted runtime identity attestation"
                if require_runtime_identity
                else "Task completed with no output"
            ),
            artifacts=[],
            next_actions=[],
            errors=["actual_identity_missing"] if require_runtime_identity else [],
            metrics={},
        )
