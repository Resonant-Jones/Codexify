import pytest

from guardian.agents.adapters.claudecode import ClaudeCodeAdapter
from guardian.agents.adapters.codex import CodexAdapter


@pytest.mark.parametrize(
    ("adapter_factory", "expected_message"),
    [
        (
            CodexAdapter,
            "Direct Codex CLI execution is unsupported for Campaign Runner.",
        ),
        (
            ClaudeCodeAdapter,
            "Direct Claude / Claude Code CLI execution is unsupported for Campaign Runner.",
        ),
    ],
)
def test_direct_cli_adapters_are_deprecated_compatibility_stubs(
    adapter_factory,
    expected_message: str,
) -> None:
    with pytest.raises(RuntimeError, match=expected_message):
        adapter_factory()
