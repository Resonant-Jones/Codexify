"""Pi-powered broker adapter for Campaign Runner and coding-worker execution."""

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


def _get_backend_version() -> str:
    package_path = (
        Path(__file__).parent.parent.parent.parent
        / "codex_runner"
        / "package.json"
    )
    try:
        payload = json.loads(package_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return "unknown"
    return str(payload.get("version") or "unknown")


class PiCodexRunnerAdapter:
    """Adapter that invokes Codex Runner through the Pi broker wrapper.

    Implements AgentAdapter protocol for Guardian orchestration.
    The legacy-compatible adapter name remains `pi_codex_runner`, but this is
    a Pi broker seam and must not be interpreted as direct Codex CLI execution.
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
        env["CAMPAIGN_RUNNER_PROVIDER_ADAPTER"] = "pi"
        env["CAMPAIGN_RUNNER_PI_ROUTE"] = env.get(
            "CAMPAIGN_RUNNER_PI_ROUTE", "default"
        )
        env["CAMPAIGN_RUNNER_REQUIRE_BACKEND_RECEIPT"] = env.get(
            "CAMPAIGN_RUNNER_REQUIRE_BACKEND_RECEIPT", "true"
        )
        env["PI_PROVIDER"] = env.get("PI_PROVIDER", "anthropic")
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
            return self._parse_result(result, env)

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
        self,
        result: subprocess.CompletedProcess[str],
        env: dict[str, str],
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
                    artifacts=[
                        *data.get("artifacts", []),
                        {
                            "kind": "backend_receipt",
                            "backend_receipt": {
                                "backend_provider": "pi",
                                "backend_version": _get_backend_version(),
                                "pi_route": env.get(
                                    "CAMPAIGN_RUNNER_PI_ROUTE", "default"
                                ),
                                "resolved_provider": env.get(
                                    "PI_PROVIDER", "anthropic"
                                ),
                                "resolved_model": env.get(
                                    "PI_MODEL",
                                    "claude-sonnet-4-20250514",
                                ),
                                "schema_mode": "adapter_json_payload",
                                "execution_mode": "task",
                                "dependency_mode": "brokered",
                                "passes": 1,
                                "fallback_chain": [],
                                "retry_count": 0,
                                "error_code": None,
                            },
                        },
                    ],
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
