from __future__ import annotations

from guardian.protocol_tokens import ErrorCode
from guardian.workers import coding_worker


def test_pi_aliases_resolve_to_pi_broker_adapter() -> None:
    for raw_value in ("pi", "pi_sdk", "pi_codex_runner", "", None):
        resolution = coding_worker._resolve_adapter_dispatch(raw_value)
        assert resolution.supported is True
        assert resolution.resolved_kind == "pi_codex_runner"


def test_direct_codex_adapter_kind_fails_closed() -> None:
    resolution = coding_worker._resolve_adapter_dispatch("codex")
    assert resolution.supported is False
    assert resolution.requested_kind == "codex"
    assert resolution.error_code == ErrorCode.CODING_ADAPTER_UNSUPPORTED.value
    assert "unsupported for Campaign Runner" in (resolution.error_message or "")


def test_direct_claudecode_adapter_kind_fails_closed() -> None:
    resolution = coding_worker._resolve_adapter_dispatch("claudecode")
    assert resolution.supported is False
    assert resolution.requested_kind == "claudecode"
    assert resolution.error_code == ErrorCode.CODING_ADAPTER_UNSUPPORTED.value
    assert "Pi broker adapter" in (resolution.error_message or "")
