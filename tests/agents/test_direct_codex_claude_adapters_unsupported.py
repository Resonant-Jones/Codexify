from __future__ import annotations

import pytest

from guardian.agents.adapters import ADAPTERS
from guardian.agents.adapters.claudecode import (
    UNSUPPORTED_DIRECT_CLAUDE_MESSAGE,
    ClaudeCodeAdapter,
)
from guardian.agents.adapters.codex import (
    UNSUPPORTED_DIRECT_CODEX_MESSAGE,
    CodexAdapter,
)


def test_direct_codex_adapter_is_not_registered() -> None:
    assert "codex" not in ADAPTERS


def test_direct_claude_adapter_is_not_registered() -> None:
    assert "claudecode" not in ADAPTERS


def test_direct_codex_adapter_construction_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="unsupported for Campaign Runner"):
        CodexAdapter()

    assert "Pi broker adapter" in UNSUPPORTED_DIRECT_CODEX_MESSAGE


def test_direct_claude_adapter_construction_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="unsupported for Campaign Runner"):
        ClaudeCodeAdapter()

    assert "Pi broker adapter" in UNSUPPORTED_DIRECT_CLAUDE_MESSAGE
