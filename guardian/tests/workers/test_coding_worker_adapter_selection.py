from __future__ import annotations

from guardian.agents.adapters import ADAPTERS
from guardian.workers import coding_worker


def test_pi_aliases_resolve_to_pi_codex_runner() -> None:
    assert coding_worker._resolve_adapter_kind("") == "pi_codex_runner"
    assert coding_worker._resolve_adapter_kind("pi") == "pi_codex_runner"
    assert coding_worker._resolve_adapter_kind("pi_sdk") == "pi_codex_runner"
    assert (
        coding_worker._resolve_adapter_kind("pi_codex_runner")
        == "pi_codex_runner"
    )


def test_direct_adapter_kinds_are_marked_unsupported() -> None:
    assert coding_worker._is_unsupported_direct_adapter_kind("codex") is True
    assert (
        coding_worker._is_unsupported_direct_adapter_kind("claudecode")
        is True
    )
    assert coding_worker._is_unsupported_direct_adapter_kind("pi") is False


def test_pi_lane_remains_registered() -> None:
    assert "pi" in ADAPTERS
    assert "pi_codex_runner" in ADAPTERS


def test_direct_adapter_kinds_are_not_registered() -> None:
    assert "codex" not in ADAPTERS
    assert "claudecode" not in ADAPTERS
