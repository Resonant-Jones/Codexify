"""Pi-powered Codex Runner adapter implementing AgentAdapter protocol."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from guardian.agents.adapters.base import (
    AgentAdapter,
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

    def _parse_result(
        self, result: subprocess.CompletedProcess[str]
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
                return AgentRunEnvelope(
                    status=data.get("status", "ok"),
                    summary=data.get(
                        "summary", data.get("text", "Task completed")
                    ),
                    artifacts=data.get("artifacts", []),
                    next_actions=data.get("next_actions", []),
                    errors=data.get("errors", []),
                    metrics=data.get("metrics", {}),
                )
            except json.JSONDecodeError:
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
            summary="Task completed with no output",
            artifacts=[],
            next_actions=[],
            errors=[],
            metrics={},
        )
