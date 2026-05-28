from __future__ import annotations

import pytest

from guardian.agents.adapters import ADAPTERS
from guardian.agents.adapters.claudecode import ClaudeCodeAdapter
from guardian.agents.adapters.codex import CodexAdapter


def test_adapter_registry_exposes_only_pi_lane() -> None:
    assert "pi" in ADAPTERS
    assert "pi_codex_runner" in ADAPTERS
    assert "codex" not in ADAPTERS
    assert "claudecode" not in ADAPTERS


@pytest.mark.parametrize(
    ("adapter_cls", "message_fragment"),
    [
        (CodexAdapter, "Direct Codex CLI execution is unsupported"),
        (
            ClaudeCodeAdapter,
            "Direct Claude/Claude Code CLI execution is unsupported",
        ),
    ],
)
def test_direct_cli_adapters_fail_closed(
    adapter_cls: type[object],
    message_fragment: str,
) -> None:
    with pytest.raises(RuntimeError, match=message_fragment):
        adapter_cls()
