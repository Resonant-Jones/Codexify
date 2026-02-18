from __future__ import annotations

import subprocess
from typing import Any
from unittest.mock import patch

import pytest

from guardian.agents.adapters.base import AgentExecutionRequest
from guardian.agents.adapters.claudecode import ClaudeCodeAdapter
from guardian.agents.adapters.codex import CodexAdapter


@pytest.mark.parametrize(
    ("adapter", "patch_target", "summary"),
    [
        (
            CodexAdapter(),
            "guardian.agents.adapters.codex.subprocess.run",
            "Codex adapter execution timed out",
        ),
        (
            ClaudeCodeAdapter(),
            "guardian.agents.adapters.claudecode.subprocess.run",
            "ClaudeCode adapter execution timed out",
        ),
    ],
)
def test_cli_adapter_timeout_returns_error_envelope(
    adapter: Any,
    patch_target: str,
    summary: str,
) -> None:
    request = AgentExecutionRequest(
        prompt="return envelope", timeout_seconds=17
    )

    with patch(
        patch_target,
        side_effect=subprocess.TimeoutExpired(cmd=["agent-cli"], timeout=17),
    ):
        envelope = adapter.execute(request)

    assert envelope.status == "error"
    assert envelope.summary == summary
    assert envelope.errors == ["timeout_expired"]
    assert envelope.metrics["timeout_seconds"] == 17
    assert envelope.spec_alignment_ok is True
    assert envelope.schema_valid is False
