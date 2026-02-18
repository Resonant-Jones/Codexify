"""Codex CLI delegated adapter."""

from __future__ import annotations

import json
import os
import shlex
import subprocess

from .base import AgentExecutionRequest, AgentRunEnvelope


def _command_from_env() -> list[str]:
    raw = os.getenv("CODEX_ADAPTER_COMMAND", "codex exec").strip()
    return shlex.split(raw) if raw else ["codex", "exec"]


class CodexAdapter:
    name = "codex"

    def execute(self, request: AgentExecutionRequest) -> AgentRunEnvelope:
        cmd = [*_command_from_env(), request.prompt]
        proc = subprocess.run(
            cmd,
            cwd=request.cwd or None,
            capture_output=True,
            text=True,
            check=False,
            timeout=request.timeout_seconds,
        )
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        if proc.returncode != 0:
            return AgentRunEnvelope(
                status="error",
                summary="Codex adapter execution failed",
                artifacts=[],
                next_actions=[],
                errors=[stderr or f"exit={proc.returncode}"],
                metrics={"returncode": proc.returncode},
                spec_alignment_ok=True,
                schema_valid=False,
            )

        try:
            payload = json.loads(stdout)
            return AgentRunEnvelope.model_validate(payload)
        except Exception:
            return AgentRunEnvelope(
                status="error",
                summary="Codex adapter returned non-JSON output",
                artifacts=[],
                next_actions=[],
                errors=["invalid_json_envelope"],
                metrics={"stdout_preview": stdout[:240]},
                spec_alignment_ok=True,
                schema_valid=False,
            )
